# -*- coding: utf-8 -*-
"""字段别名与自动映射（R-IMP-07~09，docs/05 4.3.2 mappings）"""
from __future__ import annotations

# 标准字段 → 别名表（PRD 7.3 + 样例表头实证）
FIELD_ALIASES: dict[str, list[str]] = {
    "row_no": ["行号"],
    "quote_row_no": ["报价行编号"],
    "material_code": ["物料编码", "物料编号", "编码"],
    "material_name": ["物料名称", "商品名称", "物料描述", "名称"],
    "tech_params": ["技术参数", "参数"],
    "spec_model": ["规格型号", "规格", "型号"],
    "part_no": ["零件号/图号", "零件号", "图号"],
    "material_text": ["材质"],
    "brand": ["品牌"],
    "origin_type": ["进口/国产", "进口国产"],
    "unit": ["单位", "使用单位_列"],
    "usage_unit": ["使用单位", "使用部门"],
    "receiver": ["接收人"],
    "requirement_date": ["需求日期", "日期", "报价日期", "询价日期"],
    "remark": ["备注", "需求备注"],
    "quantity": ["需求数量", "数量"],
    "supplier_spec_model": ["供应商规格型号"],
    "supplier_material": ["供应商材质"],
    "supplier_tech_params": ["供应商技术参数"],
    "supplier_name": ["供应商", "品牌/厂家", "厂家", "询价方"],
    "delivery_date": ["*交货日期", "交货日期"],
    "transport_mode": ["*运输方式", "运输方式"],
    "available_qty": ["*可供数量", "可供数量"],
    "amount": ["*含税单价", "含税单价", "报价", "定价", "单价"],
    "quote_remark": ["报价备注"],
}

# 映射到 quote/物料 组的"业务字段"（用于标准映射界面展示的顺序）
STANDARD_FIELDS = list(FIELD_ALIASES.keys())

# 品牌/厂家 明确不映射到供应商主体（R-IMP-08）；"品牌/厂家"是模板里的供应商列别名，见上表
BRAND_FIELD = "brand"


def normalize_header(text: str) -> str:
    return (text or "").strip().replace(" ", "").replace("*", "")


def match_alias(header_text: str) -> str | None:
    """返回别名命中的标准字段名（精确匹配优先）"""
    norm = normalize_header(header_text)
    if not norm:
        return None
    for std, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if norm == alias.replace("*", "").replace(" ", ""):
                return std
    # 退化子串匹配（长度 ≥2）
    for std, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            a = alias.replace("*", "")
            if len(a) >= 2 and (a in norm or norm in a):
                return std
    return None


def auto_map(header_texts: list[str]) -> dict[str, int | None]:
    """对表头行做别名自动映射：标准字段 → 源列下标（未命中为 None）。

    规则：
    - 同一源列只能映射一个字段（先到先得，精确匹配优先于子串）
    - "品牌"不得映射为 supplier_name（R-IMP-08）
    """
    used: set[int] = set()
    result: dict[str, int | None] = {}
    # 两轮：先精确后子串
    for std, aliases in FIELD_ALIASES.items():
        result[std] = None
    for exact in (True, False):
        for col, text in enumerate(header_texts):
            if col in used:
                continue
            norm = normalize_header(text)
            if not norm:
                continue
            for std, aliases in FIELD_ALIASES.items():
                if result[std] is not None:
                    continue
                for alias in aliases:
                    a = alias.replace("*", "").replace(" ", "")
                    hit = (norm == a) if exact else (len(a) >= 2 and (a in norm or norm in a))
                    if hit:
                        if std == "supplier_name" and norm == "品牌":
                            continue  # R-IMP-08
                        result[std] = col
                        used.add(col)
                        break
    return result


def header_fingerprint(header_texts: list[str]) -> str:
    import hashlib
    joined = "|".join(normalize_header(t) for t in header_texts if normalize_header(t))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
