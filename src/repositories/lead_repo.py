"""
Repository for Lead CRM entity data access and lifecycle state authority.
"""

from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from src.models.models import FollowupScheduleModel, LeadModel, LeadStatus, OutboxModel, OutboxStatus


class LeadRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, lead_id: str) -> Optional[LeadModel]:
        stmt = (
            select(LeadModel)
            .options(
                selectinload(LeadModel.client),
                selectinload(LeadModel.proposals),
                selectinload(LeadModel.conversations),
                selectinload(LeadModel.outbox_items),
                selectinload(LeadModel.approval_items),
            )
            .where(LeadModel.id == lead_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_content_hash(self, content_hash: str) -> Optional[LeadModel]:
        stmt = select(LeadModel).where(LeadModel.content_hash == content_hash)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, lead_dict: dict) -> LeadModel:
        lead = LeadModel(**lead_dict)
        self.session.add(lead)
        self.session.flush()
        return lead

    def update(self, lead_id: str, updates: dict) -> Optional[LeadModel]:
        lead = self.get_by_id(lead_id)
        if not lead:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(lead, k):
                setattr(lead, k, v)
        self.session.flush()
        return lead

    def record_reply_and_cancel_outbox(
        self,
        lead_id: str,
        reason: str = "Lead replied",
    ) -> tuple[Optional[LeadModel], int, int]:
        """
        FIX 1 & FIX 2 GUARANTEE:
        In the *same database transaction*:
        1. Transitions lead status to REPLIED
        2. Cancels all PENDING outbox items for this lead (prevents double message / duplicate follow-up)
        3. Cancels all pending follow-up schedules in conversations
        """
        lead = self.get_by_id(lead_id)
        if not lead:
            return None, 0, 0

        lead.status = LeadStatus.REPLIED.value

        # 1. Cancel pending outbox entries
        from src.repositories.outbox_repo import OutboxRepository
        outbox_repo = OutboxRepository(self.session)
        cancelled_outbox_count = outbox_repo.cancel_pending_for_lead(lead_id=lead_id, reason=reason)

        # 2. Cancel pending conversation followups
        cancelled_followups_count = 0
        for conv in lead.conversations:
            for f in conv.followups:
                if f.status == "pending":
                    f.status = "cancelled"
                    cancelled_followups_count += 1

        self.session.flush()
        return lead, cancelled_outbox_count, cancelled_followups_count

    def list_leads(
        self,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[LeadModel]:
        stmt = select(LeadModel).options(selectinload(LeadModel.client))
        if status:
            stmt = stmt.where(LeadModel.status == status)
        if min_score is not None:
            stmt = stmt.where(LeadModel.finder_score >= min_score)
        if source:
            stmt = stmt.where(LeadModel.source.ilike(f"%{source}%"))

        offset = (page - 1) * page_size
        stmt = stmt.order_by(LeadModel.created_at.desc()).offset(offset).limit(page_size)
        return list(self.session.execute(stmt).scalars().all())

    def count_leads(
        self,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        source: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(LeadModel.id))
        if status:
            stmt = stmt.where(LeadModel.status == status)
        if min_score is not None:
            stmt = stmt.where(LeadModel.finder_score >= min_score)
        if source:
            stmt = stmt.where(LeadModel.source.ilike(f"%{source}%"))
        return self.session.execute(stmt).scalar_one() or 0
