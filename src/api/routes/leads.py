"""
Leads API endpoints for Client Core Service.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.repositories.lead_repo import LeadRepository
from src.schemas.lead import LeadCreate, LeadListResponse, LeadResponse, LeadUpdate
from src.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> LeadResponse:
    service = LeadService(db)
    action, lead = service.create_or_get_lead(payload)
    return LeadResponse.model_validate(lead)


@router.get("", response_model=LeadListResponse)
def list_leads(
    status_filter: Optional[str] = Query(None, alias="status"),
    min_score: Optional[float] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> LeadListResponse:
    repo = LeadRepository(db)
    leads = repo.list_leads(status=status_filter, min_score=min_score, source=source, page=page, page_size=page_size)
    total = repo.count_leads(status=status_filter, min_score=min_score, source=source)
    total_pages = max(1, (total + page_size - 1) // page_size)

    return LeadListResponse(
        items=[LeadResponse.model_validate(l) for l in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)) -> LeadResponse:
    repo = LeadRepository(db)
    lead = repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_db)) -> LeadResponse:
    repo = LeadRepository(db)
    lead = repo.update(lead_id, payload.model_dump(exclude_unset=True))
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return LeadResponse.model_validate(lead)
