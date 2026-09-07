"""
CRM and deal proposal management service.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.models.models import ClientProfileModel, ConversationModel, MessageRecordModel, ProposalModel
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.conversation_repo import ConversationRepository, ProposalRepository
from src.schemas.client import ClientProfileCreate
from src.schemas.conversation import ConversationCreate, MessageRecordCreate
from src.schemas.proposal import ProposalCreate


class CRMService:
    def __init__(self, session: Session):
        self.session = session
        self.client_repo = ClientProfileRepository(session)
        self.conv_repo = ConversationRepository(session)
        self.prop_repo = ProposalRepository(session)

    def register_client(self, payload: ClientProfileCreate) -> ClientProfileModel:
        return self.client_repo.upsert(
            name=payload.name,
            company=payload.company,
            email=payload.email,
            website=payload.website,
            domain=payload.domain,
            confidence_score=payload.confidence_score,
            metadata_json=payload.metadata_json,
        )

    def record_proposal(self, payload: ProposalCreate) -> ProposalModel:
        return self.prop_repo.create(payload.model_dump())

    def start_conversation(self, payload: ConversationCreate) -> ConversationModel:
        return self.conv_repo.create_conversation(payload.model_dump())

    def log_message(self, payload: MessageRecordCreate) -> MessageRecordModel:
        return self.conv_repo.add_message(payload.model_dump())
