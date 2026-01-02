# multi_agent_reviewer/services/job_failure.py
import logging
import traceback
from ..db import session
from ..models.Task import Task, TaskStatus
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from datetime import datetime
from typing import cast
from redis import Redis
from ..config import settings

redis = Redis.from_url(settings.redis_url)
logger = logging.getLogger(__name__)


def _unlock_pr(owner: str, repo: str, pr_number: int):
    lock_key = f"lock:pr:{owner}:{repo}:{pr_number}"
    redis.delete(lock_key)


def on_job_failure(job, connection, type, value, tb, *args, **kwargs):
    task = None
    owner = None
    repo = None
    pr_number = None

    try:
        task_id = None
        if job.args:
            try:
                maybe_payload = job.args[0]
                if isinstance(maybe_payload, dict):
                    task_id = maybe_payload.get("task_id")
            except Exception:
                pass
        if not task_id and job.kwargs:
            try:
                maybe_payload = job.kwargs.get("payload")
                if isinstance(maybe_payload, dict):
                    task_id = maybe_payload.get("task_id")
            except Exception:
                pass

        err_text = "".join(traceback.format_exception(type, value, tb))

        if task_id:
            try:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    owner = task.owner
                    repo = task.repo
                    pr_number = task.pr_number

                    task.status = TaskStatus.FAILED
                    task.result = {"error": str(type), "traceback": err_text}
                    task.completed_at = cast(DateTime, datetime.now())
                    session.commit()
                    logger.info(
                        "Marked Task %s as FAILED due to job %s error", task_id, job.id
                    )
                else:
                    logger.warning(
                        "Task id %s not found when handling failure for job %s",
                        task_id,
                        job.id,
                    )
            except Exception as e:
                logger.exception(
                    "Failed to update Task %s in failure handler: %s", task_id, e
                )
            finally:
                session.close()
        else:
            logger.warning(
                "No task_id found in failed job %s; job args: %s kwargs: %s",
                job.id,
                job.args,
                job.kwargs,
            )
        if task and owner and repo and pr_number:
            _unlock_pr(owner, repo, pr_number)

    except Exception as e:
        logger.exception("Unhandled error in on_job_failure handler: %s", e)
