# -*- coding: utf-8 -*-
"""重刷样例1/样例2：删除旧导入数据（绕 hash 拦截）→ 走新引擎重导（含报价构成明细）。
样例3（无报价）不动。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.business import Quote, QuoteBreakdown, PurchaseRequirement, SourceRowSnapshot  # noqa: E402
from app.models.ops import ImportBatch, ImportRowResult, SourceFile  # noqa: E402

FIX = r"D:\POM\fixtures"
S1 = os.path.join(FIX, "sample1_操作器_郭剑飞8.31.xls")
S2 = os.path.join(FIX, "sample2_办公电子设备_项礼春8.30.xls")

# 1) 删除样例1/2 全部旧数据（批次 1,6,7,8,10,11）与其源文件行（解除 hash 拦截）
db = SessionLocal()
try:
    hash1 = db.query(SourceFile).filter(SourceFile.sha256.isnot(None)).all()
    s1_hash = [f.sha256 for f in hash1 if f.original_name.startswith("操作器") or (f.duplicate_of_file_id and f.duplicate_of_file_id in [1, 6, 7, 8, 11])]
    s2_hash = [f.sha256 for f in hash1 if "台式电脑" in f.original_name or "办公电子" in f.original_name]
    target_batches = set()
    for f in db.query(SourceFile).all():
        nm = f.original_name
        if ("操作器" in nm) or ("台式电脑" in nm) or ("办公电子" in nm):
            target_batches.add(f.batch_id)
    print("重刷批次:", sorted(b for b in target_batches if b))
    batches = [b for b in target_batches if b]
    snap_ids = [s.id for s in db.query(SourceRowSnapshot.id)
                .join(SourceFile, SourceFile.id == SourceRowSnapshot.source_file_id)
                .filter(SourceFile.batch_id.in_(batches)).all()]
    keep_req = {i[0] for i in db.query(Quote.requirement_id).filter(
        Quote.requirement_id.isnot(None),
        ~Quote.import_batch_id.in_(batches)).all()}
    n = db.query(Quote).filter(Quote.import_batch_id.in_(batches)).delete(synchronize_session=False)
    print("删报价", n)
    reqs = (db.query(PurchaseRequirement)
            .filter(PurchaseRequirement.id.notin_(keep_req))
            .filter(PurchaseRequirement.source_row_snapshot_id.in_(snap_ids)))
    print("删需求", reqs.delete(synchronize_session=False))
    print("删快照", db.query(SourceRowSnapshot).filter(SourceRowSnapshot.id.in_(snap_ids)).delete(synchronize_session=False))
    print("删行级结果", db.query(ImportRowResult).filter(ImportRowResult.batch_id.in_(batches)).delete(synchronize_session=False))
    print("删源文件", db.query(SourceFile).filter(SourceFile.batch_id.in_(batches)).delete(synchronize_session=False))
    # 孤儿批次（无文件引用的 6/7/8 等重复拦截批）
    orphans = [b.id for b in db.query(ImportBatch).all()
               if db.query(SourceFile).filter(SourceFile.batch_id == b.id).count() == 0
               and db.query(Quote).filter(Quote.import_batch_id == b.id).count() == 0
               and b.id not in (9,)]
    print("删孤儿批次", orphans, db.query(ImportBatch).filter(ImportBatch.id.in_(orphans)).delete(synchronize_session=False))
    db.commit()
finally:
    db.close()


def commit_sheets(c, H, batch_id, fid, sheets):
    items, token = [], None
    for sheet in sheets:
        pv = c.get(f"/api/v1/imports/{batch_id}/preview?file_id={fid}&sheet_name={sheet}",
                   headers=H).json()["data"]
        items.append({"file_id": fid, "sheet_name": sheet, "header_row": pv["header_row"],
                      "mappings": pv["mappings"], "skip_error_rows": False})
        token = pv["commit_token"]
    cm = c.post(f"/api/v1/imports/{batch_id}/commit", headers=H, json={
        "commit_token": token, "file_commits": items})
    s = cm.json()["data"]["summary"]
    print(f"批次#{batch_id} 成功{s['success']} 跳过{s['skipped']} 失败{s['failed']} 待确认{s['needs_review']}")


with TestClient(app, base_url="http://testserver") as c:
    tok = c.post("/api/v1/auth/login",
                 json={"username": "admin", "password": "$JrDjVC6j8dA"}).json()["data"]["token"]
    H = {"Authorization": "Bearer " + tok}
    for name, path, sheets in [
        ("操作器等_郭剑飞8.31.xls", S1, ["导入报价模板", "Sheet1"]),
        ("台式电脑 打印机及运动相机等办公电子设备 项礼春8.30.xls", S2, ["Sheet1"]),
    ]:
        with open(path, "rb") as fh:
            up = c.post("/api/v1/imports/upload", files={"files": (name, fh)}, headers=H)
        bid = up.json()["data"]["batch_id"]
        fid = next(f["file_id"] for f in up.json()["data"]["files"] if f["check_status"] == "passed")
        print("上传", name[:20], "→ 批次#", bid)
        commit_sheets(c, H, bid, fid, sheets)
