# AMANAH GEN integration foundation

This directory adds an opt-in, modular foundation for AMANAH GEN to the ClinicEMR deployment.

## Services

- **AI Gateway**: authenticates OIDC users, retrieves approved knowledge passages, and asks a private Ollama model to explain only that retrieved educational content. It does not diagnose, interpret individual genetic tests, classify variants, calculate inherited-disease risk, or make reproductive or marriage recommendations.
- **Knowledge API**: internal-only SQLite FTS5 retrieval. It returns only documents explicitly approved by a human reviewer. It has no host-published port.
- **Knowledge registry CLI**: registers UTF-8 Markdown/text sources as pending, then supports explicit approval and withdrawal inside the knowledge container.
- **Genetics API**: deliberately disabled scaffold. Clinical screening and genetic-record endpoints return HTTP 501 until consent, authorization, encryption, audit, retention, and clinical governance are implemented and reviewed.
- **Ollama**: private model runtime. Its port is not published to the host.
- **Keycloak**: OIDC identity provider with its own PostgreSQL database and AMANAH GEN realm.

## Setup and deployment

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for server preparation, environment/secrets, Compose validation, startup, and health checks. Keep all secrets in the untracked deployment `.env` file.

Validate and build from the repository root:

```sh
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config --quiet
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build amanah-knowledge-api amanah-ai-gateway
```

The knowledge database uses its own `amanah-knowledge-data` named volume. Do not delete volumes or reuse ClinicEMR/OpenMRS database volumes.

## Configure the retrieval credential

Generate a unique random secret on the server and add it to the existing `.env` without exposing it in chat or committing it:

```sh
openssl rand -hex 32
```

Set `AMANAH_KNOWLEDGE_RETRIEVAL_TOKEN` to that value. The same value is injected into the Knowledge API and AI Gateway; it is not an OIDC user token. Recreate only those two services after setting it.

## Knowledge document workflow

See [knowledge-api/README.md](knowledge-api/README.md). Only reviewed, approved UTF-8 Markdown/text documents are retrievable. Ingestion creates a pending record; a separate explicit approval is required. Do not use illustrative documents as clinical references.

## AI request

The authenticated `POST /amanah/api/ai/chat` request accepts only:

```json
{"question":"What does genetic screening mean?","language":"en"}
```

`language` may be `en`, `ar`, or `auto`. Caller-supplied clinical context is rejected. The gateway retrieves approved passages itself, returns their source metadata, and does not call Ollama when retrieval finds no approved material. AI remains disabled by default.

## Clinical and privacy release gates

This is an integration scaffold, not a clinically validated product. Before using real patient data:

1. Complete applicable UAE and other jurisdictional legal/privacy assessments.
2. Complete a clinical safety case and approval by qualified genetics professionals.
3. Implement server-side, purpose-specific consent and independent consent for each person in any couple workflow.
4. Implement encrypted storage, key management, retention/deletion rules, durable audit events, backups, and access reviews.
5. Validate every knowledge source, its licensing, version, review date, language, and translation quality.
6. Validate model outputs, bias, hallucinations, source faithfulness, prompt-injection resilience, and Arabic/English quality with qualified reviewers.
7. Perform threat modelling, penetration testing, incident-response and backup/restore testing.
8. Ensure raw genomic data and identifiable patient data are not sent to external model providers.

Do not treat local Ollama hosting as a privacy guarantee. Do not store genetic results in browser localStorage. Do not merge two people's records into a shared couple record. Revoking consent must stop future sharing while preserving records that must legally remain in the clinical record. Never sell genetic data or use it for advertising.

## Current scope

The Genetics API intentionally has no patient, screening, variant, or couple endpoints. The knowledge service is an educational retrieval foundation only; it is not a source of patient-specific genetic interpretation.
