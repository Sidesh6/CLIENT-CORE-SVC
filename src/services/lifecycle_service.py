"""
Lifecycle Service — Core CRM Sole State Authority (Fix 1 & Fix 2).
Enforces single state ownership, validates invariants, processes Orchestrator intents,
and writes outbox actions atomically with state transitions.
"""

from datetime import UTC, datetime
from typing import Optional
from sqlalchemy.orm import Session
from src.models.base import compute_content_hash
from src.models.models import (
    ApprovalStatus,
    LeadModel,
    LeadStatus,
    OutboxActionType,
    OutboxModel,
    OutboxStatus,
)
from src.repositories.approval_repo import ApprovalRepository
from src.repositories.client_repo import ClientProfileRepository
from src.repositories.conversation_repo import ConversationRepository
from src.repositories.lead_repo import LeadRepository
from src.repositories.outbox_repo import OutboxRepository
from src.schemas.intent import (
    ClientReplyRequest,
    ClientReplyResponse,
    IntentType,
    LeadIntentRequest,
    LeadIntentResponse,
)


class LifecycleService:
    """
    Sole authority for changing lifecycle state of leads and scheduling outbound actions.
    Orchestrator emits intents to this service; it validates state machine rules and records
    both lifecycle state and outbox items in atomic database transactions.
    """

    def __init__(self, session: Session):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.client_repo = ClientProfileRepository(session)
        self.conv_repo = ConversationRepository(session)
        self.outbox_repo = OutboxRepository(session)
        self.approval_repo = ApprovalRepository(session)

    def process_intent(self, req: LeadIntentRequest) -> LeadIntentResponse:
        """
        Processes an intent emitted by Orchestrator or another service.
        Decides state transition and atomically stages outbox / approval items.
        """
        # Find or create lead
        lead = None
        if req.lead_id:
            lead = self.lead_repo.get_by_id(req.lead_id)

        if not lead and req.title and req.description:
            content_hash = compute_content_hash(req.title, req.description)
            lead = self.lead_repo.get_by_content_hash(content_hash)
            if not lead:
                lead = self.lead_repo.create({
                    "title": req.title,
                    "description": req.description,
                    "source": req.source or "Web",
                    "source_url": req.source_url or "",
                    "budget": req.budget,
                    "skills": req.skills,
                    "finder_score": req.finder_score,
                    "intelligence_score": req.intelligence_score,
                    "status": LeadStatus.DISCOVERED.value,
                    "content_hash": content_hash,
                    "raw_data": req.intelligence_payload,
                })

        if not lead:
            return LeadIntentResponse(
                success=False,
                lead_id=req.lead_id or "",
                current_status="unknown",
                message="Lead could not be found or created from intent payload",
            )

        prev_status = lead.status
        outbox_id = None
        approval_id = None

        # 1. ENRICH_LEAD intent
        if req.intent_type == IntentType.ENRICH_LEAD:
            lead.status = LeadStatus.ENRICHED.value
            if req.intelligence_score is not None:
                lead.intelligence_score = req.intelligence_score
            if req.intelligence_payload:
                lead.raw_data.update(req.intelligence_payload)
            self.session.flush()

        # 2. QUALIFY_LEAD intent
        elif req.intent_type == IntentType.QUALIFY_LEAD:
            if (req.intelligence_score or 0) >= 70.0 or (lead.intelligence_score or 0) >= 70.0:
                lead.status = LeadStatus.QUALIFIED.value
            else:
                lead.status = LeadStatus.DISQUALIFIED.value
            self.session.flush()

        # 3. SEND_MESSAGE_REQUESTED intent (Human Approval Gated)
        elif req.intent_type == IntentType.SEND_MESSAGE_REQUESTED:
            # Enforce invariant: don't stage outreach if lead is replied or won/lost
            if lead.status in (LeadStatus.REPLIED.value, LeadStatus.ENGAGED.value, LeadStatus.WON.value, LeadStatus.LOST.value):
                return LeadIntentResponse(
                    success=False,
                    lead_id=lead.id,
                    previous_status=prev_status,
                    current_status=lead.status,
                    message=f"Cannot schedule message: lead is already in state '{lead.status}'",
                )

            lead.status = LeadStatus.MESSAGE_READY.value

            msg_payload = req.proposed_message or {
                "subject": f"Inquiry regarding {lead.title[:50]}",
                "body": f"Hello, I came across your project '{lead.title}' and would love to help.",
                "channel": "email",
                "recipient": lead.client.email if lead.client else None,
            }

            # Write Outbox entry (Idempotency Key: req.idempotency_key or generated UUID)
            outbox_entry = self.outbox_repo.create_entry(
                lead_id=lead.id,
                action_type=OutboxActionType.SEND_MESSAGE.value,
                payload_json=msg_payload,
                status=OutboxStatus.PENDING.value,
                outbox_id=req.idempotency_key,
            )
            outbox_id = outbox_entry.id

            # FIX 4: Stage in Human Review Queue before anything reaches the client
            approval_item = self.approval_repo.create_item(
                lead_id=lead.id,
                outbox_id=outbox_entry.id,
                action_type=OutboxActionType.SEND_MESSAGE.value,
                proposed_subject=msg_payload.get("subject", "Outreach Inquiry"),
                proposed_body=msg_payload.get("body", ""),
                feedback_payload={"source": lead.source, "score": lead.intelligence_score or lead.finder_score},
            )
            approval_id = approval_item.id
            self.session.flush()

        # 4. PROPOSAL_REQUESTED intent (Human Approval Gated)
        elif req.intent_type == IntentType.PROPOSAL_REQUESTED:
            lead.status = LeadStatus.PROPOSAL_READY.value
            prop_payload = req.proposed_message or {
                "title": f"Proposal: {lead.title}",
                "scope_summary": lead.description[:200],
                "amount": lead.budget or 1000.0,
            }

            outbox_entry = self.outbox_repo.create_entry(
                lead_id=lead.id,
                action_type=OutboxActionType.SEND_PROPOSAL.value,
                payload_json=prop_payload,
                status=OutboxStatus.PENDING.value,
                outbox_id=req.idempotency_key,
            )
            outbox_id = outbox_entry.id

            approval_item = self.approval_repo.create_item(
                lead_id=lead.id,
                outbox_id=outbox_entry.id,
                action_type=OutboxActionType.SEND_PROPOSAL.value,
                proposed_subject=prop_payload.get("title", f"Proposal: {lead.title}"),
                proposed_body=prop_payload.get("scope_summary", ""),
                feedback_payload={"budget": lead.budget, "source": lead.source},
            )
            approval_id = approval_item.id
            self.session.flush()

        # 5. FOLLOWUP_REQUESTED intent
        elif req.intent_type == IntentType.FOLLOWUP_REQUESTED:
            if lead.status in (LeadStatus.REPLIED.value, LeadStatus.ENGAGED.value, LeadStatus.WON.value, LeadStatus.LOST.value):
                return LeadIntentResponse(
                    success=False,
                    lead_id=lead.id,
                    previous_status=prev_status,
                    current_status=lead.status,
                    message=f"Cannot schedule followup: lead is already in state '{lead.status}'",
                )

            followup_payload = req.proposed_message or {
                "subject": f"Following up: {lead.title[:50]}",
                "body": "Hi, just checking in to see if you had a chance to review my previous note.",
            }

            outbox_entry = self.outbox_repo.create_entry(
                lead_id=lead.id,
                action_type=OutboxActionType.SCHEDULE_FOLLOWUP.value,
                payload_json=followup_payload,
                status=OutboxStatus.PENDING.value,
                outbox_id=req.idempotency_key,
            )
            outbox_id = outbox_entry.id
            self.session.flush()

        self.session.commit()

        return LeadIntentResponse(
            success=True,
            lead_id=lead.id,
            previous_status=prev_status,
            current_status=lead.status,
            outbox_id=outbox_id,
            approval_id=approval_id,
            message=f"Intent '{req.intent_type}' processed successfully; transitioned '{prev_status}' -> '{lead.status}'",
        )

    def record_client_reply(self, req: ClientReplyRequest) -> ClientReplyResponse:
        """
        FIX 1 & FIX 2 GUARANTEE:
        When a client replies:
        1. Lead transitions to REPLIED
        2. In the *same database transaction*, all PENDING outbox follow-ups/messages are cancelled
        3. All pending follow-up schedules are marked cancelled
        """
        lead, cancelled_outbox, cancelled_followups = self.lead_repo.record_reply_and_cancel_outbox(
            lead_id=req.lead_id,
            reason="Lead replied",
        )

        if not lead:
            return ClientReplyResponse(
                success=False,
                lead_id=req.lead_id,
                status="not_found",
                cancelled_outbox_count=0,
                cancelled_followups_count=0,
                message=f"Lead '{req.lead_id}' not found",
            )

        # Record conversation message
        conv = self.conv_repo.get_or_create(
            lead_id=lead.id,
            client_id=lead.client_id,
            channel=req.channel,
            subject=f"Re: {lead.title[:100]}",
        )
        self.conv_repo.add_message(
            conversation_id=conv.id,
            sender_type="client",
            message_type="reply",
            body=req.reply_body,
            sentiment=req.sentiment,
        )

        self.session.commit()

        return ClientReplyResponse(
            success=True,
            lead_id=lead.id,
            status=lead.status,
            cancelled_outbox_count=cancelled_outbox,
            cancelled_followups_count=cancelled_followups,
            message=f"Recorded reply and atomically cancelled {cancelled_outbox} pending outbox actions.",
        )
