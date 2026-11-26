# FoodShare

> Connecting surplus food donors (restaurants, events, individuals) with verified NGOs and volunteers to reduce food waste and combat hunger.

---

## Architecture Overview
* **Backend:** FastAPI + Python 3.12+ with asynchronous MongoDB Atlas (`motor`) driver.
* **Frontend:** React + Tailwind CSS (planned in next phase).
* **Specification:** [docs/master_spec (1).md](docs/master_spec%20(1).md) is the Single Source of Truth (SSOT).
* **Development Log:** [docs/person_b_work_log.md](docs/person_b_work_log.md)

---

## Quick Start (Backend)

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with your MONGODB_URL and SECRET_KEY
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload
```

Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
Tests: `uv run pytest tests/ -v` (62 tests passing)
