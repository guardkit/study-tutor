#!/bin/bash
# Nightly logical backup of the study-tutor durable StudentStore (NAS, Target A).
#
# Learner state is NOT reindexable (RUNBOOK-study-tutor-postgres-deploy.md §Phase 4),
# so a volume snapshot alone is insufficient — this takes a compressed logical dump
# (pg_dump -Fc) into the backed-up /volume1 share and prunes dumps older than
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
PGUSER="study_tutor"
PGDB="study_tutor"
BACKUP_DIR="/volume1/docker/study_tutor/backups"
RETENTION_DAYS=14
LOG="${BACKUP_DIR}/backup.log"

# --- run --------------------------------------------------------------------
mkdir -p "${BACKUP_DIR}"

log() { echo "$(date '+%F %T') $*" | tee -a "${LOG}" >&2; }

stamp="$(date +%F_%H%M%S)"
final="${BACKUP_DIR}/study_tutor_${stamp}.dump"
tmp="${final}.tmp"

log "backup start -> ${final}"

# Dump to a temp file first; only rename to the final name on success so a failed
# or partial dump never masquerades as a good backup.
if sudo -n "${DOCKER}" exec "${CONTAINER}" \
      pg_dump -U "${PGUSER}" -d "${PGDB}" -Fc > "${tmp}" 2>>"${LOG}"; then
    # A valid custom-format dump is non-empty and begins with the "PGDMP" magic.
    if [ -s "${tmp}" ] && head -c 5 "${tmp}" | grep -q "PGDMP"; then
        mv -f "${tmp}" "${final}"
        log "backup ok ($(du -h "${final}" | cut -f1))"
    else
        rm -f "${tmp}"
        log "backup FAILED: dump empty or not a valid PGDMP archive"
        exit 1
    fi
else
    rm -f "${tmp}"
    log "backup FAILED: pg_dump returned non-zero"
    exit 1
fi

# Retention: drop dumps older than RETENTION_DAYS (keeps backup.log).
deleted="$(find "${BACKUP_DIR}" -maxdepth 1 -name 'study_tutor_*.dump' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)"
log "retention: pruned ${deleted} dump(s) older than ${RETENTION_DAYS} days"
log "backup done"
