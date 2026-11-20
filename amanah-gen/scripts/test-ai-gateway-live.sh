#!/usr/bin/env bash
# Live HTTPS smoke test against the deployed Nginx -> AI Gateway -> Keycloak setup.
# Supply a short-lived access token for the synthetic AMANAH_GEN_AI_USER test account.
set -Eeuo pipefail

BASE="${AMANAH_AI_BASE_URL:-https://162.35.56.183/amanah/api/ai}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ ! -t 0 ]]; then
  echo "Run interactively so the access token can be entered without echo." >&2
  exit 2
fi

echo "AMANAH GEN live gateway smoke test"
echo "Base: $BASE"
read -r -s -p "Paste short-lived synthetic test-user access token (input hidden): " ACCESS_TOKEN
echo
[[ -n "$ACCESS_TOKEN" ]] || { echo "ERROR: No token supplied." >&2; exit 2; }

# Keep the bearer value out of curl's process arguments and shell history.
umask 077
printf 'header = "Authorization: Bearer %s"\n' "$ACCESS_TOKEN" > "$TMP/auth.curl"
unset ACCESS_TOKEN

request() {
  local name="$1" expected="$2"
  shift 2
  local actual
  actual="$(curl --silent --show-error --connect-timeout 8 --max-time 20 \
    -o "$TMP/response" -w '%{http_code}' "$@")"
  printf '%-48s expected=%s actual=%s\n' "$name" "$expected" "$actual"
  [[ "$actual" == "$expected" ]] || {
    echo "FAIL: $name" >&2
    cat "$TMP/response" >&2
    exit 1
  }
}

echo
echo "===== 1. DEPLOYMENT POLICY ====="
request "Gateway health" 200 "$BASE/health"
python3 - "$TMP/response" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("service") != "amanah-ai-gateway":
    raise SystemExit("FAIL: health endpoint is not the AI Gateway")
if data.get("ai_enabled") is not False:
    raise SystemExit("FAIL: AI must remain disabled during this security test")
print("PASS: AI assistance is disabled.")
PY

echo
echo "===== 2. AUTHENTICATION ====="
request "No token rejected" 401 "$BASE/models"
request "Malformed token rejected" 401 \
  -H "Authorization: Bearer not-a-valid-token" "$BASE/models"

echo
echo "===== 3. VALID OIDC USER AND ROLE ====="
request "Authorised test user can read models" 200 \
  --config "$TMP/auth.curl" "$BASE/models"
request "Authorised test user can read tools" 200 \
  --config "$TMP/auth.curl" "$BASE/tools"
python3 - "$TMP/response" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("tools") != []:
    raise SystemExit("FAIL: unexpected tools are exposed by the gateway")
print("PASS: no database, SQL, or patient lookup tools are exposed.")
PY

echo
echo "===== 4. INPUT BOUNDARY ====="
request "Caller-supplied clinical context rejected" 422 \
  --config "$TMP/auth.curl" \
  -H "Content-Type: application/json" \
  --data '{"question":"Explain this","language":"en","clinical_context":"synthetic untrusted context"}' \
  "$BASE/chat"

echo
echo "===== 5. AI DISABLED GUARD ====="
request "Chat blocked while AI is disabled" 503 \
  --config "$TMP/auth.curl" \
  -H "Content-Type: application/json" \
  --data '{"question":"What does genetic screening mean?","language":"en"}' \
  "$BASE/chat"

echo
echo "PASS: live HTTPS authentication, role-gated access, input boundary, and disabled-AI guard."
echo "Citation and approved-source behaviour are covered by test-ai-gateway-security.sh."
