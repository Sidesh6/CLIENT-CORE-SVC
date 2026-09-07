"""
Clients and Conversations API routes for Client Core Service.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.conversation_repo import ConversationRepository, ProposalRepository
from src.schemas.client import (
    ClientProfileCreate,
    ClientProfileListResponse,
    ClientProfileResponse,
)
from src.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageRecordCreate,
    MessageRecordResponse,
)
from src.schemas.proposal import ProposalCreate, ProposalResponse
from src.services.crm_service import CRMService

clients_router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])
conv_router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])
prop_router = APIRouter(prefix="/api/v1/proposals", tags=["Proposals"])


@clients_router.post("", response_model=ClientProfileResponse, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientProfileCreate, db: Session = Depends(get_db)) -> ClientProfileResponse:
    service = CRMService(db)
    client = service.register_client(payload)
    return ClientProfileResponse.model_validate(client)


@clients_router.get("", response_model=ClientProfileListResponse)
def list_clients(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> ClientProfileListResponse:
    repo = ClientProfileRepository(db)
    items = repo.list_clients(page=page, page_size=page_size)
    total = repo.count_clients()
    return ClientProfileListResponse(
        items=[ClientProfileResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@clients_router.get("/{client_id}", response_model=ClientProfileResponse)
def get_client(client_id: str, db: Session = Depends(get_db)) -> ClientProfileResponse:
    repo = ClientProfileRepository(db)
    client = repo.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientProfileResponse.model_validate(client)


@conv_router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> ConversationResponse:
    service = CRMService(db)
    conv = service.start_conversation(payload)
    return ConversationResponse.model_validate(conv)


@conv_router.post("/{conv_id}/messages", response_model=MessageRecordResponse, status_code=status.HTTP_201_CREATED)
def add_message(conv_id: str, payload: MessageRecordCreate, db: Session = Depends(get_db)) -> MessageRecordResponse:
    service = CRMService(db)
    msg = service.log_message(payload)
    return MessageRecordResponse.model_validate(msg)


@conv_router.get("", response_model=ConversationListResponse)
def list_conversations(lead_id: Optional[str] = None, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)) -> ConversationListResponse:
    repo = ConversationRepository(db)
    items = repo.list_conversations(lead_id=lead_id, page=page, page_size=page_size)
    total = repo.count_conversations(lead_id=lead_id)
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@prop_router.post("", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def create_proposal(payload: ProposalCreate, db: Session = Depends(get_db)) -> ProposalResponse:
    service = CRMService(db)
    prop = service.record_proposal(payload)
    return ProposalResponse.model_validate(prop)


@prop_router.get("/{prop_id}", response_model=ProposalResponse)
def get_proposal(prop_id: str, db: Session = Depends(get_db)) -> ProposalResponse:
    repo = ProposalRepository(db)
    prop = repo.get_by_id(prop_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return ProposalResponse.model_validate(prop)
