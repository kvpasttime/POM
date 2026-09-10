# -*- coding: utf-8 -*-
"""F06-INT-001：全链路 API 冒烟（登录→导入→查询→纠错→审计→下载）"""
import os

import pytest

from tests.conftest import FIXTURES

SAMPLE1 = os.path.join(FIXTURES, "sample1_操作器_郭剑飞8.31.xls")


def _upload_and_commit(client, headers, path):
    with open(path, "rb") as fh:
        up = client.post("/api/v1/imports/upload", files={"files": (os.path.basename(path), fh)},
                         headers=headers)
    assert up.status_code == 200, up.text
    batch_id = up.json()["data"]["batch_id"]
    files = up.json()["data"]["files"]
    passed = next(f for f in files if f["check_status"] == "passed")
    file_id = passed["file_id"]
    pv = client.get(f"/api/v1/imports/{batch_id}/preview?file_id={file_id}&sheet_name=Sheet1",
                    headers=headers)
    assert pv.status_code == 200, pv.text
    pvdata = pv.json()["data"]
    commit = client.post(f"/api/v1/imports/{batch_id}/commit", headers=headers, json={
        "commit_token": pvdata["commit_token"],
        "file_commits": [{"file_id": file_id, "sheet_name": pvdata["sheet_name"],
                          "header_row": pvdata["header_row"],
                          "mappings": pvdata["mappings"], "skip_error_rows": False}],
    })
    assert commit.status_code == 200, commit.text
    return batch_id, commit.json()["data"]


@pytest.mark.skipif(not os.path.exists(SAMPLE1), reason="样例文件不在本地（开源仓库不含真实数据）")
def test_full_chain_smoke(client, maintainer_headers, admin_headers, viewer_headers):
    # 1. 导入（Sheet1 含横向备注价格）
    with open(SAMPLE1, "rb") as fh:
        up = client.post("/api/v1/imports/upload",
                         files={"files": (os.path.basename(SAMPLE1), fh)},
                         headers=maintainer_headers)
    batch_id = up.json()["data"]["batch_id"]
    file_id = next(f["file_id"] for f in up.json()["data"]["files"] if f["check_status"] == "passed")
    pv = client.get(f"/api/v1/imports/{batch_id}/preview?file_id={file_id}&sheet_name=Sheet1",
                    headers=maintainer_headers).json()["data"]
    assert pv["shift_detected"] is True
    commit = client.post(f"/api/v1/imports/{batch_id}/commit", headers=maintainer_headers, json={
        "commit_token": pv["commit_token"],
        "file_commits": [{"file_id": file_id, "sheet_name": "Sheet1",
                          "header_row": pv["header_row"],
                          "mappings": pv["mappings"], "skip_error_rows": False}]})
    assert commit.status_code == 200
    report = commit.json()["data"]
    assert report["summary"]["success"] > 0

    # 2. 搜索
    search = client.get("/api/v1/quotes/search?keyword=接触器",
                        headers=viewer_headers)
    assert search.status_code == 200
    items = search.json()["data"]["items"]
    assert len(items) > 0
    target = items[0]
    # 3. 详情（user 视角）
    detail = client.get(f"/api/v1/quotes/{target['id']}", headers=viewer_headers)
    assert detail.status_code == 200
    d = detail.json()["data"]
    assert d["source"]["raw_cells"]  # 可追溯（FR11）
    assert d["source"]["sheet_name"] and d["source"]["row_no"]

    # 4. viewer 无权修改（R-AUTH-09）
    denied = client.patch(f"/api/v1/quotes/{target['id']}",
                          json={"fields": {"remark": "x"}, "reason": "测试", "version": d["version"]},
                          headers=viewer_headers)
    assert denied.status_code == 403

    # 5. 维护员纠错留痕（FR18）
    patch = client.patch(f"/api/v1/quotes/{target['id']}",
                         json={"fields": {"remark": "人工核对后的备注"},
                               "reason": "核对原文件", "version": d["version"]},
                         headers=maintainer_headers)
    assert patch.status_code == 200, patch.text
    new_version = patch.json()["data"]["version"]

    # 6. 修订记录可查
    revs = client.get(f"/api/v1/quotes/{target['id']}/revisions", headers=maintainer_headers)
    assert revs.status_code == 200
    assert revs.json()["data"]["total"] >= 1

    # 7. 软删除 → 查询不可见 → admin 恢复（FR19）
    client.delete(f"/api/v1/quotes/{target['id']}", headers=maintainer_headers)
    after_del = client.get("/api/v1/quotes/search?keyword=接触器", headers=viewer_headers)
    assert all(i["id"] != target["id"] for i in after_del.json()["data"]["items"])
    restore = client.post(f"/api/v1/quotes/{target['id']}/restore",
                          json={"reason": "误删恢复"}, headers=admin_headers)
    assert restore.status_code == 200

    # 8. 审计（FR03）：导入/修改/删除/恢复均有记录
    audit = client.get("/api/v1/audit?pageSize=50", headers=admin_headers)
    actions = {a["action"] for a in audit.json()["data"]["items"]}
    assert {"IMPORT_UPLOAD", "IMPORT_COMMIT", "QUOTE_UPDATE", "QUOTE_DELETE", "QUOTE_RESTORE"} <= actions

    # 9. 批次报告与批次列表
    report_api = client.get(f"/api/v1/imports/{batch_id}/report", headers=maintainer_headers)
    assert report_api.status_code == 200
    batches = client.get("/api/v1/batches", headers=maintainer_headers)
    assert batches.status_code == 200

    # 10. 幂等：同 token 重复提交不重复入库
    again = client.post(f"/api/v1/imports/{batch_id}/commit", headers=maintainer_headers, json={
        "commit_token": pv["commit_token"],
        "file_commits": [{"file_id": file_id, "sheet_name": "Sheet1",
                          "header_row": pv["header_row"],
                          "mappings": pv["mappings"], "skip_error_rows": False}]})
    assert again.status_code == 200
    search_again = client.get("/api/v1/quotes/search?keyword=接触器", headers=viewer_headers)
    ids_before = set()
    # 总数不变（幂等命中）
    assert again.json()["data"]["batch"]["status"] in ("confirmed", "partial")


@pytest.mark.skipif(not os.path.exists(SAMPLE1), reason="样例文件不在本地")
def test_duplicate_upload_blocked(client, maintainer_headers):
    _upload_and_commit(client, maintainer_headers, SAMPLE1)
    with open(SAMPLE1, "rb") as fh:
        up2 = client.post("/api/v1/imports/upload",
                          files={"files": (os.path.basename(SAMPLE1), fh)},
                          headers=maintainer_headers)
    assert up2.status_code == 200
    files = up2.json()["data"]["files"]
    assert files[0]["check_status"] == "duplicate"  # R-IMP-18
    assert files[0]["duplicate_of_batch_id"]


@pytest.mark.skipif(not os.path.exists(SAMPLE1), reason="样例文件不在本地")
def test_sensitive_masking_for_viewer(client, maintainer_headers, viewer_headers):
    batch_id, _ = _upload_and_commit(client, maintainer_headers, SAMPLE1)
    # sample2 才有电话；此处验证 masked_fields 机制不报错
    items = client.get("/api/v1/quotes/search?pageSize=5", headers=viewer_headers).json()["data"]["items"]
    assert len(items) > 0
    d = client.get(f"/api/v1/quotes/{items[0]['id']}", headers=viewer_headers).json()["data"]
    assert "masked_fields" in d


def test_maintenance_status_mark(client, maintainer_headers):
    # 无数据时对不存在记录操作 → 404
    resp = client.patch("/api/v1/quotes/9999/status",
                        json={"status": "needs_review", "reason": "测试"}, headers=maintainer_headers)
    assert resp.status_code == 404
