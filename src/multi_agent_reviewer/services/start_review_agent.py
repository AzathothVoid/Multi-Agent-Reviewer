from rq import get_current_job, Queue, Retry
from rq.job import Job
from redis import Redis
from ..config import settings
from typing import cast
from ..db import session
from ..models.Task import Task, TaskStatus
import logging
import time
from ..utils.github_utils import get_changed_hunks

LOCK_PREFIX = "lock:pr"

redis = Redis.from_url(settings.redis_url, decode_responses=True)
queue = Queue("default", connection=redis)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def _lock_key(owner: str, repo: str, pr_number: int) -> str:
    return f"{LOCK_PREFIX}:{owner}:{repo}:{pr_number}"


def start_revew_agent(payload: dict):
    job = cast(Job, get_current_job())
    owner = payload["owner"]
    repo = payload["repo"]
    pr = payload["pr"]

    lock_key = _lock_key(owner, repo, pr)
    got = redis.set(lock_key, job.get_id(), nx=True, ex=60 * 10)

    if not got:
        logger.info(f"Review job already in progress for {owner}/{repo} PR #{pr}")
        return {"status": "skipped", "reason": "already_running"}

    new_task = Task(
        owner=owner,
        repo=repo,
        pr_number=pr,
        status=TaskStatus.IN_PROGRESS,
        payload=payload,
    )

    session.add(new_task)
    session.commit()
    session.refresh(new_task)

    try:
        changed_hunks = get_changed_hunks(owner, repo, pr, payload["installation_id"])

        payload["changed_hunks"] = changed_hunks

        static_agent = queue.enqueue(
            "multi_agent_reviewer.services.static_check_agent.run_static_checks",
            args=(payload,),
            timeout=10 * 60,
            retry=Retry(max=2),
        )

        llm_agent = queue.enqueue(
            "multi_agent_reviewer.services.llm_review_agent.run_llm_review",
            args=(payload, static_agent.get_id()),
            timeout=10 * 60,
            retry=Retry(max=2),
            depends_on=static_agent,
        )

        finalizer_agent = queue.enqueue(
            "multi_agent_reviewer.services.finalizer_agent.finalize_review",
            args=(new_task.id, llm_agent.get_id(), static_agent.get_id()),
            on_failure="multi_agent_reviewer.services.finalizer_agent.on_failure",
            timeout=10 * 60,
            retry=Retry(max=2),
            depends_on=llm_agent,
        )

        logger.info(f"Enqueued review agents for {owner}/{repo} PR #{pr}")
        return {"status": "started", "task_id": new_task.id}
    except Exception as e:
        logger.error(f"Error processing review for {owner}/{repo} PR #{pr}: {e}")
        new_task.status = TaskStatus.FAILED
        new_task.result = {"error": str(e)}
        session.commit()
        redis.delete(lock_key)
        raise
    finally:
        session.close()
