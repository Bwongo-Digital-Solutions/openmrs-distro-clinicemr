# AMANAH GEN Portal (initial UI milestone)

A standalone React/Vite portal served below `/amanah/portal/`. It is intentionally separate from the OpenMRS O3 frontend.

## Included screens

- Individual: overview, screening, results, privacy/sharing, counselling.
- Clinician: overview, screening requests, result review, referrals.
- Genetic counsellor: overview, referral queue, appointments, follow-ups.
- Knowledge reviewer/admin: overview, knowledge registry, audit history.

Only the overview is operational in this milestone. Other screens are explicit non-operational placeholders; they do not read or modify patient records, screening results, consent, knowledge documents, or audit events.

## Authentication

The portal uses Keycloak Authorization Code flow with PKCE S256 via `keycloak-js`. Tokens remain in the adapter's in-memory state; the application does not write tokens, genetic data, or consent to localStorage/sessionStorage. Realm roles control navigation only. Every API must independently enforce authorization server-side.

Runtime configuration is read from `/amanah/portal/config.json`:

```json
{
  "url": "https://YOUR-HOST/auth",
  "realm": "amanah-gen",
  "clientId": "amanah-gen-web"
}
```

The deployed Keycloak client must explicitly allow the portal redirect URI and web origin, for example:

- Redirect URI: `https://YOUR-HOST/amanah/portal/*`
- Web origin: `https://YOUR-HOST`

Do not widen redirect URIs to arbitrary hosts. The current persistent Keycloak client may have development-only localhost settings; update it deliberately using the Keycloak admin API/CLI after reviewing the active production realm. Do not rely on realm import to overwrite an existing persistent client.

## Build

```sh
docker build -t amanah-gen-portal:dev ./amanah-gen/portal
```

The image serves the static application on port 80. Add it as an internal Compose service and route `/amanah/portal/` through the existing HTTPS gateway. Do not publish the portal container directly to the internet or introduce a second public TLS listener.

## Release boundaries

- This is an initial UI shell, not a production-ready patient portal.
- No clinical or personal genetic data is displayed.
- No patient-facing AI chat is enabled; deployment policy remains `AMANAH_AI_ENABLED=false`.
- No couple record or partner sharing workflow is implemented.
- Do not represent navigation visibility as an authorization boundary.
- Before live workflows, implement and independently test server-side consent, record-level authorization, audit logging, encryption, retention, and clinical release controls.
- Validate Arabic translations, right-to-left layout, accessibility, and clinical language with qualified reviewers before deployment.
