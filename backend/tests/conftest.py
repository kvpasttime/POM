# -*- coding: utf-8 -*-
"""pytest 夹具：内存库 + 测试客户端 + 种子用户"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 测试固定使用临时文件库与临时上传目录
_TEST_DIR = os.path.join(os.path.dirname(__file__), "_test_data")
os.makedirs(_TEST_DIR, exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TEST_DIR, "test_pom.db").replace("\\", "/")
os.environ["UPLOAD_DIR"] = os.path.join(_TEST_DIR, "uploads")
os.environ["BACKUP_DIR"] = os.path.join(_TEST_DIR, "backups")

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import SysUser  # noqa: E402


@pytest.fixture(autouse=True)
def _setup_db():
    from app.core.ratelimit import limiter
    limiter._fails.clear()
    limiter._locked_until.clear()
    limiter._ip_hits.clear()
    # 每个测试用干净的库文件
    db_file = os.path.join(_TEST_DIR, "test_pom.db")
    for suffix in ("", "-wal", "-shm"):
        p = db_file + suffix
        if os.path.exists(p):
            os.remove(p)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(SysUser).count() == 0:
            db.add_all([
                SysUser(username="admin", password_hash=hash_password("admin#Pass1"),
                        display_name="管理员", role="admin"),
                SysUser(username="maintainer", password_hash=hash_password("maint#Pass1"),
                        display_name="维护员", role="maintainer"),
                SysUser(username="viewer", password_hash=hash_password("view#Pass1"),
                        display_name="查询员", role="user"),
            ])
            db.commit()
    finally:
        db.close()
    engine.dispose()
    yield
    engine.dispose()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client):
    return auth_header(login(client, "admin", "admin#Pass1"))


@pytest.fixture()
def maintainer_headers(client):
    return auth_header(login(client, "maintainer", "maint#Pass1"))


@pytest.fixture()
def viewer_headers(client):
    return auth_header(login(client, "viewer", "view#Pass1"))


FIXTURES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures"))
