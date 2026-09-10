# -*- coding: utf-8 -*-
"""F01-QA-001：认证/权限/会话失效/限速（A-AUTH-01~08）"""


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_login_success_and_me(client, admin_headers):
    resp = client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["role"] == "admin"
    assert data["session_expires_at"]


def test_logout_then_token_invalid(client):
    from tests.conftest import auth_header, login
    token = login(client, "viewer", "view#Pass1")
    resp = client.post("/api/v1/auth/logout", headers=auth_header(token))
    assert resp.status_code == 200
    # A-AUTH-01：退出后旧令牌 401
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 401


def test_wrong_password_unified_message(client):
    resp = client.post("/api/v1/auth/login",
                       json={"username": "nouser_x", "password": "wrong"})
    assert resp.status_code == 401
    assert "账号或密码错误" in resp.json()["message"]


def test_disable_user_revokes_sessions_immediately(client, admin_headers, viewer_headers):
    # viewer 在线
    assert client.get("/api/v1/auth/me", headers=viewer_headers).status_code == 200
    # 管理员停用 viewer
    users = client.get("/api/v1/users", headers=admin_headers).json()["data"]["items"]
    viewer = next(u for u in users if u["username"] == "viewer")
    resp = client.patch(f"/api/v1/users/{viewer['id']}",
                        json={"status": "disabled", "version": viewer["version"]},
                        headers=admin_headers)
    assert resp.status_code == 200
    # A-AUTH-04：已有会话在 1 次请求内失效
    assert client.get("/api/v1/auth/me", headers=viewer_headers).status_code == 401
    # 无法再登录
    resp = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "view#Pass1"})
    assert resp.status_code == 403


def test_cannot_disable_self_or_last_admin(client, admin_headers):
    users = client.get("/api/v1/users", headers=admin_headers).json()["data"]["items"]
    me = next(u for u in users if u["role"] == "admin")
    resp = client.patch(f"/api/v1/users/{me['id']}",
                        json={"status": "disabled", "version": me["version"]},
                        headers=admin_headers)
    assert resp.status_code == 400  # 10503
    assert resp.json()["code"] == 10503


def test_role_forbidden(client, viewer_headers, maintainer_headers):
    # A-AUTH-06：user 访问用户管理 403
    assert client.get("/api/v1/users", headers=viewer_headers).status_code == 403
    # maintainer 不能管理用户
    assert client.get("/api/v1/users", headers=maintainer_headers).status_code == 403
    # viewer 不能导入
    assert client.get("/api/v1/batches", headers=viewer_headers).status_code == 403


def test_create_user_and_reset_password(client, admin_headers):
    resp = client.post("/api/v1/users",
                       json={"username": "newuser1", "display_name": "新用户", "role": "user"},
                       headers=admin_headers)
    assert resp.status_code == 200
    initial = resp.json()["data"]["initial_password"]
    assert initial
    # 用初始密码登录
    from tests.conftest import auth_header, login
    token = login(client, "newuser1", initial)
    assert token
    # 重置密码 → 旧会话失效（R-AUTH-07）
    users = client.get("/api/v1/users?keyword=newuser1", headers=admin_headers).json()["data"]["items"]
    uid = users[0]["id"]
    resp = client.post(f"/api/v1/users/{uid}/reset-password", headers=admin_headers)
    assert resp.status_code == 200
    new_pwd = resp.json()["data"]["new_password"]
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401
    assert login(client, "newuser1", new_pwd)


def test_login_rate_limit_lockout(client):
    # R-AUTH-11/12：连续失败 5 次触发锁定（同账号）
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"username": "lockme", "password": "bad"})
    resp = client.post("/api/v1/auth/login", json={"username": "lockme", "password": "bad"})
    assert resp.status_code == 429
    assert resp.json()["code"] == 10402


def test_duplicate_username_rejected(client, admin_headers):
    client.post("/api/v1/users", json={"username": "dup_user", "display_name": "A", "role": "user"},
                headers=admin_headers)
    resp = client.post("/api/v1/users",
                       json={"username": "dup_user", "display_name": "B", "role": "user"},
                       headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == 10502
