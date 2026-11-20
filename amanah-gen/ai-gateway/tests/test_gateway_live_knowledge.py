"""End-to-end gateway -> real Knowledge API test with a mocked local model.

Run only while the lifecycle script's synthetic document is APPROVED.
The gateway process temporarily enables AI in this short-lived test process;
the deployed container environment and running service remain unchanged.
"""
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/app")

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import app as gateway

DOC_ID = sys.argv[1]
PHRASE = sys.argv[2]
REAL_ASYNC_CLIENT = httpx.AsyncClient


class FakeJWKS:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self.key)


class FakeModelResponse:
    def __init__(self, answer):
        self.answer = answer

    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": self.answer}}


class KnowledgeLiveAsyncClient:
    """Pass Knowledge API traffic through; intercept only the model call."""
    answers = []
    model_calls = 0

    def __init__(self, *, timeout=8.0):
        self.timeout = timeout
        self.real = None

    async def __aenter__(self):
        self.real = REAL_ASYNC_CLIENT(timeout=self.timeout)
        await self.real.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return await self.real.__aexit__(exc_type, exc, tb)

    async def post(self, url, *, headers=None, json=None):
        if url.endswith("/api/chat"):
            type(self).model_calls += 1
            if not type(self).answers:
                raise AssertionError("Unexpected model call without a queued test answer")
            return FakeModelResponse(type(self).answers.pop(0))
        return await self.real.post(url, headers=headers, json=json)


def make_token(private_key, roles):
    now = int(time.time())
    claims = {
        "iss": gateway.ISSUER,
        "aud": gateway.AUDIENCE,
        "sub": "synthetic-e2e-test-user",
        "iat": now,
        "exp": now + 180,
        "realm_access": {"roles": roles},
    }
    return jwt.encode(
        claims, private_key, algorithm="RS256",
        headers={"kid": "synthetic-e2e-key"},
    )


def run():
    if not gateway.KNOWLEDGE_TOKEN or not gateway.KNOWLEDGE_URL:
        raise SystemExit("FAIL: live Knowledge API settings are missing from the gateway.")

    gateway.ISSUER = "https://synthetic-e2e-issuer.invalid/realms/amanah-gen"
    gateway.AUDIENCE = "amanah-gen-api"
    gateway.ROLE = "AMANAH_GEN_AI_USER"
    gateway.AI_ENABLED = True
    gateway.MODEL = "synthetic-mocked-model"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    gateway._jwks = FakeJWKS(private_key.public_key())
    token = make_token(private_key, [gateway.ROLE])
    headers = {"Authorization": "Bearer " + token}
    KnowledgeLiveAsyncClient.answers = []
    KnowledgeLiveAsyncClient.model_calls = 0

    with patch.object(gateway.httpx, "AsyncClient", KnowledgeLiveAsyncClient):
        client = TestClient(gateway.app)

        no_auth = client.post(
            "/chat", json={"question": PHRASE, "language": "en"}
        )
        assert no_auth.status_code == 401, no_auth.text
        print("PASS: unauthenticated gateway request rejected (401)")

        wrong_role = make_token(private_key, ["OTHER_ROLE"])
        denied = client.post(
            "/chat",
            headers={"Authorization": "Bearer " + wrong_role},
            json={"question": PHRASE, "language": "en"},
        )
        assert denied.status_code == 403, denied.text
        print("PASS: authenticated user without required role rejected (403)")

        extra = client.post(
            "/chat", headers=headers,
            json={
                "question": PHRASE, "language": "en",
                "clinical_context": "untrusted synthetic caller context",
            },
        )
        assert extra.status_code == 422, extra.text
        assert KnowledgeLiveAsyncClient.model_calls == 0
        print("PASS: caller-supplied clinical context rejected (422)")

        KnowledgeLiveAsyncClient.answers.append(
            "The approved synthetic source describes this phrase as a test marker [S1]."
        )
        grounded = client.post(
            "/chat", headers=headers,
            json={"question": PHRASE, "language": "en"},
        )
        assert grounded.status_code == 200, grounded.text
        data = grounded.json()
        assert data.get("grounded") is True, data
        assert any(item.get("document_id") == DOC_ID for item in data.get("sources", [])), data
        assert KnowledgeLiveAsyncClient.model_calls == 1
        print("PASS: gateway retrieved the approved document from the real Knowledge API")
        print("PASS: valid source citation accepted and source metadata returned")

        KnowledgeLiveAsyncClient.answers.append(
            "Unsupported test statement with fabricated citation [S99]."
        )
        invalid = client.post(
            "/chat", headers=headers,
            json={"question": PHRASE, "language": "en"},
        )
        assert invalid.status_code == 200, invalid.text
        invalid_data = invalid.json()
        assert invalid_data.get("grounded") is False, invalid_data
        assert "Unsupported test statement" not in invalid_data.get("answer", "")
        print("PASS: fabricated citation replaced by safe fallback")

        before = KnowledgeLiveAsyncClient.model_calls
        no_match = client.post(
            "/chat", headers=headers,
            json={
                # One unique FTS token: no common words that could match the fixture.
                "question": "zzqvnomatch7f29c4e8a6b1c3d5e7f9",
                "language": "en",
            },
        )
        assert no_match.status_code == 200, no_match.text
        no_match_data = no_match.json()
        assert no_match_data.get("grounded") is False, no_match_data
        assert no_match_data.get("sources") == [], no_match_data
        assert KnowledgeLiveAsyncClient.model_calls == before
        print("PASS: no approved retrieval result produces safe no-answer without model call")

    print("PASS: live Knowledge API -> AI Gateway security integration checks.")


if __name__ == "__main__":
    run()
