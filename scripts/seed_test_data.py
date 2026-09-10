# -*- coding: utf-8 -*-
"""把 testdata 下的文件通过 API 灌入开发库（admin 登录）"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN_PWD = os.environ.get("ADMIN_PWD", "")
FILES = [
    "测试文件1_标准模板_带价格.xlsx",
    "测试文件2_仅需求无报价.xlsx",
    "测试文件3_手工乱表_横向拆分.xlsx",
    "测试文件4_异常与特殊行.xlsx",
]
BASE = r"D:\POM\testdata"

if not ADMIN_PWD:
    print("请设置环境变量 ADMIN_PWD（admin 登录密码）")
    sys.exit(1)

with TestClient(app, base_url="http://testserver") as c:
    tok = c.post("/api/v1/auth/login", json={"username": "admin", "password": ADMIN_PWD}).json()["data"]["token"]
    H = {"Authorization": "Bearer " + tok}
    for name in FILES:
        up = c.post("/api/v1/imports/upload",
                    files={"files": (name, open(os.path.join(BASE, name), "rb"))}, headers=H)
        if up.status_code != 200:
            print(name, "UPLOAD FAIL", up.text[:200])
            continue
        bid = up.json()["data"]["batch_id"]
        fid = next(f["file_id"] for f in up.json()["data"]["files"] if f["check_status"] == "passed")
        pv = c.get(f"/api/v1/imports/{bid}/preview?file_id={fid}", headers=H).json()["data"]
        cm = c.post(f"/api/v1/imports/{bid}/commit", headers=H, json={
            "commit_token": pv["commit_token"],
            "file_commits": [{"file_id": fid, "sheet_name": pv["sheet_name"],
                              "header_row": pv["header_row"], "mappings": pv["mappings"],
                              "skip_error_rows": False}]})
        if cm.status_code == 200:
            s = cm.json()["data"]["summary"]
            print(f"{name}: 批次#{bid} 成功{s['success']} 跳过{s['skipped']} 失败{s['failed']} 待确认{s['needs_review']}")
        else:
            print(name, "COMMIT FAIL", cm.status_code, cm.text[:200])
