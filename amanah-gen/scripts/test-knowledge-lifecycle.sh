#!/usr/bin/env bash
# Run from the repository root or any directory. Uses only the AMANAH GEN
# Knowledge API and its own persistent volume; never touches OpenMRS data.
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen)
KNOWLEDGE_ID="$("${COMPOSE[@]}" ps -q amanah-knowledge-api)"
AI_ID="$("${COMPOSE[@]}" ps -q amanah-ai-gateway)"

[[ -n "$KNOWLEDGE_ID" ]] || { echo "ERROR: amanah-knowledge-api is not running." >&2; exit 1; }
[[ -n "$AI_ID" ]] || { echo "ERROR: amanah-ai-gateway is not running." >&2; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
PHRASE="zxqv${STAMP//[^a-zA-Z0-9]/}"
HOST_DOC="$(mktemp --suffix=.txt)"
CONTAINER_DOC="/tmp/amanah-knowledge-lifecycle-$STAMP.txt"
E2E_TEST="amanah-gen/ai-gateway/tests/test_gateway_live_knowledge.py"
REMOTE_E2E="/tmp/amanah-gateway-live-knowledge-$STAMP.py"
DOC_ID=""
APPROVED=0

cleanup() {
  if [[ -n "$DOC_ID" && "$APPROVED" -eq 1 ]]; then
    docker exec "$KNOWLEDGE_ID" python /app/manage.py withdraw \
      --id "$DOC_ID" --withdrawn-by "lifecycle-test-cleanup" \
      --note "Automatic cleanup after lifecycle test interruption." >/dev/null 2>&1 || true
  fi
  docker exec -u 0 "$KNOWLEDGE_ID" rm -f "$CONTAINER_DOC" >/dev/null 2>&1 || true
  docker exec -u 0 "$AI_ID" rm -f "$REMOTE_E2E" >/dev/null 2>&1 || true
  rm -f "$HOST_DOC"
}
trap cleanup EXIT

cat >"$HOST_DOC" <<EOF
AMANAH GEN SYNTHETIC TECHNICAL TEST ONLY.

The fictional phrase $PHRASE is a non-clinical marker used only to verify
document registration, indexing, approval, retrieval, withdrawal, and audit
history. It has no medical, genetic, diagnostic, counselling, or clinical
meaning and must never guide patient care.

This test content is deliberately synthetic and is not an approved clinical
reference. The test script will withdraw this record after the checks.
EOF
chmod 644 "$HOST_DOC"

echo "===== 1. REGISTER SYNTHETIC DOCUMENT AS PENDING ====="
docker cp "$HOST_DOC" "$KNOWLEDGE_ID:$CONTAINER_DOC" >/dev/null
INGEST_OUTPUT="$(docker exec "$KNOWLEDGE_ID" python /app/manage.py ingest \
  --file "$CONTAINER_DOC" \
  --title "AMANAH GEN Automated Lifecycle Test $STAMP" \
  --source "https://example.invalid/amanah-gen-lifecycle-test" \
  --publisher "AMANAH GEN automated technical test" \
  --version "$STAMP" --language en \
  --registered-by "lifecycle-test-runner")"
printf '%s\n' "$INGEST_OUTPUT"
DOC_ID="$(printf '%s\n' "$INGEST_OUTPUT" | awk '/Document registered as PENDING:/ {print $NF}')"
[[ "$DOC_ID" =~ ^[0-9a-f-]{36}$ ]] || { echo "ERROR: Could not parse document ID." >&2; exit 1; }

search_check() {
  local expected="$1"
  docker exec -i "$AI_ID" python - "$expected" "$PHRASE" "$DOC_ID" <<'PY'
import json, os, sys, urllib.request
expected, phrase, doc_id = int(sys.argv[1]), sys.argv[2], sys.argv[3]
base = os.getenv("KNOWLEDGE_API_URL", "http://amanah-knowledge-api:8000").rstrip("/")
token = os.getenv("KNOWLEDGE_RETRIEVAL_TOKEN", "")
if not token:
    raise SystemExit("FAIL: gateway retrieval credential is not configured")
payload = json.dumps({"question": phrase, "language": "en", "limit": 5}).encode()
req = urllib.request.Request(
    base + "/internal/search", data=payload,
    headers={"Content-Type": "application/json", "X-Knowledge-Token": token},
    method="POST",
)
with urllib.request.urlopen(req, timeout=10) as response:
    result = json.loads(response.read())
items = result.get("results", [])
matches = [x for x in items if x.get("document_id") == doc_id and phrase in x.get("content", "")]
print("HTTP:", response.status)
print("Matching test documents:", len(matches))
if len(matches) != expected:
    raise SystemExit(f"FAIL: expected {expected} matching document(s), got {len(matches)}")
print("PASS")
PY
}

echo
echo "===== 2. PENDING DOCUMENT MUST NOT BE RETRIEVABLE ====="
search_check 0

echo
echo "===== 3. APPROVE DOCUMENT WITH TEST REVIEWER IDENTITY ====="
docker exec "$KNOWLEDGE_ID" python /app/manage.py approve \
  --id "$DOC_ID" --approved-by "lifecycle-test-reviewer" \
  --note "Automated synthetic lifecycle test only; not clinical approval."
APPROVED=1

echo
echo "===== 4. APPROVED DOCUMENT MUST BE RETRIEVABLE ====="
search_check 1

echo
echo "===== 5. EXERCISE THE AI GATEWAY AGAINST THE REAL APPROVED KNOWLEDGE API ====="
[[ -f "$E2E_TEST" ]] || { echo "ERROR: Missing $E2E_TEST" >&2; exit 1; }
docker cp "$E2E_TEST" "$AI_ID:$REMOTE_E2E" >/dev/null
docker exec "$AI_ID" python "$REMOTE_E2E" "$DOC_ID" "$PHRASE"

echo
echo "===== 6. WITHDRAW DOCUMENT ====="
docker exec "$KNOWLEDGE_ID" python /app/manage.py withdraw \
  --id "$DOC_ID" --withdrawn-by "lifecycle-test-reviewer" \
  --note "Automated synthetic lifecycle test completed."
APPROVED=0

echo
echo "===== 7. WITHDRAWN DOCUMENT MUST NOT BE RETRIEVABLE ====="
search_check 0

echo
echo "===== 8. VERIFY AUDIT EVENTS ====="
HISTORY="$(docker exec "$KNOWLEDGE_ID" python /app/manage.py history --id "$DOC_ID")"
printf '%s\n' "$HISTORY"
for action in registered approved withdrawn; do
  grep -q "^$action |" <<<"$HISTORY" || {
    echo "FAIL: missing audit event: $action" >&2
    exit 1
  }
done
grep -q "lifecycle-test-runner" <<<"$HISTORY"
grep -q "lifecycle-test-reviewer" <<<"$HISTORY"

echo
echo "PASS: Knowledge API lifecycle, retrieval gating, withdrawal, and audit history."
echo "Test document remains WITHDRAWN so its audit trail is retained."
echo "Document ID: $DOC_ID"
