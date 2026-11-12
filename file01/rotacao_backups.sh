#!/bin/bash
RETENCAO_DIAS=7
DIR="/compartilhado/backups"
LOG="/var/log/rotacao_backups.log"

REMOVIDOS=$(find "$DIR" -maxdepth 1 -name 'appdb_*.tar.gz' -mtime +$RETENCAO_DIAS -print -delete)
echo "[$(date '+%F %T')] Rotacao (${RETENCAO_DIAS} dias). Removidos:" >> "$LOG"
echo "${REMOVIDOS:-nenhum}" >> "$LOG"
