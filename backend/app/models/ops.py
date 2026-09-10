# -*- coding: utf-8 -*-
"""导入过程对象与修订/审计（docs/06 4.3/4.4/4.5）"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import func
from sqlalchemy import (
    BigInteger, String, Integer, Text, DateTime, ForeignKey, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BigIntPK
from app.models.base import CommonMixin, VersionMixin


class ImportBatch(Base, CommonMixin, VersionMixin):
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commit_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    fail_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SourceFile(Base):
    """源文件元数据：stored_path/sha256 不可变（docs/06 4.3.2）"""
    __tablename__ = "source_file"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("import_batch.id"), nullable=False, index=True)
    original_name: Mapped[str] = mapped_column(String(256), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(nullable=False)
    file_type: Mapped[str] = mapped_column(String(8), nullable=False)
    check_status: Mapped[str] = mapped_column(String(16), nullable=False)
    check_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duplicate_of_file_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class ImportRowResult(Base):
    __tablename__ = "import_row_result"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("import_batch.id"), nullable=False, index=True)
    source_file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("source_file.id"), nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    quote_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    quote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_row_result_batch", "batch_id", "source_file_id", "row_no"),)


class MappingTemplate(Base, CommonMixin, VersionMixin):
    __tablename__ = "mapping_template"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    header_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sheet_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mappings: Mapped[list] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("uk_mapping_template_owner_name", "owner_id", "name", unique=True),)


class QuoteRevision(Base):
    """修订记录：append-only（docs/06 4.4.1）"""
    __tablename__ = "quote_revision"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("quote.id"), nullable=False, index=True)
    revision_type: Mapped[str] = mapped_column(String(16), nullable=False, default="field_change")
    field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    changed_by: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_revision_quote", "quote_id", "changed_at"),)


class AuditLog(Base):
    """审计日志：append-only（docs/06 4.5.1）"""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    actor_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    object_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    object_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
