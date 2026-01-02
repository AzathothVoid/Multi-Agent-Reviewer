import json
import httpx
import tempfile
import shutil
import jwt
from datetime import datetime
from redis import Redis
import time
import logging
from ..config import settings
from .utils import run_command
from typing import Dict
from .diff_utils import parse_unified_diff, trim_text

redis = Redis.from_url(settings.redis_url, decode_responses=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def getGithubPrivateKey() -> str:
    raw = settings.github_private_key
    if raw is None:
        raise ValueError("GITHUB_APP_PRIVATE_KEY not set")
    return raw.replace("\\n", "\n") if "\\n" in raw else raw


def make_jwt(
    app_id: str = settings.github_app_id, private_key: str | None = None
) -> str:
    if private_key is None:
        private_key = getGithubPrivateKey()

    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": app_id,
    }

    token = jwt.encode(payload=payload, key=private_key, algorithm="RS256")

    return token


def get_installation_token(installation_id: int) -> dict:
    key = f"github:installation:{installation_id}:token"

    cached = redis.get(key)

    if cached:
        return json.loads(str(cached))

    jwt = make_jwt()

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Accept": "application/vnd.github+json",
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(url, headers=headers)

    response.raise_for_status()
    data = response.json()

    token_info = {"token": data["token"], "expires_at": data["expires_at"]}

    expires_at_ts = int(
        datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")).timestamp()
    )
    ttl = max(30, expires_at_ts - int(time.time()) - 30)  # leave 30s buffer
    redis.set(key, json.dumps(token_info), ex=ttl)

    return token_info


def auth_headers_for_installation(installation_id: int) -> dict:
    info = get_installation_token(installation_id)

    return {
        "Authorization": f"Bearer {info['token']}",
        "Accept": "application/vnd.github+json",
    }


def clone_github_repo(
    owner: str, repo: str, head_sha: str, installation_id: int, depth: int = 1
) -> tuple[str, str]:
    token = get_installation_token(installation_id)["token"]

    url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"

    tempdir = tempfile.mkdtemp(prefix="repo_")
    tmp_repo_dir = f"{tempdir}/{repo}"

    try:
        res = run_command(["git", "clone", "--depth", str(depth), url], cwd=tempdir)
    except Exception as e:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise RuntimeError(f"Git clone failed: {e}")

    if res["returncode"] != 0:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise RuntimeError(f"Git clone failed: {res['stderr']}")
    try:
        res = run_command(["git", "checkout", head_sha], cwd=tmp_repo_dir)
    except Exception as e:
        shutil.rmtree(tempdir, ignore_errors=True)
        raise RuntimeError(f"git checkout {head_sha} failed: {e}")

    if res["returncode"] != 0:
        fetch_cmd = ["git", "fetch", "origin", head_sha]
        res_fetch = run_command(fetch_cmd, cwd=tmp_repo_dir)

        if res_fetch["returncode"] != 0:
            shutil.rmtree(tempdir, ignore_errors=True)
            raise RuntimeError(f"git fetch {head_sha} failed: {res_fetch['stderr']}")

        res_co = run_command(["git", "checkout", head_sha], cwd=tmp_repo_dir)

        if res_co["returncode"] != 0:
            shutil.rmtree(tempdir, ignore_errors=True)
            raise RuntimeError(
                f"git checkout {head_sha} failed after fetch: {res_co['stderr']}"
            )

    run_command(
        ["git", "config", "user.email", "multi-agent-reviewer@bot.com"],
        cwd=tmp_repo_dir,
    )
    run_command(["git", "config", "user.name", "review-bot"], cwd=tmp_repo_dir)

    return (tempdir, tmp_repo_dir)


def get_changed_hunks(
    owner: str, repo: str, pr_number: int, installation_id: int, max_chars: int = 5000
) -> Dict[str, str]:
    token = get_installation_token(installation_id)["token"]
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    with httpx.Client(timeout=20) as client:
        response = client.get(url, headers=headers)

    response.raise_for_status()
    files = response.json()
    hunks_by_filename = {}

    for f in files:
        filename = f["filename"]
        patch = f.get("patch")

        if not patch:
            continue

        patched_text = trim_text(patch, max_chars=max_chars)
        parsed = parse_unified_diff(patched_text)
        hunks_by_filename[filename] = parsed

    logger.info(f"Extracted changed hunks for PR #{pr_number} in {owner}/{repo}")
    return hunks_by_filename
