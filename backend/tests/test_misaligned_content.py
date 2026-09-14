# -*- coding: utf-8 -*-
"""串列自愈回归：价格列写备注文本 / 备注列写联系方式（用户真实痛点场景）"""
import io
import sys

sys.path.insert(0, io and ".")

from app.importers.engine import build_preview  # noqa: E402
from app.importers.splitter import parse_sheet_rows, resolve_mappings  # noqa: E402
from app.importers.reader import read_workbook  # noqa: E402
from openpyxl import Workbook  # noqa: E402

TEMPLATE_HEADER = ["行号", "报价行编号", "物料编码", "物料名称", "技术参数", "规格型号", "零件号/图号",
                   "材质", "品牌", "进口/国产", "单位", "使用单位", "需求日期", "备注", "需求数量",
                   "供应商规格型号", "供应商材质", "供应商技术参数", "品牌/厂家",
                   "*交货日期", "*运输方式", "*可供数量", "*含税单价", "报价备注"]


def _wb_bytes(wb: Workbook) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _row_with_price_text():
    """价格列('*含税单价')写入了备注文本："微信单价1350元，含税运" → 应提取 1350/含税/含运/微信"""
    wb = Workbook()
    ws = wb.active
    ws.title = "导入报价模板"
    ws.append(["导入报价模板"])
    ws.append(["日期:2026-09-01 10:00:00"])
    ws.append(TEMPLATE_HEADER)
    row = [""] * 24
    row[0] = 1                    # 行号
    row[1] = "Q-1"                # 报价行编号
    row[2] = "MIS-001"            # 物料编码
    row[3] = "测试轴承"           # 物料名称
    row[10] = "套"                # 单位
    row[11] = "测试一矿"          # 使用单位
    row[12] = "2026-11-01"        # 需求日期
    row[13] = "我是被写串的备注"  # 备注
    row[14] = 5                   # 需求数量
    row[21] = 5                         # *可供数量
    row[22] = "微信单价1350元，含税运"  # *含税单价 ← 串列！
    row[23] = ""                        # 报价备注
    ws.append(row)
    return wb


def _row_with_phone_in_remark():
    """备注列写了联系方式：微信单价9块，赵工 1337564321 → 金额 9 + 电话归供应商"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["行号", "物料编码", "物料描述", "规格型号", "技术参数", "品牌", "单位", "零件号/图号",
               "材质", "进口/国产", "数量", "接收人", "使用单位", "需求日期", "备注", "定价"])
    ws.append([1, "MIS-002", "测试弹簧||弹性件|65Mn", "5x30", "", "", "件", "", "", "",
               5, "王工", "测试六矿", "2026-12-06", "联系人13957934455，微信单价8.5含税运", ""])
    return wb


def test_price_column_contains_remark_text():
    """价格列串列：'微信单价1350元，含税运' → 金额1350/含税/含运/微信 + 待确认 + 原因"""
    preview = build_preview("mis1.xlsx", _wb_bytes(_row_with_price_text()))
    assert preview["summary"]["warn"] == 1 and preview["summary"]["error"] == 0
    row = next(r for r in preview["rows"] if r["material_code"] == "MIS-001")
    assert row["quote_count"] == 1
    q = row["preview"][0]
    assert q["amount"] == 1350.0
    assert q["status"] == "needs_review"  # 文本提取一律待人工确认
    assert any("疑似价格写在备注列" in r for r in row["reasons"])


def test_remark_column_contains_phone():
    """备注列串列联系方式：电话归供应商敏感字段 + 金额 8.5 提取"""
    preview = build_preview("mis2.xlsx", _wb_bytes(_row_with_phone_in_remark()))
    row = next(r for r in preview["rows"] if r["material_code"] == "MIS-002")
    assert row["quote_count"] == 1
    q = row["preview"][0]
    assert q["amount"] == 8.5
    # 引擎层面：RowParse 带 supplier_phone
    sheets = read_workbook("mis2.xlsx", _wb_bytes(_row_with_phone_in_remark()))
    sm = next(s for s in sheets if s.name == "Sheet1")
    mappings = resolve_mappings([c["raw"] for c in sm.rows[0]], None)
    rows = parse_sheet_rows(sm, 0, mappings, False)
    rp = rows[0]
    assert rp.quotes[0].supplier_phone == "13957934455"
    assert any("联系方式" in r for r in rp.reasons)
