# -*- coding: utf-8 -*-
"""表头/模板识别与列位移检测（R-IMP-04~06）"""
from __future__ import annotations

import datetime as _dt
import re

from app.importers.mapping import FIELD_ALIASES, match_alias, normalize_header
from app.importers.reader import SheetMatrix

TEMPLATE_TITLE = "导入报价模板"
HEADER_MIN_HITS = 3


def is_template_sheet(sm: SheetMatrix) -> bool:
    """识别"导入报价模板"：前 3 行存在标题单元格（R-IMP-04）"""
    for r in range(min(3, sm.nrows)):
        for cell in sm.rows[r]:
            if TEMPLATE_TITLE in (cell["raw"] or ""):
                return True
    return False


def find_template_date(sm: SheetMatrix) -> _dt.date | None:
    """模板日期行："日期:2026-08-25 13:32:52" """
    pat = re.compile(r"日期[:：]?\s*([0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2})")
    for r in range(min(5, sm.nrows)):
        for cell in sm.rows[r]:
            m = pat.search(cell["raw"] or "")
            if m:
                try:
                    return _dt.datetime.strptime(m.group(1), "%Y-%m-%d").date()
                except ValueError:
                    continue
    return None


def _header_hits(row: list[dict]) -> int:
    hits = 0
    for cell in row:
        if match_alias(cell["raw"] or ""):
            hits += 1
    return hits


def find_header_row(sm: SheetMatrix, is_template: bool) -> int | None:
    """定位表头行（1 基返回下标 +1 语义由调用方处理，这里返回 0 基行号）。

    模板表：标题/日期行之后首个命中 ≥3 别名的行；
    普通表：前 10 行中命中数最高且 ≥2 的首个行。
    """
    start = 0
    if is_template:
        # 样例结构：R0 标题、R1 日期行、R2 表头（R-IMP-04）
        start = min(2, max(0, sm.nrows - 1))
        best_row, best_hits = None, 0
        for r in range(start, min(sm.nrows, start + 5)):
            hits = _header_hits(sm.rows[r])
            if hits >= HEADER_MIN_HITS and hits > best_hits:
                best_row, best_hits = r, hits
        return best_row
    best_row, best_hits = None, 0
    for r in range(min(10, sm.nrows)):
        hits = _header_hits(sm.rows[r])
        if hits >= 2 and hits > best_hits:
            best_row, best_hits = r, hits
    return best_row


def detect_shift(sm: SheetMatrix, header_row: int, header_texts: list[str]) -> bool:
    """位移检测（R-IMP-06）：表头首列是标准字段（非"行号"），而数据行首列是 1..n 连续序数。

    样例1 Sheet1 即此形态：表头缺"行号"，数据多出一列序号 → 判定整体右移一列。
    """
    first_header = normalize_header(header_texts[0]) if header_texts else ""
    if not first_header:
        return False
    if match_alias(first_header) == "row_no" or first_header == "行号":
        return False
    if match_alias(first_header) is None:
        return False
    # 检查数据行首列是否为连续 1..n
    seq = []
    for r in range(header_row + 1, min(header_row + 21, sm.nrows)):
        row = sm.rows[r]
        if not row or not (row[0]["raw"] or "").strip():
            continue
        if row[0]["num"] is None or row[0]["num"] != int(row[0]["num"]):
            return False
        seq.append(int(row[0]["num"]))
    if len(seq) < 3:
        return False
    return seq == list(range(seq[0], seq[0] + len(seq)))


def score_sheet(sm: SheetMatrix) -> dict:
    """工作表识别摘要"""
    template = is_template_sheet(sm)
    header_row = find_header_row(sm, template)
    hits = _header_hits(sm.rows[header_row]) if header_row is not None else 0
    return {
        "name": sm.name,
        "row_count": sm.nrows,
        "is_template": template,
        "header_row": (header_row + 1) if header_row is not None else None,
        "detect_score": hits,
    }


def aliases_preview() -> dict[str, list[str]]:
    return FIELD_ALIASES
