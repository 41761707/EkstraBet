#!/usr/bin/env bash
# Production MySQL backup for EkstraBet (SZP-71).
# Dump streamed through gzip+openssl (no plaintext on disk), retention, off-site.
# Never logs passwords, passphrases, or connection secrets.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STATUS_LOG=""

log() {
  # ISO-8601 timestamp; message only — no secrets
  local line
  line="$(printf '%s %s' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*")"
  printf '%s\n' "${line}" >&2
  if [[ -n "${STATUS_LOG}" ]]; then
    printf '%s\n' "${line}" >>"${STATUS_LOG}"
  fi
}

die() {
  log "ERROR: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

load_env_file() {
  local path="$1"
  local line key value
  [[ -f "${path}" ]] || return 0
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    [[ "${line}" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key%"${key##*[![:space:]]}"}"
    key="${key#"${key%%[![:space:]]*}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    printf -v "${key}" '%s' "${value}"
    export "${key?}"
  done <"${path}"
}

secure_file() {
  # Artefakty DB tylko dla właściciela
  chmod 600 "$1" || die "chmod 600 failed for $1"
}

usage() {
  cat <<'EOF'
Usage: backup_mysql.sh

Creates an encrypted MySQL dump for the EkstraBet Compose stack.

Environment (typically /etc/ekstrabet/backup.env):
  MYSQL_BACKUP_USER              Backup DB user (required)
  MYSQL_BACKUP_PASSWORD          Backup DB password (required)
  MYSQL_DATABASE                 Database name (default: ekstrabet)
  BACKUP_DIR                     Local backup root (required)
  BACKUP_ENCRYPTION_PASSPHRASE   OpenSSL passphrase (required)
  EKSTRABET_ENV_DIR              Compose env dir (default: /etc/ekstrabet)
  COMPOSE_FILE                   Compose file (default: <repo>/compose.production.yml)
  COMPOSE_PROJECT_NAME           Optional Compose project name
  MYSQL_SERVICE                  Compose service name (default: mysql)
  APP_ORIGIN                     Required by Compose interpolation (dummy OK for backup)
  RETENTION_DAILY                Keep N daily copies (default: 7)
  RETENTION_WEEKLY               Keep N weekly copies (default: 4)
  RETENTION_MONTHLY              Keep N monthly copies (default: 6)
  REQUIRE_OFFSITE                Fail without off-site target (default: 1)
  OFFSITE_SYNC_CMD               Shell command; receives backup path as $1
  OFFSITE_RSYNC_TARGET           rsync destination (used if OFFSITE_SYNC_CMD unset)

Exit codes: 0 success, non-zero on dump/encrypt/sync/retention/off-site failure.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# Umask zanim powstanie jakikolwiek plik backupu
umask 077

EKSTRABET_ENV_DIR="${EKSTRABET_ENV_DIR:-/etc/ekstrabet}"
BACKUP_ENV_FILE="${BACKUP_ENV_FILE:-${EKSTRABET_ENV_DIR}/backup.env}"
load_env_file "${BACKUP_ENV_FILE}"

MYSQL_DATABASE="${MYSQL_DATABASE:-ekstrabet}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/compose.production.yml}"
MYSQL_SERVICE="${MYSQL_SERVICE:-mysql}"
RETENTION_DAILY="${RETENTION_DAILY:-7}"
RETENTION_WEEKLY="${RETENTION_WEEKLY:-4}"
RETENTION_MONTHLY="${RETENTION_MONTHLY:-6}"
REQUIRE_OFFSITE="${REQUIRE_OFFSITE:-1}"
# Compose production file requires APP_ORIGIN even for exec
export APP_ORIGIN="${APP_ORIGIN:-https://localhost}"

[[ -n "${MYSQL_BACKUP_USER:-}" ]] || die "MYSQL_BACKUP_USER is not set"
[[ -n "${MYSQL_BACKUP_PASSWORD:-}" ]] || die "MYSQL_BACKUP_PASSWORD is not set"
[[ -n "${BACKUP_DIR:-}" ]] || die "BACKUP_DIR is not set"
[[ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]] || die "BACKUP_ENCRYPTION_PASSPHRASE is not set"
[[ -f "${COMPOSE_FILE}" ]] || die "Compose file not found: ${COMPOSE_FILE}"

require_cmd docker
require_cmd gzip
require_cmd openssl
require_cmd sha256sum
require_cmd find
require_cmd sort

compose() {
  local -a args=(docker compose)
  args+=(-f "${COMPOSE_FILE}")
  if [[ -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
    args+=(-p "${COMPOSE_PROJECT_NAME}")
  fi
  EKSTRABET_ENV_DIR="${EKSTRABET_ENV_DIR}" APP_ORIGIN="${APP_ORIGIN}" \
    "${args[@]}" "$@"
}

DAY_STAMP="$(date -u +'%Y-%m-%d')"
WEEK_STAMP="$(date -u +'%G-W%V')"
MONTH_STAMP="$(date -u +'%Y-%m')"
DOW_UTC="$(date -u +'%u')"
DOM_UTC="$(date -u +'%d')"

DAILY_DIR="${BACKUP_DIR}/daily"
WEEKLY_DIR="${BACKUP_DIR}/weekly"
MONTHLY_DIR="${BACKUP_DIR}/monthly"
LOG_DIR="${BACKUP_DIR}/logs"
mkdir -p "${DAILY_DIR}" "${WEEKLY_DIR}" "${MONTHLY_DIR}" "${LOG_DIR}"
chmod 700 "${BACKUP_DIR}" "${DAILY_DIR}" "${WEEKLY_DIR}" "${MONTHLY_DIR}" "${LOG_DIR}" \
  2>/dev/null || true

BASENAME="ekstrabet_${DAY_STAMP}"
ENC_PATH="${DAILY_DIR}/${BASENAME}.sql.gz.enc"
ENC_PARTIAL="${ENC_PATH}.partial"
CHECKSUM_PATH="${ENC_PATH}.sha256"
STATUS_LOG="${LOG_DIR}/backup_${DAY_STAMP}.log"

cleanup_partial() {
  rm -f "${ENC_PARTIAL}"
}
trap cleanup_partial EXIT

log "Starting MySQL backup database=${MYSQL_DATABASE} service=${MYSQL_SERVICE}"

# Strumień: dump | gzip | encrypt — bez plaintextu na dysku
log "Running mysqldump | gzip | openssl (single-transaction, no plaintext file)"
set +e
compose exec -T \
  -e "MYSQL_PWD=${MYSQL_BACKUP_PASSWORD}" \
  "${MYSQL_SERVICE}" \
  mysqldump \
  -u"${MYSQL_BACKUP_USER}" \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --default-character-set=utf8mb4 \
  "${MYSQL_DATABASE}" \
  | gzip -c \
  | BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE}" \
      openssl enc -aes-256-cbc -pbkdf2 -salt \
      -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
      -out "${ENC_PARTIAL}"
PIPE_RCS=("${PIPESTATUS[@]}")
set -e

if [[ "${PIPE_RCS[0]}" -ne 0 ]]; then
  die "mysqldump failed with exit code ${PIPE_RCS[0]}"
fi
if [[ "${PIPE_RCS[1]}" -ne 0 ]]; then
  die "gzip failed with exit code ${PIPE_RCS[1]}"
fi
if [[ "${PIPE_RCS[2]}" -ne 0 ]]; then
  die "openssl encrypt failed with exit code ${PIPE_RCS[2]}"
fi

if [[ ! -s "${ENC_PARTIAL}" ]]; then
  die "Encrypted backup is empty"
fi

mv -f "${ENC_PARTIAL}" "${ENC_PATH}"
secure_file "${ENC_PATH}"

sha256sum "${ENC_PATH}" | awk '{print $1}' >"${CHECKSUM_PATH}"
secure_file "${CHECKSUM_PATH}"
ENC_BYTES="$(wc -c <"${ENC_PATH}" | tr -d ' ')"
CHECKSUM="$(cat "${CHECKSUM_PATH}")"
log "Encrypted backup ready path=${ENC_PATH} size_bytes=${ENC_BYTES} sha256=${CHECKSUM}"

# Weekly on Sunday UTC; monthly on the 1st UTC
if [[ "${DOW_UTC}" == "7" ]]; then
  WEEKLY_PATH="${WEEKLY_DIR}/ekstrabet_${WEEK_STAMP}.sql.gz.enc"
  cp -f "${ENC_PATH}" "${WEEKLY_PATH}"
  cp -f "${CHECKSUM_PATH}" "${WEEKLY_PATH}.sha256"
  secure_file "${WEEKLY_PATH}"
  secure_file "${WEEKLY_PATH}.sha256"
  log "Weekly copy path=${WEEKLY_PATH}"
fi

if [[ "${DOM_UTC}" == "01" ]]; then
  MONTHLY_PATH="${MONTHLY_DIR}/ekstrabet_${MONTH_STAMP}.sql.gz.enc"
  cp -f "${ENC_PATH}" "${MONTHLY_PATH}"
  cp -f "${CHECKSUM_PATH}" "${MONTHLY_PATH}.sha256"
  secure_file "${MONTHLY_PATH}"
  secure_file "${MONTHLY_PATH}.sha256"
  log "Monthly copy path=${MONTHLY_PATH}"
fi

prune_dir() {
  local dir="$1"
  local keep="$2"
  local pattern="$3"
  local count
  count="$(find "${dir}" -maxdepth 1 -type f -name "${pattern}" | wc -l | tr -d ' ')"
  if [[ "${count}" -le "${keep}" ]]; then
    return 0
  fi
  find "${dir}" -maxdepth 1 -type f -name "${pattern}" -printf '%T@ %p\n' \
    | sort -n \
    | head -n "$((count - keep))" \
    | while read -r _ path; do
        log "Pruning expired backup path=${path}"
        rm -f "${path}" "${path}.sha256"
      done
}

log "Applying retention daily=${RETENTION_DAILY} weekly=${RETENTION_WEEKLY} monthly=${RETENTION_MONTHLY}"
prune_dir "${DAILY_DIR}" "${RETENTION_DAILY}" 'ekstrabet_*.sql.gz.enc'
prune_dir "${WEEKLY_DIR}" "${RETENTION_WEEKLY}" 'ekstrabet_*.sql.gz.enc'
prune_dir "${MONTHLY_DIR}" "${RETENTION_MONTHLY}" 'ekstrabet_*.sql.gz.enc'

sync_offsite() {
  if [[ -n "${OFFSITE_SYNC_CMD:-}" ]]; then
    log "Running OFFSITE_SYNC_CMD"
    bash -c "${OFFSITE_SYNC_CMD}" _ "${ENC_PATH}"
    return $?
  fi
  if [[ -n "${OFFSITE_RSYNC_TARGET:-}" ]]; then
    require_cmd rsync
    log "Syncing to OFFSITE_RSYNC_TARGET"
    rsync -a --chmod=Du=rwx,Dg=,Fu=rw,Fg= \
      "${ENC_PATH}" "${CHECKSUM_PATH}" \
      "${OFFSITE_RSYNC_TARGET}/"
    return $?
  fi
  if [[ "${REQUIRE_OFFSITE}" == "1" || "${REQUIRE_OFFSITE}" == "true" ]]; then
    log "ERROR: off-site required but neither OFFSITE_SYNC_CMD nor OFFSITE_RSYNC_TARGET is set"
    return 1
  fi
  log "WARNING: no off-site target (REQUIRE_OFFSITE=${REQUIRE_OFFSITE})"
  return 0
}

set +e
sync_offsite
SYNC_RC=$?
set -e
if [[ "${SYNC_RC}" -ne 0 ]]; then
  die "Off-site sync failed with exit code ${SYNC_RC}"
fi

log "Backup finished successfully"
printf '%s\n' "${ENC_PATH}"
exit 0
