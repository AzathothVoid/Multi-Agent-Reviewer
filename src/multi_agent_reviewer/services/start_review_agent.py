from rq import get_current_job, Queue, Retry
from rq.job import Job
from redis import Redis
from ..config import settings
from typing import cast
from ..db import session
from ..models.Task import Task, TaskStatus
import logging
import time

LOCK_PREFIX = "lock:pr"

redis = Redis.from_url(settings.redis_url, decode_responses=True)
queue = Queue("default", connection=redis)
logger = logging.getLogger(__name__)


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
        static_agent = queue.enqueue(
            "multi_agent_reviewer.services.static_check_agent.run_static_checks",
            payload,
            timeout=10 * 60,
            retry=Retry(max=2),
        )

        llm_agent = queue.enqueue(
            "multi_agent_reviewer.services.llm_review_agent.run_llm_review",
            payload,
            static_agent.get_id(),
            timeout=10 * 60,
            retry=Retry(max=2),
            depends_on=static_agent,
        )

        while True:
            lj = Job.fetch(llm_agent.get_id(), connection=redis)
            if lj.is_finished:
                suggestions = lj.result
                break
            if lj.is_failed:
                raise Exception("LLM reviewer failed: " + str(lj.exc_info))
            time.sleep(1)

        new_task.status = TaskStatus.COMPLETED
        new_task.result = {
            "static_checks": static_agent.result,
            "llm_suggestions": llm_agent.result,
        }
        session.commit()

        return {"status": "completed", "task_id": new_task.id}
    except Exception as e:
        logger.error(f"Error processing review for {owner}/{repo} PR #{pr}: {e}")
        new_task.status = TaskStatus.FAILED
        new_task.result = {"error": str(e)}
        session.commit()
        raise
    finally:
        session.close()
        redis.delete(lock_key)
