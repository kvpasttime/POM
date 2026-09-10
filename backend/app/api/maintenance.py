# -*- coding: utf-8 -*-
"""数据维护与修订接口（docs/05 4.4）"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_maintainer
from app.core.response import BizError, ok
from app.models.business import Quote
from app.models.ops import QuoteRevision
from app.models.user import SysUser
from app.services.audit_service import record

router = APIRouter(tags=["maintenance"])

# 可修正字段白名单（R-MNT-01）：报价组 + 物料组 + 供应商组（来源组拒绝）
EDITABLE_FIELDS = {
    "amount", "currency", "tax_included", "tax_rate", "freight_included",
    "available_qty", "delivery_date", "transport_mode", "quote_date",
    "valid_until", "remark", "source_remark", "channel",
}
STATUS_VALUES = {"confirmed", "auto_extracted", "needs_review", "no_valid_price"}


def _get_quote(db: DbSession, quote_id: int) -> Quote:
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if q is None:
        raise BizError(40401, "记录不存在", http_status=404)
    return q


class PatchBody(BaseModel):
    fields: dict[str, object]
    reason: str = Field(min_length=1, max_length=512)
    version: int


class ReasonBody(BaseModel):
    reason: str = Field(min_length=1, max_length=512)


class StatusBody(BaseModel):
    status: str
    reason: str = Field(min_length=1, max_length=512)


def _add_revisions(db: DbSession, quote: Quote, fields: dict, reason: str, user: SysUser) -> list[str]:
    changed = []
    for fname, new_val in fields.items():
        old_val = getattr(quote, fname, None)
        old_s = str(old_val) if old_val is not None else None
        new_s = str(new_val) if new_val is not None else None
        if old_s == new_s:
            continue
        setattr(quote, fname, new_val)
        db.add(QuoteRevision(quote_id=quote.id, revision_type="field_change",
                             field=fname, old_value=old_s, new_value=new_s,
                             reason=reason, changed_by=user.id))
        changed.append(fname)
    return changed


@router.patch("/quotes/{quote_id}")
def patch_quote(quote_id: int, body: PatchBody, request: Request,
                user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    quote = _get_quote(db, quote_id)
    if quote.version != body.version:
        raise BizError(40404, "版本冲突，该记录已被他人修改，请刷新重试", http_status=409)
    for f in body.fields:
        if f not in EDITABLE_FIELDS:
            raise BizError(40402, f"字段 {f} 不可修改（来源组与快照受保护，R-MNT-01）")
    changed = _add_revisions(db, quote, body.fields, body.reason, user)
    if not changed:
        raise BizError(40402, "没有实际变更")
    quote.version += 1
    quote.updated_by = user.id
    record(db, "QUOTE_UPDATE", actor=user, object_type="quote", object_id=quote.id,
           summary=f"修正报价 #{quote.id}: {'、'.join(changed)}，原因：{body.reason}",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok({"id": quote.id, "version": quote.version, "changed_fields": changed})


@router.delete("/quotes/{quote_id}")
def delete_quote(quote_id: int, request: Request,
                 user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    quote = _get_quote(db, quote_id)
    if quote.status != "deleted":
        quote.status = "deleted"
        db.add(QuoteRevision(quote_id=quote.id, revision_type="delete", field="status",
                             old_value=None, new_value="deleted",
                             reason="软删除", changed_by=user.id))
        quote.version += 1
        record(db, "QUOTE_DELETE", actor=user, object_type="quote", object_id=quote.id,
               summary=f"软删除报价 #{quote.id}",
               ip=request.client.host if request.client else None)
        db.commit()
    return ok({"id": quote.id, "status": "deleted"})


@router.post("/quotes/{quote_id}/restore")
def restore_quote(quote_id: int, body: ReasonBody, request: Request,
                  user: SysUser = Depends(require_admin), db: DbSession = Depends(get_db)):
    quote = _get_quote(db, quote_id)
    if quote.status != "deleted":
        raise BizError(40405, "记录未处于删除状态")
    quote.status = "auto_extracted"
    db.add(QuoteRevision(quote_id=quote.id, revision_type="restore", field="status",
                         old_value="deleted", new_value="auto_extracted",
                         reason=body.reason, changed_by=user.id))
    quote.version += 1
    record(db, "QUOTE_RESTORE", actor=user, object_type="quote", object_id=quote.id,
           summary=f"恢复报价 #{quote.id}，原因：{body.reason}",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok({"id": quote.id, "status": quote.status})


@router.patch("/quotes/{quote_id}/status")
def mark_status(quote_id: int, body: StatusBody, request: Request,
                user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    if body.status not in STATUS_VALUES:
        raise BizError(40406, "非法状态值")
    quote = _get_quote(db, quote_id)
    if quote.status != body.status:
        old = quote.status
        quote.status = body.status
        db.add(QuoteRevision(quote_id=quote.id, revision_type="status_change", field="status",
                             old_value=old, new_value=body.status,
                             reason=body.reason, changed_by=user.id))
        quote.version += 1
        record(db, "STATUS_MARK", actor=user, object_type="quote", object_id=quote.id,
               summary=f"报价 #{quote.id} 状态 {old}→{body.status}，原因：{body.reason}",
               ip=request.client.host if request.client else None)
        db.commit()
    return ok({"id": quote.id, "status": quote.status})


@router.get("/quotes/{quote_id}/revisions")
def list_revisions(quote_id: int, page: int = Query(1, ge=1),
                   pageSize: int = Query(20, ge=1, le=100),
                   user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    _get_quote(db, quote_id)
    q = (db.query(QuoteRevision)
         .filter(QuoteRevision.quote_id == quote_id)
         .order_by(QuoteRevision.changed_at.desc(), QuoteRevision.id.desc()))
    total = q.count()
    items = q.offset((page - 1) * pageSize).limit(pageSize).all()
    users = {u.id: u.display_name for u in db.query(SysUser).filter(
        SysUser.id.in_({i.changed_by for i in items} or {0})).all()}
    return ok({"total": total, "page": page, "pageSize": pageSize, "items": [{
        "id": r.id, "revision_type": r.revision_type, "field": r.field,
        "old_value": r.old_value, "new_value": r.new_value, "reason": r.reason,
        "changed_by_name": users.get(r.changed_by),
        "changed_at": r.changed_at.isoformat() if r.changed_at else None,
    } for r in items]})
