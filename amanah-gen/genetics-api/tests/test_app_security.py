import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as api


class GeneticsAPISecurityTests(unittest.TestCase):
    def setUp(self):
        self.enabled = patch.object(api, "GENETICS_API_ENABLED", True)
        self.jwks = patch.object(
            api,
            "_jwks",
            SimpleNamespace(
                get_signing_key_from_jwt=lambda token: SimpleNamespace(
                    key="test-signing-key"
                )
            ),
        )
        self.issuer = patch.object(api, "ISSUER", "https://identity.example/realms/amanah-gen")
        self.audience = patch.object(api, "AUDIENCE", "amanah-gen-api")

        self.enabled.start()
        self.jwks.start()
        self.issuer.start()
        self.audience.start()

        self.addCleanup(self.enabled.stop)
        self.addCleanup(self.jwks.stop)
        self.addCleanup(self.issuer.stop)
        self.addCleanup(self.audience.stop)

        self.client = TestClient(api.app)

    def token(self, claims):
        return patch.object(api.jwt, "decode", return_value=claims)

    def test_health_is_public_when_api_disabled(self):
        with patch.object(api, "GENETICS_API_ENABLED", False):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)

    def test_protected_endpoint_rejects_requests_when_api_disabled(self):
        with patch.object(api, "GENETICS_API_ENABLED", False):
            response = self.client.get("/workflow/definition")

        self.assertEqual(response.status_code, 503)

    def test_missing_token_is_rejected(self):
        response = self.client.get("/workflow/definition")
        self.assertEqual(response.status_code, 401)

    def test_missing_identity_configuration_is_rejected(self):
        with patch.object(api, "_jwks", None):
            response = self.client.get(
                "/workflow/definition",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 503)

    def test_invalid_token_is_rejected(self):
        with patch.object(api.jwt, "decode", side_effect=Exception("invalid")):
            response = self.client.get(
                "/workflow/definition",
                headers={"Authorization": "Bearer invalid-token"},
            )

        self.assertEqual(response.status_code, 401)

    def test_token_without_clinical_role_is_rejected(self):
        with self.token({"sub": "test-user"}):
            response = self.client.get(
                "/workflow/definition",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 403)

    def test_authorized_realm_role_is_accepted(self):
        claims = {
            "sub": "test-user",
            "realm_access": {"roles": ["AMANAH_GEN_CLINICIAN"]},
        }

        with self.token(claims):
            response = self.client.get(
                "/workflow/definition",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)

    def test_authorized_top_level_role_is_accepted(self):
        claims = {
            "sub": "test-user",
            "roles": ["AMANAH_GEN_COUNSELLOR"],
        }

        with self.token(claims):
            response = self.client.get(
                "/workflow/definition",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)

    def test_unknown_clinical_route_requires_authentication(self):
        response = self.client.get("/patient-records")
        self.assertEqual(response.status_code, 401)

    def test_unknown_clinical_route_remains_unimplemented(self):
        claims = {
            "sub": "test-user",
            "realm_access": {"roles": ["AMANAH_GEN_ADMIN"]},
        }

        with self.token(claims):
            response = self.client.get(
                "/patient-records",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 501)


if __name__ == "__main__":
    unittest.main()
