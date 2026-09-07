"""
Repository for Client Profile CRM accounts.
"""

from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.models.models import ClientProfileModel


class ClientProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, client_id: str) -> Optional[ClientProfileModel]:
        stmt = select(ClientProfileModel).where(ClientProfileModel.id == client_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[ClientProfileModel]:
        if not email:
            return None
        stmt = select(ClientProfileModel).where(ClientProfileModel.email.ilike(email.strip()))
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, client_dict: dict) -> ClientProfileModel:
        client = ClientProfileModel(**client_dict)
        self.session.add(client)
        self.session.flush()
        return client

    def upsert(
        self,
        name: Optional[str] = None,
        company: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        domain: Optional[str] = None,
        confidence_score: float = 1.0,
        metadata_json: Optional[dict] = None,
    ) -> ClientProfileModel:
        existing = None
        if email:
            existing = self.get_by_email(email)

        if existing:
            if name and not existing.name:
                existing.name = name
            if company and not existing.company:
                existing.company = company
            if website and not existing.website:
                existing.website = website
            if domain and not existing.domain:
                existing.domain = domain
            if metadata_json:
                m = dict(existing.metadata_json or {})
                m.update(metadata_json)
                existing.metadata_json = m
            self.session.flush()
            return existing

        new_client = ClientProfileModel(
            name=name,
            company=company,
            email=email,
            website=website,
            domain=domain,
            confidence_score=confidence_score,
            metadata_json=metadata_json or {},
        )
        self.session.add(new_client)
        self.session.flush()
        return new_client

    def list_clients(self, page: int = 1, page_size: int = 20) -> list[ClientProfileModel]:
        offset = (page - 1) * page_size
        stmt = select(ClientProfileModel).order_by(ClientProfileModel.created_at.desc()).offset(offset).limit(page_size)
        return list(self.session.execute(stmt).scalars().all())

    def count_clients(self) -> int:
        stmt = select(func.count(ClientProfileModel.id))
        return self.session.execute(stmt).scalar_one() or 0
