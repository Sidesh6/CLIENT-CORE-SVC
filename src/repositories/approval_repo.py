"""
Repository for Human Review Approval Queue in Client Core Service.
"""

from datetime import UTC, datetime
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.models.models import ApprovalItemModel, ApprovalStatus, OutboxModel, OutboxStatus


class ApprovalRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_item(
        self,
        lead_id: str,
        proposed_subject: str,
        proposed_body: str,
        outbox_id: Optional[str] = None,
        action_type: str = "SEND_MESSAGE",
        feedback_payload: Optional[dict[str, Any]] = None,
    ) -> ApprovalItemModel:
        item = ApprovalItemModel(
            lead_id=lead_id,
            outbox_id=outbox_id,
            action_type=action_type,
            proposed_subject=proposed_subject,
            proposed_body=proposed_body,
            status=ApprovalStatus.PENDING_APPROVAL.value,
            feedback_payload=feedback_payload or {},
        )
        self.session.add(item)
        self.session.flush()
        return item

    def get_by_id(self, approval_id: str) -> Optional[ApprovalItemModel]:
        stmt = (
            select(ApprovalItemModel)
            .options(selectinload(ApprovalItemModel.lead), selectinload(ApprovalItemModel.outbox_item))
            .where(ApprovalItemModel.id == approval_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_pending_queue(self, limit: int = 50) -> list[ApprovalItemModel]:
        stmt = (
            select(ApprovalItemModel)
            .options(selectinload(ApprovalItemModel.lead), selectinload(ApprovalItemModel.outbox_item))
            .where(ApprovalItemModel.status == ApprovalStatus.PENDING_APPROVAL.value)
            .order_by(ApprovalItemModel.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def approve(
        self,
        approval_id: str,
        reviewer: str = "Human Operator",
        notes: Optional[str] = None,
    ) -> Optional[ApprovalItemModel]:
        item = self.get_by_id(approval_id)
        if not item:
            return None

        item.status = ApprovalStatus.APPROVED.value
        item.reviewer = reviewer
        item.reviewer_notes = notes
        item.reviewed_at = datetime.now(UTC)

        # If connected to an outbox row, ensure outbox status is PENDING for dispatcher to fire
        if item.outbox_item and item.outbox_item.status == OutboxStatus.PENDING.value:
            pass  # Already pending
        elif item.outbox_item:
            item.outbox_item.status = OutboxStatus.PENDING.value

        self.session.flush()
        return item

    def edit_and_approve(
        self,
        approval_id: str,
        subject: str,
        body: str,
        reviewer: str = "Human Operator",
        reason: str = "Manual refinement",
        notes: Optional[str] = None,
    ) -> Optional[ApprovalItemModel]:
        item = self.get_by_id(approval_id)
        if not item:
            return None

        # Record diff in feedback payload for learning service
        item.feedback_payload["original_subject"] = item.proposed_subject
        item.feedback_payload["original_body"] = item.proposed_body
        item.feedback_payload["edit_reason"] = reason

        item.proposed_subject = subject
        item.proposed_body = body
        item.status = ApprovalStatus.EDITED.value
        item.reviewer = reviewer
        item.reviewer_notes = notes or reason
        item.reviewed_at = datetime.now(UTC)

        if item.outbox_item:
            # Update payload inside outbox item
            item.outbox_item.payload_json["subject"] = subject
            item.outbox_item.payload_json["body"] = body
            item.outbox_item.status = OutboxStatus.PENDING.value

        self.session.flush()
        return item

    def reject(
        self,
        approval_id: str,
        reason: str,
        reviewer: str = "Human Operator",
        notes: Optional[str] = None,
    ) -> Optional[ApprovalItemModel]:
        item = self.get_by_id(approval_id)
        if not item:
            return None

        item.status = ApprovalStatus.REJECTED.value
        item.rejection_reason = reason
        item.reviewer = reviewer
        item.reviewer_notes = notes
        item.reviewed_at = datetime.now(UTC)

        # Cancel associated outbox row
        if item.outbox_item:
            item.outbox_item.status = OutboxStatus.CANCELLED.value
            item.outbox_item.cancel_reason = f"Rejected by reviewer: {reason}"

        self.session.flush()
        return item
