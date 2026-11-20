import os
from typing import Any

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel, ConfigDict, Field

from fhir_client import FHIRIntegrationError, fetch_openmrs_capabilities
from workflow import is_valid_transition, workflow_definition

app = FastAPI(title="AMANAH GEN Genetics API", version="0.2.0")
bearer = HTTPBearer(auto_error=False)

GENETICS_API_ENABLED = os.getenv("GENETICS_API_ENABLED", "false").lower() == "true"
FHIR_ENABLED = os.getenv("OPENMRS_FHIR_ENABLED", "false").lower() == "true"
ISSUER = os.getenv("OIDC_ISSUER", "").rstrip("/")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "")
JWKS_URL = os.getenv("OIDC_JWKS_URL", "").strip()
ALLOWED_ROLES = {
    role.strip()
    for role in os.getenv(
        "FHIR_ALLOWED_ROLES",
        "AMANAH_GEN_CLINICIAN,AMANAH_GEN_COUNSELLOR,AMANAH_GEN_ADMIN",
    ).split(",")
    if role.strip()
}
_jwks = PyJWKClient(JWKS_URL) if JWKS_URL else None


class TransitionValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_state: str = Field(min_length=1, max_length=40)
    to_state: str = Field(min_length=1, max_length=40)


async def require_clinical_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    if not GENETICS_API_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Genetics API is disabled by deployment policy",
        )
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
    roles = [role for role in roles if isinstance(role, str)]
    if not ALLOWED_ROLES.intersection(roles):
        raise HTTPException(status_code=403, detail="A clinical AMANAH GEN role is required")
    return claims


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "amanah-genetics-api",
        "clinical_endpoints_enabled": False,
        "screening_workflow_definition_available": True,
        "openmrs_fhir_enabled": FHIR_ENABLED,
    }


@app.get("/workflow/definition")
async def get_workflow_definition(_user=Depends(require_clinical_user)):
    return workflow_definition()


@app.post("/workflow/validate-transition")
async def validate_workflow_transition(
    payload: TransitionValidationRequest,
    _user=Depends(require_clinical_user),
):
    return {
        "from_state": payload.from_state,
        "to_state": payload.to_state,
        "valid": is_valid_transition(payload.from_state, payload.to_state),
    }


@app.get("/integrations/openmrs/fhir/capabilities")
async def openmrs_fhir_capabilities(_user=Depends(require_clinical_user)):
    if not FHIR_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="OpenMRS FHIR integration is disabled by deployment policy",
        )
    try:
        return await fetch_openmrs_capabilities()
    except FHIRIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def clinical_endpoints_not_implemented(
    path: str,
    _user=Depends(require_clinical_user),
):
    # Patient-linked screening, consent and result endpoints remain unavailable
    # until durable consent, record-level authorization, encryption and audit
    # controls have been implemented and reviewed.
    raise HTTPException(
        status_code=501,
        detail="Patient-linked genetic clinical workflows are not implemented",
    )
