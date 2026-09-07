"""
Lifecycle and Intent endpoints for Client Core Service (Fix 1 & Fix 2).
Sole state authority for processing intents and client replies.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.schemas.intent import (
    ClientReplyRequest,
    ClientReplyResponse,
    LeadIntentRequest,
    LeadIntentResponse,
)
from src.services.lifecycle_service import LifecycleService

router = APIRouter(prefix="/api/v1/lifecycle", tags=["Lifecycle & Intents"])


@router.post("/intent", response_model=LeadIntentResponse, status_code=status.HTTP_200_OK)
def process_intent(
    payload: LeadIntentRequest,
    db: Session = Depends(get_db),
) -> LeadIntentResponse:
    """
    Receive and process an intent emitted by Orchestrator or agents.
    Core decides state transitions, validates invariants, and writes to outbox atomically.
    """
    service = LifecycleService(db)
    res = service.process_intent(payload)
    if not res.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.message,
        )
    return res


@router.post("/reply", response_model=ClientReplyResponse, status_code=status.HTTP_200_OK)
def record_reply(
    payload: ClientReplyRequest,
    db: Session = Depends(get_db),
) -> ClientReplyResponse:
    """
    Record an inbound client reply.
    GUARANTEE: In the *same database transaction*, marks lead as REPLIED
    and cancels all PENDING outbox follow-ups/messages for this lead.
    """
    service = LifecycleService(db)
    res = service.record_client_reply(payload)
    if not res.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=res.message,
        )
    return res
