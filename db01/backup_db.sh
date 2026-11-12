#!/bin/bash
set -euo pipefail

DB="appdb"
DEST_SMB="//10.0.2.10/backups"
CRED="/root/.backup_cred"
WORKDIR="/var/backups/db"
STAMP="$(date +%Y%m%d_%H%M%S)"
SQL="${DB}_${STAMP}.sql"
ARQ="${DB}_${STAMP}.tar.gz"
LOG="/var/log/backup_db.log"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[$(date '+%F %T')] Iniciando backup de $DB" >> "$LOG"

runuser -u postgres -- pg_dump "$DB" > "$SQL"

tar -czf "$ARQ" "$SQL"
rm -f "$SQL"

smbclient "$DEST_SMB" -A "$CRED" -c "put $ARQ" >> "$LOG" 2>&1

rm -f "$ARQ"

echo "[$(date '+%F %T')] Backup concluido: $ARQ" >> "$LOG"
