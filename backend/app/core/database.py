# -*- coding: utf-8 -*-
"""数据库引擎与会话（docs/02 ADR-005：SQLite 开发 / PG 生产双方言）"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_is_sqlite = _settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite and _settings.database_url in ("sqlite://", "sqlite:///:memory:"):
    # 内存库共享单连接（测试场景）
    from sqlalchemy.pool import StaticPool
    _kwargs["poolclass"] = StaticPool
engine = create_engine(_settings.database_url, connect_args=_connect_args, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
