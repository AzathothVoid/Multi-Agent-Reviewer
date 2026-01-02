from rq.job import Job
from rq import get_current_job
from ..config import settings
from redis import Redis
from pydantic import BaseModel, Field, SecretStr
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Any, Dict, List, Optional, Any
from typing import cast
from langchain_core.output_parsers import PydanticOutputParser
import coloredlogs
import logging, re, json

redis = Redis.from_url(settings.redis_url)

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)


class Suggestion(BaseModel):
    id: str
    file: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    patch: str
    auto_fixable: bool = False
    confidence: float = Field(..., ge=0.0, le=1.0)
    explain: str


class LLMResponse(BaseModel):
    issues: List[Dict[str, Any]] = []
    suggestions: List[Suggestion] = []


PROMPT = """You are a concise code reviewer. Return only JSON that matches the format instructions.

        PR_TITLE:
        {pr_title}

        CHANGED_HUNKS:
        {changed_hunks}

        STATIC_SUMMARY:
        {static_summary}

        INSTRUCTIONS:
        {instructions}
"""

prompt_template = PromptTemplate(
    template=PROMPT,
    input_variables=[
        "pr_title",
        "changed_hunks",
        "static_summary",
        "instructions",
    ],
)

parser = PydanticOutputParser(pydantic_object=LLMResponse)


def _extract_json_from_exception(exc: Exception) -> Optional[Dict[str, Any]]:
    resp = getattr(exc, "response", None) or getattr(exc, "resp", None)
    if resp is not None:
        try:
            if hasattr(resp, "json"):
                payload = resp.json()
            else:
                payload = dict(resp)
            fg = None
            if isinstance(payload, dict):
                fg = payload.get("error", {}).get("failed_generation") or payload.get(
                    "failed_generation"
                )
            if isinstance(fg, str):
                try:
                    return json.loads(fg)
                except Exception:
                    pass
            elif isinstance(fg, dict):
                return fg
        except Exception:
            pass

    s = str(exc)

    idx = s.find("failed_generation")
    if idx == -1:
        m = re.search(r'"failed_generation"\s*:\s*', s)
        if m:
            idx = m.start()
    if idx == -1:
        return None

    start = s.find("{", idx)
    if start == -1:
        return None

    depth = 0
    end = None
    i = start
    L = len(s)
    while i < L:
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1

    if end is None:
        return None

    candidate = s[start:end]

    try:
        return json.loads(candidate)
    except Exception:
        try:
            candidate2 = candidate.replace("'", '"')
            return json.loads(candidate2)
        except Exception:
            return None


def _make_llm():
    # Create and return the LLM instance. Allows for diversity and easier testing
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=SecretStr(settings.groq_api_key),
        temperature=0.2,
        max_tokens=4000,
    )
    return llm


def run_llm_review(payload: dict, static_job_id: str):
    owner = payload["owner"]
    repo = payload["repo"]
    pr = payload["pr"]

    static_job = Job.fetch(static_job_id, connection=redis)
    static_summary = static_job.result

    job = get_current_job()

    if job is None:
        logger.error("No current job found for LLM review.")
        raise Exception("No current job found.")

    job.meta["stage"] = "llm:started"
    job.save_meta()

    logger.info(f"Running LLM review for {owner}/{repo} PR #{pr} with static summary.")

    prompt_input = {
        "pr_title": payload.get("pr_title", ""),
        "changed_hunks": payload.get("changed_hunks", ""),
        "static_summary": str(static_summary),
        "instructions": parser.get_format_instructions(),
    }
    llm = _make_llm()
    structured_llm = llm.with_structured_output(LLMResponse)

    try:
        chain = prompt_template | structured_llm
        parsed_output: LLMResponse = cast(LLMResponse, chain.invoke(prompt_input))

    except Exception as e:
        logger.warning("LLM invocation raised, attempting salvage parsing: %s", e)
        salvaged = _extract_json_from_exception(e)
        logger.info("Salvaged JSON: %s", salvaged)
        if salvaged:
            if (
                isinstance(salvaged, dict)
                and "arguments" in salvaged
                and isinstance(salvaged["arguments"], dict)
            ):
                candidate = salvaged["arguments"]
            else:
                candidate = salvaged

            try:
                parsed_output = LLMResponse(**candidate)
                logger.info(
                    "Successfully parsed salvaged LLM JSON from exception payload: %s",
                    candidate,
                )
            except Exception as e2:
                logger.exception("Salvage JSON parsed but failed validation: %s", e2)
                job.meta["stage"] = "llm:failed"
                job.save_meta()
                raise
        else:
            logger.exception(
                "Error during LLM invocation or parsing for %s/%s PR #%s: %s",
                owner,
                repo,
                pr,
                e,
            )
            job.meta["stage"] = "llm:failed"
            job.save_meta()
            raise

    job.meta["stage"] = "llm:completed"
    job.save_meta()

    logger.info(
        f"LLM review completed for {owner}/{repo} PR #{pr} with {len(parsed_output.suggestions)} suggestions."
    )
    return [s.model_dump() for s in parsed_output.suggestions]
