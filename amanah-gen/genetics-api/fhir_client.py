"""Read-only OpenMRS FHIR R4 capability discovery.

The adapter calls only the FHIR metadata endpoint. It does not read or write
Patient, Encounter, Observation, ServiceRequest, Specimen, or DiagnosticReport
resources.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx


class FHIRIntegrationError(Exception):
    """Safe, non-secret-bearing FHIR integration error."""


def normalize_capability_statement(payload: dict) -> dict:
    """Validate and reduce a FHIR CapabilityStatement to safe capability data."""
    if not isinstance(payload, dict) or payload.get("resourceType") != "CapabilityStatement":
        raise FHIRIntegrationError("OpenMRS did not return a FHIR CapabilityStatement")

    fhir_version = payload.get("fhirVersion")
    if not isinstance(fhir_version, str) or not fhir_version:
        raise FHIRIntegrationError("FHIR CapabilityStatement has no FHIR version")

    resources = {}
    system_interactions = set()
    for rest in payload.get("rest", []) or []:
        if not isinstance(rest, dict):
            continue
        for interaction in rest.get("interaction", []) or []:
            if isinstance(interaction, dict) and isinstance(interaction.get("code"), str):
                system_interactions.add(interaction["code"])
        for resource in rest.get("resource", []) or []:
            if not isinstance(resource, dict):
                continue
            resource_type = resource.get("type")
            if not isinstance(resource_type, str) or not resource_type:
                continue
            interactions = {
                item.get("code")
                for item in resource.get("interaction", []) or []
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            }
            resources.setdefault(resource_type, set()).update(interactions)

    return {
        "resourceType": "CapabilityStatement",
        "fhirVersion": fhir_version,
        "status": payload.get("status"),
        "resources": [
            {"type": name, "interactions": sorted(interactions)}
            for name, interactions in sorted(resources.items())
        ],
        "systemInteractions": sorted(system_interactions),
    }


async def fetch_openmrs_capabilities() -> dict:
    """Fetch only /metadata from the configured OpenMRS FHIR R4 endpoint."""
    enabled = os.getenv("OPENMRS_FHIR_ENABLED", "false").lower() == "true"
    if not enabled:
        raise FHIRIntegrationError("OpenMRS FHIR integration is disabled by deployment policy")

    base_url = os.getenv("OPENMRS_FHIR_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise FHIRIntegrationError("OpenMRS FHIR base URL is not configured")

    parsed = urlsplit(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise FHIRIntegrationError("OpenMRS FHIR base URL must be an HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise FHIRIntegrationError("OpenMRS FHIR base URL contains unsupported URL components")

    username = os.getenv("OPENMRS_FHIR_USERNAME", "")
    password = os.getenv("OPENMRS_FHIR_PASSWORD", "")
    if bool(username) != bool(password):
        raise FHIRIntegrationError("Both OpenMRS FHIR service-account fields must be configured")
    auth = (username, password) if username and password else None

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False, auth=auth) as client:
            response = await client.get(
                f"{base_url}/metadata",
                headers={"Accept": "application/fhir+json, application/json"},
            )
        if response.status_code == 401 or response.status_code == 403:
            raise FHIRIntegrationError("OpenMRS FHIR endpoint rejected the configured service account")
        response.raise_for_status()
        return normalize_capability_statement(response.json())
    except FHIRIntegrationError:
        raise
    except httpx.TimeoutException:
        raise FHIRIntegrationError("OpenMRS FHIR metadata request timed out")
    except httpx.HTTPStatusError as exc:
        raise FHIRIntegrationError(
            f"OpenMRS FHIR metadata endpoint returned HTTP {exc.response.status_code}"
        )
    except (httpx.HTTPError, ValueError):
        raise FHIRIntegrationError("OpenMRS FHIR metadata endpoint is unavailable or returned invalid JSON")
