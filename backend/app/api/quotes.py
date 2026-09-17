# -*- coding: utf-8 -*-
"""查询与追溯接口（docs/05 4.2）"""
import os

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session as DbSession, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import BizError, ok
from app.models.business import Material, PurchaseRequirement, Quote, SourceRowSnapshot, Supplier
from app.models.ops import ImportBatch, SourceFile
from app.models.user import SysUser
from app.services.audit_service import record

router = APIRouter(tags=["quotes"])

SENSITIVE_FIELDS = ["contact_name", "phone", "address", "bank_account"]
SORT_WHITELIST = {"quote_date": Quote.quote_date, "amount": Quote.amount, "created_at": Quote.created_at}


def mask_phone(v: str | None) -> str | None:
    if not v:
        return v
    digits = "".join(ch for ch in v if ch.isdigit())
    if len(digits) == 11:
        return v.replace(digits[3:7], "****")
    if len(v) >= 4:
        return v[:2] + "****" + v[-2:]
    return "****"


def apply_masking(user: SysUser, data: dict, supplier: Supplier | None) -> list[str]:
    """敏感字段按角色脱敏（R-SYS-06/07）：user 脱敏；maintainer/admin 明文+审计"""
    if supplier is None:
        return []
    if user.role in ("maintainer", "admin"):
        return []
    masked = []
    for f in SENSITIVE_FIELDS:
        raw = getattr(supplier, f, None)
        if raw:
            data[f] = mask_phone(raw) if f == "phone" else "已脱敏"
            masked.append(f)
    return masked


@router.get("/quotes/search")
def search_quotes(
    request: Request,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    supplier_id: int | None = None,
    unit: str | None = None,
    status: str | None = None,
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    tax_included: bool | None = None,
    freight_included: bool | None = None,
    sortField: str = "quote_date",
    sortOrder: str = "desc",
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    include_requirement: bool = Query(False, description="含无报价需求（方案A）"),
    user: SysUser = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    if price_min is not None and price_max is not None and price_min > price_max:
        raise BizError(20401, "价格区间非法：最小值大于最大值")
    words = [w.strip() for w in (keyword or "").split() if w.strip()]
    applied = {k: v for k, v in {
        "keyword": keyword, "date_from": date_from, "date_to": date_to,
        "supplier_id": supplier_id, "unit": unit, "status": status,
        "price_min": price_min, "price_max": price_max,
        "tax_included": tax_included, "freight_included": freight_included,
    }.items() if v not in (None, "")}

    q = (db.query(Quote)
         .join(Material, Quote.material_id == Material.id)
         .outerjoin(Supplier, Quote.supplier_id == Supplier.id)
         .options(joinedload(Quote.material_ref), joinedload(Quote.supplier_ref)))

    # R-QRY-03：deleted 默认不出现
    if status and status == "deleted":
        if user.role != "admin":
            raise BizError(10404, "无权限查看已删除记录", http_status=403)
        q = q.filter(Quote.status == "deleted")
    else:
        q = q.filter(Quote.status != "deleted")
        if status:
            q = q.filter(Quote.status == status)

    if words:
        for w in words:
            like = f"%{w}%"
            conds = [
                Material.name.like(like), Material.code.like(like),
                Material.spec_model.like(like), Material.tech_params.like(like),
                Material.part_no.like(like), Material.material_text.like(like),
                Material.brand.like(like), Supplier.name.like(like),
                Quote.remark.like(like), Quote.source_remark.like(like),
            ]
            q = q.filter(or_(*conds))  # R-QRY-01 多词 AND
    if date_from:
        q = q.filter(Quote.quote_date >= date_from)
    if date_to:
        q = q.filter(Quote.quote_date <= date_to)
    if supplier_id:
        q = q.filter(Quote.supplier_id == supplier_id)
    if unit:
        q = q.filter(Material.unit.like(f"%{unit}%"))
    if price_min is not None:
        q = q.filter(Quote.amount >= price_min)
    if price_max is not None:
        q = q.filter(Quote.amount <= price_max)
    if tax_included is not None:
        q = q.filter(Quote.tax_included == tax_included)
    if freight_included is not None:
        q = q.filter(Quote.freight_included == freight_included)

    total = q.count()
    col = SORT_WHITELIST.get(sortField, Quote.quote_date)
    if sortOrder == "asc":
        q = q.order_by(col.asc().nullslast() if hasattr(col, "nullslast") else col.asc())
    else:
        # R-QRY-05：默认报价日期降序，空值排最后
        q = q.order_by(col.desc().nullslast())
    items = (q.offset((page - 1) * pageSize).limit(pageSize).all())

    result_items = []
    for it in items:
        m = it.material_ref
        s = it.supplier_ref
        result_items.append({
            "id": it.id,
            "row_type": "quote",
            "requirement_id": it.requirement_id,
            "material_name": m.name if m else None,
            "material_code": m.code if m else None,
            "spec_model": m.spec_model if m else None,
            "brand": m.brand if m else None,
            "supplier_name": s.name if s else "待确认",
            "amount": float(it.amount) if it.amount is not None else None,
            "currency": it.currency,
            "tax_included": it.tax_included,
            "freight_included": it.freight_included,
            "quote_date": it.quote_date,
            "status": it.status,
            "batch_id": it.import_batch_id,
            "source_summary": source_summary(db, it),
        })
    # 报价专属筛选（供应商/价格/含税/含运/状态）不适用于需求行，存在时忽略需求补充
    has_quote_only_filter = any(v not in (None, "", False) for v in (
        supplier_id, price_min, price_max, tax_included, freight_included, status))
    requirement_items = [] if (has_quote_only_filter or not include_requirement) else \
        _search_requirement_items(db, words, date_from, date_to, unit)

    return ok({"total": total, "page": page, "pageSize": pageSize,
               "items": result_items, "applied_filters": applied,
               "requirement_items": requirement_items})


def _search_requirement_items(db: DbSession, words: list[str],
                              date_from: str | None, date_to: str | None,
                              unit: str | None) -> list[dict]:
    """方案A：查询"有物料+需求但无报价"的记录，供搜索页合并展示。

    报价专属筛选（供应商/价格/含税/含运/状态）天然不适用于需求行，
    由调用方决定是否忽略；这里只应用 keyword / 日期区间 / 使用单位。
    """
    no_quote = ~db.query(Quote.id).filter(
        Quote.requirement_id == PurchaseRequirement.id,
        Quote.status != "deleted").exists()
    q = (db.query(PurchaseRequirement, Material)
         .join(Material, PurchaseRequirement.material_id == Material.id)
         .filter(no_quote))
    if words:
        for w in words:
            like = f"%{w}%"
            conds = [
                Material.name.like(like), Material.code.like(like),
                Material.spec_model.like(like), Material.tech_params.like(like),
                Material.part_no.like(like), Material.material_text.like(like),
                Material.brand.like(like), PurchaseRequirement.remark.like(like),
                PurchaseRequirement.receiver.like(like),
            ]
            q = q.filter(or_(*conds))
    if date_from:
        q = q.filter(PurchaseRequirement.requirement_date >= date_from)
    if date_to:
        q = q.filter(PurchaseRequirement.requirement_date <= date_to)
    if unit:
        q = q.filter(PurchaseRequirement.unit.like(f"%{unit}%"))
    rows = q.order_by(PurchaseRequirement.id.desc()).limit(200).all()
    items = []
    for req, m in rows:
        items.append({
            "requirement_id": req.id,
            "row_type": "requirement",
            "material_name": m.name,
            "material_code": m.code,
            "spec_model": m.spec_model,
            "brand": m.brand,
            "supplier_name": "待确认",
            "amount": None,
            "currency": "CNY",
            "tax_included": None,
            "freight_included": None,
            "quote_date": str(req.requirement_date) if req.requirement_date else None,
            "status": "no_quote",
            "batch_id": None,
            "source_summary": snapshot_summary(db, req.source_row_snapshot_id),
        })
    return items


def source_summary(db: DbSession, quote: Quote) -> str:
    return snapshot_summary(db, quote.source_row_snapshot_id)


def snapshot_summary(db: DbSession, snapshot_id: int) -> str:
    snap = db.query(SourceRowSnapshot).filter(SourceRowSnapshot.id == snapshot_id).first()
    if snap is None:
        return "—"
    f = db.query(SourceFile).filter(SourceFile.id == snap.source_file_id).first()
    fname = f.original_name if f else "未知文件"
    return f"{fname}/{snap.sheet_name}/R{snap.row_no}"


@router.get("/quotes/{quote_id}")
def quote_detail(quote_id: int, user: SysUser = Depends(get_current_user),
                 db: DbSession = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if quote is None or (quote.status == "deleted" and user.role != "admin"):
        raise BizError(20402, "记录不存在或已删除", http_status=404)

    m = db.query(Material).filter(Material.id == quote.material_id).first()
    req = (db.query(PurchaseRequirement)
           .filter(PurchaseRequirement.id == quote.requirement_id).first()) if quote.requirement_id else None
    s = db.query(Supplier).filter(Supplier.id == quote.supplier_id).first() if quote.supplier_id else None
    snap = db.query(SourceRowSnapshot).filter(SourceRowSnapshot.id == quote.source_row_snapshot_id).first()
    f = db.query(SourceFile).filter(SourceFile.id == snap.source_file_id).first() if snap else None
    batch = db.query(ImportBatch).filter(ImportBatch.id == quote.import_batch_id).first()
    uploader = None
    if batch:
        from app.models.user import SysUser as U
        uploader = db.query(U).filter(U.id == batch.created_by).first()

    data = {
        "id": quote.id,
        "version": quote.version,
        "material": {
            "code": m.code, "name": m.name, "category": m.category,
            "spec_model": m.spec_model, "tech_params": m.tech_params,
            "part_no": m.part_no, "material_text": m.material_text,
            "brand": m.brand, "origin_type": m.origin_type, "unit": m.unit,
            "name_raw": m.name_raw,
        } if m else None,
        "requirement": ({
            "quantity": float(req.quantity) if req.quantity is not None else None,
            "unit": req.unit, "requirement_date": req.requirement_date,
            "receiver": req.receiver, "quote_row_no": req.quote_row_no, "remark": req.remark,
        } if req else None),
        "quote": {
            "amount": float(quote.amount) if quote.amount is not None else None,
            "currency": quote.currency, "tax_included": quote.tax_included,
            "tax_rate": float(quote.tax_rate) if quote.tax_rate is not None else None,
            "freight_included": quote.freight_included,
            "available_qty": float(quote.available_qty) if quote.available_qty is not None else None,
            "delivery_date": quote.delivery_date, "transport_mode": quote.transport_mode,
            "quote_date": quote.quote_date, "date_inferred_from": quote.date_inferred_from,
            "valid_until": quote.valid_until, "status": quote.status,
            "remark": quote.remark, "source_remark": quote.source_remark,
            "channel": quote.channel,
            "supplier_spec_model": quote.supplier_spec_model,
            "supplier_material": quote.supplier_material,
            "supplier_tech_params": quote.supplier_tech_params,
        },
        "supplier": ({
            "name": s.name, "status": s.status, "channel": s.channel,
            "contact_name": s.contact_name, "phone": s.phone,
            "address": s.address, "bank_account": s.bank_account,
        } if s else None),
        "source": ({
            "file_id": f.id, "file_name": f.original_name,
            "sha256_8": f.sha256[:8], "sheet_name": snap.sheet_name,
            "row_no": snap.row_no, "batch_id": batch.id if batch else None,
            "batch_no": f"BATCH-{batch.id:05d}" if batch else None,
            "uploaded_by": uploader.display_name if uploader else None,
            "uploaded_at": batch.created_at.isoformat() if batch and batch.created_at else None,
            "raw_cells": snap.cells,
        } if snap and f else None),
    }
    masked = apply_masking(user, data["supplier"] or {}, s)
    data["masked_fields"] = masked

    siblings = (db.query(Quote)
                .filter(Quote.source_row_snapshot_id == quote.source_row_snapshot_id,
                        Quote.id != quote.id, Quote.status != "deleted")
                .all())
    data["sibling_quotes"] = [
        {"id": b.id, "group_label": b.group_label,
         "supplier_name": (db.query(Supplier).filter(Supplier.id == b.supplier_id).first().name
                           if b.supplier_id else "待确认"),
         "amount": float(b.amount) if b.amount is not None else None, "status": b.status}
        for b in siblings
    ]

    if masked and s is not None:
        record(db, "SENSITIVE_VIEW", actor=user, object_type="quote", object_id=quote.id,
               summary=f"查看报价 #{quote.id} 敏感字段: {'、'.join(masked)}",
               ip=None)
        db.commit()
    return ok(data)


@router.get("/requirements/{requirement_id}")
def requirement_detail(requirement_id: int, user: SysUser = Depends(get_current_user),
                       db: DbSession = Depends(get_db)):
    """无报价需求详情（方案A：纯需求 Excel 导入后也能溯源查看）"""
    req = db.query(PurchaseRequirement).filter(PurchaseRequirement.id == requirement_id).first()
    if req is None:
        raise BizError(20402, "记录不存在或已删除", http_status=404)
    m = db.query(Material).filter(Material.id == req.material_id).first()
    snap = db.query(SourceRowSnapshot).filter(SourceRowSnapshot.id == req.source_row_snapshot_id).first()
    f = db.query(SourceFile).filter(SourceFile.id == snap.source_file_id).first() if snap else None
    # 需求记录通过快照→文件→批次定位来源
    batch = db.query(ImportBatch).filter(ImportBatch.id == f.batch_id).first() if f else None
    uploader = None
    if batch:
        uploader = db.query(SysUser).filter(SysUser.id == batch.created_by).first()

    data = {
        "id": req.id,
        "row_type": "requirement",
        "material": ({
            "code": m.code, "name": m.name, "category": m.category,
            "spec_model": m.spec_model, "tech_params": m.tech_params,
            "part_no": m.part_no, "material_text": m.material_text,
            "brand": m.brand, "origin_type": m.origin_type, "unit": m.unit,
            "name_raw": m.name_raw,
        } if m else None),
        "requirement": {
            "quantity": float(req.quantity) if req.quantity is not None else None,
            "unit": req.unit, "requirement_date": str(req.requirement_date) if req.requirement_date else None,
            "receiver": req.receiver, "quote_row_no": req.quote_row_no, "remark": req.remark,
        },
        "source": ({
            "file_id": f.id, "file_name": f.original_name,
            "sha256_8": f.sha256[:8], "sheet_name": snap.sheet_name,
            "row_no": snap.row_no, "batch_id": batch.id if batch else None,
            "batch_no": f"BATCH-{batch.id:05d}" if batch else None,
            "uploaded_by": uploader.display_name if uploader else None,
            "uploaded_at": batch.created_at.isoformat() if batch and batch.created_at else None,
            "raw_cells": snap.cells,
        } if snap and f else None),
        "no_quote": True,
    }
    return ok(data)


@router.get("/suppliers/options")
def supplier_options(keyword: str | None = None, limit: int = Query(20, ge=1, le=50),
                     user: SysUser = Depends(get_current_user), db: DbSession = Depends(get_db)):
    q = db.query(Supplier).filter(Supplier.status != "deleted")
    if keyword:
        q = q.filter(Supplier.name.like(f"%{keyword.strip()}%"))
    items = q.order_by(Supplier.name).limit(limit).all()
    return ok({"items": [{"id": i.id, "name": i.name, "status": i.status} for i in items]})


@router.get("/meta/units")
def unit_options(user: SysUser = Depends(get_current_user), db: DbSession = Depends(get_db)):
    from sqlalchemy import distinct
    rows = db.query(distinct(PurchaseRequirement.unit)).filter(PurchaseRequirement.unit.isnot(None)).all()
    units = sorted({r[0] for r in rows if r[0]})
    return ok({"items": units})


@router.get("/files/{file_id}")
def download_file(file_id: int, request: Request, user: SysUser = Depends(get_current_user),
                  db: DbSession = Depends(get_db)):
    f = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if f is None:
        raise BizError(20403, "文件不存在或已丢失", http_status=404)
    path = f.stored_path
    if not os.path.isabs(path):
        path = os.path.join(get_settings().upload_dir, path)
    if not os.path.exists(path):
        raise BizError(20403, "文件不存在或已丢失", http_status=404)
    record(db, "FILE_DOWNLOAD", actor=user, object_type="file", object_id=f.id,
           summary=f"下载原始文件 {f.original_name}",
           ip=request.client.host if request.client else None)
    db.commit()
    return FileResponse(path, filename=f.original_name,
                        headers={"Cache-Control": "no-store"})


# --- ORM 关系挂载（避免循环 import 放文件底部） ---
from sqlalchemy.orm import relationship  # noqa: E402
Quote.material_ref = relationship(Material, foreign_keys=[Quote.material_id], lazy="selectin")
Quote.supplier_ref = relationship(Supplier, foreign_keys=[Quote.supplier_id], lazy="selectin")
