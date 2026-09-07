"""
Declarative base and hashing utilities for Client Core Service.
"""

import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Optional
from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Support postgres schema isolation (core_svc schema) only when connecting to postgresql
_db_url = os.getenv("DATABASE_URL", "")
_db_schema = os.getenv("DB_SCHEMA", "core_svc")
_schema = _db_schema if (_db_url.startswith("postgresql") or _db_url.startswith("postgres")) else None
_metadata = MetaData(schema=_schema) if _schema else MetaData()


class Base(DeclarativeBase):
    metadata = _metadata


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


def generate_uuid() -> str:
    return str(uuid.uuid4())


def compute_content_hash(title: str, description: str) -> str:
    norm = f"{title.strip().lower()}|{description.strip().lower()}".encode("utf-8")
    return hashlib.sha256(norm).hexdigest()
