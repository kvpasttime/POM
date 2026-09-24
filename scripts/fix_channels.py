# -*- coding: utf-8 -*-
"""存量数据修复：渠道按店走。
- quote_breakdown.store_name 剥离 TB/JD/TM/PDD 尾缀 → channel 字段填充
- 组合报价（明细>1 家店）的 quote.channel 清空（不再整条标单一渠道）
- supplier 表店名同步清洗尾缀
幂等：再次执行无变化。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from app.core.database import SessionLocal  # noqa: E402
import app.models.ops  # noqa: E402,F401  注册 ImportBatch 等（FK 排序需要）
from app.models.business import Quote, QuoteBreakdown, Supplier  # noqa: E402
from app.importers.extract import strip_channel_suffix  # noqa: E402

db = SessionLocal()
try:
    n_clean, n_ch = 0, 0
    for bd in db.query(QuoteBreakdown).all():
        clean, ch = strip_channel_suffix(bd.store_name)
        if clean != bd.store_name:
            bd.store_name = clean
            n_clean += 1
        if ch and bd.channel != ch:
            bd.channel = ch
            n_ch += 1
    print(f"明细店名清洗 {n_clean} 条，渠道补齐 {n_ch} 条")

    # 组合报价（≥2 家明细店）主渠道置空；单店报价主渠道=该店渠道
    n_q = 0
    for q in db.query(Quote).all():
        bds = db.query(QuoteBreakdown).filter(QuoteBreakdown.quote_id == q.id).all()
        stores = {(b.store_name or "").strip() for b in bds}
        want = None if len(stores) >= 2 else (bds[0].channel if bds else q.channel)
        if q.channel != want:
            q.channel = want
            n_q += 1
    print(f"报价主渠道修正 {n_q} 条")

    n_s = 0
    for s in db.query(Supplier).all():
        clean, _ch = strip_channel_suffix(s.name)
        if clean != s.name and len(clean) >= 3:
            s.name = clean
            n_s += 1
    print(f"供应商名清洗 {n_s} 条")

    db.commit()
    print("--- 已提交 ---")
finally:
    db.close()
