"""
Repository for Outbox table managing transactional message scheduling and cancellation.
"""

from datetime import UTC, datetime
from typing import Any, Optional
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload
from src.models.models import OutboxActionType, OutboxModel, OutboxStatus


class OutboxRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_entry(
        self,
        lead_id: str,
        action_type: str,
        payload_json: dict[str, Any],
        status: str = OutboxStatus.PENDING.value,
        outbox_id: Optional[str] = None,
    ) -> OutboxModel:
        kwargs = {
            "lead_id": lead_id,
            "action_type": action_type,
            "payload_json": payload_json,
            "status": status,
        }
        if outbox_id:
            kwargs["id"] = outbox_id

        entry = OutboxModel(**kwargs)
        self.session.add(entry)
        self.session.flush()
        return entry

    def get_by_id(self, outbox_id: str) -> Optional[OutboxModel]:
        stmt = (
            select(OutboxModel)
            .options(selectinload(OutboxModel.lead), selectinload(OutboxModel.approval))
            .where(OutboxModel.id == outbox_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_pending(self, limit: int = 50) -> list[OutboxModel]:
        stmt = (
            select(OutboxModel)
            .options(selectinload(OutboxModel.lead), selectinload(OutboxModel.approval))
            .where(OutboxModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxModel.created_at.asc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def cancel_pending_for_lead(self, lead_id: str, reason: str = "Lead replied") -> int:
        """
        ATOMIC CANCELLATION:
        Marks all PENDING outbox rows for this lead as CANCELLED in the active transaction.
        Enforces Fix 2: 'cancel all follow-ups on reply'.
        """
        stmt = (
            update(OutboxModel)
            .where(
                OutboxModel.lead_id == lead_id,
                OutboxModel.status == OutboxStatus.PENDING.value,
            )
            .values(
                status=OutboxStatus.CANCELLED.value,
                cancel_reason=reason,
                updated_at=datetime.now(UTC),
            )
        )
        res = self.session.execute(stmt)
        self.session.flush()
        return res.rowcount or 0

    def mark_sent(self, outbox_id: str) -> Optional[OutboxModel]:
        entry = self.get_by_id(outbox_id)
        if entry:
            entry.status = OutboxStatus.SENT.value
            entry.processed_at = datetime.now(UTC)
            self.session.flush()
        return entry

    def mark_failed(self, outbox_id: str, error_message: str) -> Optional[OutboxModel]:
        entry = self.get_by_id(outbox_id)
        if entry:
            entry.status = OutboxStatus.FAILED.value
            entry.error_message = error_message
            entry.retry_count += 1
            entry.processed_at = datetime.now(UTC)
            self.session.flush()
        return entry

    def count_pending(self) -> int:
        stmt = select(func.count(OutboxModel.id)).where(OutboxModel.status == OutboxStatus.PENDING.value)
        return self.session.execute(stmt).scalar_one() or 0

    def list_outbox(
        self,
        status: Optional[str] = None,
        lead_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[OutboxModel]:
        stmt = select(OutboxModel).options(selectinload(OutboxModel.lead))
        if status:
            stmt = stmt.where(OutboxModel.status == status)
        if lead_id:
            stmt = stmt.where(OutboxModel.lead_id == lead_id)

        offset = (page - 1) * page_size
        stmt = stmt.order_by(OutboxModel.created_at.desc()).offset(offset).limit(page_size)
        return list(self.session.execute(stmt).scalars().all())
