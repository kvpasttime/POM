# -*- coding: utf-8 -*-
"""清理报价构成明细重复行：同一 quote 内同店名只保留最早一条（幂等修复）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from app.core.database import SessionLocal  # noqa: E402
from app.models.business import QuoteBreakdown  # noqa: E402

db = SessionLocal()
try:
    seen: dict[tuple, int] = {}
    removed = 0
    for bd in db.query(QuoteBreakdown).order_by(QuoteBreakdown.id).all():
        key = (bd.quote_id, (bd.store_name or "").strip())
        if key in seen:
            db.delete(bd)
            removed += 1
        else:
            seen[key] = bd.id
    db.commit()
    print(f"去除重复明细 {removed} 条，剩余 {len(seen)} 条唯一明细")
finally:
    db.close()
