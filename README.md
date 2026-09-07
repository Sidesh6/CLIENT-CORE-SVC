# Client Core Service (`CLIENT-CORE-SVC`)

Centralized business data repository and CRM for leads, clients, conversations, proposals, and follow-up sequences (Port 8003).

---

## 🚀 Quickstart

### 1. Initialize Database
```powershell
cd "C:\PRIVATE PROJECTS\CLIENT-CORE-SVC"
python -m src.cli init-db
```

### 2. Start REST API Server
```powershell
python -m src.cli run-server --port 8003
```

- Swagger UI: [http://localhost:8003/docs](http://localhost:8003/docs)
- Health Check: [http://localhost:8003/health](http://localhost:8003/health)

### 3. List Leads and Clients via CLI
```powershell
python -m src.cli list-leads
python -m src.cli list-clients
```

### 4. Run Tests
```powershell
pytest tests -v --cov=src
```
