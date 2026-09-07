"""
Pydantic schemas for Proposal and Follow-up entities.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProposalBase(BaseModel):
    lead_id: str
    client_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=300)
    scope_summary: str = Field(min_length=1)
    amount: Optional[float] = None
    currency: str = "USD"
    status: str = "draft"  # 'draft', 'sent', 'accepted', 'declined'


class ProposalCreate(ProposalBase):
    pass


class ProposalResponse(ProposalBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class FollowupScheduleCreate(BaseModel):
    conversation_id: str
    proposal_id: Optional[str] = None
    attempt_number: int = 1
    scheduled_at: datetime


class FollowupScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    proposal_id: Optional[str] = None
    attempt_number: int
    scheduled_at: datetime
    status: str
    created_at: datetime
