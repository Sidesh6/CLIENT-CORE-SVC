"""
Human Review Approval Queue API endpoints for Client Core Service (Fix 4).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.database.session import get_db
from src.schemas.approval import (
    ApprovalActionRequest,
    ApprovalEditRequest,
    ApprovalItemResponse,
    ApprovalQueueResponse,
    ApprovalRejectRequest,
)
from src.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/v1/approvals", tags=["Human Review Approvals"])


@router.get("", response_model=ApprovalQueueResponse)
def get_approval_queue(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ApprovalQueueResponse:
    """Fetch items in the human review queue awaiting decision."""
    service = ApprovalService(db)
    return service.get_pending_queue(limit=limit)


@router.post("/{approval_id}/approve", response_model=ApprovalItemResponse)
def approve_item(
    approval_id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
) -> ApprovalItemResponse:
    """Approve outreach proposal for dispatch."""
    service = ApprovalService(db)
    item = service.approve_item(approval_id, payload)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval item '{approval_id}' not found",
        )
    return item


@router.post("/{approval_id}/edit", response_model=ApprovalItemResponse)
def edit_and_approve_item(
    approval_id: str,
    payload: ApprovalEditRequest,
    db: Session = Depends(get_db),
) -> ApprovalItemResponse:
    """Edit message draft, record feedback diff for Learning SVC, and approve."""
    service = ApprovalService(db)
    item = service.edit_and_approve_item(approval_id, payload)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval item '{approval_id}' not found",
        )
    return item


@router.post("/{approval_id}/reject", response_model=ApprovalItemResponse)
def reject_item(
    approval_id: str,
    payload: ApprovalRejectRequest,
    db: Session = Depends(get_db),
) -> ApprovalItemResponse:
    """Reject outreach proposal, record labeled feedback reason, and cancel outbox item."""
    service = ApprovalService(db)
    item = service.reject_item(approval_id, payload)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval item '{approval_id}' not found",
        )
    return item
