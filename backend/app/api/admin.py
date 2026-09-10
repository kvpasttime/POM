# -*- coding: utf-8 -*-
"""系统管理与审计接口（docs/05 4.5）"""
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import distinct
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.response import BizError, ok
from app.models.ops import AuditLog
from app.models.user import SysUser

router = APIRouter(tags=["admin"])

AUDIT_ACTIONS = {
    "LOGIN", "LOGIN_FAILED", "LOGOUT", "USER_CREATE", "USER_DISABLE", "USER_RESET",
    "IMPORT_UPLOAD", "IMPORT_COMMIT", "QUOTE_UPDATE", "QUOTE_DELETE", "QUOTE_RESTORE",
    "STATUS_MARK", "SENSITIVE_VIEW", "FILE_DOWNLOAD", "USER_UPDATE",
}


@router.get("/audit")
def query_audit(
    request: Request,
    time_from: str | None = None,
    time_to: str | None = None,
    actor_id: int | None = None,
    action: str | None = None,
    object_type: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: SysUser = Depends(require_admin),
    db: DbSession = Depends(get_db),
):
    if action and action not in AUDIT_ACTIONS:
        raise BizError(50401, f"非法动作过滤值: {action}")
    q = db.query(AuditLog)
    if time_from:
        q = q.filter(AuditLog.created_at >= time_from)
    if time_to:
        q = q.filter(AuditLog.created_at <= time_to)
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if object_type:
        q = q.filter(AuditLog.object_type == object_type)
    if keyword:
        q = q.filter(AuditLog.summary.like(f"%{keyword.strip()}%"))
    total = q.count()
    items = (q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
             .offset((page - 1) * pageSize).limit(pageSize).all())
    return ok({"total": total, "page": page, "pageSize": pageSize, "items": [{
        "id": a.id, "created_at": a.created_at.isoformat() if a.created_at else None,
        "actor_id": a.actor_id, "actor_name": a.actor_name, "action": a.action,
        "object_type": a.object_type, "object_id": a.object_id, "result": a.result,
        "summary": a.summary, "detail": a.detail,
    } for a in items]})


@router.get("/admin/backup-status")
def backup_status(user: SysUser = Depends(require_admin)):
    settings = get_settings()
    bdir = settings.backup_dir
    items = []
    if os.path.isdir(bdir):
        for name in sorted(os.listdir(bdir), reverse=True):
            path = os.path.join(bdir, name)
            if os.path.isfile(path) and name.startswith("backup-"):
                stat = os.stat(path)
                # 产物命名约定：backup-YYYYMMDD-HHMMSS.tar.gz
                date_part = name.replace("backup-", "")[:8]
                items.append({
                    "backup_date": f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}" if len(date_part) == 8 else name,
                    "type": "db+files",
                    "size_bytes": stat.st_size,
                    "size": f"{stat.st_size / 1024 / 1024:.1f}MB",
                    "status": "success",
                    "artifact_name": name,
                })
    alert = None
    if items:
        latest = items[0]["backup_date"]
        try:
            latest_dt = datetime.strptime(latest, "%Y-%m-%d")
            if datetime.now() - latest_dt > timedelta(days=2):
                alert = {"level": "error", "message": "连续 2 天以上无成功备份，请检查备份任务"}
        except ValueError:
            alert = {"level": "error", "message": "备份产物命名异常，无法解析日期"}
    else:
        alert = {"level": "error", "message": "尚未生成备份"}
    return ok({"alert": alert, "items": items[:30], "retention_days": 30})
