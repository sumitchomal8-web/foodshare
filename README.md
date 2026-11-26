# FoodShare

> A full-stack, community-driven platform connecting surplus food donors (restaurants, banquets, grocery stores, individuals) with verified NGOs and volunteer networks to rescue food and eliminate hunger.

---

## 1. Project Overview & Architecture

FoodShare connects three primary stakeholder roles:
- **DONOR:** List surplus food, specify food types, expiry times, pickup addresses, and track real-time collection progress.
- **NGO / VOLUNTEER:** Browse available food donations filtered by city and food type, claim donations with atomic concurrency controls, and track distribution milestones (`ACCEPTED` → `PICKED_UP` → `DISTRIBUTED` → `COMPLETED`).
- **ADMIN:** Oversee platform activity, review and verify NGO registrations, manage user permissions, and monitor real-time food rescue analytics.

### Architecture Stack
* **Backend:** Python 3.12+ · FastAPI · Motor (Async MongoDB Atlas Driver) · JWT Authentication · Bcrypt
* **Frontend:** React 18 · Vite 5 · Tailwind CSS v3 · React Router DOM v6 · Lucide React
* **Database:** MongoDB Atlas (or local MongoDB 7.0 via Docker) with database name `foodshare`
* **Containerization:** Docker & Docker Compose
* **Documentation & SSOT:** [`docs/master_spec (1).md`](docs/master_spec%20(1).md) · [`docs/person_b_work_log.md`](docs/person_b_work_log.md)

---

## 2. Quick Start

### Option A: Run with Docker Compose (Recommended)

Spins up the FastAPI backend, React frontend, and local MongoDB database in containers:

```bash
docker compose up --build
```

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Local Development

#### 1. Backend Setup
```bash
cd backend
uv sync
cp .env.example .env
# Configure MONGODB_URL, DB_NAME=foodshare, and SECRET_KEY in .env

# Seed initial database records (admin, sample donor, verified & pending NGOs)
uv run python scripts/seed.py

# Start backend server
uv run uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000). The dev server automatically proxies `/api` calls to `http://127.0.0.1:8000`.

---

## 3. Running Backend Tests

The backend test suite contains **62 unit and integration tests** testing all status transitions, atomic acceptance, access control, admin functions, and authentication.

```bash
cd backend
uv run pytest tests/ -v
```

All 62 tests pass in ~4 seconds.

---

## 4. Default Seeded Credentials

When running `scripts/seed.py`, the following demo accounts are created:

| Role | Email | Password | Details |
|---|---|---|---|
| **ADMIN** | `admin@foodshare.org` | `AdminPass123!` | Platform administrator |
| **NGO (Verified)** | `feedindia@ngo.org` | `NgoPass123!` | Verified organization; can accept donations |
| **NGO (Pending)** | `hope@volunteer.org` | `HopePass123!` | Pending verification; browse-only until verified |
| **DONOR** | `taj_caterers@donor.org` | `DonorPass123!` | Sample restaurant donor with active listing |

---

## 5. Repository Structure

```
foodshare/
├── docker-compose.yml       # Multi-container orchestration
├── README.md                # Root project documentation
├── docs/
│   ├── master_spec (1).md   # Master Specification (SSOT v1.0)
│   └── person_b_work_log.md # Detailed architectural development log
├── frontend/
│   ├── Dockerfile & nginx.conf
│   ├── package.json & vite.config.js
│   ├── tailwind.config.js
│   └── src/                 # React components, contexts, and role-based views
└── backend/
    ├── Dockerfile
    ├── pyproject.toml & uv.lock
    ├── .env.example
    ├── scripts/seed.py      # Database seeding script
    ├── app/                 # FastAPI routers, services, schemas, and utils
    └── tests/               # 62 unit & API integration test cases
```
