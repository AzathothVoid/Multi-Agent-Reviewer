from rq.job import Job
from rq import get_current_job
from ..db import session
from ..models.Task import Task, TaskStatus
from ..config import settings
from redis import Redis
from typing import cast
from datetime import datetime
from sqlalchemy import DateTime
import coloredlogs
import logging, time
from multi_agent_reviewer import metrics

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
redis = Redis.from_url(settings.redis_url)

AGENT = "finalizer_agent"


def _unlock_pr(owner: str, repo: str, pr_number: int):
    lock_key = f"lock:pr:{owner}:{repo}:{pr_number}"
    redis.delete(lock_key)


def finalize_review(task_id: int, llm_job_id: str, static_job_id: str):
    global task

    metrics.MAR_JOBS_STARTED.labels(AGENT).inc()
    start_time = time.time()

    try:
        task = cast(Task, session.get(Task, task_id))
        current_job = cast(Job, get_current_job())

        if not task:
            logger.error(f"Task {task_id} not found.")
            return

        static_job = Job.fetch(static_job_id, connection=redis)
        llm_job = Job.fetch(llm_job_id, connection=redis)

        task.status = TaskStatus.COMPLETED
        task.completed_at = cast(DateTime, datetime.now())
        task.result = {
            "static_checks": static_job.result,
            "llm_suggestions": llm_job.result,
        }

        session.commit()
        logger.info(
            f"Job {current_job.id} has completed sucessfully with result: {task.result}"
        )
        metrics.MAR_JOBS_SUCCEEDED.labels(AGENT).inc()
    except Exception as e:
        logger.error(f"Error in finalize_review for task {task_id}: {e}")
        task.status = TaskStatus.FAILED
        task.completed_at = cast(DateTime, datetime.now())
        task.result = {"error": str(e)}
        session.commit()
        metrics.MAR_JOBS_FAILED.labels(AGENT, type(e).__name__).inc()
        raise e

    finally:
        if task:
            _unlock_pr(task.owner, task.repo, task.pr_number)
        session.close()
        metrics.MAR_JOB_DURATION.labels(AGENT).observe(time.time() - start_time)
