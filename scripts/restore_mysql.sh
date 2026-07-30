#!/usr/bin/env bash
# Restore an encrypted EkstraBet MySQL backup (SZP-71).
# Requires an explicit target database and a typed confirmation phrase.
# Prefer restoring into an empty test database before production use.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CONFIRM_PHRASE="YES_I_UNDERSTAND_DATA_LOSS"

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
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

usage() {
  cat <<EOF
Usage: restore_mysql.sh --file <path.sql.gz.enc> --target-database <name> --confirm ${CONFIRM_PHRASE}

Decrypts, decompresses and loads a backup created by backup_mysql.sh into the
explicit target database. Refuses to run without --confirm.

Environment (typically /etc/ekstrabet/backup.env):
  BACKUP_ENCRYPTION_PASSPHRASE   Same passphrase used at backup time
  EKSTRABET_ENV_DIR / COMPOSE_FILE / MYSQL_SERVICE / APP_ORIGIN
  MYSQL_ADMIN_USER / MYSQL_ADMIN_PASSWORD
      Preferred: DROP/CREATE DATABASE then LOAD
  MYSQL_BACKUP_USER / MYSQL_BACKUP_PASSWORD
      Fallback only when admin credentials are unset (needs write grants;
      target DB must already exist and be empty — no DROP DATABASE)

Safety:
  - Always restore first into an empty test database (e.g. ekstrabet_restore_test).
  - Only after checksum/table checks, restore into production with a fresh confirm.
EOF
}

BACKUP_FILE=""
TARGET_DATABASE=""
CONFIRM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --file)
      BACKUP_FILE="${2:-}"
      shift 2
      ;;
    --target-database)
      TARGET_DATABASE="${2:-}"
      shift 2
      ;;
    --confirm)
      CONFIRM="${2:-}"
      shift 2
      ;;
    *)
      die "Unknown argument: $1 (see --help)"
      ;;
  esac
done

EKSTRABET_ENV_DIR="${EKSTRABET_ENV_DIR:-/etc/ekstrabet}"
BACKUP_ENV_FILE="${BACKUP_ENV_FILE:-${EKSTRABET_ENV_DIR}/backup.env}"
load_env_file "${BACKUP_ENV_FILE}"

COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/compose.production.yml}"
MYSQL_SERVICE="${MYSQL_SERVICE:-mysql}"
export APP_ORIGIN="${APP_ORIGIN:-https://localhost}"

[[ -n "${BACKUP_FILE}" ]] || die "--file is required"
[[ -n "${TARGET_DATABASE}" ]] || die "--target-database is required"
[[ "${CONFIRM}" == "${CONFIRM_PHRASE}" ]] || die "Refusing restore without --confirm ${CONFIRM_PHRASE}"
[[ -f "${BACKUP_FILE}" ]] || die "Backup file not found: ${BACKUP_FILE}"
[[ -n "${BACKUP_ENCRYPTION_PASSPHRASE:-}" ]] || die "BACKUP_ENCRYPTION_PASSPHRASE is not set"
[[ -f "${COMPOSE_FILE}" ]] || die "Compose file not found: ${COMPOSE_FILE}"

if [[ -n "${MYSQL_ADMIN_USER:-}" && -n "${MYSQL_ADMIN_PASSWORD:-}" ]]; then
  RESTORE_USER="${MYSQL_ADMIN_USER}"
  RESTORE_PASSWORD="${MYSQL_ADMIN_PASSWORD}"
  HAVE_ADMIN=1
elif [[ -n "${MYSQL_BACKUP_USER:-}" && -n "${MYSQL_BACKUP_PASSWORD:-}" ]]; then
  RESTORE_USER="${MYSQL_BACKUP_USER}"
  RESTORE_PASSWORD="${MYSQL_BACKUP_PASSWORD}"
  HAVE_ADMIN=0
  log "WARNING: MYSQL_ADMIN_* unset; using MYSQL_BACKUP_USER (needs write grants)"
else
  die "Set MYSQL_ADMIN_USER/PASSWORD (preferred) or MYSQL_BACKUP_USER/PASSWORD"
fi

# Reject unsafe target names (identifier only)
[[ "${TARGET_DATABASE}" =~ ^[A-Za-z0-9_]+$ ]] || die "Invalid --target-database name"

require_cmd docker
require_cmd gzip
require_cmd openssl
require_cmd sha256sum

compose() {
  local -a args=(docker compose)
  args+=(-f "${COMPOSE_FILE}")
  if [[ -n "${COMPOSE_PROJECT_NAME:-}" ]]; then
    args+=(-p "${COMPOSE_PROJECT_NAME}")
  fi
  EKSTRABET_ENV_DIR="${EKSTRABET_ENV_DIR}" APP_ORIGIN="${APP_ORIGIN}" \
    "${args[@]}" "$@"
}

mysql_as() {
  local user="$1"
  local password="$2"
  shift 2
  compose exec -T \
    -e "MYSQL_PWD=${password}" \
    "${MYSQL_SERVICE}" \
    mysql -u"${user}" --batch --raw --default-character-set=utf8mb4 "$@"
}

CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ -f "${CHECKSUM_FILE}" ]]; then
  EXPECTED="$(tr -d '[:space:]' <"${CHECKSUM_FILE}")"
  ACTUAL="$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')"
  if [[ "${EXPECTED}" != "${ACTUAL}" ]]; then
    die "Checksum mismatch for ${BACKUP_FILE}"
  fi
  log "Checksum OK sha256=${ACTUAL}"
else
  log "WARNING: checksum file missing (${CHECKSUM_FILE}); continuing without verify"
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/ekstrabet_restore.XXXXXX")"
cleanup() {
  rm -rf "${WORKDIR}"
}
trap cleanup EXIT

GZ_PATH="${WORKDIR}/dump.sql.gz"
SQL_PATH="${WORKDIR}/dump.sql"

log "Decrypting backup file=${BACKUP_FILE}"
BACKUP_ENCRYPTION_PASSPHRASE="${BACKUP_ENCRYPTION_PASSPHRASE}" \
  openssl enc -d -aes-256-cbc -pbkdf2 \
  -pass env:BACKUP_ENCRYPTION_PASSPHRASE \
  -in "${BACKUP_FILE}" \
  -out "${GZ_PATH}"

log "Decompressing"
gzip -dc "${GZ_PATH}" >"${SQL_PATH}"
rm -f "${GZ_PATH}"

if [[ ! -s "${SQL_PATH}" ]]; then
  die "Decrypted dump is empty"
fi

SQL_BYTES="$(wc -c <"${SQL_PATH}" | tr -d ' ')"
log "Plain SQL ready size_bytes=${SQL_BYTES} target_database=${TARGET_DATABASE}"

if [[ "${HAVE_ADMIN}" -eq 1 ]]; then
  # DROP DATABASE omija błąd 1347 (DROP TABLE na VIEW, np. matches_pretty_print)
  log "Recreating empty target database (DROP + CREATE)"
  mysql_as "${RESTORE_USER}" "${RESTORE_PASSWORD}" -e \
    "DROP DATABASE IF EXISTS \`${TARGET_DATABASE}\`; CREATE DATABASE \`${TARGET_DATABASE}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
else
  log "Assuming target database already exists and is empty"
fi

log "Loading dump into target_database=${TARGET_DATABASE}"
set +e
mysql_as "${RESTORE_USER}" "${RESTORE_PASSWORD}" \
  "${TARGET_DATABASE}" <"${SQL_PATH}"
LOAD_RC=$?
set -e
if [[ "${LOAD_RC}" -ne 0 ]]; then
  die "mysql restore failed with exit code ${LOAD_RC}"
fi

TABLE_COUNT="$(
  mysql_as "${RESTORE_USER}" "${RESTORE_PASSWORD}" -N \
    -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${TARGET_DATABASE}';" \
    | tr -d '\r[:space:]'
)"
log "Restore finished target_database=${TARGET_DATABASE} table_count=${TABLE_COUNT}"
printf 'restored_database=%s table_count=%s\n' "${TARGET_DATABASE}" "${TABLE_COUNT}"
exit 0
