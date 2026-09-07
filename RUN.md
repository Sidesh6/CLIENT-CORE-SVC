# How to Run `CLIENT-CORE-SVC`

---

## 1. Initialize Database
```powershell
cd "C:\PRIVATE PROJECTS\CLIENT-CORE-SVC"
python -m src.cli init-db
```

## 2. Start REST API Server
```powershell
python -m src.cli run-server --port 8003
```

## 3. CLI Commands
```powershell
python -m src.cli list-leads
python -m src.cli list-clients
```

## 4. Run Tests
```powershell
pytest tests -v --cov=src
```
