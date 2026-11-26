# FoodShare – Master Specification

**Version:** 1.0
**Date:** 2026-11-26
**Rule:** This file is the single source of truth. No one changes a name, route, field or status in code before it is changed here and both partners agree. After every change: update the version and change log, commit, and paste the new version into both AI chats.

---

## 0. Project status

| Phase | State |
|---|---|
| Planning and spec | Completed |
| Phase 1: project setup, MongoDB connection, `/health`, indexes | Done (`feature/setup`) |
| Phase 2: password hashing and JWT helpers (`utils/security.py`) | Done (`feature/auth`) |
| Phase 3: register / login / user routes | Done (`feature/auth`) |
| Phase 4: Donor module | Done (`feature/donor`) |
| Phase 5: Donation lifecycle module | Done (`feature/donations`) |
| Phase 6: NGO / Volunteer module | Done (`feature/ngo`) |
| Phase 7: Admin & Analytics modules | Done (`feature/admin`) |
| Phase 8: Frontend (React + Vite + Tailwind CSS) | Done (`feature/frontend`) |
| Phase 9: Docker & Containerization | Done |

---

## 1. Overview

FoodShare connects food donors with NGOs/volunteers who collect and distribute surplus food. An admin verifies NGOs and oversees the platform.

**Stack (frozen):** React + Tailwind (frontend, built later) · Python 3.12 + FastAPI · MongoDB Atlas (Motor, async driver) · JWT (python-jose) + bcrypt (passlib) · REST · Git + GitHub

**Tooling:** `uv` manages the Python environment and packages (`pyproject.toml` and `uv.lock` are committed; there is no `requirements.txt`). Always run commands from `backend/` with `uv run`, for example:

```
uv run uvicorn app.main:app --reload
```

**Out of scope for v1:** maps, QR codes, AI/ML, real-time notifications, payments, image upload.

---

## 2. Roles

| Role value | Who | Can do |
|---|---|---|
| `DONOR` | Individuals, restaurants, events | Create / edit / cancel own donations, view own history |
| `NGO` | NGOs and volunteers | Browse available donations, accept, update pickup/distribution, view own completed |
| `ADMIN` | Platform admin | Manage users and donations, verify NGOs, view statistics |

Admin accounts are created manually in the database (seed script), never through public registration.

---

## 3. Naming conventions

- Collections: plural, `snake_case` (`users`, `donations`)
- Fields: `snake_case`
- Enum values: `UPPER_CASE`
- References to other documents: `<thing>_id`, stored as MongoDB `ObjectId` (e.g. `donor_id`)
- Timestamps: UTC, field names end in `_at`
- API JSON returns `id` (string) instead of `_id`
- API base path: `/api/v1`
- Database name: `foodshare` (lowercase; database names are case-sensitive, so both partners must use exactly this in `.env`)

---

## 4. Database schema

### 4.1 `users`

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | auto | |
| `name` | string | yes | Person name |
| `email` | string | yes | Unique, stored lowercase |
| `password_hash` | string | yes | bcrypt hash, never returned by API |
| `role` | enum | yes | `DONOR` / `NGO` / `ADMIN` |
| `phone` | string | yes | |
| `address` | object | yes | `{ street, city, state, pincode }` |
| `ngo_profile` | object / null | only if role = `NGO` | See below |
| `is_active` | bool | yes | Default `true`; admin can deactivate |
| `created_at` | datetime | auto | |
| `updated_at` | datetime | auto | |

`ngo_profile`:

| Field | Type | Notes |
|---|---|---|
| `organization_name` | string | |
| `org_type` | enum | `NGO` / `VOLUNTEER` |
| `registration_number` | string / null | Required when `org_type` = `NGO` |
| `verification_status` | enum | `PENDING` (default) / `VERIFIED` / `REJECTED` |
| `verified_by` | ObjectId / null | Admin user id |
| `verified_at` | datetime / null | |

### 4.2 `donations`

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | auto | |
| `donor_id` | ObjectId | yes | Ref `users._id` |
| `title` | string | yes | Short label, e.g. "Veg biryani, 30 plates" |
| `food_type` | enum | yes | `COOKED` / `PACKAGED` / `RAW` / `BAKERY` / `OTHER` |
| `quantity` | number | yes | > 0 |
| `quantity_unit` | enum | yes | `PLATES` / `KG` / `PACKETS` / `ITEMS` |
| `description` | string | no | |
| `pickup_address` | object | yes | `{ street, city, state, pincode }` |
| `available_from` | datetime | yes | |
| `expires_at` | datetime | yes | After this, an unaccepted donation becomes `EXPIRED` |
| `status` | enum | yes | See section 5 |
| `accepted_by` | ObjectId / null | | Ref `users._id` (NGO) |
| `accepted_at` / `picked_up_at` / `distributed_at` / `completed_at` / `cancelled_at` | datetime / null | | Set when status changes |
| `status_history` | array | yes | `[{ status, changed_by, changed_at }]`, appended on every change |
| `created_at` / `updated_at` | datetime | auto | |

### 4.3 Relationships

```
users (DONOR) 1 ───< donations >─── 0..1 users (NGO)
                 donor_id          accepted_by
users (ADMIN) 1 ───< users.ngo_profile.verified_by
```

### 4.4 Indexes

| Collection | Index | Why | Created by |
|---|---|---|---|
| `users` | `email` (unique) | Login, duplicate prevention | A (done) |
| `users` | `role` | Admin listing by role | A (done) |
| `donations` | `donor_id` | Donor's own list | B |
| `donations` | `accepted_by` | NGO's accepted/completed list | B |
| `donations` | `status`, `expires_at` | Browse available, expiry check | B |
| `donations` | `pickup_address.city`, `status` | Filter available by city | B |

Convention: all indexes are created in `app/database.py`. Person A owns `create_user_indexes()` and Person B owns `create_donation_indexes()`; `create_indexes()` calls both. This keeps your edits in separate functions and avoids merge conflicts.

---

## 5. Donation status lifecycle (frozen)

```
AVAILABLE -> ACCEPTED -> PICKED_UP -> DISTRIBUTED -> COMPLETED
AVAILABLE -> CANCELLED
AVAILABLE -> EXPIRED
```

| From | To | Who triggers | Rule |
|---|---|---|---|
| `AVAILABLE` | `ACCEPTED` | `NGO` | NGO must be `VERIFIED` and active. Sets `accepted_by`. First accept wins (atomic update filtered on `status = AVAILABLE`). |
| `ACCEPTED` | `PICKED_UP` | the NGO in `accepted_by` | |
| `PICKED_UP` | `DISTRIBUTED` | the NGO in `accepted_by` | |
| `DISTRIBUTED` | `COMPLETED` | the NGO in `accepted_by` (or `ADMIN`) | |
| `AVAILABLE` | `CANCELLED` | the donor who owns it (or `ADMIN`) | Only while still `AVAILABLE` |
| `AVAILABLE` | `EXPIRED` | system | When `expires_at` has passed. Checked when listing/fetching (no background job in v1). |

Any other transition returns `409 INVALID_STATUS_TRANSITION`. Donors may edit a donation only while `AVAILABLE`.

---

## 6. Authentication & authorization

- Passwords: bcrypt via passlib, minimum 8 characters.
- Login returns a JWT access token: algorithm `HS256`, expiry 60 minutes, payload `{ sub: <user id as string>, role: <role>, exp }`. Never put a password or hash in the payload.
- Clients send `Authorization: Bearer <token>`.
- Secrets (`MONGODB_URL`, `DB_NAME`, `SECRET_KEY`) live in `backend/.env`, never committed. `backend/.env.example` holds placeholders only.
- Unverified NGOs can log in and browse but cannot accept donations.
- Deactivated users (`is_active = false`) get `403 ACCOUNT_DISABLED` on login.

### 6.1 Shared interfaces (Person A builds, everyone uses)

These are the contract Person B can code against now.

**`app/utils/security.py` (done)**

| Function | Signature | Purpose |
|---|---|---|
| `hash_password` | `(password: str) -> str` | bcrypt hash |
| `verify_password` | `(plain_password: str, password_hash: str) -> bool` | Compare |
| `create_access_token` | `(user_id: str, role: str) -> str` | Signed JWT |
| `decode_access_token` | `(token: str) -> dict` | Returns payload; raises `JWTError` if invalid or expired |

**`app/utils/dependencies.py` (in progress)**

| Name | Behaviour |
|---|---|
| `get_current_user()` | FastAPI dependency. Reads the Bearer token, decodes it, loads the user from `users`, and returns the user document as a dict (with `_id` as ObjectId). Errors: `401 TOKEN_INVALID`, `403 ACCOUNT_DISABLED`. |
| `require_role(*roles)` | Dependency factory. Usage: `Depends(require_role("NGO"))`. Returns the user document, or `403 FORBIDDEN` if the role isn't allowed. |

**`app/database.py`**: exports `db` (the Motor database) and `client`. Routers and services import `db` from here and never create their own client.

---

## 7. API endpoints (v1)

Owner: **A** = Person A, **B** = Person B.

### Auth & users

| Method | Route | Access | Owner |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public (role `DONOR` or `NGO` only) | A |
| POST | `/api/v1/auth/login` | Public | A |
| GET | `/api/v1/users/me` | Any logged-in | A |
| PUT | `/api/v1/users/me` | Any logged-in | A |

**Register request body:**

```json
{
  "name": "string",
  "email": "user@example.com",
  "password": "min 8 chars",
  "phone": "string",
  "role": "DONOR | NGO",
  "address": { "street": "", "city": "", "state": "", "pincode": "" },
  "ngo_profile": { "organization_name": "", "org_type": "NGO | VOLUNTEER", "registration_number": "" }
}
```

`ngo_profile` is required when `role` is `NGO` and must be absent for `DONOR`. The server sets `verification_status` to `PENDING`. Response: `201` with the user object (`id`, `name`, `email`, `role`, `phone`, `address`, `ngo_profile`, `is_active`, `created_at`), never the password or hash.

**Login request body:** `{ "email": "...", "password": "..." }` (JSON). Response: `{ "access_token": "...", "token_type": "bearer" }`.

### Donor

| Method | Route | Access | Owner |
|---|---|---|---|
| POST | `/api/v1/donations` | `DONOR` | A |
| GET | `/api/v1/donations/mine` | `DONOR` | A |
| PUT | `/api/v1/donations/{id}` | `DONOR` (owner, `AVAILABLE` only) | A |
| POST | `/api/v1/donations/{id}/cancel` | `DONOR` (owner) | A |

### Donations & NGO

| Method | Route | Access | Owner |
|---|---|---|---|
| GET | `/api/v1/donations` | `NGO`, `ADMIN` (filters: `status`, `city`, `food_type`) | B |
| GET | `/api/v1/donations/{id}` | Owner donor, assigned NGO, `ADMIN`; `NGO` for `AVAILABLE` | B |
| POST | `/api/v1/donations/{id}/accept` | `NGO` (verified) | B |
| POST | `/api/v1/donations/{id}/pickup` | `NGO` (assigned) | B |
| POST | `/api/v1/donations/{id}/distribute` | `NGO` (assigned) | B |
| POST | `/api/v1/donations/{id}/complete` | `NGO` (assigned) | B |
| GET | `/api/v1/ngo/donations` | `NGO` (accepted by me, filter by `status`) | B |

### Admin

| Method | Route | Access | Owner |
|---|---|---|---|
| GET | `/api/v1/admin/users` | `ADMIN` (filter: `role`, `is_active`) | B |
| PATCH | `/api/v1/admin/users/{id}/status` | `ADMIN` (activate / deactivate) | B |
| GET | `/api/v1/admin/ngos/pending` | `ADMIN` | B |
| POST | `/api/v1/admin/ngos/{id}/verify` | `ADMIN` (body: `approve: true/false`) | B |
| GET | `/api/v1/admin/donations` | `ADMIN` | B |
| GET | `/api/v1/admin/stats` | `ADMIN` | B |

Note: `POST /donations` (create) and `GET /donations/mine` are donor routes owned by A; `GET /donations` (browse) is owned by B. They share the `/donations` prefix but live in different router files (`donor.py` and `donations.py`). Register `/donations/mine` before `/donations/{id}`, otherwise `mine` is read as an id.

---

## 8. Request/response and error rules

- All bodies are JSON. Dates are ISO 8601 UTC strings.
- List endpoints accept `page` (default 1) and `limit` (default 20, max 100) and return `{ items: [...], total, page, limit }`.
- Errors always use this shape:

```json
{ "detail": "Human readable message", "code": "ERROR_CODE" }
```

| HTTP | Code | When |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Bad input |
| 401 | `INVALID_CREDENTIALS` / `TOKEN_INVALID` | Wrong login or bad/expired token |
| 403 | `FORBIDDEN` / `ACCOUNT_DISABLED` / `NGO_NOT_VERIFIED` | Wrong role, disabled account, unverified NGO |
| 404 | `NOT_FOUND` | Missing resource |
| 409 | `EMAIL_EXISTS` / `INVALID_STATUS_TRANSITION` / `ALREADY_ACCEPTED` | Conflicts |

---

## 9. Folder structure

```
foodshare/
  .gitignore
  README.md
  docs/
    master_spec.md
  frontend/
  backend/
    .env                 # real secrets, never committed
    .env.example         # placeholders, committed
    .python-version
    pyproject.toml
    uv.lock
    README.md
    app/
      main.py
      config.py
      database.py
      models/
      schemas/           # user.py, donation.py, ...
      routers/           # auth.py, users.py, donor.py, donations.py, ngo.py, admin.py
      services/          # business logic (status transitions live here)
      utils/             # security.py, dependencies.py
    tests/
```

---

## 10. Git workflow

- `main` always runs. Never commit directly to it.
- One branch per module: `feature/setup`, `feature/auth`, `feature/donor`, `feature/donations`, `feature/ngo`, `feature/admin`.
- Small commits, each a single step, with a clear message starting with a verb ("Add", "Fix", "Update"). No angle brackets or placeholders in messages.
- Stage files by name (`git add <file>`), not `git add .`. Run `git status` before every commit.
- Merge through pull requests; your partner reviews before merging.
- `.env` is in `.gitignore`. Commit `.env.example` only. If a secret is ever committed, rotate it immediately.

---

## 11. Ownership summary

| Person A | Person B | Both |
|---|---|---|
| Auth, user/profile, donor module, notifications (last) | Donation lifecycle, NGO module, admin, analytics | Schema, API contract, integration, testing, deployment |

---

## 12. Local setup (each person)

1. Clone the repo, then `cd backend`.
2. Run `uv sync` to install the packages from `uv.lock`.
3. Copy `.env.example` to `.env` and fill in your own values (`MONGODB_URL`, `DB_NAME=foodshare`, a random `SECRET_KEY`). Never share `.env` in chat or commit it.
4. In MongoDB Atlas, add your current IP under Network Access (or share one cluster with separate database users, see section 13).
5. Run `uv run uvicorn app.main:app --reload`, then open `http://127.0.0.1:8000/docs` and call `/health`.

Generate a secret key with: `uv run python -c "import secrets; print(secrets.token_hex(32))"`

---

## 13. Open decisions (resolved & implemented)

1. **NGO and VOLUNTEER:** Resolved as single `NGO` role with `ngo_profile.org_type: NGO | VOLUNTEER`.
2. **Verification gate:** Resolved as yes — NGO must have `verification_status: VERIFIED` to accept donations.
3. **Expiry handling:** Resolved as lazy expiry on read (if `expires_at < utcnow` and status is `AVAILABLE`, marked `EXPIRED`).
4. **Delivery:** Resolved as NGO pickup lifecycle (`AVAILABLE -> ACCEPTED -> PICKED_UP -> DISTRIBUTED -> COMPLETED`).
5. **Atlas setup:** Database name `foodshare`; configurable via `MONGODB_URL` with local MongoDB Docker option.
6. **Database name:** `foodshare` (lowercase).
7. **Tooling:** `uv` for Python backend, `npm` + `vite` for React frontend.
8. **NGO registration:** `ngo_profile` required for `role = NGO` and prohibited for `DONOR`.

---

## 14. Change log

| Date | Version | Change | Agreed by |
|---|---|---|---|
| 2026-10-08 | 0.1 | Initial draft | |
| 2026-10-19 | 0.2 | Switched tooling to uv; set database name `foodshare`; added project status, shared interfaces (section 6.1), register/login bodies, local setup, index ownership; expanded open decisions | |
| 2026-11-26 | 1.0 | Full backend implementation (donations, NGO, admin, auth, donor), 62 unit/API tests, React frontend (Vite + Tailwind), Docker containerization, and resolved all open decisions | Person A & B |
