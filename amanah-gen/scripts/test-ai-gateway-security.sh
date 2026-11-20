#!/usr/bin/env bash
# Runs the gateway's security regression suite inside the deployed container.
# Tests use synthetic JWT keys and mocked downstream services; AI stays disabled.
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f amanah-gen/compose.amanah.yml --profile amanah-gen)
AI_ID="$("${COMPOSE[@]}" ps -q amanah-ai-gateway)"
[[ -n "$AI_ID" ]] || { echo "ERROR: amanah-ai-gateway is not running." >&2; exit 1; }

TEST_FILE="amanah-gen/ai-gateway/tests/test_gateway_security.py"
[[ -f "$TEST_FILE" ]] || { echo "ERROR: Missing $TEST_FILE" >&2; exit 1; }

REMOTE_TEST="/tmp/amanah-gateway-security-test-$$.py"
cleanup() {
  docker exec -u 0 "$AI_ID" rm -f "$REMOTE_TEST" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Copying security tests into the running AI Gateway container..."
docker cp "$TEST_FILE" "$AI_ID:$REMOTE_TEST"

echo
echo "Running synthetic OIDC, authorization, input-validation, retrieval, and citation tests..."
docker exec "$AI_ID" python "$REMOTE_TEST"

echo
echo "PASS: AI Gateway security regression suite."
echo "No model was enabled and no external model provider was contacted."
