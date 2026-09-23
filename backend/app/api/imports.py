# -*- coding: utf-8 -*-
"""Excel 导入接口（docs/05 4.3.1~4.3.9）"""
import os

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_maintainer
from app.core.response import BizError, ok
from app.core.security import sha256_bytes
from app.importers import engine
from app.models.business import Material, PurchaseRequirement, Quote, SourceRowSnapshot, Supplier
from app.models.business import QuoteBreakdown
from app.models.ops import ImportBatch, ImportRowResult, MappingTemplate, SourceFile
from app.models.user import SysUser
from app.services.audit_service import record
from app.services.storage_service import safe_original_name, save_upload

router = APIRouter(tags=["imports"])


def _load_signature(data: bytes, ext_ok: bool) -> None:
    """文件签名校验（R-IMP-01）：xls=OLE2 D0CF11E0 / xlsx=ZIP PK"""
    if not ext_ok:
        raise BizError(30401, "仅支持 .xls / .xlsx 文件")
    if len(data) < 4:
        raise BizError(30401, "文件内容为空或损坏")
    if not (data[:4] == b"\xd0\xcf\x11\xe0" or data[:2] == b"PK"):
        raise BizError(30401, "文件签名与扩展名不符（伪装文件）")


@router.post("/imports/upload")
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    user: SysUser = Depends(require_maintainer),
    db: DbSession = Depends(get_db),
):
    settings = get_settings()
    if not files:
        raise BizError(30401, "未选择文件")
    batch = ImportBatch(created_by=user.id, status="pending")
    db.add(batch)
    db.flush()
    results = []
    for uf in files:
        name = safe_original_name(uf.filename or "file")
        ext = os.path.splitext(name.lower())[1]
        ext_ok = ext in (".xls", ".xlsx")
        data = await uf.read()
        size = len(data)
        item = {"filename": name, "size": size, "check_status": "failed", "check_message": None}
        if size > settings.max_upload_mb * 1024 * 1024:
            item["check_message"] = f"超过大小限制 {settings.max_upload_mb}MB"
            results.append(item)
            continue
        try:
            _load_signature(data, ext_ok)
        except BizError as e:
            item["check_message"] = e.message
            results.append(item)
            continue
        sha = sha256_bytes(data)
        dup = db.query(SourceFile).filter(SourceFile.sha256 == sha).first()
        if dup is not None:
            sf = SourceFile(batch_id=batch.id, original_name=name, stored_path="", sha256=sha,
                            file_size=size, file_type=ext.lstrip("."),
                            check_status="duplicate", check_message=f"与既有文件（批次#{dup.batch_id}）重复",
                            duplicate_of_file_id=dup.id, created_by=user.id)
            db.add(sf)
            db.flush()
            item.update({"file_id": sf.id, "sha256": sha[:8], "check_status": "duplicate",
                         "check_message": item["check_message"],
                         "duplicate_of_batch_id": dup.batch_id})
            results.append(item)
            continue
        rel = save_upload(data, name)
        sf = SourceFile(batch_id=batch.id, original_name=name, stored_path=rel, sha256=sha,
                        file_size=size, file_type=ext.lstrip("."), check_status="passed",
                        created_by=user.id)
        db.add(sf)
        db.flush()
        try:
            overview = engine.summarize_sheets(name, data)
            item["sheets"] = overview["sheets"]
        except ValueError as e:
            sf.check_status = "failed"
            sf.check_message = str(e)
            item["check_status"] = "failed"
            item["check_message"] = str(e)
            results.append(item)
            continue
        item.update({"file_id": sf.id, "sha256": sha[:8], "check_status": "passed"})
        results.append(item)

    passed = [r for r in results if r.get("check_status") == "passed"]
    batch.file_count = len(results)
    db.flush()
    record(db, "IMPORT_UPLOAD", actor=user, object_type="import_batch", object_id=batch.id,
           summary=f"上传 {len(results)} 个文件，{len(passed)} 个通过校验",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok({"batch_id": batch.id, "files": results})


@router.get("/imports/{batch_id}/preview")
def get_preview(
    batch_id: int,
    file_id: int,
    sheet_name: str | None = None,
    header_row: int | None = None,
    user: SysUser = Depends(require_maintainer),
    db: DbSession = Depends(get_db),
):
    batch, sf = _get_batch_file(db, batch_id, file_id)
    if sf.check_status != "passed":
        raise BizError(30401, "该文件未通过上传校验，无法解析")
    data = _read_stored(sf)
    existing_hashes = _existing_row_hashes(db)
    existing_keys = _existing_business_keys(db)
    try:
        result = engine.build_preview(sf.original_name, data, sheet_name, header_row,
                                      None, existing_hashes, existing_keys)
    except ValueError as e:
        raise BizError(30404, str(e))
    _save_commit_token(db, batch, result["commit_token"])
    db.commit()
    return ok(result)


class MappingItem(BaseModel):
    standard_field: str
    source_column: int | None = None


class PreviewUpdateBody(BaseModel):
    file_id: int
    sheet_name: str
    header_row: int
    mappings: list[MappingItem]
    skip_error_rows: bool = False


class CommitItem(BaseModel):
    file_id: int
    sheet_name: str
    header_row: int
    mappings: list[MappingItem]
    skip_error_rows: bool = False


class CommitBody(BaseModel):
    commit_token: str
    file_commits: list[CommitItem]


@router.put("/imports/{batch_id}/preview")
def update_preview(batch_id: int, body: PreviewUpdateBody,
                   user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    batch, sf = _get_batch_file(db, batch_id, body.file_id)
    data = _read_stored(sf)
    # 映射冲突校验（30405）：同一源列不可重复映射
    cols = [m.source_column for m in body.mappings if m.source_column is not None]
    if len(cols) != len(set(cols)):
        raise BizError(30405, "映射冲突：同一源列被映射到多个标准字段")
    try:
        result = engine.build_preview(sf.original_name, data, body.sheet_name, body.header_row,
                                      [m.model_dump() for m in body.mappings],
                                      _existing_row_hashes(db), _existing_business_keys(db))
    except ValueError as e:
        raise BizError(30404, str(e))
    _save_commit_token(db, batch, result["commit_token"])
    db.commit()
    return ok(result)


@router.post("/imports/{batch_id}/commit")
def commit_import(batch_id: int, body: CommitBody, request: Request,
                  user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise BizError(30409, "批次不存在", http_status=404)
    # 幂等（R-IMP-23 / docs/05 4.3.4）
    if batch.commit_token == body.commit_token and batch.status in ("confirmed", "partial"):
        return ok(_batch_report(db, batch))
    if batch.status != "pending":
        raise BizError(30408, "批次已提交或状态冲突")
    if batch.commit_token and batch.commit_token != body.commit_token:
        raise BizError(30407, "commit_token 与最近一次预览不一致，请重新预览")

    totals = {"success": 0, "skipped": 0, "failed": 0, "needs_review": 0}
    try:
        for fc in body.file_commits:
            sf = db.query(SourceFile).filter(
                SourceFile.id == fc.file_id, SourceFile.batch_id == batch_id).first()
            if sf is None:
                raise BizError(30409, f"文件 {fc.file_id} 不属于该批次", http_status=404)
            data = _read_stored(sf)
            result = engine.build_preview(
                sf.original_name, data, fc.sheet_name, fc.header_row,
                [m.model_dump() for m in fc.mappings], set(), set())
            _commit_file(db, user, batch, sf, result, fc.skip_error_rows, totals)
        batch.status = "confirmed" if totals["failed"] == 0 else "partial"
        batch.success_count = totals["success"]
        batch.skipped_count = totals["skipped"]
        batch.failed_count = totals["failed"]
        batch.needs_review_count = totals["needs_review"]
        batch.commit_token = body.commit_token
        from datetime import datetime
        batch.confirmed_at = datetime.utcnow()
        record(db, "IMPORT_COMMIT", actor=user, object_type="import_batch", object_id=batch.id,
               summary=f"批次导入完成：成功 {totals['success']} 跳过 {totals['skipped']} "
                       f"失败 {totals['failed']} 待确认 {totals['needs_review']}",
               ip=request.client.host if request.client else None)
        db.commit()
    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        batch.status = "failed"
        batch.fail_reason = str(e)[:500]
        db.commit()
        raise BizError(30406, f"批次写入失败，已整体回滚：{e}", http_status=500)
    return ok(_batch_report(db, batch))


def _commit_file(db: DbSession, user: SysUser, batch: ImportBatch, sf: SourceFile,
                 result: dict, skip_error: bool, totals: dict) -> None:
    """把单个文件的解析结果写入业务表（批次事务内）"""
    from app.importers.splitter import parse_sheet_rows
    from app.importers.detect import is_template_sheet, find_header_row
    sheets = engine.read_workbook(sf.original_name, _read_stored(sf))
    sm = next(s for s in sheets if s.name == result["sheet_name"])
    hrow0 = result["header_row"] - 1
    header_texts_raw = [c["raw"] for c in sm.rows[hrow0]]
    shift = result["shift_detected"]
    header_texts = (["行号"] + header_texts_raw) if shift else header_texts_raw
    mappings = {m["standard_field"]: m["source_column"] for m in result["mappings"]}
    rows = parse_sheet_rows(sm, hrow0, mappings, shift)

    for rp in rows:
        status = rp.status
        reasons = list(rp.reasons)
        quote_ids: list[int] = []
        if status == "error" and skip_error:
            status = "skipped_row"
        if status == "error":
            totals["failed"] += 1
        elif status == "duplicate":
            totals["skipped"] += 1
        else:
            snap = SourceRowSnapshot(source_file_id=sf.id, sheet_name=result["sheet_name"],
                                     row_no=rp.row_no, cells=rp.cells,
                                     content_hash=rp.content_hash, created_by=user.id)
            db.add(snap)
            db.flush()
            material = _upsert_material(db, rp.material)
            requirement = PurchaseRequirement(
                material_id=material.id,
                quantity=rp.requirement.get("quantity"),
                unit=rp.requirement.get("unit"),
                requirement_date=rp.requirement.get("requirement_date"),
                receiver=rp.requirement.get("receiver"),
                quote_row_no=rp.requirement.get("quote_row_no"),
                remark=rp.requirement.get("remark"),
                source_row_snapshot_id=snap.id,
                created_by=user.id,
            )
            db.add(requirement)
            db.flush()
            if status == "ok" or status == "warn":
                totals["success"] += 1
                if not rp.quotes:
                    quote_ids = []
            for q in rp.quotes:
                supplier = _upsert_supplier(db, q)
                needs_review = q.status == "needs_review"
                quote = Quote(
                    material_id=material.id,
                    requirement_id=requirement.id,
                    supplier_id=supplier.id if supplier else None,
                    quoter=q.group_label,  # 报价人（组合采购语义）
                    amount=q.amount,
                    tax_included=q.tax_included,
                    freight_included=q.freight_included,
                    quote_date=rp.requirement.get("requirement_date"),
                    status=q.status,
                    remark=q.remark,
                    source_remark=rp.cells.get("备注") or rp.cells.get("报价备注"),
                    channel=q.channel,
                    group_label=q.group_label,
                    source_row_snapshot_id=snap.id,
                    import_batch_id=batch.id,
                    created_by=user.id,
                )
                db.add(quote)
                db.flush()
                # 报价构成明细（组合采购）：引擎预填；未给则按主体单条兜底
                bds = q.breakdowns or [{"store_name": q.supplier_name or "待确认",
                                        "amount": q.amount, "note": None}]
                for bd in bds:
                    db.add(QuoteBreakdown(
                        quote_id=quote.id, store_name=bd.get("store_name") or "待确认",
                        amount=bd.get("amount"), note=bd.get("note"), created_by=user.id))
                quote_ids.append(quote.id)
                if needs_review:
                    totals["needs_review"] += 1
            if status == "skipped_row":
                totals["skipped"] += 1
        rr = ImportRowResult(batch_id=batch.id, source_file_id=sf.id,
                             sheet_name=result["sheet_name"], row_no=rp.row_no,
                             status=status, reasons=reasons, quote_ids=quote_ids,
                             quote_count=len(quote_ids))
        db.add(rr)


def _upsert_material(db: DbSession, mat: dict) -> Material:
    q = db.query(Material)
    obj = None
    if mat.get("code"):
        obj = q.filter(Material.code == mat["code"]).first()
    if obj is None and mat.get("name") and mat.get("spec_model"):
        obj = (q.filter(Material.code.is_(None), Material.name == mat["name"],
                        Material.spec_model == mat["spec_model"]).first())
    if obj is None and mat.get("name"):
        obj = q.filter(Material.code.is_(None), Material.name == mat["name"]).first()
    if obj is not None:
        return obj
    obj = Material(code=mat.get("code"), name=mat.get("name"), category=mat.get("category"),
                   spec_model=mat.get("spec_model"), tech_params=mat.get("tech_params"),
                   part_no=mat.get("part_no"), material_text=mat.get("material_text"),
                   brand=mat.get("brand"), origin_type=mat.get("origin_type"),
                   unit=mat.get("unit"), name_raw=mat.get("name_raw"), created_by=None)
    db.add(obj)
    db.flush()
    return obj


def _upsert_supplier(db: DbSession, q: object):
    from app.importers.extract import normalize_supplier_key
    name = getattr(q, "supplier_name", None)
    if not name:
        return None
    key = normalize_supplier_key(name)
    obj = db.query(Supplier).filter(Supplier.normalized_key == key).first()
    if obj is not None:
        return obj
    obj = Supplier(name=name, normalized_key=key,
                   phone=getattr(q, "supplier_phone", None),
                   channel=getattr(q, "channel", None),
                   status="confirmed" if name else "pending")
    db.add(obj)
    db.flush()
    return obj


def _get_batch_file(db: DbSession, batch_id: int, file_id: int):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise BizError(30409, "批次不存在", http_status=404)
    sf = db.query(SourceFile).filter(SourceFile.id == file_id, SourceFile.batch_id == batch_id).first()
    if sf is None:
        raise BizError(30409, "文件不属于该批次", http_status=404)
    return batch, sf


def _read_stored(sf: SourceFile) -> bytes:
    from app.services.storage_service import resolve_path
    full = resolve_path(sf.stored_path)
    if not os.path.exists(full):
        raise BizError(20403, "文件已丢失，无法解析", http_status=404)
    with open(full, "rb") as fh:
        return fh.read()


def _existing_row_hashes(db: DbSession) -> set[str]:
    return {h for (h,) in db.query(SourceRowSnapshot.content_hash).all()}


def _existing_business_keys(db: DbSession) -> set[tuple]:
    rows = db.query(Quote.material_id, Quote.amount, Quote.quote_date, Quote.supplier_id).filter(
        Quote.amount.isnot(None)).all()
    return {(str(m), a, str(d), str(s)) for m, a, d, s in rows}


def _save_commit_token(db: DbSession, batch: ImportBatch, token: str) -> None:
    batch.commit_token = token


def _batch_report(db: DbSession, batch: ImportBatch) -> dict:
    rows = (db.query(ImportRowResult)
            .filter(ImportRowResult.batch_id == batch.id)
            .order_by(ImportRowResult.source_file_id, ImportRowResult.row_no).all())
    files = {f.id: f.original_name for f in db.query(SourceFile).filter(SourceFile.batch_id == batch.id).all()}
    return {
        "batch": {"id": batch.id, "status": batch.status, "created_at": batch.created_at.isoformat()},
        "summary": {"success": batch.success_count, "skipped": batch.skipped_count,
                    "failed": batch.failed_count, "needs_review": batch.needs_review_count},
        "items": [{
            "file_name": files.get(r.source_file_id, ""),
            "sheet_name": r.sheet_name, "row_no": r.row_no, "status": r.status,
            "quote_ids": r.quote_ids or [], "reasons": r.reasons or [],
        } for r in rows],
    }


@router.get("/imports/{batch_id}/report")
def batch_report(batch_id: int, status: str | None = None,
                 page: int = Query(1, ge=1), pageSize: int = Query(50, ge=1, le=200),
                 user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise BizError(30409, "批次不存在", http_status=404)
    report = _batch_report(db, batch)
    if status:
        report["items"] = [i for i in report["items"] if i["status"] == status]
    return ok(report)


class TemplateBody(BaseModel):
    name: str
    header_fingerprint: str
    sheet_hint: str | None = None
    mappings: list[MappingItem]


@router.post("/mapping-templates")
def save_template(body: TemplateBody, user: SysUser = Depends(require_maintainer),
                  db: DbSession = Depends(get_db)):
    exists = db.query(MappingTemplate).filter(
        MappingTemplate.owner_id == user.id, MappingTemplate.name == body.name).first()
    if exists:
        raise BizError(30410, "模板名已存在")
    t = MappingTemplate(name=body.name, owner_id=user.id,
                        header_fingerprint=body.header_fingerprint,
                        sheet_hint=body.sheet_hint,
                        mappings=[m.model_dump() for m in body.mappings], created_by=user.id)
    db.add(t)
    db.commit()
    return ok({"id": t.id, "name": t.name})


@router.get("/mapping-templates")
def list_templates(header_fingerprint: str | None = None,
                   user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    q = db.query(MappingTemplate).filter(MappingTemplate.owner_id == user.id)
    if header_fingerprint:
        q = q.filter(MappingTemplate.header_fingerprint == header_fingerprint)
    items = q.order_by(MappingTemplate.id.desc()).all()
    return ok({"items": [{
        "id": t.id, "name": t.name, "sheet_hint": t.sheet_hint,
        "mappings": t.mappings, "created_at": t.created_at.isoformat(),
    } for t in items]})


@router.get("/batches")
def list_batches(keyword: str | None = None, status: str | None = None,
                 page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100),
                 user: SysUser = Depends(require_maintainer), db: DbSession = Depends(get_db)):
    q = db.query(ImportBatch)
    if user.role != "admin":
        q = q.filter(ImportBatch.created_by == user.id)  # docs/03 5.1.1
    if status:
        q = q.filter(ImportBatch.status == status)
    items_q = q.order_by(ImportBatch.id.desc())
    total = items_q.count()
    batches = items_q.offset((page - 1) * pageSize).limit(pageSize).all()
    out = []
    for b in batches:
        names = [f.original_name for f in db.query(SourceFile).filter(SourceFile.batch_id == b.id).all()]
        if keyword and keyword.strip() and not any(keyword.strip() in n for n in names) \
                and keyword.strip() not in f"BATCH-{b.id:05d}":
            total -= 1
            continue
        out.append(_batch_view(db, b, names))
    return ok({"total": total, "page": page, "pageSize": pageSize, "items": out})


def _batch_view(db: DbSession, b: ImportBatch, names: list[str]) -> dict:
    uploader = db.query(SysUser).filter(SysUser.id == b.created_by).first()
    return {
        "id": b.id, "batch_no": f"BATCH-{b.id:05d}", "file_names": names,
        "file_count": b.file_count, "uploaded_by_name": uploader.display_name if uploader else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "success_count": b.success_count, "skipped_count": b.skipped_count,
        "failed_count": b.failed_count, "needs_review_count": b.needs_review_count,
        "status": b.status,
    }


@router.get("/batches/{batch_id}")
def batch_detail(batch_id: int, user: SysUser = Depends(require_maintainer),
                 db: DbSession = Depends(get_db)):
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise BizError(30409, "批次不存在", http_status=404)
    view = _batch_view(db, batch, [])
    files = db.query(SourceFile).filter(SourceFile.batch_id == batch_id).all()
    view["files"] = [{
        "file_id": f.id, "filename": f.original_name, "sha256": f.sha256[:8],
        "size": f.file_size, "check_status": f.check_status, "check_message": f.check_message,
    } for f in files]
    rows = (db.query(ImportRowResult)
            .filter(ImportRowResult.batch_id == batch_id)
            .order_by(ImportRowResult.source_file_id, ImportRowResult.row_no).all())
    quote_status = {}
    if rows:
        qids = [q for r in rows for q in (r.quote_ids or [])]
        if qids:
            for qt in db.query(Quote).filter(Quote.id.in_(qids)).all():
                quote_status[qt.id] = qt.status
    fname = {f.id: f.original_name for f in files}
    view["row_results"] = [{
        "file_name": fname.get(r.source_file_id, ""), "sheet_name": r.sheet_name,
        "row_no": r.row_no, "status": r.status, "reasons": r.reasons or [],
        "quote_ids": r.quote_ids or [], "quote_count": r.quote_count,
        "quote_statuses": {str(q): quote_status.get(q) for q in (r.quote_ids or [])},
    } for r in rows]
    return ok(view)
