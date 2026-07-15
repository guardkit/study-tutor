#!/bin/bash
# Nightly logical backup of the study-tutor durable StudentStore and Keycloak realm
# state (NAS, Target A).
#
# Learner state and realm/user state are NOT reindexable (RUNBOOK-study-tutor-postgres-deploy.md §Phase 4,
# KC-D1), so a volume snapshot alone is insufficient — this takes compressed logical dumps
# (pg_dump -Fc) for both databases into the backed-up /volume1 share and prunes dumps older than
# RETENTION_DAYS.
#
# Intended to be run nightly by DSM Task Scheduler (user: root) — see the
# "Schedule" note at the bottom of this file. Idempotent, atomic (temp-then-rename),
# and exits non-zero on any failure so the Task Scheduler surfaces/e-mails errors.
#
# Manual run (from the NAS, or via ssh):
#   sudo /volume1/docker/study_tutor/backup.sh
set -euo pipefail

# --- config -----------------------------------------------------------------
DOCKER="/usr/local/bin/docker"          # NAS docker binary (scoped NOPASSWD sudoers)
CONTAINER="study_tutor_postgres"
BACKUP_DIR="/volume1/docker/study_tutor/backups"
RETENTION_DAYS=14
LOG="${BACKUP_DIR}/backup.log"

# --- run --------------------------------------------------------------------
mkdir -p "${BACKUP_DIR}"

log() { echo "$(date '+%F %T') $*" | tee -a "${LOG}" >&2; }

# Helper function: validate a dump file and rename to final location.
# Exits non-zero on validation failure (empty or invalid PGDMP format).
validate_and_finalize() {
    local tmp="$1"
    local final="$2"
    local db_name="$3"

    # A valid custom-format dump is non-empty and begins with the "PGDMP" magic.
    if [ -s "${tmp}" ] && head -c 5 "${tmp}" | grep -q "PGDMP"; then
        mv -f "${tmp}" "${final}"
        log "backup ok (${db_name}: $(du -h "${final}" | cut -f1))"
    else
        rm -f "${tmp}"
        log "backup FAILED (${db_name}): dump empty or not a valid PGDMP archive"
        exit 1
    fi
}

# Shared timestamp for both dumps
stamp="$(date +%F_%H%M%S)"

# --- Dump study_tutor database ----------------------------------------------
final_study_tutor="${BACKUP_DIR}/study_tutor_${stamp}.dump"
tmp_study_tutor="${final_study_tutor}.tmp"

log "backup start (study_tutor) -> ${final_study_tutor}"

# Dump to a temp file first; only rename to the final name on success so a failed
# or partial dump never masquerades as a good backup.
# shellcheck disable=SC2024  # script runs as root, redirects are fine
if sudo -n "${DOCKER}" exec "${CONTAINER}" \
      pg_dump -U study_tutor -d study_tutor -Fc > "${tmp_study_tutor}" 2>>"${LOG}"; then
    validate_and_finalize "${tmp_study_tutor}" "${final_study_tutor}" "study_tutor"
else
    rm -f "${tmp_study_tutor}"
    log "backup FAILED (study_tutor): pg_dump returned non-zero"
    exit 1
fi

# --- Dump keycloak database -------------------------------------------------
final_keycloak="${BACKUP_DIR}/keycloak_${stamp}.dump"
tmp_keycloak="${final_keycloak}.tmp"

log "backup start (keycloak) -> ${final_keycloak}"

# Dump keycloak database as the keycloak role (KC-D3 isolation: study_tutor role
# has no grants into the keycloak DB).
# shellcheck disable=SC2024  # script runs as root, redirects are fine
if sudo -n "${DOCKER}" exec "${CONTAINER}" \
      pg_dump -U keycloak -d keycloak -Fc > "${tmp_keycloak}" 2>>"${LOG}"; then
    validate_and_finalize "${tmp_keycloak}" "${final_keycloak}" "keycloak"
else
    rm -f "${tmp_keycloak}"
    log "backup FAILED (keycloak): pg_dump returned non-zero"
    exit 1
fi

# --- Retention --------------------------------------------------------------
# Drop dumps older than RETENTION_DAYS (keeps backup.log).
# Prune both dump families with the shared retention policy.
deleted_study_tutor="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'study_tutor_*.dump' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)"
deleted_keycloak="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'keycloak_*.dump' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)"
log "retention: pruned ${deleted_study_tutor} study_tutor dump(s), ${deleted_keycloak} keycloak dump(s) older than ${RETENTION_DAYS} days"
log "backup done"
