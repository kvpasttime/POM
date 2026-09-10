# POM 备份恢复手册（RESTORE.md）

> 依据 docs/02-架构设计.md 9.5 场景 A 与 PRD 8.3。上线前必须完成一次完整恢复演练并记录步骤与耗时（R-SYS-04）。

## 产物约定

- 每日备份产物：`backup-YYYYMMDD-HHMMSS.tar.gz`（数据卷 `backups`）
- 内容：`pom.dump`（pg_dump 自定义格式）+ `uploads/`（全部原始 Excel 文件）
- 备份保留：默认 30 天（`BACKUP_KEEP_DAYS` 可调）
- 备份状态查看：系统内 系统管理 → 备份状态（`GET /api/v1/admin/backup-status`）

## 恢复步骤

```bash
# 1. 停止应用（保留数据卷）
docker compose stop frontend backend backup

# 2. 解开备份包
cd /tmp && mkdir -p restore-YYYYMMDD && cd restore-YYYYMMDD
docker compose -f docker-compose.yml run --rm backend true   # 确保卷存在
tar -xzf /var/lib/docker/volumes/pom_backups/_data/backup-YYYYMMDD-HHMMSS.tar.gz

# 3. 恢复数据库
docker compose up -d db
cat pom.dump | docker exec -i $(docker compose ps -q db) \
    pg_restore -U pom -d pom --clean --if-exists

# 4. 恢复上传文件
docker cp uploads/. $(docker compose ps -q backend):/data/uploads/

# 5. 重启应用
docker compose up -d backend frontend

# 6. 抽检验证
#    - 浏览器登录，任取一条报价核对来源定位（文件名/工作表/行号）
#    - 下载一个原始文件确认可打开
#    - 管理员查看备份状态页恢复正常日期
```

## 演练记录（上线前执行一次，此后每季度抽检）

| 日期 | 环境 | 备份产物 | 恢复耗时 | 抽检结果 | 执行人 |
| ---- | ---- | -------- | -------- | -------- | ------ |
|      |      |          |          |          |        |
