#!/usr/bin/env bash
#
# ############################################################################
# ##  D R A F T  —  N O T   E X E C U T E D  —  awaiting the attended walk  ##
# ############################################################################
#
# provision-pilot-student.sh — the provisioning half of
# docs/runbooks/RUNBOOK-pilot-provisioning.md (Lane 3 step 5; commissioned by
# ADR-ARCH-034 D3). Creates ONE pilot student account so that no single-step
# failure can leave a half-provisioned account:
#
#   A2  student row          (seed-students CLI, idempotent)
#   A3  identity user        CREATED DISABLED, with the student_id attribute AND
#                            the password in the SAME create call
#   A4  realm role `student`
#   A5  read back all of it
#   A6  enable the user      <- the single, reversible go-live act
#
# A1 (the consent record) is NOT here and cannot be: no consent table exists
# (zero `consent` occurrences in src/, alembic/, app/lib as of 2026-08-14;
# migration head 346cd366b66e). The script REFUSES to run without an operator-
# supplied consent reference, which is procedural enforcement only — the
# mechanical gate is ADR-ARCH-034 D6's build.
#
# STATUS: this file has NEVER been run. It was written from the repo by a
# non-executing session; `provision-live-suite.sh` is its model (dual-mode
# secret load :34-53, single-call user create :132-141, role mapping :143-144,
# student_id mapper :87-99). Its first execution is Rich's attended walk, which
# should follow the runbook's manual steps with this open alongside.
#
# CHECKED, and only this far: `bash -n` parses clean and every embedded Python
# block parses clean (ast.parse). `shellcheck` is NOT installed on this host, so
# no lint receipt is claimed — run it on the walk. The file is deliberately left
# NON-EXECUTABLE (no chmod +x): making it runnable is a decision, not a default.
#
# EVERY live WRITE sits behind an explicit confirm prompt — the user create, the
# role mapping, the enable, and the seed CLI. Read-only GETs (existence check,
# role lookup, read-backs) are not individually confirmed; first contact with the
# identity server is still gated, by the admin-token confirm. There is no
# --yes/--force flag on purpose: this creates an account for a child.
#
# Usage:
#   ./provision-pilot-student.sh --student-id <slug> --username <login> \
#       --consent-ref <reference> [--year-group N] [--target-grade G] \
#       [--name "Display Name"] [--kc-base URL]
#
# Reads admin creds exactly like provision-live-suite.sh:
#   deploy/keycloak/.env.deploy (gitignored, preferred), else the sops-encrypted
#   ${SECRETS_ROOT}/study-tutor/keycloak-env-deploy.enc.env
# Needs STUDY_TUTOR_PG_DSN in the environment for the seed step.
# The student's password is typed at a prompt: never an argument — not this
# script's, and not curl's either, since the create body is fed to curl on stdin
# (`--data @-`) so it never appears in `ps` — never a file, never echoed, never
# logged.

set -euo pipefail
cd "$(dirname "$0")"

KC_BASE="${KC_BASE:-}"
REALM="${REALM:-study-tutor}"
STUDENT_ID=""
USERNAME=""
CONSENT_REF=""
DISPLAY_NAME=""
YEAR_GROUP=""
TARGET_GRADE=""

die() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "-- $*"; }

# confirm PROMPT — every live write goes through this. Reads from the terminal,
# not stdin, so a piped/redirected run cannot answer on the operator's behalf.
confirm() {
    local prompt="$1" reply=""
    [ -r /dev/tty ] || die "no terminal available — this script is attended-only"
    printf '\n>> %s\n   type exactly "yes" to proceed: ' "$prompt" > /dev/tty
    read -r reply < /dev/tty
    if [ "$reply" != "yes" ]; then
        echo "   aborted by operator." > /dev/tty
        exit 10
    fi
}

usage() {
    sed -n '1,54p' "$0"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --student-id)   STUDENT_ID="${2:-}"; shift 2 ;;
        --username)     USERNAME="${2:-}"; shift 2 ;;
        --consent-ref)  CONSENT_REF="${2:-}"; shift 2 ;;
        --name)         DISPLAY_NAME="${2:-}"; shift 2 ;;
        --year-group)   YEAR_GROUP="${2:-}"; shift 2 ;;
        --target-grade) TARGET_GRADE="${2:-}"; shift 2 ;;
        --kc-base)      KC_BASE="${2:-}"; shift 2 ;;
        -h|--help)      usage ;;
        *) die "unknown arg: $1" ;;
    esac
done

[ -n "$STUDENT_ID" ]  || die "--student-id is required"
[ -n "$USERNAME" ]    || die "--username is required"
[ -n "$KC_BASE" ]     || die "--kc-base (or KC_BASE) is required — name the deployment explicitly"
[ -n "${STUDY_TUTOR_PG_DSN:-}" ] || die "STUDY_TUTOR_PG_DSN must be set for the seed step"

# --- A1 gate: consent, procedurally ------------------------------------------
# ADR-ARCH-033 D5: "No consent record, no session." The record has nowhere to
# land yet (runbook §0), so this script will not create an account without the
# operator naming the consent record it is standing on.
if [ -z "$CONSENT_REF" ]; then
    die "--consent-ref is required: name the consent + ownership-attestation record for ${STUDENT_ID}.
     If no such record exists, STOP — ADR-ARCH-033 D5 forbids the account (runbook section 0)."
fi

# --- config load (mirrors provision-live-suite.sh:34-53) ----------------------
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
    die "missing both deploy/keycloak/.env.deploy and ${SECRETS_ROOT}/${ENC_ENV} (admin creds)"
fi
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?not in .env.deploy}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?not in .env.deploy}"

TOKEN=""
api() { # api METHOD PATH [JSON_BODY]
    local m="$1" p="$2" body="${3:-}"
    if [ -n "$body" ]; then
        # Body goes in on stdin (--data @-), NOT in curl's argv: the A3 user
        # representation carries the student's plaintext password, and an argv
        # copy is readable in `ps`/`/proc` by any other user on the host. The
        # model script (provision-live-suite.sh:132-141) passes it as an
        # argument; this is the one place this script deliberately diverges.
        printf '%s' "$body" | curl -fsS -X "$m" "${KC_BASE}/admin/realms/${REALM}${p}" \
            -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" --data @-
    else
        curl -fsS -X "$m" "${KC_BASE}/admin/realms/${REALM}${p}" \
            -H "Authorization: Bearer ${TOKEN}"
    fi
}

cat <<BANNER

================================================================================
 PROVISION PILOT STUDENT — attended procedure
   identity server : ${KC_BASE}  (realm ${REALM})
   student_id      : ${STUDENT_ID}
   username        : ${USERNAME}
   consent record  : ${CONSENT_REF}
 The account is created DISABLED and is enabled only as the final step, after
 every piece has been read back. Abort at any prompt and nothing is usable.
================================================================================
BANNER

# --- A2: student row ----------------------------------------------------------
note "A2 — seed the student row (idempotent: INSERT ... ON CONFLICT DO NOTHING)"
# STUDY_TUTOR_CLI lets the operator say `uv run study-tutor` or a venv path.
read -r -a SEED_CMD <<< "${STUDY_TUTOR_CLI:-study-tutor}"
confirm "seed a student row for '${STUDENT_ID}' in the tutor database?"
"${SEED_CMD[@]}" seed-students --student-ids "${STUDENT_ID}"

# The CLI hard-codes name/year_group/target_grade (cli/main.py:1336-1341) and has
# no flags for them. Correct the row here rather than leaving a wrong profile.
if [ -n "$DISPLAY_NAME" ] || [ -n "$YEAR_GROUP" ] || [ -n "$TARGET_GRADE" ]; then
    echo
    echo "   The seed CLI wrote: name=<student_id title-cased>, year_group=10, target_grade='7'."
    echo "   Correct them by hand against the tutor database (runbook A2), e.g.:"
    echo
    echo "     UPDATE student SET name='${DISPLAY_NAME:-<name>}',"
    echo "            year_group=${YEAR_GROUP:-<7-13>}, target_grade='${TARGET_GRADE:-<grade>}'"
    echo "      WHERE student_id='${STUDENT_ID}';"
    echo
    echo "   This script does NOT run SQL against the tutor database (runbook Q5:"
    echo "   whether the CLI should grow the flags is an open question)."
    confirm "have you applied that UPDATE (or accepted the defaults)?"
fi

# --- admin token --------------------------------------------------------------
note "admin token (realm master, admin-cli)"
confirm "authenticate to ${KC_BASE} as the bootstrap admin?"
TOKEN=$(curl -fsS "${KC_BASE}/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    --data-urlencode "username=${KC_BOOTSTRAP_ADMIN_USERNAME}" \
    --data-urlencode "password=${KC_BOOTSTRAP_ADMIN_PASSWORD}" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
[ -n "$TOKEN" ] || die "no admin token"

# --- A3: create the user DISABLED, attribute + credential in ONE call ---------
note "A3 — create '${USERNAME}' DISABLED, with student_id='${STUDENT_ID}' and a password"
EXISTING=$(api GET "/users?username=${USERNAME}&exact=true" \
    | python3 -c 'import sys,json;r=json.load(sys.stdin);print(r[0]["id"] if r else "")')
if [ -n "$EXISTING" ]; then
    die "user '${USERNAME}' already exists (${EXISTING}).
     STOP and inspect it by hand: a pre-existing user may be a half-provisioned
     account (runbook section 1, H1/H2), and this script will not repair one.
     NOTE: A2 already ran, so a 'student' row for '${STUDENT_ID}' is left behind.
     It is inert (half-state H3 — nothing resolves to it), but if you are not
     continuing, roll it back per runbook A2:
       DELETE FROM student WHERE student_id = '${STUDENT_ID}';"
fi

[ -r /dev/tty ] || die "no terminal available"
printf '\n   password for %s (not echoed, not stored): ' "${USERNAME}" > /dev/tty
read -rs NEW_PASSWORD < /dev/tty
printf '\n   repeat: ' > /dev/tty
read -rs NEW_PASSWORD2 < /dev/tty
printf '\n' > /dev/tty
[ -n "$NEW_PASSWORD" ] || die "empty password"
[ "$NEW_PASSWORD" = "$NEW_PASSWORD2" ] || die "passwords do not match"
export NEW_PASSWORD
unset NEW_PASSWORD2

USER_JSON=$(python3 - "$USERNAME" "$STUDENT_ID" "$DISPLAY_NAME" <<'PY'
import json, os, sys
username, student_id, display = sys.argv[1], sys.argv[2], sys.argv[3]
rep = {
    "username": username,
    # Born switched off. A6 is the only step that makes this account reachable,
    # so any failure before it leaves an account nobody can sign into.
    "enabled": False,
    "emailVerified": False,
    # The claim the API derives identity from. In the SAME call as the user, so
    # the "attribute missing" half-state (ADR-034 D2) cannot persist.
    "attributes": {"student_id": [student_id]},
    "credentials": [
        {"type": "password", "value": os.environ["NEW_PASSWORD"], "temporary": False}
    ],
}
if display:
    rep["firstName"] = display
print(json.dumps(rep))
PY
)

confirm "CREATE the disabled user '${USERNAME}' in realm ${REALM}?"
api POST "/users" "${USER_JSON}" > /dev/null
unset NEW_PASSWORD USER_JSON
UID_KC=$(api GET "/users?username=${USERNAME}&exact=true" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')
note "created ${USERNAME} (${UID_KC}) — DISABLED"
note "rollback for everything below: DELETE /admin/realms/${REALM}/users/${UID_KC}"

# --- A4: realm role -----------------------------------------------------------
note "A4 — assign the realm role 'student' (never 'parent' — reserved, ADR-033 D5)"
confirm "assign realm role 'student' to ${USERNAME}?"
ROLE_ID=$(api GET "/roles/student" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
api POST "/users/${UID_KC}/role-mappings/realm" "[{\"id\":\"${ROLE_ID}\",\"name\":\"student\"}]" > /dev/null

# --- A5: read back BEFORE enabling -------------------------------------------
note "A5 — read back (nothing is enabled yet; fix anything wrong now)"
READBACK=$(api GET "/users/${UID_KC}")

# The checker programs are built as strings and passed with `python3 -c` — a
# heredoc would occupy stdin, which is where the representation arrives.
CHECK_USER=$(cat <<'PY'
import json, sys
rep = json.load(sys.stdin)
want = sys.argv[1]
got = (rep.get("attributes") or {}).get("student_id") or []
problems = []
if rep.get("enabled") is not False:
    problems.append("user is NOT disabled - it should still be off at this point")
if got != [want]:
    problems.append("student_id attribute is {}, expected {}".format(got, [want]))
print("   enabled          : {}".format(rep.get("enabled")))
print("   student_id attr  : {}".format(got))
if problems:
    print("   READ-BACK FAILED:")
    for p in problems:
        print("     - {}".format(p))
    raise SystemExit(1)
print("   read-back OK (identity half)")
PY
)
printf '%s' "${READBACK}" | python3 -c "${CHECK_USER}" "${STUDENT_ID}"

CHECK_ROLE=$(cat <<'PY'
import json, sys
names = [r["name"] for r in json.load(sys.stdin)]
print("   realm roles      : {}".format(names))
if "student" not in names:
    print("   READ-BACK FAILED: role student is not mapped")
    raise SystemExit(1)
PY
)
api GET "/users/${UID_KC}/role-mappings/realm" | python3 -c "${CHECK_ROLE}"

cat <<MANUAL

   Two read-backs this script deliberately does NOT do for you:
     1. the student row in the tutor database (name / year_group / target_grade)
     2. the consent + ownership-attestation record ${CONSENT_REF}
   Check both by hand now. They are the halves whose absence produces a silent
   401 (unseeded guard, http/auth.py:286-297) or an account that should not exist.

MANUAL
confirm "have you verified the student row AND the consent record for '${STUDENT_ID}'?"

# --- A6: enable ---------------------------------------------------------------
note "A6 — ENABLE the account (the single go-live act; rollback = set enabled false)"
confirm "ENABLE ${USERNAME}? This makes the account reachable by a real person."
FLIP_ENABLED=$(cat <<'PY'
import json, sys
rep = json.load(sys.stdin)
rep["enabled"] = True
print(json.dumps(rep))
PY
)
api PUT "/users/${UID_KC}" \
    "$(printf '%s' "${READBACK}" | python3 -c "${FLIP_ENABLED}")" > /dev/null

CHECK_ENABLED=$(cat <<'PY'
import json, sys
rep = json.load(sys.stdin)
print("   enabled now      : {}".format(rep.get("enabled")))
if rep.get("enabled") is not True:
    raise SystemExit("enable did not take")
PY
)
api GET "/users/${UID_KC}" | python3 -c "${CHECK_ENABLED}"

cat <<DONE

================================================================================
 Provisioned: ${USERNAME} -> student_id ${STUDENT_ID} (realm ${REALM})
 NOT FINISHED until Part B of docs/runbooks/RUNBOOK-pilot-provisioning.md has
 been walked attended: token obtained (B1), student_id claim present (B2),
 GET /api/student-model returns 200 (B3), one real session start/turn/end (B4),
 isolation looked at with your own eyes (B5).
 Rollback at any point: set enabled=false, then
   DELETE /admin/realms/${REALM}/users/${UID_KC}
   DELETE FROM student WHERE student_id = '${STUDENT_ID}';   -- cascades
================================================================================
DONE
