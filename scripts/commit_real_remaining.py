# -*- coding: utf-8 -*-
"""提交已上传的样例1/样例2残留工作表（通过 API，走正常行级校验）"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN_PWD = "$JrDjVC6j8dA"

with TestClient(app, base_url="http://testserver") as c:
    tok = c.post("/api/v1/auth/login",
                 json={"username": "admin", "password": ADMIN_PWD}).json()["data"]["token"]
    H = {"Authorization": "Bearer " + tok}

    def commit(batch_id: int, fid: int, sheets: list[str]):
        items, token = [], None
        for sheet in sheets:
            pv = c.get(f"/api/v1/imports/{batch_id}/preview?file_id={fid}&sheet_name={sheet}",
                       headers=H).json()["data"]
            items.append({"file_id": fid, "sheet_name": sheet, "header_row": pv["header_row"],
                          "mappings": pv["mappings"], "skip_error_rows": False})
            token = pv["commit_token"]
        cm = c.post(f"/api/v1/imports/{batch_id}/commit", headers=H, json={
            "commit_token": token, "file_commits": items})
        if cm.status_code != 200:
            print(f"批次#{batch_id} COMMIT FAIL {cm.status_code}", cm.text[:200])
            return
        s = cm.json()["data"]["summary"]
        print(f"批次#{batch_id} 提交完成：成功{s['success']} 跳过{s['skipped']} "
              f"失败{s['failed']} 待确认{s['needs_review']}")

    # 样例2（台式电脑…已经 upload passed 在批次#10 文件#10）
    commit(10, 10, ["导入报价模板", "Sheet1"])
    # 样例1 的 Sheet1（批次#11 文件#11 为我登记的新文件行）
    commit(11, 11, ["Sheet1"])
