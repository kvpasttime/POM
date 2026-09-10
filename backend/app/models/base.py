# -*- coding: utf-8 -*-
"""模型基类与公共字段（docs/06 2.3）"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# SQLite 开发 / PG 生产双方言（ADR-005）：SQLite 主键必须 INTEGER 才能自增
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class CommonMixin:
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
