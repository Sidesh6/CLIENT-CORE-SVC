"""
Repositories for Conversations, Messages, Proposals, and Follow-ups.
"""

from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from src.models.models import (
    ConversationModel,
    FollowupScheduleModel,
    MessageRecordModel,
    ProposalModel,
)


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, conv_id: str) -> Optional[ConversationModel]:
        stmt = (
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages), selectinload(ConversationModel.followups))
            .where(ConversationModel.id == conv_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self,
        lead_id: str,
        client_id: Optional[str] = None,
        channel: str = "email",
        subject: str = "Inquiry",
    ) -> ConversationModel:
        stmt = (
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages), selectinload(ConversationModel.followups))
            .where(ConversationModel.lead_id == lead_id)
        )
        conv = self.session.execute(stmt).scalars().first()
        if not conv:
            conv = ConversationModel(
                lead_id=lead_id,
                client_id=client_id,
                channel=channel,
                subject=subject,
                status="active",
            )
            self.session.add(conv)
            self.session.flush()
        return conv

    def create_conversation(self, conv_dict: dict) -> ConversationModel:
        conv = ConversationModel(**conv_dict)
        self.session.add(conv)
        self.session.flush()
        return conv

    def add_message(
        self,
        conversation_id: str,
        sender_type: str = "us",
        message_type: str = "proposal",
        body: str = "",
        sentiment: Optional[str] = None,
    ) -> MessageRecordModel:
        msg = MessageRecordModel(
            conversation_id=conversation_id,
            sender_type=sender_type,
            message_type=message_type,
            body=body,
            sentiment=sentiment,
        )
        self.session.add(msg)
        self.session.flush()
        return msg

    def list_conversations(self, lead_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> list[ConversationModel]:
        stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
        if lead_id:
            stmt = stmt.where(ConversationModel.lead_id == lead_id)
        offset = (page - 1) * page_size
        stmt = stmt.order_by(ConversationModel.created_at.desc()).offset(offset).limit(page_size)
        return list(self.session.execute(stmt).scalars().all())

    def count_conversations(self, lead_id: Optional[str] = None) -> int:
        stmt = select(func.count(ConversationModel.id))
        if lead_id:
            stmt = stmt.where(ConversationModel.lead_id == lead_id)
        return self.session.execute(stmt).scalar_one() or 0


class ProposalRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, prop_id: str) -> Optional[ProposalModel]:
        stmt = select(ProposalModel).where(ProposalModel.id == prop_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, prop_dict: dict) -> ProposalModel:
        prop = ProposalModel(**prop_dict)
        self.session.add(prop)
        self.session.flush()
        return prop

    def update_status(self, prop_id: str, new_status: str) -> Optional[ProposalModel]:
        prop = self.get_by_id(prop_id)
        if prop:
            prop.status = new_status
            self.session.flush()
        return prop

    def list_proposals(self, lead_id: Optional[str] = None, page: int = 1, page_size: int = 20) -> list[ProposalModel]:
        stmt = select(ProposalModel)
        if lead_id:
            stmt = stmt.where(ProposalModel.lead_id == lead_id)
        offset = (page - 1) * page_size
        stmt = stmt.order_by(ProposalModel.created_at.desc()).offset(offset).limit(page_size)
        return list(self.session.execute(stmt).scalars().all())


class FollowupRepository:
    def __init__(self, session: Session):
        self.session = session

    def schedule(self, data: dict) -> FollowupScheduleModel:
        f = FollowupScheduleModel(**data)
        self.session.add(f)
        self.session.flush()
        return f

    def list_pending(self) -> list[FollowupScheduleModel]:
        stmt = select(FollowupScheduleModel).where(FollowupScheduleModel.status == "pending")
        return list(self.session.execute(stmt).scalars().all())
