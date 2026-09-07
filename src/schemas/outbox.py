"""
Pydantic schemas for Outbox entity and dispatch responses.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class OutboxBase(BaseModel):
    lead_id: str
    action_type: str = Field(description="SEND_MESSAGE, SCHEDULE_FOLLOWUP, SEND_PROPOSAL")
    payload_json: dict[str, Any] = Field(default_factory=dict)


class OutboxCreate(OutboxBase):
    id: Optional[str] = Field(None, description="Optional custom idempotency key")
    status: str = "PENDING"


class OutboxResponse(OutboxBase):
    model_config = ConfigDict(from_attributes=True)

    id: str  # Idempotency key
    status: str
    cancel_reason: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OutboxListResponse(BaseModel):
    items: list[OutboxResponse]
    total: int
    pending_count: int


class OutboxDispatchResponse(BaseModel):
    dispatched_count: int
    failed_count: int
    skipped_count: int
    details: list[dict[str, Any]] = Field(default_factory=list)
