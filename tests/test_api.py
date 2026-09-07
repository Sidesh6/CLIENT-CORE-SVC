from fastapi.testclient import TestClient


def test_api_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "client-core-svc"


def test_leads_and_clients_api(client: TestClient):
    # 1. Create client
    client_res = client.post(
        "/api/v1/clients",
        json={
            "name": "Sarah Connor",
            "company": "Cyberdyne AI",
            "email": "sarah@cyberdyne.ai",
        },
    )
    assert client_res.status_code == 201
    client_id = client_res.json()["id"]

    # 2. Create lead
    lead_res = client.post(
        "/api/v1/leads",
        json={
            "title": "Python & pgvector Search Engineer",
            "description": "Construct high-throughput vector search microservice.",
            "source": "Hacker News",
            "source_url": "https://news.ycombinator.com/item?id=888",
            "budget": 4500.0,
            "skills": ["Python", "FastAPI", "pgvector"],
            "client_id": client_id,
            "finder_score": 91.0,
        },
    )
    assert lead_res.status_code == 201
    lead_id = lead_res.json()["id"]

    # 3. List leads
    list_res = client.get("/api/v1/leads?min_score=80.0")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 4. Patch status
    patch_res = client.patch(f"/api/v1/leads/{lead_id}", json={"status": "qualified"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "qualified"

    # 5. Create conversation & proposal
    conv_res = client.post(
        "/api/v1/conversations",
        json={
            "lead_id": lead_id,
            "client_id": client_id,
            "subject": "Proposal: pgvector Microservice",
        },
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    prop_res = client.post(
        "/api/v1/proposals",
        json={
            "lead_id": lead_id,
            "client_id": client_id,
            "title": "pgvector Architecture Proposal",
            "scope_summary": "Sub-200ms document indexing & API",
            "amount": 4500.0,
        },
    )
    assert prop_res.status_code == 201
