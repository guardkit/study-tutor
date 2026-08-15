#!/usr/bin/env bash
# FEAT-AUTH-004 R1 — apply the reachy-robot audience mapper to the LIVE realm.
#
# WHAT: adds ONE protocol mapper (aud-study-tutor-app) to ONE client
# (reachy-robot) on the live NAS Keycloak, so a device-grant token carries the
# audience the server hard-pins. Realm-as-code already has it (b41bc7a, with
# the realm-invariant tests); this converges the live realm with the repo.
# The identical mapper block was applied to the live-suite client in July by
# provision-live-suite.sh — same precedent, same shape, same API.
#
# WHERE: run this wherever the Keycloak admin credential lives (the Mac, per
# custody — the spark deliberately holds neither .env.deploy nor the
# keycloak-env sops file). Attended, per the playbook: live surfaces stay a
# human step.
#
# SAFE: additive only, idempotent (re-run says "already applied"), and the
# rollback is printed with the real mapper id after the apply. It never
# touches the study-tutor-app client, users, sessions, or any other realm
# state. It is NOT a realm import.
set -euo pipefail
cd "$(dirname "$0")"

REALM="study-tutor"
CLIENT_ID_NAME="reachy-robot"
KC_BASE="${KC_BASE:-https://whitestocks.tailebf801.ts.net:8443}"

# --- config load — byte-for-byte the provision-live-suite.sh dual-mode block --
SOPS_BIN="${SOPS_BIN:-$HOME/.local/bin/sops}"
SECRETS_ROOT="${SECRETS_ROOT:-$HOME/.config/fleet-secrets}"
ENC_ENV="${ENC_ENV:-study-tutor/keycloak-env-deploy.enc.env}"
if [ -f .env.deploy ]; then
    # shellcheck disable=SC1091
    set -a; source .env.deploy; set +a
elif [ -x "${SOPS_BIN}" ] && [ -f "${SECRETS_ROOT}/${ENC_ENV}" ]; then
    set -a
    # shellcheck disable=SC1090
    source <( cd "${SECRETS_ROOT}" && "${SOPS_BIN}" -d "${ENC_ENV}" )
    set +a
else
    echo "missing both deploy/keycloak/.env.deploy and ${SECRETS_ROOT}/${ENC_ENV} (admin creds)" >&2; exit 1
fi
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

echo "== R1: aud-study-tutor-app mapper -> client ${CLIENT_ID_NAME} on ${KC_BASE} =="
read -r -p "Apply to the LIVE realm '${REALM}'? [y/N] " answer
[ "${answer}" = "y" ] || { echo "aborted — nothing touched"; exit 0; }

echo "== admin token (realm master, admin-cli) =="
TOKEN=$(curl -fsS "${KC_BASE}/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  --data-urlencode "username=${KC_BOOTSTRAP_ADMIN_USERNAME}" \
  --data-urlencode "password=${KC_BOOTSTRAP_ADMIN_PASSWORD}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

CID=$(api GET "/clients?clientId=${CLIENT_ID_NAME}" | python3 -c 'import sys,json;r=json.load(sys.stdin);print(r[0]["id"] if r else "")')
[ -n "$CID" ] || { echo "client ${CLIENT_ID_NAME} not found in realm ${REALM} — is the realm the one you think it is?" >&2; exit 1; }

EXISTING=$(api GET "/clients/${CID}/protocol-mappers/models" | python3 -c '
import sys, json
for m in json.load(sys.stdin):
    if m.get("name") == "aud-study-tutor-app":
        print(m["id"]); break')
if [ -n "$EXISTING" ]; then
  echo "already applied (mapper id ${EXISTING}) — nothing to do"; exit 0
fi

echo "== creating the mapper (same block as realm-as-code + the July live-suite apply) =="
api POST "/clients/${CID}/protocol-mappers/models" '{
  "name": "aud-study-tutor-app",
  "protocol": "openid-connect",
  "protocolMapper": "oidc-audience-mapper",
  "consentRequired": false,
  "config": {
    "included.client.audience": "study-tutor-app",
    "id.token.claim": "false",
    "access.token.claim": "true"
  }
}'

echo "== verify: the client's mappers, read back =="
MID=$(api GET "/clients/${CID}/protocol-mappers/models" | python3 -c '
import sys, json
ms = json.load(sys.stdin)
for m in ms:
    print("  {}: {}".format(m.get("name"), m.get("protocolMapper")), file=sys.stderr)
aud = [m for m in ms if m.get("name") == "aud-study-tutor-app"]
assert aud, "mapper missing after create"
assert aud[0]["config"]["included.client.audience"] == "study-tutor-app"
print(aud[0]["id"])')

echo
echo "APPLIED. Rollback, if ever needed (deletes ONLY this mapper):"
echo "  curl -fsS -X DELETE '${KC_BASE}/admin/realms/${REALM}/clients/${CID}/protocol-mappers/models/${MID}' -H 'Authorization: Bearer <fresh admin token>'"
echo
echo "Next per the spec (§9): the fleet-gateway robot build can start; KC-G4 is the gate."
