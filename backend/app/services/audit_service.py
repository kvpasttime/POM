# -*- coding: utf-8 -*-
"""审计服务（docs/03 R-SYS-01）：统一入口，失败不阻断主业务"""
import logging

from sqlalchemy.orm import Session as DbSession

from app.models.ops import AuditLog

logger = logging.getLogger("pom.audit")


def record(
    db: DbSession,
    action: str,
    actor=None,
    object_type: str | None = None,
    object_id: int | None = None,
    result: str = "success",
    summary: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    try:
        entry = AuditLog(
            action=action,
            actor_id=getattr(actor, "id", None),
            actor_name=getattr(actor, "username", None),
            object_type=object_type,
            object_id=object_id,
            result=result,
            summary=(summary or "")[:500] or None,
            detail=detail,
            ip=ip,
        )
        db.add(entry)
        db.flush()
    except Exception:
        logger.exception("audit write failed (non-blocking)")


def record_and_commit(**kwargs) -> None:
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        record(db, **kwargs)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
