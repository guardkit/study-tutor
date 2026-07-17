#!/usr/bin/env bash
# provision-live-suite.sh — Batch C2 (weekend handoff §7): create the `live-suite`
# confidential client (Direct Access Grant) in the study-tutor realm, and
# optionally the `alex` test user. Deliberately NOT in realm-as-code (§1) —
# imperative admin-API provisioning, idempotent, attended (Batch C).
#
# Usage:
#   ./provision-live-suite.sh [--with-alex] [--rotate-secret]
#
# Reads admin creds from deploy/keycloak/.env.deploy (gitignored):
#   KC_BOOTSTRAP_ADMIN_USERNAME / KC_BOOTSTRAP_ADMIN_PASSWORD
# Optional env: KC_BASE (default https://whitestocks.tailebf801.ts.net:8443),
#   ALEX_PASSWORD (required with --with-alex).
# Writes the KCA2-006 env surface to deploy/keycloak/.env.live-suite (gitignored):
#   STUDY_TUTOR_OIDC_ISSUER / STUDY_TUTOR_LIVE_SUITE_CLIENT_ID /
#   STUDY_TUTOR_LIVE_SUITE_CLIENT_SECRET / STUDY_TUTOR_LIVE_SUITE_USERS
# Secrets land ONLY in env files — never in git, never echoed to the terminal.

set -euo pipefail
cd "$(dirname "$0")"

KC_BASE="${KC_BASE:-https://whitestocks.tailebf801.ts.net:8443}"
REALM=study-tutor
WITH_ALEX=false
ROTATE=false
for a in "$@"; do
  case "$a" in
    --with-alex) WITH_ALEX=true ;;
    --rotate-secret) ROTATE=true ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

[ -f .env.deploy ] || { echo "missing deploy/keycloak/.env.deploy (admin creds)" >&2; exit 1; }
# shellcheck disable=SC1091
set -a; source .env.deploy; set +a
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?not in .env.deploy}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?not in .env.deploy}"

api() { # api METHOD PATH [JSON_BODY]
  local m="$1" p="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -fsS -X "$m" "${KC_BASE}/admin/realms/${REALM}${p}" \
      -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d "$body"
  else
    curl -fsS -X "$m" "${KC_BASE}/admin/realms/${REALM}${p}" \
      -H "Authorization: Bearer ${TOKEN}"
  fi
}

echo "== admin token (realm master, admin-cli) =="
TOKEN=$(curl -fsS "${KC_BASE}/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  --data-urlencode "username=${KC_BOOTSTRAP_ADMIN_USERNAME}" \
  --data-urlencode "password=${KC_BOOTSTRAP_ADMIN_PASSWORD}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

echo "== client live-suite: create-if-absent =="
CID=$(api GET "/clients?clientId=live-suite" | python3 -c 'import sys,json;r=json.load(sys.stdin);print(r[0]["id"] if r else "")')
if [ -z "$CID" ]; then
  api POST "/clients" '{
    "clientId": "live-suite",
    "name": "Live contract suite (KC-G2, Direct Access Grant)",
    "description": "KCA2-006/KC-G2 token-minting client. Confidential, DAG only. Provisioned imperatively (handoff §7 C2) - deliberately not realm-as-code.",
    "enabled": true,
    "protocol": "openid-connect",
    "publicClient": false,
    "directAccessGrantsEnabled": true,
    "standardFlowEnabled": false,
    "implicitFlowEnabled": false,
    "serviceAccountsEnabled": false,
    "protocolMappers": [
      {
        "name": "student_id",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": false,
        "config": {
          "user.attribute": "student_id",
          "claim.name": "student_id",
          "jsonType.label": "String",
          "id.token.claim": "true",
          "access.token.claim": "true",
          "userinfo.token.claim": "true"
        }
      },
      {
        "name": "aud-study-tutor-app",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "consentRequired": false,
        "config": {
          "included.client.audience": "study-tutor-app",
          "id.token.claim": "false",
          "access.token.claim": "true"
        }
      }
    ]
  }'
  CID=$(api GET "/clients?clientId=live-suite" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
  echo "created client live-suite (${CID})"
else
  echo "client live-suite already present (${CID}) — leaving config as-is"
fi

if $ROTATE; then
  echo "== rotating client secret =="
  api POST "/clients/${CID}/client-secret" >/dev/null
fi
SECRET=$(api GET "/clients/${CID}/client-secret" | python3 -c 'import sys,json;print(json.load(sys.stdin)["value"])')

USERS="lilymay"
if $WITH_ALEX; then
  echo "== user alex: create-if-absent =="
  : "${ALEX_PASSWORD:?--with-alex needs ALEX_PASSWORD in env}"
  AID=$(api GET "/users?username=alex&exact=true" | python3 -c 'import sys,json;r=json.load(sys.stdin);print(r[0]["id"] if r else "")')
  if [ -z "$AID" ]; then
    api POST "/users" "$(python3 - <<PY
import json, os
print(json.dumps({
  "username": "alex", "enabled": True, "emailVerified": True,
  "firstName": "Alex", "lastName": "Test",
  "attributes": {"student_id": ["alex"]},
  "credentials": [{"type": "password", "value": os.environ["ALEX_PASSWORD"], "temporary": False}],
}))
PY
)"
    AID=$(api GET "/users?username=alex&exact=true" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
    RID=$(api GET "/roles/student" | python3 -c 'import sys,json;r=json.load(sys.stdin);print(r["id"])')
    api POST "/users/${AID}/role-mappings/realm" "[{\"id\":\"${RID}\",\"name\":\"student\"}]"
    echo "created user alex (role student, student_id=alex)"
  else
    echo "user alex already present (${AID}) — leaving as-is"
  fi
  USERS="lilymay,alex"
fi

echo "== writing .env.live-suite (gitignored; secret not echoed) =="
umask 077
cat > .env.live-suite <<ENV
# Generated by provision-live-suite.sh — KCA2-006 env surface. NEVER commit.
STUDY_TUTOR_OIDC_ISSUER=${KC_BASE}/realms/${REALM}
STUDY_TUTOR_LIVE_SUITE_CLIENT_ID=live-suite
STUDY_TUTOR_LIVE_SUITE_CLIENT_SECRET=${SECRET}
STUDY_TUTOR_LIVE_SUITE_USERS=${USERS}
ENV
echo "done: client live-suite ready; env at deploy/keycloak/.env.live-suite (users: ${USERS})"
echo "note: user passwords for the DAG grant stay in .env.deploy — the harness reads them from env, not from this file"
