import os, shutil, logging
from rq.job import Job
from rq import get_current_job
from ..utils.utils import run_command

logger = logging.getLogger(__name__)


def run_static_checks(payload: dict):
    owner = payload["owner"]
    repo = payload["repo"]
    pr_number = payload["pr"]
    head_sha = payload["head_sha"]

    job = get_current_job()

    if job is None:
        logger.error("No current job found for static checks.")
        raise Exception("No current job found.")

    job.meta["stage"] = "static:started"
    job.save_meta()
    job_id = job.get_id()

    # clone the repo and checkout the PR head SHA
    tmpdir = ""
    try:
        black = run_command(["black", "--check", "."], cwd=tmpdir)
        flake = run_command(["flake8", "."], cwd=tmpdir)

        aggregated = {
            "status": "ok" if black["returncode"] == 0 else "failed",
            "artifacts": {"black": black, "flake8": flake},
            "summary": {"errors": len(flake.get("stdout", ""))},
            "workspace": tmpdir,
        }
        job.meta["stage"] = "static:completed"
        job.save_meta()
        return aggregated
    except Exception as e:
        logger.error(
            f"Error during static checks for {owner}/{repo} PR #{pr_number}: {e}"
        )
        job.meta["stage"] = "static:failed"
        job.save_meta()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
