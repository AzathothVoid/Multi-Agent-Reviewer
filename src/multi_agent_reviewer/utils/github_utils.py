import json
import httpx
import jwt
from datetime import datetime
import redis as Redis
import time
from ..config import settings

redis = Redis.from_url(settings.redis_url, decode_responses=True)


def make_jwt(
    app_id: str = settings.github_app_id, private_key: str | None = None
) -> str:
    if private_key is None:
        private_key = settings.github_private_key

    now = time.time()

    payload = {
        "iat": now + 30,
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
        "Authorization": f"token {info['token']}",
        "Accept": "application/vnd.github+json",
    }
