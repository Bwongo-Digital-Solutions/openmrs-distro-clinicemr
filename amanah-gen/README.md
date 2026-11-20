# AMANAH GEN integration foundation

This directory adds an opt-in, modular foundation for AMANAH GEN to the ClinicEMR deployment.

## Services

- **AI Gateway**: authenticated access to a private Ollama runtime. It is an educational explanation service only; it does not diagnose, classify variants, calculate inherited-disease risk, or make reproductive or marriage recommendations.
- **Genetics API**: deliberately disabled scaffold. Clinical screening and genetic-record endpoints return HTTP 501 until consent, authorization, encryption, audit, retention, and clinical governance are implemented and reviewed.
- **Ollama**: private model runtime. Its port is not published to the host.

## Setup and deployment

Follow the complete [deployment guide](DEPLOYMENT.md) for Ubuntu preparation, branch checkout, environment/secrets, Compose validation, startup, health checks, optional model provisioning, identity-provider setup, and safe stop/restart procedures.

Quick start from the repository root, after completing the deployment guide's host and environment checks:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config --quiet
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build
~~~

The default gateway host port is 80. If another service (such as an existing Bahmni deployment) already uses it, use a separate VM/server or change the gateway host-port mapping as documented in DEPLOYMENT.md. Do not reuse another deployment's database volumes.

## Required configuration

Set these in the deployment environment; never commit real secrets:

- AMANAH_OIDC_ISSUER: exact issuer URL from the identity provider.
- AMANAH_OIDC_AUDIENCE: API audience expected in the access token.
- AMANAH_JWT_JWKS_URL: explicit JWKS endpoint for signature verification.
- AMANAH_ALLOWED_ROLE: role required for AI access (default AMANAH_GEN_AI_USER).
- AMANAH_OLLAMA_MODEL: locally installed, reviewed model name.
- AMANAH_AI_ENABLED=true: explicit opt-in. Keep false until identity, model, security, and clinical governance checks are complete.

The gateway rejects requests if OIDC configuration is absent, the token is invalid, or the required role is missing. Configure the identity provider to issue short-lived access tokens with the required audience and role, and verify the role claim mapping.

## Clinical and privacy release gates

This is an integration scaffold, not a clinically validated product. Before using real patient data:

1. Complete a UAE legal/privacy assessment, including applicable health-data and genetic-data requirements.
2. Complete a clinical safety case and approval by qualified genetics professionals.
3. Implement server-side, purpose-specific consent and independent consent for each person in any couple workflow.
4. Implement encrypted storage, key management, retention/deletion rules, access reviews, and durable audit events.
5. Validate the model, approved knowledge base, Arabic/English content, bias, and hallucination controls.
6. Perform threat modelling, penetration testing, backup/restore testing, and operational monitoring.
7. Ensure raw genomic data and identifiable patient data are not sent to external model providers.

Do not treat local Ollama hosting as a privacy guarantee. Do not store genetic results in browser localStorage. Do not merge two people's records into a shared couple record. Revoking consent must stop future sharing while preserving records that must legally remain in the clinical record.

## Current scope

The Genetics API intentionally has no patient, screening, variant, or couple endpoints. Add those only after the above controls are designed, implemented, tested, and approved.
