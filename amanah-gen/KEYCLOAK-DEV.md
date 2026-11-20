# Keycloak development setup for AMANAH GEN

This guide adds Keycloak as the OIDC identity provider for the AMANAH GEN development stack. It is for isolated development and synthetic test accounts only. Do not use real patient, health, or genetic data.

## Why this setup uses localhost and an SSH tunnel

The VPS currently has an IP address but no domain or HTTPS certificate. Rather than exposing Keycloak login pages and credentials over public HTTP, the Compose service binds port 8081 to 127.0.0.1 on the VPS. Your workstation reaches it through an encrypted SSH tunnel. The public IP is used only as the SSH destination; the OIDC issuer is http://localhost:8081/realms/amanah-gen.

## What the integration adds

- Keycloak 26.8.2 with a dedicated PostgreSQL 16 database and persistent volume.
- A preconfigured amanah-gen realm.
- A public OIDC client named amanah-gen-web using Authorization Code Flow with PKCE; direct password grants and implicit flow are disabled.
- The amanah-gen-api audience mapper.
- Realm roles AMANAH_GEN_AI_USER, AMANAH_GEN_CLINICIAN, AMANAH_GEN_COUNSELLOR, and AMANAH_GEN_ADMIN.
- Keycloak's host port is loopback-only and is not publicly published.
- AI remains disabled by default.

## 1. Update the existing .env safely

Do not replace your current .env; it contains existing OpenMRS database settings. From the repository root, run this script. It preserves existing settings, generates separate Keycloak passwords if they are missing, and does not print password values:

~~~bash
python3 - <<'PY'
from pathlib import Path
import secrets
import os

path = Path('.env')
lines = path.read_text().splitlines() if path.exists() else []
values = {}
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith('#') and '=' in stripped:
        key, value = stripped.split('=', 1)
        values[key] = value

updates = {
    'AMANAH_KEYCLOAK_IMAGE': 'quay.io/keycloak/keycloak:26.8.2',
    'AMANAH_KEYCLOAK_HOSTNAME': 'http://localhost:8081',
    'AMANAH_KEYCLOAK_ADMIN_USERNAME': values.get('AMANAH_KEYCLOAK_ADMIN_USERNAME') or 'admin',
    'AMANAH_OIDC_ISSUER': 'http://localhost:8081/realms/amanah-gen',
    'AMANAH_OIDC_AUDIENCE': 'amanah-gen-api',
    'AMANAH_JWT_JWKS_URL': 'http://amanah-keycloak:8080/realms/amanah-gen/protocol/openid-connect/certs',
    'AMANAH_ALLOWED_ROLE': 'AMANAH_GEN_AI_USER',
    'AMANAH_AI_ENABLED': 'false',
}
for key in ('AMANAH_KEYCLOAK_DB_PASSWORD', 'AMANAH_KEYCLOAK_ADMIN_PASSWORD'):
    current = values.get(key, '')
    if not current or current.startswith('REPLACE_'):
        updates[key] = secrets.token_urlsafe(48)

for key, value in updates.items():
    prefix = key + '='
    lines = [line for line in lines if not line.startswith(prefix)]
    lines.append(prefix + value)

path.write_text('\n'.join(lines).rstrip() + '\n')
os.chmod(path, 0o600)
print('Updated .env safely. Existing OpenMRS credentials were preserved.')
print('Keycloak passwords were generated if missing; values were not displayed.')
PY
~~~

## 2. Validate and start

~~~bash
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen config --quiet
docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen up -d --build
~~~

The Keycloak database uses its own named volume and is separate from OpenMRS MariaDB. Do not delete volumes or run down with -v.

## 3. Open an SSH tunnel from your workstation

Run this on the computer where your browser is running, not inside the VPS:

~~~bash
ssh -N -L 8081:127.0.0.1:8081 root@162.35.56.183
~~~

Keep the terminal open and visit http://localhost:8081 in that computer's browser. Sign in to the Keycloak Administration Console with the administrator username and password configured in the VPS .env. Keep the password private.

Select the amanah-gen realm. The realm import creates the client, audience mapper, and roles. Create a synthetic test user and assign AMANAH_GEN_AI_USER only if that user needs to test the protected AI endpoint. Do not use real patient identities or data.

## 4. Verify the provider and API

On the VPS, run:

~~~bash
curl -fsS http://localhost:8081/realms/amanah-gen/.well-known/openid-configuration
curl -fsS http://localhost:8081/realms/amanah-gen/protocol/openid-connect/certs
curl -i http://localhost/amanah/api/ai/health
curl -i http://localhost/amanah/api/ai/models
~~~

The models request without a bearer token should return 401 Unauthorized. That means the identity provider is configured and the request is rejected because no token was supplied. A 503 indicates the gateway still has missing OIDC configuration. A 403 means a valid token lacks the required role.

## 5. Security boundary

This is a development-only arrangement. SSH encrypts the workstation-to-VPS tunnel, and Docker publishes Keycloak only on VPS loopback. Do not expose port 8081 publicly. Before a pilot, use a domain with HTTPS, production-mode Keycloak, hardened secrets, a reviewed network and identity design, and appropriate security and clinical governance. Keep AMANAH_AI_ENABLED=false until authentication and all required safety reviews are complete.

## 6. Persistent data

Keycloak state is stored in the amanah-keycloak-db-data volume. Back it up alongside the other deployment data. Do not use docker compose down -v or volume-pruning commands as part of routine updates.
