# AMANAH GEN Knowledge Service

Internal, read-only retrieval API backed by SQLite FTS5. The service is not exposed on a host port. Only documents explicitly approved by a human reviewer can appear in search results.

## Lifecycle

1. Place a UTF-8 `.md` or `.txt` source file in `amanah-gen/knowledge-input/`.
2. Copy it into the running container (or mount it into an approved administrative workflow).
3. Register it using `manage.py ingest`. Registration creates a **pending** document and indexes its chunks, but pending content is never returned by search.
4. A qualified content reviewer verifies source authority, accuracy, version, language, and suitability, then approves the exact document ID.
5. Approved documents become retrievable. Withdrawn documents are immediately excluded from retrieval.

Example (run from the repository root; replace the metadata and path with real reviewed material):

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
  --language en

docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py list
```

After an authorised reviewer has independently checked the material, approve using the document ID printed by the ingest command:

```sh
docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py approve --id DOCUMENT_UUID --approved-by "REVIEWER_IDENTIFIER"
```

To stop future retrieval of a source:

```sh
docker exec openmrs-distro-clinicemr-amanah-knowledge-api-1 \
  python /app/manage.py withdraw --id DOCUMENT_UUID
```

Do not approve example content, unverified translations, user uploads, promotional material, or sources that have not been reviewed by the appropriate clinical/content governance team. The sample source URL above is illustrative and is not an approved reference.

## API

- `GET /health`: service and document-count health information; no document content.
- `POST /internal/search`: internal retrieval endpoint. Requires `X-Knowledge-Token` and returns only approved source passages.

The retrieval credential is separate from any document-administration mechanism. It is shared only by the Knowledge API and AI Gateway. It must be a long random secret and must not be committed to Git. The service has no public port mapping.

## Storage and limitations

- SQLite database persists in the dedicated `amanah-knowledge-data` named volume.
- FTS5 keyword retrieval is intentionally lightweight; it is not semantic/vector search.
- Only UTF-8 Markdown and plain text are accepted by the initial ingestion CLI.
- Ingestion is pending by default. Approval and withdrawal are explicit, audited in document metadata, and performed inside the container by an administrator.
- This is a development foundation, not a validated clinical knowledge system. Establish reviewer identity, change control, immutable audit retention, backups, source licensing, periodic review/expiry, and disaster recovery before production.
