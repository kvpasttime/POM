# -*- coding: utf-8 -*-
"""补导入真实样例残留工作表：
- 样例2（台式电脑/项礼春8.30）：从未导入 → 模板表 + Sheet1 一批双表提交
- 样例1（操作器/郭剑飞8.31）：文件哈希已注册（批次#1 只导过模板表）→ 直登记新批次导入 Sheet1
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.ops import ImportBatch, SourceFile  # noqa: E402
from app.services.storage_service import save_upload  # noqa: E402
from app.core.security import sha256_bytes  # noqa: E402
from app.core.config import get_settings  # noqa: E402

FIX = r"D:\POM\fixtures"
S1 = os.path.join(FIX, "sample1_操作器_郭剑飞8.31.xls")
S2 = os.path.join(FIX, "sample2_办公电子设备_项礼春8.30.xls")

ADMIN_PWD = "$JrDjVC6j8dA"

with TestClient(app, base_url="http://testserver") as c:
    tok = c.post("/api/v1/auth/login",
                 json={"username": "admin", "password": ADMIN_PWD}).json()["data"]["token"]
    H = {"Authorization": "Bearer " + tok}

    def commit_sheets(batch_id, file_id, sheets: list[str]):
        """对同批次同一文件，逐 sheet 预览并合并为一次提交"""
        items = []
        token = None
        for sheet in sheets:
            pv = c.get(f"/api/v1/imports/{batch_id}/preview?file_id={fid}&sheet_name={sheet}",
                       headers=H).json()["data"]
            items.append({"file_id": fid, "sheet_name": sheet,
                          "header_row": pv["header_row"], "mappings": pv["mappings"],
                          "skip_error_rows": False})
            token = pv["commit_token"]
        cm = c.post(f"/api/v1/imports/{batch_id}/commit", headers=H, json={
            "commit_token": token, "file_commits": items})
        s = cm.json()["data"]["summary"]
        print(f"批次#{batch_id} 提交完成：成功{s['success']} 跳过{s['skipped']} 失败{s['failed']} 待确认{s['needs_review']}")

    # ---------- 样例2：全新上传，两张表一起提交 ----------
    data2 = open(S2, "rb").read()
    up = c.post("/api/v1/imports/upload",
                files={"files": ("台式电脑 打印机及运动相机等办公电子设备 项礼春8.30.xls", data2)},
                headers=H)
    bid = up.json()["data"]["batch_id"]
    fid = next(f["file_id"] for f in up.json()["data"]["files"] if f["check_status"] == "passed")
    print("样例2 上传批次#", bid)
    cm = c.post(f"/api/v1/imports/{bid}/commit", headers=H, json={
        "commit_token": None, "file_commits": []})
    # 先逐表预览拿 token，再一次提交
    token = None
    commit_items = []
    for sheet in ("导入报价模板", "Sheet1"):
        pv = c.get(f"/api/v1/imports/{bid}/preview?file_id={fid}&sheet_name={sheet}",
                   headers=H).json()["data"]
        commit_items.append({"file_id": fid, "sheet_name": sheet,
                             "header_row": pv["header_row"], "mappings": pv["mappings"],
                             "skip_error_rows": False})
        token = pv["commit_token"]
    cm = c.post(f"/api/v1/imports/{bid}/commit", headers=H, json={
        "commit_token": token, "file_commits": commit_items})
    s = cm.json()["data"]["summary"]
    print(f"样例2 批次#{bid}：成功{s['success']} 跳过{s['skipped']} 失败{s['failed']} 待确认{s['needs_review']}")

    # ---------- 样例1 的 Sheet1（哈希已注册，绕过文件级拦截登记新批次） ----------
    data1 = open(S1, "rb").read()
    rel = save_upload(data1, "操作器等_郭剑飞8.31.xls")
    db_dir = get_settings().upload_dir
    full = os.path.join(db_dir, rel)

    db = None
    from app.core.database import SessionLocal
    db = SessionLocal()
    batch = ImportBatch(created_by=1, status="pending", file_count=1)
    db.add(batch)
    db.flush()
    sf = SourceFile(batch_id=batch.id, original_name="操作器等_郭剑飞8.31.xls",
                    stored_path=rel, sha256=sha256_bytes(data1),
                    file_size=len(data1), file_type="xls", check_status="passed", created_by=1)
    db.add(sf)
    db.commit()
    bid = batch.id
    fid = sf.id
    db.close()
    print("样例1 新批次#", bid)

    pv = c.get(f"/api/v1/imports/{bid}/preview?file_id={fid}&sheet_name=Sheet1", headers=H).json()["data"]
    cm = c.post(f"/api/v1/imports/{bid}/commit", headers=H, json={
        "commit_token": pv["commit_token"],
        "file_commits": [{"file_id": fid, "sheet_name": "Sheet1",
                          "header_row": pv["header_row"], "mappings": pv["mappings"],
                          "skip_error_rows": False}]})
    s = cm.json()["data"]["summary"]
    print(f"样例1(Sheet1) 批次#{bid}：成功{s['success']} 跳过{s['skipped']} 失败{s['failed']} 待确认{s['needs_review']}")
