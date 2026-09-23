# -*- coding: utf-8 -*-
"""结构增量（2026-09-23）：报价人字段 + 报价构成明细表。
对已存在的库执行：ALTER quote ADD quoter / CREATE quote_breakdown（幂等）。
新库由 create_all 自动包含。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from app.core.database import Base, engine  # noqa: E402
import app.models.user  # noqa: E402,F401
import app.models.business  # noqa: E402,F401
import app.models.ops  # noqa: E402,F401

from sqlalchemy import text  # noqa: E402

with engine.begin() as conn:
    # 幂等加列（PG/SQLite 同语法）
    try:
        conn.execute(text("ALTER TABLE quote ADD COLUMN quoter VARCHAR(64)"))
        print("quote.quoter 列已添加")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "exists" in msg or "already" in msg:
            print("quote.quoter 已存在，跳过")
        else:
            raise

Base.metadata.create_all(engine)
print("表结构就绪（quote_breakdown 由 create_all 保证）")
