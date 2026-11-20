# AMANAH GEN Knowledge Service

Internal, read-only retrieval API backed by SQLite FTS5. The service is not exposed on a host port. Only documents explicitly approved by a human reviewer can appear in search results.

## Lifecycle

1. Prepare a UTF-8 `.md` or `.txt` source that is suitable for patient education and whose licensing permits this use.
2. Copy it into the running knowledge container.
3. Register it using `manage.py ingest`. Registration creates a **pending** document and indexes its chunks, but pending content is never returned by search.
4. A qualified reviewer independently verifies source authority, clinical accuracy, version, language/translation, and suitability, then approves the exact document ID using their reviewer identifier.
5. Approved documents become retrievable. Withdrawn documents are immediately excluded from new retrievals.
6. Use `history` to inspect the registry events for a document.

Example (run from the repository root; replace the illustrative metadata and path with an actual reviewed source):

```sh
docker cp ./amanah-gen/knowledge-input/example.md \
  openmrs-distro-clinicemr-amanah-knowledge-api-1:/tmp/example.md

docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py ingest \
  --file /tmp/example.md \
  --title "Reviewed patient education resource" \
  --source "https://example.org/resource" \
  --publisher "Publishing organisation" \
  --version "2026-01" \
  --language en \
  --registered-by "CONTENT-ADMIN-IDENTIFIER"

docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py list
```

After a qualified reviewer has independently checked the material, approve using the document ID printed by the ingest command:

```sh
docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py approve \
  --id DOCUMENT_UUID \
  --approved-by "REVIEWER-IDENTIFIER" \
  --note "Review record or ticket reference"
```

To stop future retrieval of a source:

```sh
docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py withdraw \
  --id DOCUMENT_UUID \
  --withdrawn-by "REVIEWER-IDENTIFIER" \
  --note "Reason for withdrawal"
```

Inspect the document event history:

```sh
docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py history --id DOCUMENT_UUID
```

Do not approve illustrative content, unverified translations, user uploads, promotional material, or sources that have not been reviewed by the appropriate clinical/content governance team. The sample source URL above is illustrative and is not an approved reference.

## API

- `GET /health`: service and approved-document count; no document content.
- `POST /internal/search`: internal retrieval endpoint. Requires `X-Knowledge-Token` and returns only approved source passages.

The retrieval credential is separate from user OIDC tokens and document administration. It is shared only by the Knowledge API and AI Gateway. It must be a long random secret and must not be committed to Git. The service has no public port mapping.

## Storage and limitations

- SQLite database persists in the dedicated `amanah-knowledge-data` named volume.
- FTS5 keyword retrieval is intentionally lightweight; it is not semantic/vector search.
- Only UTF-8 Markdown and plain text are accepted by the initial ingestion CLI (1 MB maximum per file).
- Ingestion is pending by default. Approval and withdrawal are explicit and create actor-attributed event records.
- The event table is an application-level audit trail, not tamper-proof. Production requires central append-only audit storage, access controls, backups, and periodic audit review.
- Establish reviewer identity, separation of duties, change control, source licensing, periodic review/expiry, and disaster recovery before production.
