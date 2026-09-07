from sqlalchemy.orm import Session
from src.models.base import compute_content_hash
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.lead_repo import LeadRepository
from src.schemas.client import ClientProfileCreate
from src.schemas.lead import LeadCreate
from src.services.crm_service import CRMService
from src.services.lead_service import LeadService


def test_lead_repository_and_service(db_session: Session):
    lead_svc = LeadService(db_session)
    req = LeadCreate(
        title="FastAPI AI Specialist",
        description="Build microservices",
        source="Upwork",
        source_url="https://upwork.com/ai",
        budget=3000.0,
    )
    status, lead = lead_svc.create_or_get_lead(req)
    assert status == "created"
    assert lead.id is not None

    # Duplicate should return existing
    status2, lead2 = lead_svc.create_or_get_lead(req)
    assert status2 == "existing"
    assert lead2.id == lead.id


def test_crm_service(db_session: Session):
    crm = CRMService(db_session)
    client_req = ClientProfileCreate(
        name="Michael",
        company="Vanguard Tech",
        email="michael@vanguard.io",
    )
    client = crm.register_client(client_req)
    assert client.id is not None
    assert client.company == "Vanguard Tech"
