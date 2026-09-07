"""
SQLAlchemy ORM models for Client Core Service CRM entities.
Includes Lead, ClientProfile, Conversation, MessageRecord, Proposal,
FollowupSchedule, OutboxModel, and ApprovalItemModel.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin, generate_uuid


class LeadStatus(StrEnum):
    """Lifecycle status of a lead in the acquisition pipeline."""
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    QUALIFIED = "qualified"
    MESSAGE_READY = "message_ready"
    PROPOSAL_READY = "proposal_ready"
    CONTACTED = "contacted"
    REPLIED = "replied"
    ENGAGED = "engaged"
    PROPOSAL_SENT = "proposal_sent"
    WON = "won"
    LOST = "lost"
    DISQUALIFIED = "disqualified"
    ARCHIVED = "archived"


class OutboxActionType(StrEnum):
    """Types of outbound actions queued in the outbox."""
    SEND_MESSAGE = "SEND_MESSAGE"
    SCHEDULE_FOLLOWUP = "SCHEDULE_FOLLOWUP"
    SEND_PROPOSAL = "SEND_PROPOSAL"


class OutboxStatus(StrEnum):
    """Status of outbox action items."""
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"
    SENT = "SENT"
    FAILED = "FAILED"


class ApprovalStatus(StrEnum):
    """Human approval status for outreach and proposals."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class LeadModel(Base, TimestampMixin):
    """Core persistent lead / opportunity record. Sole lifecycle authority."""
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    finder_score: Mapped[Optional[float]] = mapped_column(Float, index=True, nullable=True)
    intelligence_score: Mapped[Optional[float]] = mapped_column(Float, index=True, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default=LeadStatus.DISCOVERED.value, index=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    client_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    client: Mapped[Optional["ClientProfileModel"]] = relationship("ClientProfileModel", back_populates="leads")
    proposals: Mapped[list["ProposalModel"]] = relationship("ProposalModel", back_populates="lead", cascade="all, delete-orphan")
    conversations: Mapped[list["ConversationModel"]] = relationship("ConversationModel", back_populates="lead", cascade="all, delete-orphan")
    outbox_items: Mapped[list["OutboxModel"]] = relationship("OutboxModel", back_populates="lead", cascade="all, delete-orphan")
    approval_items: Mapped[list["ApprovalItemModel"]] = relationship("ApprovalItemModel", back_populates="lead", cascade="all, delete-orphan")


class ClientProfileModel(Base, TimestampMixin):
    """CRM account profile representing a client or hiring company."""
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(200), index=True, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    leads: Mapped[list["LeadModel"]] = relationship("LeadModel", back_populates="client")
    proposals: Mapped[list["ProposalModel"]] = relationship("ProposalModel", back_populates="client")
    conversations: Mapped[list["ConversationModel"]] = relationship("ConversationModel", back_populates="client")


class ConversationModel(Base, TimestampMixin):
    """Communication thread with a client regarding an opportunity."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), default="email", nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    # Relationships
    lead: Mapped["LeadModel"] = relationship("LeadModel", back_populates="conversations")
    client: Mapped[Optional["ClientProfileModel"]] = relationship("ClientProfileModel", back_populates="conversations")
    messages: Mapped[list["MessageRecordModel"]] = relationship("MessageRecordModel", back_populates="conversation", cascade="all, delete-orphan")
    followups: Mapped[list["FollowupScheduleModel"]] = relationship("FollowupScheduleModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageRecordModel(Base, TimestampMixin):
    """Individual message in a conversation thread."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(20), default="us", nullable=False)  # 'us', 'client'
    message_type: Mapped[str] = mapped_column(String(50), default="proposal", nullable=False)  # 'proposal', 'reply', 'followup'
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    conversation: Mapped["ConversationModel"] = relationship("ConversationModel", back_populates="messages")


class ProposalModel(Base, TimestampMixin):
    """Business proposal and deal terms."""
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scope_summary: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # 'draft', 'sent', 'accepted', 'declined'

    # Relationships
    lead: Mapped["LeadModel"] = relationship("LeadModel", back_populates="proposals")
    client: Mapped[Optional["ClientProfileModel"]] = relationship("ClientProfileModel", back_populates="proposals")
    followups: Mapped[list["FollowupScheduleModel"]] = relationship("FollowupScheduleModel", back_populates="proposal")


class FollowupScheduleModel(Base, TimestampMixin):
    """Follow-up sequence state machine."""
    __tablename__ = "followups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    proposal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("proposals.id", ondelete="SET NULL"), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # 'pending', 'executed', 'cancelled'

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship("ConversationModel", back_populates="followups")
    proposal: Mapped[Optional["ProposalModel"]] = relationship("ProposalModel", back_populates="followups")


class OutboxModel(Base, TimestampMixin):
    """
    Outbox table ensuring atomic multi-service messaging and idempotency.
    Guarantees no double-sends and allows transactional cancellation on reply.
    """
    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)  # Acts as Idempotency Key
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # OutboxActionType
    status: Mapped[str] = mapped_column(String(50), default=OutboxStatus.PENDING.value, index=True, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    lead: Mapped["LeadModel"] = relationship("LeadModel", back_populates="outbox_items")
    approval: Mapped[Optional["ApprovalItemModel"]] = relationship("ApprovalItemModel", back_populates="outbox_item", uselist=False)


class ApprovalItemModel(Base, TimestampMixin):
    """
    Human-in-the-loop review queue item before messages reach external platforms.
    Records labeled datasets for Learning SVC.
    """
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False)
    outbox_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("outbox.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), default=OutboxActionType.SEND_MESSAGE.value, nullable=False)
    proposed_subject: Mapped[str] = mapped_column(String(300), nullable=False)
    proposed_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ApprovalStatus.PENDING_APPROVAL.value, index=True, nullable=False)

    reviewer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    feedback_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    lead: Mapped["LeadModel"] = relationship("LeadModel", back_populates="approval_items")
    outbox_item: Mapped[Optional["OutboxModel"]] = relationship("OutboxModel", back_populates="approval")
