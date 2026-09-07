"""
Pydantic schemas for Human Review Approval Queue in Client Core Service.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApprovalActionRequest(BaseModel):
    reviewer: str = Field(default="Human Operator")
    notes: Optional[str] = None


class ApprovalEditRequest(BaseModel):
    proposed_subject: str = Field(min_length=1, max_length=300)
    proposed_body: str = Field(min_length=1)
    reviewer: str = Field(default="Human Operator")
    reason: Optional[str] = Field(default="Manual refinement", max_length=500)
    notes: Optional[str] = None


class ApprovalRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500, description="Mandatory labeled reason for rejection")
    reviewer: str = Field(default="Human Operator")
    notes: Optional[str] = None


class ApprovalItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    outbox_id: Optional[str] = None
    action_type: str
    proposed_subject: str
    proposed_body: str
    status: str
    reviewer: Optional[str] = None
    reviewer_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    feedback_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    # Lead context
    lead_title: Optional[str] = None
    lead_source: Optional[str] = None
    lead_score: Optional[float] = None


class ApprovalQueueResponse(BaseModel):
    pending_count: int
    items: list[ApprovalItemResponse]
