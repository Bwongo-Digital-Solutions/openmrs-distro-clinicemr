import unittest

from fhir_client import FHIRIntegrationError, normalize_capability_statement


class FHIRCapabilityTests(unittest.TestCase):
    def test_normalizes_supported_resources_and_interactions(self):
        statement = {
            "resourceType": "CapabilityStatement",
            "fhirVersion": "4.0.1",
            "status": "active",
            "rest": [{
                "mode": "server",
                "interaction": [{"code": "search-system"}],
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [{"code": "read"}, {"code": "search-type"}],
                    },
                    {
                        "type": "ServiceRequest",
                        "interaction": [{"code": "create"}],
                    },
                ],
            }],
        }

        result = normalize_capability_statement(statement)

        self.assertEqual(result["fhirVersion"], "4.0.1")
        self.assertEqual(
            result["resources"],
            [
                {"type": "Patient", "interactions": ["read", "search-type"]},
                {"type": "ServiceRequest", "interactions": ["create"]},
            ],
        )
        self.assertEqual(result["systemInteractions"], ["search-system"])

    def test_rejects_non_capability_statement(self):
        with self.assertRaises(FHIRIntegrationError):
            normalize_capability_statement({"resourceType": "Patient"})

    def test_rejects_missing_fhir_version(self):
        with self.assertRaises(FHIRIntegrationError):
            normalize_capability_statement({"resourceType": "CapabilityStatement"})


if __name__ == "__main__":
    unittest.main()
