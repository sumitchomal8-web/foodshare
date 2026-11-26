# FoodShare Backend API

FastAPI + MongoDB Atlas backend for **FoodShare** — a platform connecting surplus food donors with NGOs and volunteers.

---

## Tech Stack
* **Language & Runtime:** Python 3.12+ / 3.14
* **Web Framework:** FastAPI (REST, OpenAPI / Swagger documentation)
* **Database & Driver:** MongoDB Atlas with Motor (asynchronous driver)
* **Authentication:** OAuth2 Password Bearer + HS256 JWT (`python-jose`) + bcrypt (`passlib`)
* **Package Manager:** `uv`
* **Test Runner:** `pytest` + `httpx`

---

## Getting Started

### 1. Install Dependencies
```bash
uv sync
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the three variables in `.env`:
```env
MONGODB_URL=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=foodshare
SECRET_KEY=<generate with: uv run python -c "import secrets; print(secrets.token_hex(32))">
```
*(Never commit `.env`)*

### 3. Run the Development Server
```bash
uv run uvicorn app.main:app --reload
```
Interactive API docs are available at:
* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 4. Seed Database (Admin & Demo Data)
```bash
uv run python scripts/seed.py
```
This initializes indexes and provisions:
* **Admin:** `admin@foodshare.org` / `FoodShare@2026`
* **Verified NGO:** `feedindia@ngo.org` / `FoodShare@2026`
* **Pending NGO:** `hope@volunteer.org` / `FoodShare@2026`
* **Donor:** `taj_caterers@donor.org` / `FoodShare@2026`
* **Sample Donation:** in `AVAILABLE` status

---

## Running Tests

Run the full test suite (62 tests):
```bash
uv run pytest tests/ -v
```

---

## API Endpoints Summary

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/health` | Public | System & DB health check |
| `POST` | `/api/v1/auth/register` | Public | Register donor or NGO |
| `POST` | `/api/v1/auth/login` | Public | Authenticate and obtain JWT |
| `GET` | `/api/v1/users/me` | Authenticated | View current profile |
| `PUT` | `/api/v1/users/me` | Authenticated | Update current profile |
| `POST` | `/api/v1/donations` | `DONOR` | Create a donation |
| `GET` | `/api/v1/donations/mine` | `DONOR` | View donor's own donations |
| `PUT` | `/api/v1/donations/{id}` | `DONOR` (owner) | Edit `AVAILABLE` donation |
| `POST` | `/api/v1/donations/{id}/cancel` | `DONOR` (owner), `ADMIN` | Cancel donation |
| `GET` | `/api/v1/donations` | `NGO`, `ADMIN` | Browse available donations |
| `GET` | `/api/v1/donations/{id}` | Access controlled | Detail view of a donation |
| `POST` | `/api/v1/donations/{id}/accept` | `NGO` (`VERIFIED`) | Claim available donation |
| `POST` | `/api/v1/donations/{id}/pickup` | Assigned `NGO` | Mark donation picked up |
| `POST` | `/api/v1/donations/{id}/distribute` | Assigned `NGO` | Mark donation distributed |
| `POST` | `/api/v1/donations/{id}/complete` | Assigned `NGO`, `ADMIN` | Mark donation complete |
| `GET` | `/api/v1/ngo/donations` | `NGO` | View accepted donations |
| `GET` | `/api/v1/admin/users` | `ADMIN` | List all users |
| `PATCH` | `/api/v1/admin/users/{id}/status` | `ADMIN` | Activate/deactivate user |
| `GET` | `/api/v1/admin/ngos/pending` | `ADMIN` | Review pending NGO verifications |
| `POST` | `/api/v1/admin/ngos/{id}/verify` | `ADMIN` | Approve or reject NGO verification |
| `GET` | `/api/v1/admin/donations` | `ADMIN` | View all donations across statuses |
| `GET` | `/api/v1/admin/stats` | `ADMIN` | Platform analytics and counts |
