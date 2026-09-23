# -*- coding: utf-8 -*-
"""移除编造测试数据（批次 #2/#3/#4/#5，gen_test_data.py 的 4 个文件产生）。

删除顺序（逆依赖）：报价 → 需求 → 快照 → 行级结果 → 源文件 → 批次 → 只被测试引用的物料/供应商。
真实数据（批次 #1/#9/#10/#11 等）不动。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from app.core.database import SessionLocal  # noqa: E402
from app.models.business import Material, PurchaseRequirement, Quote, SourceRowSnapshot, Supplier  # noqa: E402
from app.models.ops import ImportBatch, ImportRowResult, SourceFile  # noqa: E402

TEST_BATCHES = [2, 3, 4, 5]

db = SessionLocal()
try:
    batch = db.query(ImportBatch).filter(ImportBatch.id.in_(TEST_BATCHES)).all()
    print("目标批次:", [b.id for b in batch])

    # 1) 删除测试批次报价
    n = db.query(Quote).filter(Quote.import_batch_id.in_(TEST_BATCHES)).delete(synchronize_session=False)
    db.flush()
    print(f"删除报价 {n} 条")

    # 2) 测试批次关联的快照（通过 源文件→批次）
    snap_ids = [r[0] for r in (db.query(SourceRowSnapshot.id)
                .join(SourceFile, SourceFile.id == SourceRowSnapshot.source_file_id)
                .filter(SourceFile.batch_id.in_(TEST_BATCHES)).all())]

    # 3) 无报价引用的需求（保留仍被真实报价引用的需求）
    keep_req = {i[0] for i in db.query(Quote.requirement_id)
                .filter(Quote.requirement_id.isnot(None)).all()}
    reqs = (db.query(PurchaseRequirement)
            .filter(PurchaseRequirement.id.notin_(keep_req))
            .filter(PurchaseRequirement.source_row_snapshot_id.in_(snap_ids)))
    del_req = reqs.all()
    for r in del_req:
        db.delete(r)
    print(f"删除需求 {len(del_req)} 条")

    # 4) 快照
    n = db.query(SourceRowSnapshot).filter(SourceRowSnapshot.id.in_(snap_ids)).delete(synchronize_session=False)
    print(f"删除快照 {n} 行")

    # 5) 行级结果 + 源文件
    n = db.query(ImportRowResult).filter(ImportRowResult.batch_id.in_(TEST_BATCHES)).delete(synchronize_session=False)
    print(f"删除行级结果 {n} 条")
    n = db.query(SourceFile).filter(SourceFile.batch_id.in_(TEST_BATCHES)).delete(synchronize_session=False)
    print(f"删除源文件 {n} 条")

    # 6) 批次
    db.query(ImportBatch).filter(ImportBatch.id.in_(TEST_BATCHES)).delete(synchronize_session=False)
    print("删除批次 4 个")

    # 7) 物料：TEST-* 前缀且已无报价引用
    del_m = []
    for m in db.query(Material).filter(Material.code.like("TEST%")).all():
        if db.query(Quote).filter(Quote.material_id == m.id).count() == 0:
            db.delete(m)
            del_m.append(m)
    print(f"删除物料 {len(del_m)} 个")

    # 8) 供应商：删除后无任何报价引用（never referenced by real quotes）
    del_s = []
    for s in db.query(Supplier).all():
        refs = db.query(Quote).filter(Quote.supplier_id == s.id).count()
        if refs == 0 and s.id not in (keep_sup := {q.supplier_id for q in db.query(Quote).all() if q.supplier_id}):
            db.delete(s)
            del_s.append(s)
    print(f"删除孤儿供应商 {len(del_s)} 个")

    db.commit()
    print("--- 已提交 ---")
    print("剩余 material", db.query(Material).count(),
          "| quote", db.query(Quote).count(),
          "| requirement", db.query(PurchaseRequirement).count(),
          "| batch", db.query(ImportBatch).count())
    db.close()
except Exception:
    db.rollback()
    db.close()
    raise
