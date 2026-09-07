"""
Outbox Dispatcher — Background worker ensuring reliable, idempotent outbound action dispatch (Fix 2 & Fix 4).
Polls PENDING outbox entries, checks pre-flight status, respects human approval gate,
and sends with idempotency keys.
"""

from datetime import UTC, datetime
from typing import Any
import httpx
from sqlalchemy.orm import Session
from src.config.settings import settings
from src.models.models import ApprovalStatus, LeadStatus, OutboxActionType, OutboxStatus
from src.repositories.lead_repo import LeadRepository
from src.repositories.outbox_repo import OutboxRepository
from src.schemas.outbox import OutboxDispatchResponse


class OutboxDispatcher:
    def __init__(self, session: Session, messager_url: str = settings.messager_svc_url):
        self.session = session
        self.outbox_repo = OutboxRepository(session)
        self.lead_repo = LeadRepository(session)
        self.messager_url = messager_url.rstrip("/")

    def dispatch_pending(self, limit: int = 50, dry_run: bool = False) -> OutboxDispatchResponse:
        """
        Polls PENDING outbox records and dispatches them with idempotency keys.
        Pre-flight check: ensures status is STILL 'PENDING' immediately before firing.
        Enforces human approval gate (Fix 4).
        """
        pending_items = self.outbox_repo.get_pending(limit=limit)
        dispatched = 0
        failed = 0
        skipped = 0
        details: list[dict[str, Any]] = []

        for item in pending_items:
            # 1. Pre-flight check: Verify status is still PENDING (prevents race condition if reply arrived)
            if item.status != OutboxStatus.PENDING.value:
                skipped += 1
                details.append({"id": item.id, "status": "skipped", "reason": f"Status is '{item.status}', not PENDING"})
                continue

            # 2. Fix 4 Approval Gate check: If approval record exists, must be APPROVED or EDITED
            if item.approval and item.approval.status not in (ApprovalStatus.APPROVED.value, ApprovalStatus.EDITED.value):
                skipped += 1
                details.append({
                    "id": item.id,
                    "status": "skipped",
                    "reason": f"Awaiting human review (approval status: '{item.approval.status}')",
                })
                continue

            if dry_run:
                dispatched += 1
                details.append({"id": item.id, "status": "dry_run", "action_type": item.action_type})
                continue

            # 3. Call Messager Service with Idempotency Key
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{self.messager_url}/api/v1/messages/send",
                        json={
                            "idempotency_key": item.id,
                            "lead_id": item.lead_id,
                            "action_type": item.action_type,
                            "payload": item.payload_json,
                        },
                        headers={"Idempotency-Key": item.id},
                    )

                if resp.status_code in (200, 201, 204):
                    self.outbox_repo.mark_sent(item.id)

                    # Update lead lifecycle state
                    lead = self.lead_repo.get_by_id(item.lead_id)
                    if lead:
                        if item.action_type == OutboxActionType.SEND_MESSAGE.value:
                            lead.status = LeadStatus.CONTACTED.value
                        elif item.action_type == OutboxActionType.SEND_PROPOSAL.value:
                            lead.status = LeadStatus.PROPOSAL_SENT.value

                    dispatched += 1
                    details.append({"id": item.id, "status": "sent", "http_status": resp.status_code})
                else:
                    err_msg = f"Messager returned HTTP {resp.status_code}: {resp.text[:200]}"
                    self.outbox_repo.mark_failed(item.id, err_msg)
                    failed += 1
                    details.append({"id": item.id, "status": "failed", "error": err_msg})

            except Exception as e:
                err_msg = f"Network/Dispatcher exception: {str(e)}"
                self.outbox_repo.mark_failed(item.id, err_msg)
                failed += 1
                details.append({"id": item.id, "status": "failed", "error": err_msg})

        self.session.commit()

        return OutboxDispatchResponse(
            dispatched_count=dispatched,
            failed_count=failed,
            skipped_count=skipped,
            details=details,
        )
