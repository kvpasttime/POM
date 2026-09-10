# -*- coding: utf-8 -*-
"""创建手动测试账号（若不存在）并输出登录口令"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ADMIN_PWD = os.environ.get("ADMIN_PWD", "")
ACCOUNTS = [("tester_user", "查询员(测试)", "user"), ("tester_maint", "维护员(测试)", "maintainer")]

if not ADMIN_PWD:
    print("请设置环境变量 ADMIN_PWD")
    sys.exit(1)

with TestClient(app, base_url="http://testserver") as c:
    tok = c.post("/api/v1/auth/login", json={"username": "admin", "password": ADMIN_PWD}).json()["data"]["token"]
    H = {"Authorization": "Bearer " + tok}
    for username, name, role in ACCOUNTS:
        exists = c.get(f"/api/v1/users?keyword={username}", headers=H).json()["data"]["items"]
        if exists:
            print(f"已存在 {username}，跳过")
            continue
        resp = c.post("/api/v1/users", json={"username": username, "display_name": name, "role": "user" if username.endswith("user") else "maintainer"}, headers=H)
        if resp.status_code == 200:
            d = resp.json()["data"]
            print(f"创建 {username}（{d['id']}）初始密码: {d['initial_password']}")
        else:
            print(username, "FAIL", resp.status_code, resp.text[:150])
