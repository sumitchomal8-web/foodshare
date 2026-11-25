# FoodShare – Master Brief for the Coding Agent

Date: 2026-11-25. Read this whole file before doing anything. It replaces earlier scope rules where they conflict. If anything here conflicts with `docs/master_spec.md`, the spec wins and you must tell me about the conflict instead of choosing.

---

## 1. What this project is

FoodShare is a food donation platform for a college project (2-person team, deadline is close). Donors post surplus food, verified NGOs/volunteers accept and track it, and an admin verifies NGOs and sees statistics.

Stack: React + Tailwind (frontend), Python 3.12 + FastAPI, MongoDB Atlas via Motor (async), JWT (python-jose) + bcrypt (passlib), REST under `/api/v1`, `uv` for Python packages, Git/GitHub.

Two students own this code and will be questioned about every file in a viva. So: simple, readable code, short functions, comments that explain why, no clever tricks, no unrequested features.

## 2. Source of truth

1. `docs/master_spec.md` (v0.2) is the contract: collections, fields, routes, status lifecycle, error codes, naming. Never rename or change anything in it.
2. If the spec is wrong or missing something, do not invent. Write the problem into `docs/SPEC_CHANGE_REQUESTS.md` (what, why, your proposal) and continue with the closest spec-compliant option.
3. Decisions already made for this build (treat as spec):
   - Collection is `donations`, never `listings`.
   - `PATCH /api/v1/users/me` (not PUT). Validation errors are `422` with code `VALIDATION_ERROR`.
   - Admin verifies NGOs with `POST /api/v1/admin/ngos/{id}/verify` (body `{ "approve": true | false }`), not PATCH.
   - Errors always look like `{ "detail": "...", "code": "..." }` via the existing `AppError`.
   - Database name is `foodshare`.

## 3. Current state of the code

Done (backend/app): `config.py`, `database.py` (Motor client, `db`, `create_indexes`), `main.py` (lifespan, `/health`, exception handlers), `utils/security.py` (hash/verify/JWT), `utils/errors.py` (`AppError`), `utils/dependencies.py` (`get_current_user` loads the user from the DB and checks `is_active`; `require_role(*roles)`), `schemas/user.py`, `routers/auth.py` (register, login), `routers/users.py` (`GET`/`PATCH /users/me`, helper `user_to_response`).

Known problems to fix first (Phase A):
- `schemas/user.py`: password `max_length=72`; `min_length=1` on name, phone and all address fields; pincode exactly 6 digits; `NgoProfileIn` requires `registration_number` when `org_type == "NGO"`.
- `routers/auth.py`: set `created_at` and `updated_at` from one `now`; NGO `ngo_profile` gets `verification_status="PENDING"`, `verified_by=None`, `verified_at=None`; inactive login uses code `ACCOUNT_DISABLED`.
- Earlier unreviewed drafts exist for `routers/admin.py`, `routers/listings.py` and `schemas/listing.py` (wrong naming, outside the plan). Do not reuse or extend them. They are being removed by me. Build the modules below fresh from the spec.
- There is a temporary `/test-protected` route. Remove it once `/users/me` is verified.

## 4. Hard rules (safety)

You may do these only with my explicit approval each time: run any terminal command, install a package, create a folder.

You must never:
- read, open, print, create, edit or copy `.env` files (backend or frontend). Use `.env.example` for placeholders. Do not ask me to paste secrets.
- run `git commit`, `git push`, `git reset`, `git checkout`, `git merge`, delete files, or change `.gitignore`, `pyproject.toml`, `uv.lock`, `docs/master_spec.md`.
- make network requests other than my own running dev server, and the package installs I approve.
- install anything not on the approved list below without asking first with the exact package name and why.

Approved package names (exact spelling, ask before each install): backend: `pytest`, `pytest-asyncio`, `httpx`. Frontend: `vite`, `react`, `react-dom`, `react-router-dom`, `axios`, `tailwindcss` (and the official Tailwind plugin for Vite). Anything else: ask. Be especially careful with look-alike names (for example `httpx2` is not `httpx`).

Allowed read-only commands (with approval): `git status`, `git diff`. Whenever you show a diff, it must come from a real `git diff`, never written by hand. If you cannot run it, say so.

## 5. How to work (every phase)

1. Plan first: list the files you will create or change and what each does. Wait for my "go".
2. Implement only that phase. Maximum about five files per step.
3. Show the real diff, then explain each file in plain language (what it does, why it is built that way).
4. Self-review against the spec: list every route, field name and error code you used, and any place you deviated.
5. Give me a manual test list (steps in `/docs`, expected status and code) and write automated tests for the phase.
6. Add or update `docs/VIVA_NOTES.md`: one short section per module (purpose, main flow, key decisions, 3 likely examiner questions with answers).
7. STOP and wait for me to review, test and commit. Never start the next phase on your own.

Report at the end of each phase: files changed, assumptions, deviations from spec, anything you were unsure about.

## 6. Code standards

- `async def` and `await` with Motor everywhere in routes and services.
- Routers stay thin; business rules live in `services/`.
- Naming per spec: snake_case, UPPER_CASE enum values, `<thing>_id` ObjectId references, timestamps UTC ending in `_at`.
- Convert `_id` to `id` (string) and every ObjectId to string in responses. Use one helper per document type.
- Never return `password_hash`. Input schemas use `extra="forbid"`; response schemas do not.
- Every error is an `AppError` with a code from spec section 8. No bare `HTTPException`.
- Paginated lists return `{ items, total, page, limit }` (page default 1, limit default 20, max 100).
- No hard-coded secrets, URLs or magic numbers. New non-secret settings go into `config.py` and `.env.example`.
- Comments explain why, not what. No dead code, no unused imports.

## 7. Build plan

### Phase A: finish auth cleanup (Person A)
Fix the items in section 3. Remove `/test-protected`. Add a validation-error handler if `main.py` does not already return `{detail, code: "VALIDATION_ERROR"}` with status 422.
Done when: registering with a 73-char password, a 5-digit pincode, an empty name, or an NGO without registration number returns 422; users have `created_at` and `updated_at`; inactive login returns `403 ACCOUNT_DISABLED`.

### Phase B: donation schemas and donor routes (Person A)
- `schemas/donation.py` from spec 4.2: `DonationCreate` (title, food_type, quantity > 0, quantity_unit, description optional, pickup_address, available_from, expires_at), `DonationUpdate` (all optional, `extra="forbid"`), `DonationResponse` (with `donor_id`, `accepted_by` as strings, all timestamps, `status`, `status_history`).
- Rules: `expires_at` must be after `available_from` and in the future at creation. Donors cannot set `status`, `donor_id`, `accepted_by` or timestamps.
- `routers/donor.py` (role `DONOR`): `POST /donations`, `GET /donations/mine` (filter `status`, paginated, newest first), `PUT /donations/{id}` (owner only, `AVAILABLE` only), `POST /donations/{id}/cancel` (owner only, `AVAILABLE` only, status becomes `CANCELLED`).
- New donation: `status="AVAILABLE"`, `status_history=[{status, changed_by, changed_at}]`.
- Register `/donations/mine` before any `/donations/{id}` route.
- Add `create_donation_indexes()` in `database.py` per spec 4.4, called from `create_indexes()`.
Done when: a donor can create, list, edit and cancel their own donations; another donor gets `404 NOT_FOUND` (do not reveal that it exists); editing a non-`AVAILABLE` donation returns `409 INVALID_STATUS_TRANSITION`.

### Phase C: donation lifecycle service and NGO routes (Person B scope; build on its own branch I will create)
- `services/donation_service.py`: one transition table (spec section 5) and one function that applies a transition: checks the allowed transition and the actor, performs an atomic `update_one` filtered on the expected current status, appends to `status_history` with `$push`, sets the stage timestamp and `updated_at`. If no document matched, return `409` (`ALREADY_ACCEPTED` for a lost accept race, otherwise `INVALID_STATUS_TRANSITION`).
- Expiry on read: before listing or fetching, mark `AVAILABLE` donations with `expires_at` in the past as `EXPIRED` (`update_many`, history entry with `changed_by=None`).
- `routers/donations.py`: `GET /donations` (roles `NGO`, `ADMIN`; filters `status` (NGOs default to `AVAILABLE`), `city`, `food_type`; paginated), `GET /donations/{id}` (owner donor, assigned NGO, admin; an NGO may view an `AVAILABLE` one), `POST /donations/{id}/accept` (verified, active NGO only, else `403 NGO_NOT_VERIFIED`), `POST .../pickup`, `/distribute`, `/complete` (assigned NGO; complete also allowed for admin).
- `routers/ngo.py`: `GET /ngo/donations` (accepted by me, filter `status`, paginated).
Done when: two NGOs accepting the same donation at once result in exactly one success and one `409`; an unverified NGO cannot accept; illegal transitions return `409`.

### Phase D: admin module and seed script (Person B scope; same branch)
- `routers/admin.py`: `GET /admin/users` (filters `role`, `is_active`, paginated), `PATCH /admin/users/{id}/status` (body `{ "is_active": bool }`, an admin cannot deactivate themselves), `GET /admin/ngos/pending`, `POST /admin/ngos/{id}/verify` (sets `verification_status` to `VERIFIED` or `REJECTED`, `verified_by` ObjectId of the admin, `verified_at`), `GET /admin/donations` (paginated, filter `status`), `GET /admin/stats` (counts of users by role, donations by status, completed donations per city; use `aggregate`).
- `backend/scripts/seed_admin.py`: asks for admin email and password with `getpass` on the terminal (never from a file), hashes the password, inserts an `ADMIN` user if none exists with that email. Document how to run it.
Done when: only admins reach these routes (`403 FORBIDDEN` otherwise), verifying an NGO lets it accept donations.

### Phase E: automated tests
- `backend/tests/` with pytest, `pytest-asyncio` and `httpx` (`AsyncClient` with `ASGITransport`). Use a separate database named `foodshare_test` by overriding `settings.db_name` in a fixture; never run tests against `foodshare`. Clean the test database before and after each test session.
- Cover: register/login rules, token errors (missing, tampered, expired, deleted user, disabled user), role checks, profile update restrictions (role, email, is_active rejected), donor CRUD and ownership, full lifecycle, concurrent accept, expiry, admin verification and stats.
Done when: `uv run pytest` passes and the test list is documented in `docs/VIVA_NOTES.md`.

### Phase F: CORS and frontend foundation (both)
- Backend: add `CORSMiddleware` with allowed origins from a new setting `cors_origins` (default `http://localhost:5173`), listed in `.env.example`.
- `frontend/`: Vite + React, Tailwind (follow the official Tailwind + Vite install guide; tell me the version), `react-router-dom`, `axios`.
- Structure: `src/api/` (axios instance with base URL from `VITE_API_URL`, one file per resource), `src/context/AuthContext.jsx` (token and current user, login, logout; token kept in `localStorage`; request interceptor adds `Authorization: Bearer`; on `401 TOKEN_INVALID` log out and redirect to login), `src/components/` (Navbar, ProtectedRoute with role check, StatusBadge, Pagination, ErrorMessage, Loading), `src/pages/`, `frontend/.env.example` with `VITE_API_URL=`.
- Show backend `detail` messages to the user; map known codes to friendly text.

### Phase G: frontend pages
Public: Login, Register (role choice; NGO shows organization fields). Donor: dashboard with my donations and status filter, create donation form, edit/cancel. NGO: browse available donations (filters), donation detail with Accept, my accepted donations with buttons for the next valid status only. Admin: users list with activate/deactivate, pending NGOs with approve/reject, all donations, stats cards. Simple, clean, mobile-friendly layout; no extra libraries beyond the approved list.
Done when: a full flow works in the browser: donor creates, admin verifies NGO, NGO accepts and moves it to `COMPLETED`, donor sees every status.

### Phase H: documentation and deployment notes
- Update `docs/FoodShare_Project_Document.md` progress table with real results, finish `docs/VIVA_NOTES.md`, and write run instructions in `README.md` (backend, frontend, tests, seed admin).
- Write `docs/DEPLOYMENT.md` with steps for a free setup (backend on a Python host, frontend on a static host, Atlas IP allowlist, environment variables set in the host's dashboard, strong new `SECRET_KEY`, CORS origin set to the deployed frontend). Do not deploy anything yourself.

## 8. Permissions by phase

- Phases A, B: Person A files only, plus the donation index function in `database.py`.
- Phases C, D: new files for Person B's modules on a separate branch, plus `include_router` lines in `main.py` and the donation index function. Do not edit Person A's files except to fix a bug I approve.
- Phase E: `backend/tests/` only (and a `conftest.py`).
- Phases F, G: `frontend/**` plus the CORS change in `main.py` and `config.py`.
- Phase H: docs and `README.md`.
Always: never touch the files and commands listed in section 4.

## 9. Ask me instead of deciding

Ask before: adding a route, field, collection, status or error code not in the spec; changing any existing behaviour; adding any dependency; choosing between two reasonable designs.

## 10. Definition of done for the project

All endpoints in spec section 7 work and are tested; the full flow runs in the browser; `uv run pytest` passes; no secrets in the repo (`git ls-files` shows no `.env`); `docs/VIVA_NOTES.md` explains every module; README explains how to run everything; every deviation from the spec is listed in `docs/SPEC_CHANGE_REQUESTS.md`.

Start with Phase A. Reply with your plan for it and wait for my approval.
