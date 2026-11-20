# AMANAH GEN deployment guide

This guide deploys the AMANAH GEN integration scaffold with the ClinicEMR services in this repository. It is for development and controlled integration testing only.

> **Not production-ready:** This branch does not yet include validated genetic screening workflows, clinical genetic interpretation, consent management, encrypted genetic-record storage, durable audit logging, or a complete AMANAH GEN user interface. Do not connect real patient/genomic data or use this scaffold to make care decisions.

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

If already cloned, run the fetch, checkout, and pull commands from the repository root.

## 3. Configure environment variables and secrets

Compose reads .env from the repository root. If .env already exists, do not overwrite it; back it up and add/update only the required variables.

For a fresh deployment:

~~~
cp amanah-gen/deployment.env.example .env
~~~

Generate two different strong passwords:

~~~
openssl rand -hex 32
openssl rand -hex 32
~~~

Add the base ClinicEMR database settings and AMANAH GEN settings to .env. Example:

~~~
TAG=qa
OMRS_DB_USER=openmrs
OMRS_DB_PASSWORD=REPLACE_WITH_A_UNIQUE_STRONG_PASSWORD
MYSQL_ROOT_PASSWORD=REPLACE_WITH_A_DIFFERENT_UNIQUE_STRONG_PASSWORD

AMANAH_AI_ENABLED=false
AMANAH_OLLAMA_IMAGE=ollama/ollama:latest
AMANAH_OLLAMA_MODEL=
AMANAH_OIDC_ISSUER=
AMANAH_OIDC_AUDIENCE=
AMANAH_JWT_JWKS_URL=
AMANAH_ALLOWED_ROLE=AMANAH_GEN_AI_USER
AMANAH_MAX_INPUT_CHARS=4000
~~~

Set the exact issuer, audience, and JWKS URL from your identity provider before testing authenticated AI access. The gateway validates token signature and claims and requires the configured role. Confirm the role claim format against your identity provider; do not assume a role mapping.

Protect the file:

~~~
chmod 600 .env
~~~

Never commit .env, passwords, signing keys, tokens, or other secrets. Changing database passwords in .env does not automatically change credentials inside an already initialized database volume. Coordinate credential rotation with the database itself.

Keep AMANAH_AI_ENABLED=false until OIDC, role assignment, model approval, and security/clinical governance checks are complete.

## 4. Validate the Compose configuration

Run from the repository root:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config --quiet
~~~

Fix any errors before starting containers. You can inspect the rendered configuration by removing --quiet, but take care not to share output that may contain environment values.

## 5. Build and start

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build
~~~

This starts the ClinicEMR services in this repository plus the opt-in AMANAH GEN services. It creates/uses this Compose project's own named volumes. Do not run against a production deployment without a reviewed migration, backup, and rollback plan.

## 6. Check containers and health endpoints

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen ps
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen logs --tail=100
curl -i http://localhost/amanah/api/ai/health
curl -i http://localhost/amanah/api/genetics/health
~~~

If you changed the gateway host port to 8088, use http://localhost:8088 for the curl requests. A healthy endpoint only confirms that the service responds; it does not mean clinical functionality is implemented or approved.

## 7. Provision a local Ollama model (optional)

Only do this after reviewing the model and confirming the host has sufficient memory and disk. Ollama is not published on a host port.

Set AMANAH_OLLAMA_MODEL in .env to the approved model identifier, then pull and verify it:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen exec amanah-ollama ollama pull MODEL_NAME
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen exec amanah-ollama ollama list
~~~

Replace MODEL_NAME with the model approved by project reviewers. Pin and review the Ollama image and model version/digest before production. Local hosting is not by itself a privacy or clinical-safety guarantee.

## 8. Configure identity and test authenticated access

Before enabling chat:

1. Configure the identity provider to issue short-lived access tokens for the expected API audience.
2. Assign the AMANAH_GEN_AI_USER role only to authorized users.
3. Set AMANAH_OIDC_ISSUER, AMANAH_OIDC_AUDIENCE, and AMANAH_JWT_JWKS_URL to the exact provider values.
4. Test signature, issuer, audience, expiry, subject, and role validation with test accounts.
5. Confirm raw genomic data and identifiable patient data are not sent to external model providers.
6. Obtain security, privacy, and clinical governance approval.

Only after these checks should an administrator deliberately set AMANAH_AI_ENABLED=true and recreate the AI service:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build amanah-ai-gateway
~~~

Test only with synthetic/non-identifiable content. The AI service is limited to explaining clinician-approved information. It must not diagnose, classify variants, independently calculate inherited-disease risk, infer carrier status, or recommend marriage/reproductive decisions. It does not replace qualified genetic counselling.

## 9. Access the application

Open the server address in a browser:

- Default: http://SERVER_IP/
- If using the alternate port: http://SERVER_IP:8088/

The OpenMRS frontend is the ClinicEMR shell. API routes are under /amanah/api/. This branch does not yet include a complete AMANAH GEN user interface.

## 10. Stop and restart without deleting data

Stop containers while preserving persistent data:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen stop
~~~

Start them again:

~~~
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d
~~~

Do not use docker compose down -v unless you intentionally want to delete this project's named volumes and have verified backups. Never use volume-pruning commands on a host with other deployments.

## 11. Backups and production readiness

Establish and test backups for MariaDB and the OpenMRS application-data volume. Keep backups encrypted and access-controlled, and test restoration in an isolated environment.

Before production or real-patient use, complete at minimum:

- UAE legal/privacy assessment for applicable health and genetic data requirements.
- Clinical safety case and review by qualified genetics professionals.
- Server-side, purpose-specific consent, with independent consent from each person in any couple workflow.
- Encrypted storage, key management, retention/deletion controls, access reviews, and durable audit events.
- Arabic/English content review, approved knowledge sources, and model validation.
- Threat modelling, penetration testing, monitoring, incident response, and backup/restore testing.
- Formal approval of the complete clinical workflow and all user-facing explanations.

Never sell genetic data or use it for advertising. Do not merge individuals' records into a shared couple record. Declining or revoking sharing consent must not disclose a person's result or screening participation to another person. Follow applicable record-retention obligations when processing withdrawal requests.
