from rq.job import Job
from rq import get_current_job
from ..db import session
from ..models.Task import Task, TaskStatus
from ..config import settings
from redis import Redis
from typing import cast
import logging

logger = logging.getLogger(__name__)
redis = Redis.from_url(settings.redis_url, decode_responses=True)


def _unlock_pr(owner: str, repo: str, pr_number: int):
    lock_key = f"lock:pr:{owner}:{repo}:{pr_number}"
    redis.delete(lock_key)


def on_failure(job, conneciton, type, value, traceback):
    logger.error(f"Job {job.id} failed with error: {value}")
    task_id = job.meta.get("task_id")

    if not task_id:
        return

    task = cast(Task, session.get(Task, task_id))

    if task:
        task.status = TaskStatus.FAILED
        task.result = {"error": f"Job {job.id} failed: {value}"}
        session.commit()
        _unlock_pr(task.owner, task.repo, task.pr_number)

    session.close()


def finalize_review(task_id: int, llm_job_id: str, static_job_id: str):
    global task
    try:
        task = cast(Task, session.get(Task, task_id))
        current_job = cast(Job, get_current_job())

        if not task:
            logger.error(f"Task {task_id} not found.")
            return

        static_job = Job.fetch(static_job_id, connection=redis)
        llm_job = Job.fetch(llm_job_id, connection=redis)

        task.status = TaskStatus.COMPLETED
        task.result = {
            "static_checks": static_job.result,
            "llm_suggestions": llm_job.result,
        }

        session.commit()
        logger.info(f"Job {current_job.id} has completed sucessfully")
    except Exception as e:
        logger.error(f"Error in finalize_review for task {task_id}: {e}")
        task.status = TaskStatus.FAILED
        task.result = {"error": str(e)}
        session.commit()
        raise

    finally:
        session.close()
        if "task" in locals() and task:
            _unlock_pr(task.owner, task.repo, task.pr_number)
