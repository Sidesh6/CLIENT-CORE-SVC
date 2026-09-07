from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    status: str = "success"
    message: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 20
    total_items: int = 0
    total_pages: int = 1


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "client-core-svc"
    version: str = "0.1.0"
    database: str = "connected"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
