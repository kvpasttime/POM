# -*- coding: utf-8 -*-
"""行解析与横向拆分（F03-BE-001 核心：R-IMP-11~20）

把"表头行 + 数据行 + 映射"解析为结构化结果：
RowParse{row_no, status, reasons, material{...}, requirement{...}, quotes[]}
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass, field

from app.importers.detect import find_template_date
from app.importers.extract import (
    extract_amount, extract_channel, extract_phone, extract_tax_freight,
    extract_vendor, is_no_price_text, is_price_context, normalize_supplier_key,
    split_material_desc, to_number,
)
from app.importers.mapping import auto_map, normalize_header
from app.importers.reader import SheetMatrix, parse_date_value

# 行级状态（docs/03 5.2 row_result_status）
OK, WARN, ERROR, DUPLICATE = "ok", "warn", "error", "duplicate"


@dataclass
class QuoteParse:
    amount: float | None = None
    tax_included: bool | None = None
    freight_included: bool | None = None
    channel: str | None = None
    supplier_name: str | None = None
    supplier_phone: str | None = None
    status: str = "auto_extracted"  # quote_quality_status
    remark: str | None = None
    group_label: str | None = None
    business_dup: bool = False


@dataclass
class RowParse:
    row_no: int            # 1 基源行号
    status: str = OK
    reasons: list[str] = field(default_factory=list)
    cells: dict = field(default_factory=dict)          # 列名→原文（快照）
    material: dict = field(default_factory=dict)
    requirement: dict = field(default_factory=dict)
    quotes: list[QuoteParse] = field(default_factory=list)
    content_hash: str = ""

    @property
    def quote_count(self) -> int:
        return len(self.quotes)


def _header_texts(sm: SheetMatrix, header_row: int, shift: int) -> list[str]:
    """真实表头文本（不加虚拟列；位移由取数时 +shift 处理，R-IMP-06）"""
    return [c["raw"] for c in sm.rows[header_row]]


def _data_row_texts(sm: SheetMatrix, row: list[dict], shift: int) -> list[str]:
    if shift == 0:
        return [c["raw"] for c in row]
    return [c["raw"] for c in row]  # 数据不变，映射时错位取值


def resolve_mappings(header_texts: list[str], user_mappings: list[dict] | None) -> dict[str, int]:
    """合并自动映射与用户映射。user_mappings: [{standard_field, source_column}]"""
    base = auto_map(header_texts)
    for m in (user_mappings or []):
        std, col = m.get("standard_field"), m.get("source_column")
        if std in base and isinstance(col, int) and 0 <= col < len(header_texts):
            base[std] = col
    return base


def parse_data_row(
    sm: SheetMatrix,
    row_idx: int,
    header_row: int,
    mappings: dict[str, int],
    shift: int,
    template_date: _dt.date | None,
) -> RowParse:
    """解析一行数据 → RowParse（含横向拆分）。row_idx 为 0 基。"""
    row = sm.rows[row_idx]
    header_texts = _header_texts(sm, header_row, shift)
    rp = RowParse(row_no=row_idx + 1)

    def val(std: str) -> dict:
        """取标准字段的单元格：位移时数据列 = 表头列 + shift（R-IMP-06）"""
        col = mappings.get(std)
        if col is None:
            return {"raw": "", "num": None, "date": None}
        data_col = col + shift
        if data_col >= len(row):
            return {"raw": "", "num": None, "date": None}
        return row[data_col]

    def header_name(std: str) -> str:
        col = mappings.get(std)
        return header_texts[col] if col is not None and col < len(header_texts) else ""

    # 快照 cells：列名→原文（真实表头名优先，无名/位移越界用 列序号）
    cells: dict[str, str] = {}
    for j, c in enumerate(row):
        hidx = j - shift
        name = header_texts[hidx] if 0 <= hidx < len(header_texts) and normalize_header(header_texts[hidx]) else f"列{j + 1}"
        cells[name] = c["raw"]
    rp.cells = cells
    hasher = hashlib.sha256()
    hasher.update(json.dumps(cells, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    rp.content_hash = hasher.hexdigest()

    # ---- 物料（R-IMP-28：名称或编码至少一个） ----
    desc_raw = val("material_name")["raw"]
    name_candidate, desc_full = split_material_desc(desc_raw)
    code = val("material_code")["raw"]
    mat = {
        "code": code or None,
        "name": (name_candidate or None) if name_candidate else (val("material_name")["raw"] or None),
        "name_raw": desc_full or desc_raw or None,
        "spec_model": val("spec_model")["raw"] or None,
        "tech_params": val("tech_params")["raw"] or None,
        "part_no": val("part_no")["raw"] or None,
        "material_text": val("material_text")["raw"] or None,
        "brand": val("brand")["raw"] or None,
        "origin_type": val("origin_type")["raw"] or None,
        "unit": val("unit")["raw"] or None,
        "category": None,
    }
    # 管道串第二段作为分类候选（"操作器||控制电器|…" → 控制电器）
    if desc_full and "|" in desc_full:
        segs = [s.strip() for s in desc_full.split("|") if s.strip()]
        if len(segs) >= 2:
            mat["category"] = segs[1]
    rp.material = mat

    # ---- 需求 ----
    req_date = parse_date_value(val("requirement_date"))
    date_inferred_from = None
    if req_date is not None:
        date_inferred_from = "cell"
    elif template_date is not None:
        req_date = template_date
        date_inferred_from = "template_date_row"  # 推断来源必标（API-TBD-001）
    qty = to_number(val("quantity"))
    rp.requirement = {
        "quantity": qty,
        "unit": val("usage_unit")["raw"] or val("unit")["raw"] or None,
        "requirement_date": req_date,
        "date_inferred_from": date_inferred_from,
        "receiver": val("receiver")["raw"] or None,
        "quote_row_no": val("quote_row_no")["raw"] or None,
        "remark": val("remark")["raw"] or None,
    }

    # ---- 行级校验 ----
    if not mat["name"] and not mat["code"]:
        rp.status = ERROR
        rp.reasons.append("物料名称与物料编码均为空，无法建立物料（R-IMP-28）")
        return rp

    # ---- 报价列（映射内的 *含税单价 等） ----
    std_quote = _quote_from_mapped_columns(val, rp)

    # ---- 横向拆分（R-IMP-14~17）：尾部非标准列分组 ----
    rp.quotes.extend(std_quote)
    rp.quotes.extend(_split_trailing_groups(row, header_texts, mappings, rp, shift))

    # ---- 备注价格提取（PRD 5.4："微信单价1350元 含税运" → 结构化报价，原文同存） ----
    if not rp.quotes:
        q = _quote_from_remark(rp)
        if q is not None:
            rp.quotes.append(q)
    return rp


def _quote_from_remark(rp: RowParse) -> QuoteParse | None:
    """从需求备注/备注单元格提取报价（无其他报价来源时）。

    - 单价邻域数字 → 高可信（auto_extracted）
    - "等报价/停产"类 → no_valid_price 记录
    - 其余不强行拆分（原文在快照与备注中保留）
    """
    texts: list[str] = []
    if rp.requirement.get("remark"):
        texts.append(rp.requirement["remark"])
    note = rp.cells.get("备注") or rp.cells.get("报价备注")
    if note and note not in texts:
        texts.append(note)
    joined = "\n".join(t for t in texts if t and t.strip())
    if not joined:
        return None
    amount, confident = extract_amount(joined)
    tax, freight = extract_tax_freight(joined)
    if amount is None:
        if is_no_price_text(joined):
            return QuoteParse(
                supplier_name=extract_vendor(joined), channel=extract_channel(joined),
                status="no_valid_price", remark=joined, group_label="备注",
            )
        return None
    # 备注语境严格化：仅当存在"单价"上下文或含税/含运语义时才提取（PRD 5.4 不强行转换）
    if not (confident or tax is not None or freight is not None):
        return None
    # 备注里的联系方式 → 供应商电话（R-IMP-15 敏感字段）
    phone = extract_phone(joined)
    if phone and rp.status == OK:
        rp.status = WARN
        rp.reasons.append("检测到联系方式出现在备注列，已归入供应商信息（敏感字段按角色展示）")
    return QuoteParse(
        amount=amount, tax_included=tax, freight_included=freight,
        channel=extract_channel(joined), supplier_name=extract_vendor(joined),
        supplier_phone=phone,
        status="auto_extracted" if confident else "needs_review",
        remark=joined, group_label="备注",
    )


def _quote_from_mapped_columns(val, rp: RowParse) -> list[QuoteParse]:
    """映射内的报价字段（模板 *含税单价 列等）→ 0..1 条报价。

    串列自愈（"价格列写了备注"场景）：
    - 金额列非数值但内容含价格语境（单价/含税/含运/元）→ 按文本提取金额语义，
      标记 needs_review 并给行级原因；原文仍保留在快照与报价备注中
    """
    amount = to_number(val("amount"))
    delivery = parse_date_value(val("delivery_date"))
    remark = val("quote_remark")["raw"] or None
    supplier_txt = val("supplier_name")["raw"] or None

    tax = freight = channel = None
    text_extracted = False
    amount_cell_text = (val("amount")["raw"] or "").strip()
    if amount is None and amount_cell_text and is_price_context(amount_cell_text):
        extracted, confident = extract_amount(amount_cell_text)
        if extracted is not None:
            amount = extracted
            tax, freight = extract_tax_freight(amount_cell_text)
            channel = extract_channel(amount_cell_text)
            text_extracted = True

    # 报价备注列写了价格文本（"含税单价620元含运"）→ 同样按语境提取，标记待确认
    if amount is None and remark and is_price_context(remark):
        extracted, confident = extract_amount(remark)
        if extracted is not None:
            amount = extracted
            tax, freight = extract_tax_freight(remark)
            channel = extract_channel(remark)
            text_extracted = True

    if amount is None and not supplier_txt and not remark and not text_extracted:
        return []
    qp = QuoteParse(
        amount=amount,
        tax_included=(True if amount is not None and not text_extracted else None),
        freight_included=freight,
        channel=channel or (extract_channel(remark or "") if remark else None),
        supplier_name=supplier_txt,
        remark=remark,
        status="needs_review",
    )
    # 备注列/价格列文本里的联系方式 → 供应商电话（R-IMP-15 敏感字段）
    phone = extract_phone((remark or "") + " " + amount_cell_text)
    if phone:
        qp.supplier_phone = phone
        if "检测到联系方式出现在非联系列，已归入供应商信息（敏感字段按角色展示）" not in rp.reasons:
            rp.reasons.append("检测到联系方式出现在非联系列，已归入供应商信息（敏感字段按角色展示）")
        if rp.status == OK:
            rp.status = WARN
    if text_extracted:
        rp.reasons.append("金额列为空但报价列文本含价格语义（疑似价格写在备注列），已提取金额并标记待确认，原文见快照")
        if rp.status == OK:
            rp.status = WARN
    elif amount is not None:
        qp.status = "auto_extracted"
    elif supplier_txt or remark or qp.supplier_phone:
        rp.reasons.append("映射列存在供应商/备注但无有效金额，标记待核对")
        if rp.status == OK:
            rp.status = WARN
    if delivery:
        rp.requirement["delivery_date"] = delivery
    return [qp]


def _split_trailing_groups(
    row: list[dict], header_texts: list[str], mappings: dict[str, int], rp: RowParse, shift: int
) -> list[QuoteParse]:
    """尾部非标准列按非空表头分组 → 每组 0..1 条报价（R-IMP-14~17）。

    坐标约定：mappings 为真实表头坐标；数据列 j 对应表头 j-shift。
    - 表头为空的尾部内容列（样例3）只并入需求备注，不拆报价
    - 组内提取金额/供应商/电话/渠道；可信度决定 quote.status
    """
    mapped_header_cols = {c for c in mappings.values() if c is not None}
    n_data = len(row)
    n_header = len(header_texts)

    def data_label(j: int) -> str:
        hidx = j - shift
        return normalize_header(header_texts[hidx]) if 0 <= hidx < n_header else ""

    quotes: list[QuoteParse] = []
    tail_texts: list[str] = []
    i = 0
    while i < n_data:
        if (i - shift) in mapped_header_cols:
            i += 1
            continue
        label = data_label(i)
        group_cols: list[int] = []
        j = i
        # 收集连续未映射列为一组，直到遇到下一个非空表头
        while j < n_data and (j - shift) not in mapped_header_cols:
            group_cols.append(j)
            j += 1
            if j < n_data and data_label(j):
                break
        texts = [row[c]["raw"] for c in group_cols if (row[c]["raw"] or "").strip()]
        joined = "\n".join(texts)
        # 内容型标签（含数字或过长，如样例3"频率要5600"）不作为分组报价依据，并入备注
        if label and (len(label) > 4 or any(ch.isdigit() for ch in label)):
            if joined:
                tail_texts.append(f"{label}: {joined}")
            i = j
            continue
        if not label:
            if joined:
                tail_texts.append(joined)
        elif joined:
            qp = _parse_group(label, texts)
            if qp is not None:
                quotes.append(qp)
        i = j

    if tail_texts:
        extra = "\n".join(tail_texts)
        rp.requirement["remark"] = ((rp.requirement.get("remark") or "") + ("\n" if rp.requirement.get("remark") else "") + extra) or None
        rp.reasons.append("存在无表头尾列内容，已并入需求备注不强行拆分（R-IMP-14）")
        if rp.status == OK:
            rp.status = WARN
    return quotes


def _parse_group(label: str, texts: list[str]) -> QuoteParse | None:
    joined = "\n".join(texts)
    phone = extract_phone(joined)
    vendor = None
    for t in texts:
        vendor = extract_vendor(t)
        if vendor:
            break
    amount, confident = extract_amount(joined)
    tax, freight = extract_tax_freight(joined)
    channel = extract_channel(joined)
    remark = joined

    if is_no_price_text(joined) and amount is None:
        return QuoteParse(
            supplier_name=vendor, supplier_phone=phone, channel=channel,
            status="no_valid_price", remark=remark, group_label=label,
        )
    if amount is None and not vendor and not phone:
        return None
    status = "auto_extracted" if (amount is not None and confident and (vendor or phone)) else "needs_review"
    return QuoteParse(
        amount=amount, tax_included=tax, freight_included=freight, channel=channel,
        supplier_name=vendor, supplier_phone=phone, status=status, remark=remark,
        group_label=label,
    )


def parse_sheet_rows(
    sm: SheetMatrix, header_row: int, mappings: dict[str, int], shift: bool
) -> list[RowParse]:
    """解析表头之下全部数据行"""
    shift_i = 1 if shift else 0
    template_date = find_template_date(sm)
    rows: list[RowParse] = []
    for idx in range(header_row + 1, sm.nrows):
        row = sm.rows[idx]
        if not any((c["raw"] or "").strip() for c in row):
            continue  # 全空行跳过（不计入结果）
        rows.append(parse_data_row(sm, idx, header_row, mappings, shift_i, template_date))
    return rows
