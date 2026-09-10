# -*- coding: utf-8 -*-
"""核心业务对象：物料/需求/供应商/快照/报价（docs/06 4.2）"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import func
from sqlalchemy import (
    BigInteger, String, Integer, Text, DateTime, Date, Boolean, Numeric,
    ForeignKey, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import BigIntPK
from app.models.base import CommonMixin, VersionMixin


class Material(Base, CommonMixin, VersionMixin):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    spec_model: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    tech_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    material_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    origin_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name_raw: Mapped[str | None] = mapped_column(Text, nullable=True)


class PurchaseRequirement(Base, CommonMixin):
    __tablename__ = "purchase_requirement"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("material.id"), nullable=False, index=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requirement_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    receiver: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quote_row_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_row_snapshot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_row_snapshot.id"), nullable=False
    )


class Supplier(Base, CommonMixin, VersionMixin):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="confirmed")


class SourceRowSnapshot(Base):
    """原始行快照：append-only，禁止更新（R-IMP-26）"""
    __tablename__ = "source_row_snapshot"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_file.id"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    cells: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("uk_snapshot_row_identity", "source_file_id", "sheet_name", "row_no", unique=True),
    )


class Quote(Base, CommonMixin, VersionMixin):
    __tablename__ = "quote"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("material.id"), nullable=False, index=True)
    requirement_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("purchase_requirement.id"), nullable=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("supplier.id"), nullable=True, index=True
    )
    amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    tax_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    freight_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    available_qty: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    delivery_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quote_date: Mapped[str | None] = mapped_column(Date, nullable=True, index=True)
    date_inferred_from: Mapped[str | None] = mapped_column(String(32), nullable=True)
    valid_until: Mapped[str | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="auto_extracted", index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    supplier_spec_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    supplier_material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    supplier_tech_params: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_row_snapshot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("source_row_snapshot.id"), nullable=False, index=True
    )
    import_batch_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("import_batch.id"), nullable=False, index=True
    )
    group_label: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (Index("idx_quote_batch", "import_batch_id"),)
