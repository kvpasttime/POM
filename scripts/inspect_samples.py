# -*- coding: utf-8 -*-
"""检查样例 xls 结构，用于导入规则设计（临时脚本）"""
import sys
import xlrd
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

for f in sorted(Path(r"D:\POM\fixtures").glob("*.xls")):
    print("=" * 80)
    print("FILE:", f.name)
    wb = xlrd.open_workbook(str(f))
    for ws in wb.sheets():
        print(f"  SHEET: {ws.name!r} rows={ws.nrows} cols={ws.ncols}")
        # 打印前 6 行，每行截断
        for r in range(min(6, ws.nrows)):
            vals = []
            for c in range(ws.ncols):
                v = ws.cell_value(r, c)
                if isinstance(v, str):
                    v = v.replace("\n", "\\n")[:24]
                elif isinstance(v, float) and v == int(v):
                    v = int(v)
                vals.append(str(v)[:24])
            # 压缩尾部空列
            while vals and vals[-1] == "":
                vals.pop()
            print(f"    R{r}: {vals}")
