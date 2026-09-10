# -*- coding: utf-8 -*-
"""备注/文本清洗提取（R-IMP-12/13、PRD 5.4 清洗边界）。

只提取明确且可验证的内容；不可靠内容保留原文并降低可信度。
"""
from __future__ import annotations

import re

# 渠道关键词（PRD 5.4 示例：微信渠道）
CHANNEL_PATTERNS = [
    ("微信", "微信"), ("淘宝", "淘宝"), ("天猫", "天猫"), ("京东", "京东"),
    ("1688", "1688"), ("阿里巴巴", "1688"), ("拼多多", "拼多多"), ("电话", "电话"),
    ("TB", "淘宝"),
]

# 供应商名特征词（样例2：上海赛博数码/DJI大疆美承专卖店、影石Insta360官方旗舰店）
VENDOR_HINTS = ["公司", "店", "处", "厂", "商行", "贸易", "科技", "专营", "专卖", "经销", "旗舰店", "有限"]

NO_PRICE_PATTERNS = ["等报价", "未报价", "暂无报价", "未回复", "没有回", "询价失败", "已停产", "停产"]

AMOUNT_RE = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:元|块|万)?")
UNIT_PRICE_CTX = re.compile(r"(?:单价|价格|定价|报价|含税单价)\s*[:：]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)")

PHONE_RE = re.compile(r"1[3-9]\d{9}|0\d{2,3}-?\d{7,8}")


def _clean(text: str) -> str:
    return (text or "").strip()


def extract_amount(text: str) -> tuple[float | None, bool]:
    """提取金额。返回 (金额, 是否高可信)。优先"单价"邻域数字（样例：微信单价1350元）。"""
    t = _clean(text)
    m = UNIT_PRICE_CTX.search(t)
    if m:
        try:
            return float(m.group(1).replace(",", "")), True
        except ValueError:
            pass
    m = AMOUNT_RE.search(t)
    if m:
        try:
            return float(m.group(1).replace(",", "")), False
        except ValueError:
            pass
    return None, False


def extract_tax_freight(text: str) -> tuple[bool | None, bool | None]:
    """含税/含运识别。无法判断返回 None（不静默猜测）。"""
    t = _clean(text)
    tax: bool | None = None
    freight: bool | None = None
    if "含税运" in t or "含税含运" in t or "含税，含运" in t:
        tax, freight = True, True
    else:
        if "含税" in t:
            tax = "不含税" not in t and "未含税" not in t
        if "含运" in t or "含邮" in t:
            freight = True
        if "不含运" in t or "运费另" in t:
            freight = False
    return tax, freight


def extract_channel(text: str) -> str | None:
    t = _clean(text)
    for kw, name in CHANNEL_PATTERNS:
        if kw in t:
            return name
    return None


def extract_vendor(text: str) -> str | None:
    """从组内文本提取供应商名（VENDOR_HINTS 特征）。取最长命中片段。"""
    t = _clean(text)
    if not t:
        return None
    best: str | None = None
    for seg in re.split(r"[\n/，,；; ]+", t):
        seg = seg.strip()
        if len(seg) >= 3 and any(h in seg for h in VENDOR_HINTS):
            if best is None or len(seg) > len(best):
                best = seg
    return best


def extract_phone(text: str) -> str | None:
    m = PHONE_RE.search(_clean(text))
    return m.group(0) if m else None


def is_no_price_text(text: str) -> bool:
    t = _clean(text)
    return any(p in t for p in NO_PRICE_PATTERNS)


def split_material_desc(desc: str) -> tuple[str | None, str | None]:
    """物料描述管道串拆分（R-IMP-13）："操作器||控制电器|WP-D435-022-12"。

    返回 (物料名称候选, 原文整串)。名称取第一段非空。
    """
    t = _clean(desc)
    if not t:
        return None, None
    if "|" not in t:
        return t, t
    first = next((seg.strip() for seg in t.split("|") if seg.strip()), None)
    return first, t


def normalize_supplier_key(name: str) -> str:
    """供应商归一键（R-IMP-29）：去空格/全半角/小写"""
    t = _clean(name)
    t = t.translate(str.maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ（）", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz()"))
    return t.replace(" ", "").lower()


def to_number(cell: dict) -> float | None:
    """单元格转数值：num 优先，文本退化解析（PRD 7.2 金额必须为数值或为空）"""
    if cell["num"] is not None:
        return cell["num"]
    t = _clean(cell["raw"]).replace(",", "").replace("元", "")
    try:
        return float(t)
    except ValueError:
        return None
