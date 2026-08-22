#!/usr/bin/env bash
set -euo pipefail

# Daily PostgreSQL backup. Intended for cron:
#   15 2 * * * /path/to/pickle-pos/scripts/backup_postgres.sh
#
# Uses docker compose by default. Override with PG_DUMP_CMD for a host install.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/pickle_pos-$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

if [[ -n "${PG_DUMP_CMD:-}" ]]; then
  eval "$PG_DUMP_CMD" | gzip > "$FILE"
else
  cd "$ROOT"
  docker compose exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-pickle_pos}" "${POSTGRES_DB:-pickle_pos}" \
    | gzip > "$FILE"
fi

find "$BACKUP_DIR" -name 'pickle_pos-*.sql.gz' -mtime "+$RETENTION_DAYS" -delete
echo "Wrote $FILE"
