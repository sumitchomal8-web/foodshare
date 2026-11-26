# Person B Development Log & Architectural Record
**Project:** FoodShare  
**Engineer:** Person B  
**Role Scope:** Donation Lifecycle & Rules, NGO/Volunteer Module, Admin Module, Analytics/Reporting  
**Last Updated:** 2026-11-23

---

## 1. Role Boundaries & Shared Interfaces

### Module Division
* **Person B Modules:**
  1. Donation module (`app/schemas/donation.py`, `app/services/donation_service.py`, `app/routers/donations.py`)
  2. NGO module (`app/routers/ngo.py`, `app/services/ngo_service.py`)
  3. Admin module (`app/schemas/admin.py`, `app/routers/admin.py`, `app/services/admin_service.py`)
  4. Analytics/Reporting (`app/services/stats_service.py`)
* **Person A Modules (Strictly Untouched by B):**
  - Authentication (`routers/auth.py`, `utils/security.py`)
  - User and Profile Management (`routers/users.py`)
  - Donor module (`routers/donor.py` — `POST /donations`, `GET /donations/mine`)
  - Notifications
* **Shared Contract:**
  - Person B consumes Person A's auth dependency (`get_current_user`, `require_role`) per Section 6.1 of the Master Spec.
  - Person B defines and exports `DonationCreate` and `DonationResponse` from `app/schemas/donation.py` for Person A's donor router.
  - `app/database.py` divides index creation cleanly: `create_user_indexes()` (Person A) and `create_donation_indexes()` (Person B).

---

## 2. Step 0: Setup Audit & Fixes

During the initial Step 0 audit, several gaps were identified and resolved:

| Item | Problem Found | Resolution Applied |
|---|---|---|
| **`.gitignore`** | File was 0 bytes; `.env` appeared as untracked in Git status. | Created complete `.gitignore` ignoring `.env`, `__pycache__/`, `.venv/`, `.pytest_cache/`. Verified `.env` is ignored. |
| **`.env.example`** | File was empty. | Populated `.env.example` with standard placeholders (`MONGODB_URL`, `DB_NAME=foodshare`, `SECRET_KEY`). |
| **`app/config.py`** | File was empty. | Implemented Pydantic `BaseSettings` reading environment variables with safe dev defaults. |
| **`app/database.py`** | File was empty. | Implemented Motor client initialization, export of `db`, `client`, `create_user_indexes()`, and `create_donation_indexes()`. |
| **`app/main.py`** | File was empty. | Implemented FastAPI instance with lifespan handler and `/health` route. |
| **`pyproject.toml`** | Pytest lacked Python path configuration. | Added `[tool.pytest.ini_options]` with `pythonpath = ["."]`. |

### Answers to Master Spec Review Questions (Section 6)
1. **Where Motor client and db are created:** `backend/app/database.py`
2. **Where `create_indexes()` is defined:** `backend/app/database.py` (coordinates `create_user_indexes()` and `create_donation_indexes()`)
3. **Where environment variables are read:** `backend/app/config.py` using `pydantic-settings`

---

## 3. MongoDB Document Design & Indexing

### Document Design for `donations`
* **Referencing (`donor_id`, `accepted_by`):** Stored as `ObjectId`. Avoids data duplication and keeps user profile updates decoupled from past donations.
* **Point-in-Time Embedding (`pickup_address`):** Embedded subdocument `{ street, city, state, pincode }`. Crucial so future donor address changes do not alter historic pickup locations.
* **Bounded Audit History (`status_history`):** Embedded array of `[{ status, changed_by, changed_at }]`. Max 5–6 transitions in lifecycle; guarantees fast single-roundtrip detail fetches without `$lookup`.

### Indexing Strategy (`create_donation_indexes`)
```python
IndexModel([("donor_id", ASCENDING)])
IndexModel([("accepted_by", ASCENDING)])
IndexModel([("status", ASCENDING), ("expires_at", ASCENDING)])
IndexModel([("pickup_address.city", ASCENDING), ("status", ASCENDING)])
```
* **ESR Rule Applied:** Compound index `(status, expires_at)` places Equality field first (`status="AVAILABLE"`), then Range field (`expires_at > now`).
* **Location Filtering:** Compound index `(pickup_address.city, status)` accelerates localized searches for NGOs.

---

## 4. Donation Status State Machine & Transition Rules

### Valid State Transitions
```
                 ┌─────────────► CANCELLED (by Donor while AVAILABLE or ADMIN)
                 │
AVAILABLE ───────┼─────────────► EXPIRED (System / On-Read when expires_at passed)
                 │
                 └─────────────► ACCEPTED (by Verified NGO, atomic)
                                     │
                                     ▼
                                 PICKED_UP (by assigned NGO)
                                     │
                                     ▼
                                DISTRIBUTED (by assigned NGO)
                                     │
                                     ▼
                                 COMPLETED (by assigned NGO or ADMIN)
```

### Authorization & Guard Matrix
* **`-> ACCEPTED`:** Only active NGOs with `ngo_profile.verification_status == "VERIFIED"`. Donation must not be expired (`expires_at > now`).
* **`-> PICKED_UP`:** Only the assigned NGO (`actor._id == donation.accepted_by`).
* **`-> DISTRIBUTED`:** Only the assigned NGO (`actor._id == donation.accepted_by`).
* **`-> COMPLETED`:** Assigned NGO or platform `ADMIN`.
* **`-> CANCELLED`:** Owner donor (`actor._id == donation.donor_id`) while `status == AVAILABLE`, or platform `ADMIN`.
* **Any Invalid Jump:** Raises `409 INVALID_STATUS_TRANSITION`.
* **Permission Violations:** Raise `403 FORBIDDEN` or `403 NGO_NOT_VERIFIED`.

---

## 5. Implementation Files

### 5.1 `app/schemas/donation.py`
* Enums: `FoodType`, `QuantityUnit`, `DonationStatus`.
* Sub-schemas: `AddressSchema`, `StatusHistoryEntry`.
* Requests: `DonationCreate`, `DonationUpdate`.
* Responses: `DonationResponse`, `PaginatedDonationsResponse`.

### 5.2 `app/services/donation_service.py`
* **Exception Mapping:** Implemented `FoodShareAPIException` matching Section 8 format `{ "detail": "...", "code": "..." }`.
* **Validation Engine:** `validate_status_transition` and `apply_status_transition` in-memory state transition applicator.
* **Database Operations (Motor Async):**
  - `accept_donation`: First-accept-wins atomic conditional update on `status=AVAILABLE` and `expires_at > now`.
  - `transition_donation_status`: Atomic status prerequisite validation and update (`PICKED_UP`, `DISTRIBUTED`, `COMPLETED`, `CANCELLED`).
  - `get_donation_detail`: Role-based access enforcement (owner donor, assigned NGO, admin, or NGO for available).
  - `list_donations`: Paginated filtering for NGOs/Admins with automatic unexpired filtering.
  - `list_ngo_donations`: Filtered query for NGO's claimed donations.
  - `serialize_donation`: Converts ObjectIds and dates to standard API JSON response structures.

---

## 6. Test Suite & Verification Results

**Test File:** `backend/tests/test_donation_service.py`  
**Execution Command:** `uv run pytest tests/test_donation_service.py -v`  
**Result:** **18 passed in 0.80s.**

### Test Coverage Summary
1. `test_full_lifecycle_happy_path`: Validates complete chain `AVAILABLE` -> `ACCEPTED` -> `PICKED_UP` -> `DISTRIBUTED` -> `COMPLETED`.
2. `test_donor_can_cancel_own_available_donation`: Verifies donor cancellation while `AVAILABLE`.
3. `test_admin_can_cancel_available_donation`: Verifies admin cancellation.
4. `test_donor_cannot_cancel_other_donor_donation`: Verifies 403 when wrong donor attempts cancellation.
5. `test_donor_cannot_cancel_accepted_donation`: Verifies 409 when cancelling once accepted.
6. `test_invalid_transition_jumps_rejected`: Verifies 409 on invalid skip (`AVAILABLE` -> `PICKED_UP`).
7. `test_terminal_states_cannot_transition`: Verifies 409 attempting to transition from `COMPLETED`.
8. `test_unverified_ngo_cannot_accept`: Verifies 403 `NGO_NOT_VERIFIED` for unverified NGOs.
9. `test_donor_cannot_accept_donation`: Verifies 403 `FORBIDDEN` when donor role attempts acceptance.
10. `test_inactive_ngo_cannot_accept`: Verifies 403 `ACCOUNT_DISABLED` for deactivated users.
11. `test_other_ngo_cannot_update_assigned_donation`: Verifies 403 `FORBIDDEN` when NGO B updates NGO A's pickup.
12. `test_cannot_accept_expired_donation`: Verifies 409 rejection when donation has expired.
13. `test_accept_donation_db_success`: Verifies atomic `find_one_and_update` DB query, setting `accepted_by` and history.
14. `test_accept_donation_db_already_accepted_raises_409`: Verifies `409 ALREADY_ACCEPTED` on race condition / duplicate accept.
15. `test_accept_donation_db_expired_raises_409`: Verifies `409 INVALID_STATUS_TRANSITION` when attempting to accept past expiry.
16. `test_transition_donation_status_db_flow`: Verifies DB update for `PICKED_UP` status with timestamp setting.
17. `test_get_donation_detail_access_control`: Verifies role-based visibility matrix (Admin, Owner Donor, Assigned NGO, Non-assigned NGO).
18. `test_list_donations_filters_and_pagination`: Verifies query filtering by city/food_type and pagination envelope.

---

## 7. HTTP Routers Implemented

### 7.1 `app/utils/dependencies.py` (Stub — awaiting Person A)
Defines the agreed auth contract (`get_current_user`, `require_role`). Currently raises `HTTP 503 AUTH_NOT_IMPLEMENTED` on every protected route. Person A replaces this file with real JWT decode + DB lookup on `feature/auth`.

### 7.2 `app/routers/donations.py`

| Method | Route | Access | Calls |
|---|---|---|---|
| `GET` | `/api/v1/donations` | `NGO`, `ADMIN` | `list_donations()` |
| `GET` | `/api/v1/donations/{id}` | Access-controlled | `get_donation_detail()` |
| `POST` | `/api/v1/donations/{id}/accept` | `NGO` | `accept_donation()` |
| `POST` | `/api/v1/donations/{id}/pickup` | `NGO` | `transition_donation_status(PICKED_UP)` |
| `POST` | `/api/v1/donations/{id}/distribute` | `NGO` | `transition_donation_status(DISTRIBUTED)` |
| `POST` | `/api/v1/donations/{id}/complete` | `NGO`, `ADMIN` | `transition_donation_status(COMPLETED)` |

**Route order note:** `GET /donations/mine` (Person A's donor.py) must be included in `main.py` BEFORE this router to prevent FastAPI parsing `"mine"` as a `{donation_id}` parameter.

### 7.3 `app/routers/ngo.py`

| Method | Route | Access | Calls |
|---|---|---|---|
| `GET` | `/api/v1/ngo/donations` | `NGO` | `list_ngo_donations()` |

### 7.4 `app/main.py` — Updated
- Added lifespan `create_indexes()` call on startup.
- Registered `app.include_router(donations.router)` and `app.include_router(ngo.router)`.
- Added global `HTTPException` handler to pass `{detail, code}` bodies through cleanly.
- Person A's routers stubbed out as comments for easy merge.

---

## 8. Test Suite Summary — All Tests

**Command:** `uv run pytest tests/ -v`  
**Result:** **34 passed in 1.19s.**

| Test File | Tests | Result |
|---|---|---|
| `test_donation_service.py` | 18 | ✅ All passed |
| `test_donations_api.py` | 16 | ✅ All passed |

### API Test Coverage (`test_donations_api.py`)
Tests use FastAPI `dependency_overrides` for auth and `unittest.mock.patch` for service calls — no live DB needed.

1. `test_browse_donations_as_ngo_returns_200`
2. `test_browse_donations_as_admin_returns_200`
3. `test_get_donation_detail_success`
4. `test_get_donation_detail_not_found_returns_404`
5. `test_get_donation_detail_forbidden_returns_403`
6. `test_accept_donation_success_returns_200`
7. `test_accept_donation_already_accepted_returns_409`
8. `test_accept_donation_unverified_ngo_returns_403`
9. `test_pickup_success`
10. `test_distribute_success`
11. `test_complete_success_as_ngo`
12. `test_complete_success_as_admin`
13. `test_wrong_ngo_pickup_returns_403`
14. `test_invalid_transition_returns_409`
15. `test_ngo_list_own_donations`
16. `test_ngo_list_filtered_by_status`

---

## 10. Admin Module

### 10.1 `app/schemas/admin.py`
* `UserAdminResponse`, `PaginatedUsersResponse` — user list responses (strips `password_hash`).
* `UserStatusUpdate` — `{ is_active: bool }` for PATCH.
* `NgoVerificationRequest` — `{ approve: bool }` for POST verify.
* `PlatformStats`, `DonationStats` — analytics response shapes.

### 10.2 `app/services/admin_service.py`
| Function | Purpose |
|---|---|
| `list_users` | Paginated user list, filtered by role and/or is_active |
| `set_user_active` | Activate / deactivate any user account |
| `list_pending_ngos` | NGOs with `verification_status=PENDING`, oldest-first |
| `verify_ngo` | Sets `VERIFIED` or `REJECTED`, stamps `verified_by` and `verified_at` |
| `admin_list_donations` | All donations across all statuses with optional filters |

### 10.3 `app/services/stats_service.py`
* `get_platform_stats`: Runs 6 count queries and 1 aggregation pipeline **concurrently** via `asyncio.gather` — single round-trip to MongoDB.
* `_aggregate_donation_counts`: `$group` by status, returns dict with `total` + per-status counts.

### 10.4 `app/routers/admin.py`

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/v1/admin/users` | Paginated users, filter by role/is_active |
| `PATCH` | `/api/v1/admin/users/{id}/status` | Activate/deactivate |
| `GET` | `/api/v1/admin/ngos/pending` | Pending verification queue |
| `POST` | `/api/v1/admin/ngos/{id}/verify` | Approve / reject NGO |
| `GET` | `/api/v1/admin/donations` | All donations, any status |
| `GET` | `/api/v1/admin/stats` | Platform analytics |

---

## 11. Full Route Table (Person B)

```
GET    /health
GET    /api/v1/donations
GET    /api/v1/donations/{donation_id}
POST   /api/v1/donations/{donation_id}/accept
POST   /api/v1/donations/{donation_id}/pickup
POST   /api/v1/donations/{donation_id}/distribute
POST   /api/v1/donations/{donation_id}/complete
GET    /api/v1/ngo/donations
GET    /api/v1/admin/users
PATCH  /api/v1/admin/users/{user_id}/status
GET    /api/v1/admin/ngos/pending
POST   /api/v1/admin/ngos/{user_id}/verify
GET    /api/v1/admin/donations
GET    /api/v1/admin/stats
```

---

## 12. Complete Test Results

**Command:** `uv run pytest tests/ -v`  
**Result:** **49 passed in 1.28s.**

| Test File | Tests | Result |
|---|---|---|
| `test_donation_service.py` | 18 | ✅ All passed |
| `test_donations_api.py` | 16 | ✅ All passed |
| `test_admin_api.py` | 15 | ✅ All passed |

### Admin API Test Coverage (`test_admin_api.py`)
1. `test_admin_list_users_returns_200`
2. `test_admin_list_users_with_role_filter` — asserts service called with correct kwargs
3. `test_non_admin_cannot_list_users` — 403 for NGO role
4. `test_admin_deactivate_user`
5. `test_admin_activate_user`
6. `test_admin_status_user_not_found_returns_404`
7. `test_admin_list_pending_ngos`
8. `test_admin_pending_ngos_empty`
9. `test_admin_approve_ngo` — response shows `VERIFIED`
10. `test_admin_reject_ngo` — response shows `REJECTED`
11. `test_admin_verify_ngo_not_found_returns_404`
12. `test_admin_list_all_donations`
13. `test_admin_list_donations_with_filters`
14. `test_admin_stats_returns_platform_data`
15. `test_admin_stats_non_admin_forbidden`

---

## 13. NGO Service & End-to-End Router Integration

### 13.1 `app/services/ngo_service.py`
Implemented verification rules and status checks:
* `is_ngo_verified(user)`: Returns boolean checking role = `NGO`, active account, and `ngo_profile.verification_status == "VERIFIED"`.
* `assert_ngo_verified(user)`: Raises `403 ACCOUNT_DISABLED`, `403 FORBIDDEN`, or `403 NGO_NOT_VERIFIED` with proper code/detail.

### 13.2 Full Router Registration in `app/main.py`
Registered all routers following strict path precedence:
1. `auth.router` (`/api/v1/auth`)
2. `users.router` (`/api/v1/users`)
3. `donor.router` (`/api/v1/donations`) — **registered BEFORE `donations.router`** so that `GET /api/v1/donations/mine` is matched before `GET /api/v1/donations/{id}`.
4. `donations.router` (`/api/v1/donations`)
5. `ngo.router` (`/api/v1/ngo`)
6. `admin.router` (`/api/v1/admin`)

---

## 14. Full OpenAPI Route Table (19 Endpoints, 22 Operations)

| Method | Path | Description / Role |
|---|---|---|
| `GET` | `/health` | DB connection and health check |
| `POST` | `/api/v1/auth/register` | User registration (DONOR, NGO) |
| `POST` | `/api/v1/auth/login` | JWT login |
| `GET` | `/api/v1/users/me` | Current user profile |
| `PUT` | `/api/v1/users/me` | Update current user profile |
| `POST` | `/api/v1/donations` | Create donation (DONOR) |
| `GET` | `/api/v1/donations/mine` | Donor's own donations list |
| `GET` | `/api/v1/donations` | Browse available donations (NGO, ADMIN) |
| `GET` | `/api/v1/donations/{id}` | Donation detail view (access controlled) |
| `PUT` | `/api/v1/donations/{id}` | Edit donation (Owner DONOR, AVAILABLE only) |
| `POST` | `/api/v1/donations/{id}/cancel` | Cancel donation (Owner DONOR, ADMIN) |
| `POST` | `/api/v1/donations/{id}/accept` | Accept donation (Verified NGO) |
| `POST` | `/api/v1/donations/{id}/pickup` | Mark picked up (Assigned NGO) |
| `POST` | `/api/v1/donations/{id}/distribute` | Mark distributed (Assigned NGO) |
| `POST` | `/api/v1/donations/{id}/complete` | Mark completed (Assigned NGO, ADMIN) |
| `GET` | `/api/v1/ngo/donations` | NGO accepted donations list |
| `GET` | `/api/v1/admin/users` | List users with role / active filters |
| `PATCH` | `/api/v1/admin/users/{id}/status` | Activate / deactivate user |
| `GET` | `/api/v1/admin/ngos/pending` | List pending NGO verifications |
| `POST` | `/api/v1/admin/ngos/{id}/verify` | Approve or reject NGO verification |
| `GET` | `/api/v1/admin/donations` | Admin view of all donations |
| `GET` | `/api/v1/admin/stats` | Platform statistics |

---

## 15. Complete Test Suite Execution

**Command:** `uv run pytest tests/ -v`  
**Result:** **62 passed in 3.24s.**

| Test File | Tests | Coverage | Result |
|---|---|---|---|
| `test_donation_service.py` | 18 | Full lifecycle state machine, validation rules, DB operations | ✅ Passed |
| `test_donations_api.py` | 16 | Donation & NGO routes, transitions, filters | ✅ Passed |
| `test_admin_api.py` | 15 | Admin user management, verification, stats | ✅ Passed |
| `test_auth_donor_api.py` | 13 | Auth register/login, users/me, donor routes, NGO rules | ✅ Passed |
| **Total** | **62** | **Full system coverage** | **100% Passed** |

---

## 16. Database Seed Script & Project Documentation

### 16.1 Seed Script (`backend/scripts/seed.py`)
Per Section 2 of the Master Spec (*"Admin accounts are created manually in the database (seed script), never through public registration"*):
* Calls `create_indexes()` for users and donations collections.
* Provisions `admin@foodshare.org` with role `ADMIN`.
* Provisions demo verified NGO `feedindia@ngo.org` with `verification_status: VERIFIED`.
* Provisions demo pending NGO `hope@volunteer.org` with `verification_status: PENDING` for admin verification testing.
* Provisions demo donor `taj_caterers@donor.org` and a sample active `AVAILABLE` donation.

### 16.2 Documentation
* Created [`backend/README.md`](file:///c:/foodshare/backend/README.md) with complete setup, env guide, route references, seed instructions, and test commands.
* Created root [`README.md`](file:///c:/foodshare/README.md) outlining repository architecture.
