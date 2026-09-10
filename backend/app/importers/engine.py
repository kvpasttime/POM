# -*- coding: utf-8 -*-
"""导入引擎编排（engine）：preview 构建、重复检测、校验汇总"""
from __future__ import annotations

import uuid
from dataclasses import asdict

from app.importers.detect import detect_shift, find_header_row, is_template_sheet, score_sheet
from app.importers.mapping import header_fingerprint
from app.importers.reader import SheetMatrix, read_workbook
from app.importers.splitter import DUPLICATE, ERROR, WARN, parse_sheet_rows, resolve_mappings


def summarize_sheets(filename: str, data: bytes) -> dict:
    """工作表扫描（upload 后、preview 前）"""
    sheets = read_workbook(filename, data)
    items = [score_sheet(sm) for sm in sheets]
    return {"sheets": items, "best": max(items, key=lambda s: s["detect_score"]) if items else None}


def build_preview(
    filename: str,
    data: bytes,
    sheet_name: str | None = None,
    header_row: int | None = None,
    user_mappings: list[dict] | None = None,
    existing_row_hashes: set[str] | None = None,
    existing_business_keys: set[tuple] | None = None,
) -> dict:
    """解析单个工作表并产出行级预览（docs/05 4.3.2/4.3.3 响应结构）"""
    sheets = read_workbook(filename, data)
    if not sheets:
        raise ValueError("工作簿无工作表")
    sm: SheetMatrix | None = None
    if sheet_name:
        sm = next((s for s in sheets if s.name == sheet_name), None)
        if sm is None:
            raise ValueError(f"工作表不存在: {sheet_name}")
    else:
        scored = [(score_sheet(s), s) for s in sheets]
        sm = max(scored, key=lambda t: t[0]["detect_score"])[1]

    template = is_template_sheet(sm)
    hrow0 = find_header_row(sm, template)
    if hrow0 is None:
        raise ValueError("无法识别表头行，请手动指定表头行")
    if header_row is not None:
        hrow0 = header_row - 1
        if hrow0 < 0 or hrow0 >= sm.nrows:
            raise ValueError("表头行号超出范围")

    header_texts_raw = [c["raw"] for c in sm.rows[hrow0]]
    shift = detect_shift(sm, hrow0, header_texts_raw)
    # 映射使用真实表头坐标（位移在取数时 +shift，R-IMP-06）
    header_texts = header_texts_raw
    mappings = resolve_mappings(header_texts, user_mappings)

    rows = parse_sheet_rows(sm, hrow0, mappings, shift)

    # 行级重复（R-IMP-19）
    summary = {"ok": 0, "warn": 0, "error": 0, "duplicate": 0}
    existing_row_hashes = existing_row_hashes or set()
    existing_business_keys = existing_business_keys or set()
    for rp in rows:
        if rp.content_hash in existing_row_hashes:
            rp.status = DUPLICATE
            rp.reasons.append("行级精确重复（同文件哈希+工作表+行号+内容，R-IMP-19）")
        for q in rp.quotes:
            bkey = (
                (rp.material.get("code") or rp.material.get("name") or ""),
                (rp.material.get("spec_model") or ""),
                (q.supplier_name or ""),
                q.amount,
                str(rp.requirement.get("requirement_date") or ""),
            )
            if q.amount is not None and bkey in existing_business_keys:
                q.business_dup = True
                q.status = "needs_review"
                if "业务疑似重复，请人工确认（R-IMP-20）" not in rp.reasons:
                    rp.reasons.append("业务疑似重复，请人工确认（R-IMP-20）")
        if rp.status != DUPLICATE:
            summary[rp.status] = summary.get(rp.status, 0) + 1
        else:
            summary["duplicate"] += 1

    preview_rows = []
    for rp in rows:
        preview_rows.append({
            "row_no": rp.row_no,
            "status": rp.status,
            "reasons": rp.reasons,
            "quote_count": rp.quote_count,
            "material_name": rp.material.get("name"),
            "material_code": rp.material.get("code"),
            "preview": [
                {"amount": q.amount, "supplier": q.supplier_name, "status": q.status}
                for q in rp.quotes
            ],
        })

    return {
        "sheet_name": sm.name,
        "sheet_names": [s.name for s in sheets],
        "is_template": template,
        "header_row": hrow0 + 1,
        "header_texts": header_texts,
        "shift_detected": shift,
        "shift_message": (
            "检测到数据列整体右移一位（表头缺行号），已自动对齐，请确认（R-IMP-06）" if shift else None
        ),
        "mappings": [
            {"standard_field": std, "source_column": (col if col is not None else None),
             "header_text": (header_texts[col] if col is not None and col < len(header_texts) else None)}
            for std, col in mappings.items()
        ],
        "header_fingerprint": header_fingerprint(header_texts),
        "commit_token": uuid.uuid4().hex,
        "rows": preview_rows,
        "summary": summary,
        "row_hashes": {rp.row_no: rp.content_hash for rp in rows},
    }


def sheets_overview(filename: str, data: bytes) -> list[dict]:
    return [asdict_info(s) for s in read_workbook(filename, data)]


def asdict_info(sm: SheetMatrix) -> dict:
    return {"name": sm.name, "row_count": sm.nrows, "col_count": sm.ncols()}


__all__ = ["build_preview", "summarize_sheets", "sheets_overview", "ERROR", "WARN"]
