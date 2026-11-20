# AMANAH GEN deployment guide

This guide deploys the AMANAH GEN integration scaffold with the ClinicEMR services in this repository. It is for development and controlled integration testing only.

> **Not production-ready:** This branch does not yet include validated genetic screening workflows, clinical genetic interpretation, consent management, encrypted genetic-record storage, durable central audit logging, or a complete AMANAH GEN user interface. Do not connect real patient/genomic data or use this scaffold to make care decisions.

## 1. Choose the host

### Recommended: a new server or VM

Use a separate Ubuntu server/VM. This avoids collisions with an existing Bahmni/ClinicEMR deployment, especially HTTP port 80, Docker networks, Compose project names, and persistent volumes.

### If sharing a host with Bahmni or another application

Check whether port 80 is occupied:

~~~
sudo ss -ltnp | grep ':80 '
~~~

The base Compose file publishes gateway port 80 as 80:80. If that port is already in use, preferably use a separate VM/server. Alternatively, change the gateway mapping in docker-compose.yml to an unused host port, for example:

~~~
ports:
  - "8088:80"
~~~

Then use http://SERVER_IP:8088/. Confirm the port is allowed by the firewall. Keep this deployment's Compose project and volumes separate. **Do not reuse, rename, delete, or attach existing Bahmni database volumes.** Never run volume deletion commands as a shortcut.

## 2. Prepare the server and clone the branch

Install Docker Engine and the Docker Compose plugin. Verify:

~~~
docker --version
docker compose version
~~~

Clone the repository and check out the integration branch:

~~~
git clone https://github.com/Bwongo-Digital-Solutions/openmrs-distro-clinicemr.git
cd openmrs-distro-clinicemr
git fetch origin
git checkout amanah-gen-integration
git pull --ff-only origin amanah-gen-integration
~~~

If already cloned, inspect `git status --short` before pulling. Preserve and review any local modifications; do not discard them to make the pull succeed.

## 3. Configure environment variables and secrets

Compose reads `.env` from the repository root. If `.env` already exists, do not overwrite it; add/update only the required variables.

For a fresh deployment, follow the deployment environment example and add the base ClinicEMR settings. Keep the existing database credentials unchanged when reusing an existing deployment.

Generate a dedicated retrieval secret on the server:

~~~
openssl rand -hex 32
~~~

Set the generated value as `AMANAH_KNOWLEDGE_RETRIEVAL_TOKEN` in the untracked `.env` file. Do not use an OIDC user token, Keycloak password, or database password for this purpose. Do not paste the secret into chat or commit it. Protect `.env`:

~~~
chmod 600 .env
~~~

Keep these settings:

~~~
AMANAH_AI_ENABLED=false
AMANAH_OLLAMA_MODEL=qwen3:1.7b
AMANAH_MAX_INPUT_CHARS=4000
AMANAH_KNOWLEDGE_RETRIEVAL_TOKEN=REPLACE_WITH_A_UNIQUE_RANDOM_SECRET
~~~

Set the exact OIDC issuer, audience, and JWKS URL for the active identity provider. The gateway validates token signature and claims and requires the configured role. Confirm the role claim format against the identity provider; do not assume a role mapping.

Never commit `.env`, passwords, signing keys, tokens, or other secrets. Changing database passwords in `.env` does not automatically change credentials inside an already initialized database volume. Coordinate credential rotation with the database itself.

## 4. Validate the Compose configuration

Run from the repository root:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config --quiet
~~~

Fix any errors before starting containers. You can inspect the rendered configuration by removing `--quiet`, but take care not to share output that may contain environment values.

## 5. Build and start the knowledge and AI services

For an existing ClinicEMR deployment, build and recreate only the two services being introduced/updated:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build amanah-knowledge-api amanah-ai-gateway
~~~

This command does not request recreation of OpenMRS, its database, Keycloak, or Ollama. It creates a separate `amanah-knowledge-data` volume for the knowledge registry. Do not run `down -v`, volume-pruning commands, or broad cleanup commands.

## 6. Verify service health

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen ps amanah-knowledge-api amanah-ai-gateway
docker logs --tail=80 openmrs-distro-clinicemr-amanah-knowledge-api-1
docker logs --tail=80 openmrs-distro-clinicemr-amanah-ai-gateway-1
~~~

The knowledge service health endpoint is internal to the Compose network. The AI gateway health endpoint remains available through the existing configured gateway route. A healthy endpoint confirms process availability, not clinical approval.

## 7. Register and approve knowledge documents

The knowledge API accepts only UTF-8 Markdown/text through its container-local administration CLI. See [knowledge-api/README.md](knowledge-api/README.md) for the exact workflow.

- Ingestion creates a pending document.
- Pending documents are never returned by retrieval.
- A qualified reviewer checks authority, content, language, version, licensing and clinical suitability.
- An authorised reviewer explicitly approves the document using a reviewer identifier.
- Withdrawal excludes a document from future retrieval.
- Document events are recorded in the SQLite registry. This is not a tamper-proof central audit system.

Do not seed the system with invented clinical content or assume that an arbitrary website is an approved source. Start with no approved documents until the clinical/content governance team has selected and reviewed real sources.

## 8. Configure identity and test authenticated access

Before any chat test:

1. Configure the identity provider to issue short-lived access tokens for the expected API audience.
2. Assign the AMANAH_GEN_AI_USER role only to authorised test users.
3. Set OIDC issuer, audience, and JWKS URL to the exact active provider values.
4. Test signature, issuer, audience, expiry, subject, and role validation with test accounts.
5. Confirm raw genomic data and identifiable patient data are not sent to external model providers.
6. Obtain security, privacy, and clinical governance approval.

The authenticated `POST /amanah/api/ai/chat` request accepts only a question and language, for example:

~~~
{"question":"What does genetic screening mean?","language":"en"}
~~~

Supported languages are `en`, `ar`, and `auto`. Caller-supplied explanation context is rejected. The gateway retrieves approved passages itself and returns source metadata. If no approved passages match, it returns a safe no-answer response without calling Ollama.

**Keep `AMANAH_AI_ENABLED=false`.** Do not enable patient-facing AI merely because the model and retrieval API respond. First validate source coverage, source faithfulness, prompt-injection resilience, Arabic/English quality, bias, hallucinations, escalation pathways, and clinical safety with qualified reviewers.

## 9. Provision a local Ollama model (optional)

Only do this after reviewing the model and confirming the host has sufficient memory and disk. Ollama is not published on a host port.

Set `AMANAH_OLLAMA_MODEL` in `.env` to the reviewed local model identifier, then pull and verify it:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen exec amanah-ollama ollama pull MODEL_NAME
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen exec amanah-ollama ollama list
~~~

Pin and review the Ollama image and model digest before production. Local hosting is not by itself a privacy or clinical-safety guarantee.

## 10. Access the application

Open the configured server address in a browser. The OpenMRS frontend is the ClinicEMR shell. API routes are under `/amanah/api/`. This branch does not yet include a complete AMANAH GEN user interface.

## 11. Stop and restart without deleting data

Stop containers while preserving persistent data:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen stop
~~~

Start them again:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d
~~~

Do not use `docker compose down -v` or volume-pruning commands on a host with other deployments.

## 12. Backups and production readiness

Back up the knowledge volume as well as the existing application data, using an approved encrypted backup process. Test restoration in an isolated environment. The knowledge SQLite database uses WAL mode; use a SQLite-consistent backup method (such as SQLite's backup API or a quiesced volume backup) rather than copying only the main database file while writes are active.

Before production or real-patient use, complete at minimum:

- Applicable legal/privacy assessment, including UAE and any other jurisdiction involved.
- Clinical safety case and review by qualified genetics professionals.
- Server-side, purpose-specific consent, with independent consent from each person in any couple workflow.
- Encryption, key management, retention/deletion controls, central append-only audit events, access reviews, and incident response.
- Approved and licensed knowledge sources, version/review dates, Arabic/English translation review, and model validation.
- Threat modelling, penetration testing, monitoring, incident response, and backup/restore testing.
- Formal approval of the complete clinical workflow and all user-facing explanations.

Never sell genetic data or use it for advertising. Do not merge individuals' records into a shared couple record. Declining or revoking sharing consent must not disclose a person's result or screening participation to another person. Follow applicable record-retention obligations when processing withdrawal requests.
