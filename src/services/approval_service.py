"""
Approval Service — Human Review Queue and Labeled Dataset generation for Learning SVC (Fix 4).
"""

from typing import Optional
from sqlalchemy.orm import Session
from src.repositories.approval_repo import ApprovalRepository
from src.schemas.approval import (
    ApprovalActionRequest,
    ApprovalEditRequest,
    ApprovalItemResponse,
    ApprovalQueueResponse,
    ApprovalRejectRequest,
)


class ApprovalService:
    def __init__(self, session: Session):
        self.session = session
        self.approval_repo = ApprovalRepository(session)

    def get_pending_queue(self, limit: int = 50) -> ApprovalQueueResponse:
        items = self.approval_repo.get_pending_queue(limit=limit)
        response_items: list[ApprovalItemResponse] = []

        for item in items:
            lead = item.lead
            resp = ApprovalItemResponse.model_validate(item)
            if lead:
                resp.lead_title = lead.title
                resp.lead_source = lead.source
                resp.lead_score = lead.intelligence_score or lead.finder_score
            response_items.append(resp)

        return ApprovalQueueResponse(
            pending_count=len(response_items),
            items=response_items,
        )

    def approve_item(
        self, approval_id: str, req: ApprovalActionRequest
    ) -> Optional[ApprovalItemResponse]:
        item = self.approval_repo.approve(
            approval_id=approval_id,
            reviewer=req.reviewer,
            notes=req.notes,
        )
        if not item:
            return None
        self.session.commit()
        return ApprovalItemResponse.model_validate(item)

    def edit_and_approve_item(
        self, approval_id: str, req: ApprovalEditRequest
    ) -> Optional[ApprovalItemResponse]:
        item = self.approval_repo.edit_and_approve(
            approval_id=approval_id,
            subject=req.proposed_subject,
            body=req.proposed_body,
            reviewer=req.reviewer,
            reason=req.reason or "Manual refinement",
            notes=req.notes,
        )
        if not item:
            return None
        self.session.commit()
        return ApprovalItemResponse.model_validate(item)

    def reject_item(
        self, approval_id: str, req: ApprovalRejectRequest
    ) -> Optional[ApprovalItemResponse]:
        item = self.approval_repo.reject(
            approval_id=approval_id,
            reason=req.reason,
            reviewer=req.reviewer,
            notes=req.notes,
        )
        if not item:
            return None
        self.session.commit()
        return ApprovalItemResponse.model_validate(item)
