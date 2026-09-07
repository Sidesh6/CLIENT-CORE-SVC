"""
Pydantic schemas for Intent emission from Orchestrator and inbound Client Replies.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Optional
from pydantic import BaseModel, Field


class IntentType(StrEnum):
    DISCOVER_LEAD = "DISCOVER_LEAD"
    ENRICH_LEAD = "ENRICH_LEAD"
    QUALIFY_LEAD = "QUALIFY_LEAD"
    SEND_MESSAGE_REQUESTED = "SEND_MESSAGE_REQUESTED"
    FOLLOWUP_REQUESTED = "FOLLOWUP_REQUESTED"
    PROPOSAL_REQUESTED = "PROPOSAL_REQUESTED"


class LeadIntentRequest(BaseModel):
    """
    Intent emitted by Orchestrator or external agent.
    Orchestrator NEVER writes lifecycle state directly; it emits intents to Core.
    """
    intent_type: IntentType
    lead_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    budget: Optional[float] = None
    skills: list[str] = Field(default_factory=list)
    finder_score: Optional[float] = None
    intelligence_score: Optional[float] = None
    intelligence_payload: dict[str, Any] = Field(default_factory=dict)
    proposed_message: Optional[dict[str, Any]] = None  # {subject, body, channel, recipient}
    idempotency_key: Optional[str] = None


class LeadIntentResponse(BaseModel):
    success: bool
    lead_id: str
    previous_status: Optional[str] = None
    current_status: str
    outbox_id: Optional[str] = None
    approval_id: Optional[str] = None
    message: str


class ClientReplyRequest(BaseModel):
    """
    Inbound reply from a client. Triggers immediate atomic cancellation of all pending outbox followups.
    """
    lead_id: str
    reply_body: str = Field(min_length=1)
    sentiment: Optional[str] = None
    channel: str = "email"


class ClientReplyResponse(BaseModel):
    success: bool
    lead_id: str
    status: str
    cancelled_outbox_count: int
    cancelled_followups_count: int
    message: str
