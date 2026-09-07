"""
Outbox endpoints for Client Core Service (Fix 2).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.repositories.outbox_repo import OutboxRepository
from src.schemas.outbox import (
    OutboxDispatchResponse,
    OutboxListResponse,
    OutboxResponse,
)
from src.services.outbox_dispatcher import OutboxDispatcher

router = APIRouter(prefix="/api/v1/outbox", tags=["Outbox"])


@router.get("", response_model=OutboxListResponse)
def list_outbox_items(
    status_filter: Optional[str] = Query(None, alias="status"),
    lead_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> OutboxListResponse:
    repo = OutboxRepository(db)
    items = repo.list_outbox(status=status_filter, lead_id=lead_id, page=page, page_size=page_size)
    pending_cnt = repo.count_pending()

    return OutboxListResponse(
        items=[OutboxResponse.model_validate(i) for i in items],
        total=len(items),
        pending_count=pending_cnt,
    )


@router.get("/pending", response_model=list[OutboxResponse])
def get_pending_outbox(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[OutboxResponse]:
    repo = OutboxRepository(db)
    items = repo.get_pending(limit=limit)
    return [OutboxResponse.model_validate(i) for i in items]


@router.post("/dispatch", response_model=OutboxDispatchResponse, status_code=status.HTTP_200_OK)
def trigger_outbox_dispatch(
    limit: int = Query(50, ge=1, le=200),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
) -> OutboxDispatchResponse:
    """
    Trigger background outbox dispatcher.
    Pre-flight status checks prevent double sends, and approvals are enforced.
    """
    dispatcher = OutboxDispatcher(db)
    return dispatcher.dispatch_pending(limit=limit, dry_run=dry_run)
