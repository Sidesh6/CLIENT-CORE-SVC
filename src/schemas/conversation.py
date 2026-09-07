"""
Pydantic schemas for Conversation and Message records.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageRecordBase(BaseModel):
    sender_type: str = "us"  # 'us', 'client'
    message_type: str = "proposal"  # 'proposal', 'reply', 'followup'
    body: str = Field(min_length=1)
    sentiment: Optional[str] = None


class MessageRecordCreate(MessageRecordBase):
    conversation_id: str


class MessageRecordResponse(MessageRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    created_at: datetime


class ConversationBase(BaseModel):
    lead_id: str
    client_id: Optional[str] = None
    channel: str = "email"
    subject: str = Field(min_length=1, max_length=300)
    status: str = "active"


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRecordResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int
