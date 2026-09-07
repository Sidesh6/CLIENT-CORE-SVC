from sqlalchemy.orm import Session
from src.models.base import compute_content_hash
from src.models.models import ClientProfileModel, ConversationModel, LeadModel, LeadStatus, ProposalModel


def test_models_and_relationships(db_session: Session):
    client = ClientProfileModel(
        name="Elena Rostova",
        company="Rostov Robotics",
        email="elena@rostov.io",
    )
    db_session.add(client)
    db_session.flush()

    lead = LeadModel(
        title="ROS 2 & Python Robotics Engineer",
        description="Autonomous navigation pipeline",
        source="Hacker News",
        source_url="https://hn.com/ros",
        content_hash=compute_content_hash("ROS 2", "Robotics"),
        client_id=client.id,
    )
    db_session.add(lead)
    db_session.flush()

    conv = ConversationModel(
        lead_id=lead.id,
        client_id=client.id,
        subject="Robotics Proposal",
    )
    db_session.add(conv)
    db_session.flush()

    prop = ProposalModel(
        lead_id=lead.id,
        client_id=client.id,
        title="ROS 2 Navigation Architecture",
        scope_summary="Full SLAM and path planner",
        amount=6000.0,
    )
    db_session.add(prop)
    db_session.flush()

    assert lead.client.company == "Rostov Robotics"
    assert len(lead.conversations) == 1
    assert len(lead.proposals) == 1
