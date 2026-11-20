import os
from fastapi import FastAPI, HTTPException

app = FastAPI(title="AMANAH GEN Genetics API", version="0.1.0")
ENABLED = os.getenv("GENETICS_API_ENABLED", "false").lower() == "true"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "amanah-genetics-api", "clinical_endpoints_enabled": ENABLED}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def clinical_endpoints_not_implemented(path: str):
    # Deliberately no storage or clinical endpoints until consent, authorization,
    # encryption, audit, retention, and clinical governance are implemented.
    raise HTTPException(
        status_code=501,
        detail="Genetic clinical workflows are not implemented or enabled in this scaffold",
    )
