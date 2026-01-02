from rq.job import Job
from rq import get_current_job
from ..config import settings
from redis import Redis
from pydantic import BaseModel, Field, SecretStr
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from typing import Any, Dict, List, Any
from typing import cast
import httpx
import coloredlogs
import logging

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
"""

prompt_template = PromptTemplate(
    template=PROMPT,
    input_variables=[
        "pr_title",
        "changed_hunks",
        "static_summary",
    ],
)


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
    }
    llm = _make_llm()
    structured_llm = llm.with_structured_output(LLMResponse)

    try:
        chain = prompt_template | structured_llm
        parsed_output: LLMResponse = cast(LLMResponse, chain.invoke(prompt_input))

    except httpx.HTTPStatusError as e:
        resp_text = None
        try:
            resp_text = e.response.text
        except Exception:
            resp_text = str(e)

        logger.error(
            f"HTTP error from LLM provider for {owner}/{repo} PR #{pr}: {e} - response: {resp_text}"
        )
        job.meta["stage"] = "llm:failed"
        job.save_meta()
        raise

    except Exception as e:
        logger.error(
            f"Error during LLM invocation or parsing for {owner}/{repo} PR #{pr}: {e}"
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
