# Deployment notes

## Compose invocation

Run from the repository root. This adds AMANAH GEN to the existing Compose project without replacing the current ClinicEMR services:

```sh
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build
```

The first command validates and prints the merged Compose configuration. Review it before starting containers.

## Environment

Copy `amanah-gen/deployment.env.example` values into the deployment's secret/environment management system. Set an explicit OIDC JWKS endpoint that matches the configured issuer. The API checks issuer, audience, expiry, subject, signature, and the configured role. Validate the exact role claim shape against the deployed identity provider before integration testing.

AI is disabled unless `AMANAH_AI_ENABLED=true`; even then, authenticated access requires a valid token and configured local model. The Genetics API has no clinical data endpoints and remains disabled.

## Gateway

The Nginx configuration adds:

- `/amanah/api/ai/chat`
- `/amanah/api/ai/models`
- `/amanah/api/ai/tools`
- `/amanah/api/genetics/health`

The proxy strips the `/amanah/api/ai/` and `/amanah/api/genetics/` prefixes before forwarding. The AI app endpoints therefore remain `/chat`, `/models`, and `/tools`.

## Model provisioning

Ollama is not exposed on a host port. Provision only a model approved by the project's clinical, security, and governance reviewers. Pin the Ollama image and model digest/tag in deployment configuration before production.

## Important

This branch is an integration scaffold. It does not yet include the ESM Expert System UI, genetic screening workflows, consent management, encrypted genetic record storage, audit persistence, or clinical validation. Do not connect patient data or enable patient-facing clinical use based on this scaffold alone.
