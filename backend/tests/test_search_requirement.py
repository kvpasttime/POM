# -*- coding: utf-8 -*-
"""方案A：含无报价需求搜索 + 需求详情（纯需求 Excel 可被搜到并溯源）"""
import os

import pytest

from tests.conftest import FIXTURES

SAMPLE3 = os.path.join(FIXTURES, "sample3_高性能计算机_张传亮8.27.xls")


def _upload_commit_requirement(client, headers, path):
    """上传样例3（纯需求无报价），提交模板表，返回 (batch_id, keyword)"""
    with open(path, "rb") as fh:
        up = client.post("/api/v1/imports/upload",
                         files={"files": (os.path.basename(path), fh)}, headers=headers)
    assert up.status_code == 200
    bid = up.json()["data"]["batch_id"]
    fid = next(f["file_id"] for f in up.json()["data"]["files"] if f["check_status"] == "passed")
    pv = client.get(f"/api/v1/imports/{bid}/preview?file_id={fid}", headers=headers).json()["data"]
    cm = client.post(f"/api/v1/imports/{bid}/commit", headers=headers, json={
        "commit_token": pv["commit_token"],
        "file_commits": [{"file_id": fid, "sheet_name": pv["sheet_name"],
                          "header_row": pv["header_row"], "mappings": pv["mappings"],
                          "skip_error_rows": False}]})
    assert cm.status_code == 200
    return bid


@pytest.mark.skipif(not os.path.exists(SAMPLE3), reason="样例文件不在本地")
def test_search_include_requirement(client, maintainer_headers, viewer_headers):
    _upload_commit_requirement(client, maintainer_headers, SAMPLE3)

    # 默认搜索（只查报价）：纯需求文件的物料搜不到
    r1 = client.get("/api/v1/quotes/search?keyword=高性能计算机", headers=viewer_headers).json()["data"]
    assert all(i["row_type"] == "quote" for i in r1["items"])

    # 方案A：include_requirement 打开 → 出现无报价需求行
    r2 = client.get("/api/v1/quotes/search?keyword=高性能计算机&include_requirement=true",
                    headers=viewer_headers).json()["data"]
    req_rows = [i for i in r2["requirement_items"] if i["row_type"] == "requirement"]
    assert len(req_rows) >= 1
    target = req_rows[0]
    assert target["material_name"] == "高性能计算机"
    assert target["amount"] is None
    assert target["status"] == "no_quote"
    assert target["source_summary"]  # 可追溯来源摘要

    # 需求详情可溯源
    d = client.get(f"/api/v1/requirements/{target['requirement_id']}",
                   headers=viewer_headers)
    assert d.status_code == 200
    dd = d.json()["data"]
    assert dd["no_quote"] is True
    assert dd["source"]["raw_cells"]
    assert dd["source"]["sheet_name"] and dd["source"]["row_no"]


@pytest.mark.skipif(not os.path.exists(SAMPLE3), reason="样例文件不在本地")
def test_search_requirement_quote_only_filter(client, maintainer_headers, viewer_headers):
    """报价专属筛选（价格）存在时，无报价需求不应混入"""
    _upload_commit_requirement(client, maintainer_headers, SAMPLE3)
    r = client.get("/api/v1/quotes/search?keyword=高性能计算机&include_requirement=true&price_min=100",
                   headers=viewer_headers).json()["data"]
    assert r["requirement_items"] == []


@pytest.mark.skipif(not os.path.exists(SAMPLE3), reason="样例文件不在本地")
def test_requirement_detail_404(client, viewer_headers):
    r = client.get("/api/v1/requirements/999999", headers=viewer_headers)
    assert r.status_code == 404
