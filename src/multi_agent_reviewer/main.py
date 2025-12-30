from fastapi import FastAPI, Request, Header
import json, hmac, hashlib
import logging 
from .config import settings

logger = logging.getLogger(name=__name__)

app = FastAPI()

def verify_signature(secret: str, body: bytes, hub_signature: str) -> bool:
    if not hub_signature:
        return False
    prefix = 'sha256='
    if not hub_signature.startswith(prefix):
        return False
    signature = hub_signature[len(prefix):]
    max = hmac.new(secret.encode(), body, hashlib.sha256)
    return hmac.compare_digest(max.hexdigest(), signature)

@app.post("/review-webhook")
async def review(request: Request, x_github_event: str | None = Header(default=None), x_hub_signature_256: str | None = Header(default=None)):
    body = await request.body()
    payload = await request.json()

    if not verify_signature()
    return {"message": "Review endpoint"}

@app.get("/oauth")
async def oauthCallback():
    return {"message": "OAuth callback endpoint"}