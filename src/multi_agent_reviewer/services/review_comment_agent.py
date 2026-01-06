import logging
from multi_agent_reviewer.utils.github_utils import post_pr_review_comment
from rq.job import Job
from rq import get_current_job
from redis import Redis
from ..config import settings
from prometheus_client import REGISTRY
from multi_agent_reviewer.metrics import get_metrics
import coloredlogs, time

redis = Redis.from_url(settings.redis_url)
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "review_comment_agent"


def post_review_comments(payload: dict, llm_agent_id: str):
    owner = payload["owner"]
    repo = payload["repo"]
    pr = payload["pr"]
    installation_id = payload["installation_id"]

    metrics_dict = get_metrics(REGISTRY)
    metrics_dict["MAR_JOBS_STARTED"].labels(AGENT).inc()
    start_time = time.time()

    llm_agent = Job.fetch(llm_agent_id, connection=redis)
    llm_suggestions = llm_agent.result

    for suggestion in llm_suggestions:
        try:
            comment_body = f"LLM Suggestion:\n{suggestion['explain']}\n\nPatch:\n```{suggestion['patch']}```\nReply `/apply {suggestion['id']}` to apply this change automatically."
            post_pr_review_comment(
                owner=owner,
                repo=repo,
                pr_number=pr,
                body=comment_body,
                path=suggestion["file"],
                line=suggestion["start_line"],
                installation_id=installation_id,
                commit_id=payload["head_sha"],
            )
            logger.info(
                f"Posted review comment for suggestion {suggestion['id']} on PR #{pr}."
            )
        except Exception as e:
            logger.error(
                f"Error posting comment for suggestion {suggestion['id']} on {owner}/{repo} PR #{pr}: {e}"
            )

    metrics_dict["MAR_JOBS_SUCCEEDED"].labels(AGENT).inc()
    metrics_dict["MAR_JOB_DURATION"].labels(AGENT).observe(time.time() - start_time)
