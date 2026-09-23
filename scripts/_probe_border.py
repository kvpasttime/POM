# -*- coding: utf-8 -*-
"""边界形态实测：
A. 标签列在组头，空表头跨两列放数据（样例2 刘/曾组同款形态）
B. 数据放在标签列左侧一格（标签未盖住该组数据）
C. 位移检测在首列序列断档（1,2,4,5）时是否仍识别
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8")

from openpyxl import Workbook  # noqa: E402

from app.importers.engine import build_preview  # noqa: E402
from app.importers.detect import detect_shift, find_header_row  # noqa: E402
from app.importers.reader import read_workbook  # noqa: E402


def make(header: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def show(tag: str, preview: dict) -> None:
    print(f"--- {tag} ---")
    print("  shift:", preview["shift_detected"], "| summary:", preview["summary"])
    for r in preview["rows"]:
        qs = [(q["amount"], q["supplier"]) for q in r["preview"]]
        print(f"  R{r['row_no']} 状态={r['status']} 报价{r['quote_count']}条 {qs}")
        for reason in r["reasons"]:
            print("     reason:", reason[:64])


print("== A: 组标签在组头（刘列起，组内含空表头列） ==")
h_a = ["物料编码", "物料描述", "规格型号", "技术参数", "品牌", "单位", "零件号/图号",
       "材质", "进口/国产", "数量", "使用单位", "需求日期", "备注", "", "刘", "", "曾"]
rows_a = [[1, "A-001", "测试物料A", "SP-1", "", "", "件", "", "", 5, "矿A", "2026-11-01",
           "", "", "13812345678", "9605 含税运", "西门子专卖"]]
show("A", build_preview("A.xlsx", make(h_a, rows_a)))

print()
print("== B: 数据放到标签列左侧的空表头列 ==")
# 列序同上：第14列(空表头)放了价格，刘列只有电话
rows_b = [[1, "B-001", "测试物料B", "SP-2", "", "", "件", "", "", 3, "矿B", "2026-11-02",
           "", "9605 含税运", "13812345678", "", "等报价"]]
show("B", build_preview("B.xlsx", make(h_a, rows_b)))

print()
print("== C: 位移检测 + 首列序列断档（1,2,4,5） ==")
h_c = ["物料编码", "物料描述", "规格型号", "数量", "备注"]  # 无行号表头
rows_c = [
    [1, "C-001", "件1", 2, "备注1"],
    [2, "C-002", "件2", 3, "备注2"],
    [4, "C-004", "件4", 5, "备注4"],   # 断档：没有 3
    [5, "C-005", "件5", 6, "备注5"],
]
data_c = make(h_c, rows_c)
sheets = read_workbook("C.xlsx", data_c)
sm = sheets[0]
h = find_header_row(sm, False)
ok = detect_shift(sm, h, [c["raw"] for c in sm.rows[h]])
print("  shift 识别结果:", ok, "（序列断档时 True=仍识别 / False=放弃位移判定）")
