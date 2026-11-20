import os
from typing import Any

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel, Field

app = FastAPI(title="AMANAH GEN AI Gateway", version="0.1.0")
bearer = HTTPBearer(auto_error=False)

AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
ISSUER = os.getenv("OIDC_ISSUER", "").rstrip("/")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "")
ROLE = os.getenv("ALLOWED_ROLE", "AMANAH_GEN_AI_USER")
MODEL = os.getenv("OLLAMA_MODEL", "")
OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://amanah-ollama:11434").rstrip("/")
MAX_INPUT = int(os.getenv("MAX_INPUT_CHARS", "4000"))
JWKS_URL = os.getenv("OIDC_JWKS_URL", "").strip()
_jwks = PyJWKClient(JWKS_URL) if JWKS_URL else None


class ExplainRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    approved_explanation_context: str = Field(default="", max_length=4000)


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _jwks or not ISSUER or not AUDIENCE:
        raise HTTPException(status_code=503, detail="Identity provider is not configured")
    try:
        signing_key = _jwks.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")
    realm_access = claims.get("realm_access") or {}
    roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    if not isinstance(roles, list):
        roles = []
    top_level_roles = claims.get("roles", [])
    if isinstance(top_level_roles, list):
        roles.extend(top_level_roles)
    if ROLE not in roles:
        raise HTTPException(status_code=403, detail="Required role is missing")
    return claims


@app.get("/health")
async def health():
    return {"status": "ok", "service": "amanah-ai-gateway", "ai_enabled": AI_ENABLED}


@app.get("/models")
async def models(_user=Depends(require_user)):
    if not MODEL:
        return {"models": []}
    return {"models": [{"name": MODEL, "provider": "private-ollama"}]}


@app.get("/tools")
async def tools(_user=Depends(require_user)):
    # Fail closed: this service exposes no database, SQL, patient lookup, or agent tools.
    return {"tools": []}


@app.post("/chat")
async def explain(payload: ExplainRequest, _user=Depends(require_user)):
    if not AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI assistance is disabled by deployment policy")
    if not MODEL:
        raise HTTPException(status_code=503, detail="No approved local model is configured")
    question = payload.question.strip()
    context = payload.approved_explanation_context.strip()
    if len(question) > MAX_INPUT or len(context) > MAX_INPUT:
        raise HTTPException(status_code=413, detail="Input exceeds configured limit")

    system = (
        "You are an educational assistant for a clinician-supervised genetic health service. "
        "Explain only the clinician-approved context supplied in this request in plain language. "
        "Do not diagnose, classify variants, calculate inherited-disease risk, infer carrier status, "
        "or recommend whether anyone should marry, have children, or make reproductive choices. "
        "Do not infer facts that are not in the supplied context. State when information is missing "
        "and direct clinical questions to a qualified genetics professional. "
        "Do not request names, dates of birth, contact details, raw genomic files, or identifiers. "
        "This response is educational and is not a clinical decision."
    )
    prompt = (
        f"Approved explanation context (may be empty):\n{context or '[No approved context supplied]'}"
        f"\n\nUser question:\n{question}"
    )
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{OLLAMA}/api/chat",
                json={
                    "model": MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "options": {"temperature": 0.2},
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Local model service is unavailable")

    answer = data.get("message", {}).get("content", "")
    if not answer:
        raise HTTPException(status_code=502, detail="Local model returned an empty response")
    return {
        "answer": answer,
        "disclaimer": "Educational explanation only. Discuss personal results with a qualified genetics professional.",
        "model": MODEL,
    }
