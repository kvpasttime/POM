# -*- coding: utf-8 -*-
"""验证生成的测试数据导入预览结果"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from app.importers.engine import build_preview  # noqa: E402

for f in sorted(os.listdir(r"D:\POM\testdata")):
    data = open(os.path.join(r"D:\POM\testdata", f), "rb").read()
    p = build_preview(f, data)
    print("==", f, "| header_row", p["header_row"], "| shift", p["shift_detected"], "|", p["summary"])
    for r in p["rows"][:8]:
        qs = " | ".join(f"{q['amount']}/{q['supplier']}" for q in r["preview"]) or "-"
        print("  R%d %s %s [%s] %s" % (r["row_no"], r["status"], r["material_name"], qs, ";".join(r["reasons"])[:50]))
