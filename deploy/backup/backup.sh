#!/bin/sh
# POM 每日备份：数据库 + 上传文件同一备份策略（PRD 8.3 / R-SYS-03）
# 产物：/data/backups/backup-YYYYMMDD-HHMMSS.tar.gz（含 db dump + uploads）
set -eu

TS=$(date +%Y%m%d-%H%M%S)
OUT=/data/backups
WORK=/tmp/backup-$TS
KEEP_DAYS=${BACKUP_KEEP_DAYS:-30}

mkdir -p "$OUT" "$WORK"

echo "[backup] dumping database..."
pg_dump -h db -U pom -d pom -F c -f "$WORK/pom.dump"

echo "[backup] archiving uploads..."
mkdir -p "$WORK/uploads"
if [ -d /data/uploads ]; then
    cp -r /data/uploads/. "$WORK/uploads/" 2>/dev/null || true
fi

tar -czf "$OUT/backup-$TS.tar.gz" -C "$WORK" pom.dump uploads
rm -rf "$WORK"

echo "[backup] pruning backups older than $KEEP_DAYS days..."
find "$OUT" -name "backup-*.tar.gz" -type f -mtime +"$KEEP_DAYS" -delete

echo "[backup] done: $OUT/backup-$TS.tar.gz"
