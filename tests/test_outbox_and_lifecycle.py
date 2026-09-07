"""
Tests for Fix 1 (Sole State Authority & Intents), Fix 2 (Outbox & Atomic Cancellation on Reply),
and Fix 4 (Human Approval Gate).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.models import ApprovalStatus, LeadModel, LeadStatus, OutboxActionType, OutboxStatus
from src.repositories.approval_repo import ApprovalRepository
from src.repositories.lead_repo import LeadRepository
from src.repositories.outbox_repo import OutboxRepository
from src.schemas.approval import ApprovalActionRequest, ApprovalEditRequest, ApprovalRejectRequest
from src.schemas.intent import ClientReplyRequest, IntentType, LeadIntentRequest
from src.services.approval_service import ApprovalService
from src.services.lifecycle_service import LifecycleService
from src.services.outbox_dispatcher import OutboxDispatcher


def test_intent_processing_and_approval_staging(db_session: Session):
    service = LifecycleService(db_session)

    # 1. Emit SEND_MESSAGE_REQUESTED intent
    intent_req = LeadIntentRequest(
        intent_type=IntentType.SEND_MESSAGE_REQUESTED,
        title="High-Scale FastAPI & pgvector Engineer",
        description="Build semantic RAG system with sub-100ms vector search.",
        source="Upwork",
        source_url="https://upwork.com/jobs/123",
        budget=3500.0,
        skills=["Python", "FastAPI", "pgvector"],
        finder_score=92.0,
        intelligence_score=95.0,
        proposed_message={
            "subject": "Proposal for your pgvector RAG System",
            "body": "Hi there, I have built multiple production RAG architectures...",
            "channel": "platform",
        },
        idempotency_key="idemp-key-001",
    )

    res = service.process_intent(intent_req)
    assert res.success is True
    assert res.current_status == LeadStatus.MESSAGE_READY.value
    assert res.outbox_id == "idemp-key-001"
    assert res.approval_id is not None

    # Verify Outbox item was created in DB
    outbox_repo = OutboxRepository(db_session)
    outbox_item = outbox_repo.get_by_id("idemp-key-001")
    assert outbox_item is not None
    assert outbox_item.status == OutboxStatus.PENDING.value
    assert outbox_item.action_type == OutboxActionType.SEND_MESSAGE.value

    # Verify Approval item is staged in PENDING_APPROVAL
    appr_repo = ApprovalRepository(db_session)
    appr_item = appr_repo.get_by_id(res.approval_id)
    assert appr_item is not None
    assert appr_item.status == ApprovalStatus.PENDING_APPROVAL.value
    assert "pgvector RAG" in appr_item.proposed_subject


def test_atomic_cancellation_on_reply(db_session: Session):
    """
    FIX 2 CRITICAL TEST:
    When a reply arrives, Core marks every PENDING follow-up / outbox row
    as CANCELLED in the *same transaction* that records the reply.
    """
    lead_repo = LeadRepository(db_session)
    outbox_repo = OutboxRepository(db_session)
    service = LifecycleService(db_session)

    # Create a lead in CONTACTED status
    lead = lead_repo.create({
        "title": "React Native Mobile Developer",
        "description": "Cross-platform iOS and Android application.",
        "source": "HackerNews",
        "source_url": "https://news.ycombinator.com/item?id=999",
        "content_hash": "hash_mobile_123",
        "status": LeadStatus.CONTACTED.value,
    })
    db_session.commit()

    # Stage 2 pending follow-ups in the outbox
    outbox1 = outbox_repo.create_entry(
        lead_id=lead.id,
        action_type=OutboxActionType.SCHEDULE_FOLLOWUP.value,
        payload_json={"subject": "Followup 1", "body": "Checking in"},
        status=OutboxStatus.PENDING.value,
        outbox_id="fup-001",
    )
    outbox2 = outbox_repo.create_entry(
        lead_id=lead.id,
        action_type=OutboxActionType.SCHEDULE_FOLLOWUP.value,
        payload_json={"subject": "Followup 2", "body": "Any updates?"},
        status=OutboxStatus.PENDING.value,
        outbox_id="fup-002",
    )
    db_session.commit()

    # Verify both are PENDING
    assert outbox_repo.get_by_id("fup-001").status == OutboxStatus.PENDING.value
    assert outbox_repo.get_by_id("fup-002").status == OutboxStatus.PENDING.value

    # Simulate client reply
    reply_res = service.record_client_reply(
        ClientReplyRequest(
            lead_id=lead.id,
            reply_body="Hi! Yes, we'd love to chat tomorrow at 2pm.",
            sentiment="positive",
        )
    )

    assert reply_res.success is True
    assert reply_res.status == LeadStatus.REPLIED.value
    assert reply_res.cancelled_outbox_count == 2

    # Verify database state after transaction:
    lead_refreshed = lead_repo.get_by_id(lead.id)
    assert lead_refreshed.status == LeadStatus.REPLIED.value

    # BOTH pending outbox items MUST be CANCELLED with cancel_reason
    outbox1_refreshed = outbox_repo.get_by_id("fup-001")
    outbox2_refreshed = outbox_repo.get_by_id("fup-002")
    assert outbox1_refreshed.status == OutboxStatus.CANCELLED.value
    assert outbox1_refreshed.cancel_reason == "Lead replied"
    assert outbox2_refreshed.status == OutboxStatus.CANCELLED.value
    assert outbox2_refreshed.cancel_reason == "Lead replied"


def test_human_approval_workflow(db_session: Session):
    service = LifecycleService(db_session)
    appr_service = ApprovalService(db_session)

    # 1. Create a lead and message request
    res = service.process_intent(
        LeadIntentRequest(
            intent_type=IntentType.SEND_MESSAGE_REQUESTED,
            title="DevOps Kubernetes Specialist",
            description="Terraform and EKS infrastructure setup.",
            source="Freelancer",
            source_url="https://freelancer.com/projects/444",
            proposed_message={"subject": "Kubernetes Setup", "body": "I can help configure your cluster."},
            idempotency_key="outbox-k8s-01",
        )
    )
    appr_id = res.approval_id

    # 2. Check pending queue
    queue = appr_service.get_pending_queue()
    assert queue.pending_count >= 1
    item_in_queue = next(i for i in queue.items if i.id == appr_id)
    assert item_in_queue.status == ApprovalStatus.PENDING_APPROVAL.value

    # 3. Edit and Approve
    edit_res = appr_service.edit_and_approve_item(
        appr_id,
        ApprovalEditRequest(
            proposed_subject="Expert Kubernetes & Terraform CI/CD Implementation",
            proposed_body="I have extensive experience deploying production EKS clusters with Terraform...",
            reviewer="Alice",
            reason="Make pitch more specific to Terraform modules",
        ),
    )
    assert edit_res.status == ApprovalStatus.EDITED.value

    # 4. Outbox item should reflect updated body
    outbox_repo = OutboxRepository(db_session)
    outbox_item = outbox_repo.get_by_id("outbox-k8s-01")
    assert "Expert Kubernetes" in outbox_item.payload_json["subject"]
    assert outbox_item.status == OutboxStatus.PENDING.value


def test_api_lifecycle_and_approvals(client: TestClient):
    # 1. Send intent via REST API
    res = client.post(
        "/api/v1/lifecycle/intent",
        json={
            "intent_type": "SEND_MESSAGE_REQUESTED",
            "title": "Next.js Frontend Lead",
            "description": "Build high performance dashboard.",
            "source": "Web",
            "source_url": "https://example.com/job/1",
            "proposed_message": {"subject": "Next.js Help", "body": "Experienced frontend dev ready."},
            "idempotency_key": "api-idemp-001",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    lead_id = data["lead_id"]
    approval_id = data["approval_id"]

    # 2. List approvals
    appr_res = client.get("/api/v1/approvals")
    assert appr_res.status_code == 200
    assert appr_res.json()["pending_count"] >= 1

    # 3. Approve via REST API
    approve_res = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reviewer": "Bob", "notes": "Approved for sending"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # 4. Test Outbox listing and dry-run dispatch
    outbox_res = client.get("/api/v1/outbox")
    assert outbox_res.status_code == 200
    assert outbox_res.json()["total"] >= 1

    dispatch_res = client.post("/api/v1/outbox/dispatch?dry_run=true")
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["dispatched_count"] >= 1

    # 5. Send client reply via REST API
    reply_res = client.post(
        "/api/v1/lifecycle/reply",
        json={
            "lead_id": lead_id,
            "reply_body": "Thanks for reaching out! Let's talk.",
        },
    )
    assert reply_res.status_code == 200
    assert reply_res.json()["status"] == "replied"
