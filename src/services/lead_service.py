"""
Business logic service for managing leads and qualification.
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.models.base import compute_content_hash
from src.models.models import LeadModel, LeadStatus
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.lead_repo import LeadRepository
from src.schemas.lead import LeadCreate, LeadUpdate


class LeadService:
    def __init__(self, session: Session):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.client_repo = ClientProfileRepository(session)

    def create_or_get_lead(self, payload: LeadCreate) -> tuple[str, LeadModel]:
        content_hash = compute_content_hash(payload.title, payload.description)
        existing = self.lead_repo.get_by_content_hash(content_hash)
        if existing:
            return "existing", existing

        lead_data = payload.model_dump()
        lead_data["content_hash"] = content_hash
        lead = self.lead_repo.create(lead_data)
        return "created", lead

    def update_lead_status(self, lead_id: str, new_status: str) -> Optional[LeadModel]:
        return self.lead_repo.update(lead_id, {"status": new_status})

    def update_lead_scores(
        self,
        lead_id: str,
        finder_score: Optional[float] = None,
        intelligence_score: Optional[float] = None,
    ) -> Optional[LeadModel]:
        updates: dict = {}
        if finder_score is not None:
            updates["finder_score"] = finder_score
        if intelligence_score is not None:
            updates["intelligence_score"] = intelligence_score
        return self.lead_repo.update(lead_id, updates)
