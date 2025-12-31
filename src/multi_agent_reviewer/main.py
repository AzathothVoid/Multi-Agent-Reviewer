from fastapi import FastAPI, Request, Header, HTTPException
from rq import Queue, Retry
from redis import Redis
import json, hmac, hashlib
import logging
from .config import settings
from .db import session
from .models.Repo import Repo
from .services.start_review_agent import start_revew_agent

logger = logging.getLogger(name=__name__)
redis = Redis.from_url(settings.redis_url, decode_responses=True)
queue = Queue("default", connection=redis)

app = FastAPI()


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
    body = await request.body()
    payload = await request.json()

    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "")
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

    if event == "installation":
        logger.info(f"Received installation event for repo {repo_name}")
        action = payload.get("action")
        installation = payload.get("installation", {})
        installation_id = installation.get("id")

        if action in ("created", "replaced"):
            repos = payload.get("repositories", [])

            for r in repos:
                repo_name = r["full_name"]
                owner = r["owner"]["login"]

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
        action = payload.get("action")

        if action in ("opened", "synchronize", "reopened"):
            owner = repo["owner"]["login"]
            repo = repo["full_name"]
            pr_number = pr.get("number")
            install_id = repo_record.installation_id if repo_record else None
            payload_for_job = {
                "owner": owner,
                "repo": repo,
                "pr": pr_number,
                "installation_id": install_id,
            }

            review_agent = queue.enqueue(
                "multi_agent_reviewer.services.start_review_agent.start_revew_agent",
                payload_for_job,
                timeout=10 * 60,
                retry=Retry(max=3),
            )

            logger.info(f"Enqueuing review job for PR #{pr_number} in repo {repo}")

    return {"ok": True}


@app.get("/oauth")
async def oauthCallback():
    return {"message": "OAuth callback endpoint"}
