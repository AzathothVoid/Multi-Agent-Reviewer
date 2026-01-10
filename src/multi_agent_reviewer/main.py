from fastapi import FastAPI, Request, Header, HTTPException, Response
from rq import Queue, Retry
from redis import Redis
import os, hmac, hashlib
import logging
from .config import settings
from .db import session
from .models.Repo import Repo
import coloredlogs
from .services.start_review_agent import start_revew_agent
from prometheus_client import REGISTRY
from multi_agent_reviewer.metrics import (
    get_metrics,
    ensure_multiproc_dir,
    metrics_response,
)

metrics_dict = get_metrics(REGISTRY)
from dotenv import load_dotenv
import time

logger = logging.getLogger(name=__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(filename="app.log", level=logging.DEBUG)
redis = Redis.from_url(settings.redis_url)
queue = Queue("default", connection=redis)
load_dotenv()

os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", settings.prometheus_multiproc_dir)

metric_dir = settings.prometheus_multiproc_dir
ensure_multiproc_dir(metric_dir)

from prometheus_client import Counter, Histogram, generate_latest

app = FastAPI()

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["endpoint"]
)


def verify_signature(secret: str, body: bytes, hub_signature: str | None) -> bool:
    if not hub_signature:
        return False
    prefix = "sha256="
    if not hub_signature.startswith(prefix):
        return False
    signature = hub_signature[len(prefix) :]
    max = hmac.new(secret.encode(), body, hashlib.sha256)
    return hmac.compare_digest(max.hexdigest(), signature)


@app.post("/review-webhook")
async def review(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
):
    logger.info("Received webhook request")

    body = await request.body()
    payload = await request.json()

    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")
    repo_owner = repo.get("owner", {}).get("login", "")
    repo_record = None

    if repo_name and repo_owner:
        repo_record = session.query(Repo).filter(Repo.repo_name == repo_name).first()
        session.close()

    secret = (
        repo_record.webhook_secret
        if repo_record and repo_record.webhook_secret
        else settings.github_app_secret
    )

    if not secret:
        logger.error("No secret found for verifying webhook")
        raise HTTPException(
            status_code=401, detail="No webhook secret configured for this repo"
        )

    if not verify_signature(
        secret=secret, body=body, hub_signature=x_hub_signature_256
    ):
        logger.warning("Invalid signature for incoming webhook")
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = x_github_event or payload.get("action")

    if event == "issue_comment":
        comment = payload.get("comment", {})
        body = comment.get("body", "")
        if body.strip().startswith("/apply"):
            parts = body.strip().split()
            if len(parts) == 2:
                suggestion_id = parts[1]
                pr = payload.get("issue", {})
                pr_number = pr.get("number")
                repo = payload.get("repository", {})
                owner = repo.get("owner", {}).get("login")
                repo_name = repo.get("name")
                installation_id = repo.get("installation_id")
                # TODO: Retrieve suggestion details from storage or context
                suggestion = {
                    "id": suggestion_id,
                    "file": "<file_path>",
                    "patch": "<patch_contents>",
                    "head_sha": "<head_sha>",
                }
                # TODO: Enqueue the auto fix agent job
                success = True
                if success:
                    return {
                        "ok": True,
                        "message": f"Applied suggestion {suggestion_id}",
                    }
                else:
                    return {
                        "ok": False,
                        "message": f"Failed to apply suggestion {suggestion_id}",
                    }

    if event == "installation":
        action = payload.get("action")
        installation = payload.get("installation", {})
        installation_id = installation.get("id")

        if action in ("created", "replaced"):
            repos = payload.get("repositories", [])

            for r in repos:
                logger.info(f"Processing Repo: {r}")

                repo_name = r["name"]
                owner = installation["account"]["login"]

                record = (
                    session.query(Repo)
                    .filter(Repo.repo_name == repo_name, Repo.owner == owner)
                    .first()
                )

                if not record:
                    record = Repo(
                        repo_name=repo_name,
                        installation_id=installation_id,
                        owner=owner,
                    )
                    session.add(record)
                    logger.info(f"Added new repo record for {repo_name}")
                else:
                    record.installation_id = installation_id
                    logger.info(f"Updated installation_id for repo {repo_name}")

            session.commit()
            session.close()

        elif action == "deleted":
            repos = payload.get("repositories", [])
            session.query(Repo).filter(Repo.installation_id == installation_id).update(
                {"installation_id": None}
            )
            session.commit()
            session.close()

    if event == "pull_request":
        logger.info(f"Received pull_request event for repo {repo_name}")
        pr = payload.get("pull_request", {})
        head_sha = pr.get("head", {}).get("sha")
        action = payload.get("action")

        if action in ("opened", "synchronize", "reopened"):
            owner = repo["owner"]["login"]
            repo = repo["name"]
            pr_number = pr.get("number")
            pr_title = pr.get("title", "")

            install_id = repo_record.installation_id if repo_record else None
            payload_for_job = {
                "owner": owner,
                "repo": repo,
                "pr": pr_number,
                "installation_id": install_id,
                "pr_title": pr_title,
                "head_sha": head_sha,
            }

            review_agent = queue.enqueue(
                "multi_agent_reviewer.services.start_review_agent.start_revew_agent",
                args=(payload_for_job,),
                timeout=10 * 60,
                retry=Retry(max=3),
            )

            logger.info(f"Enqueuing review job for PR #{pr_number} in repo {repo}")

    return {"ok": True}


@app.get("/oauth")
async def oauthCallback():
    return {"message": "OAuth callback endpoint"}


@app.get("/metrics")
def metrics_fn():
    return metrics_response()


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()

    REQUEST_LATENCY.labels(request.url.path).observe(duration)

    return response
