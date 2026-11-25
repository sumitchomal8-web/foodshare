# FoodShare – Viva Notes

## Phase A: Core Setup, Authentication & User Profile

### 1. `app/utils/security.py` & `app/utils/errors.py`
- **Purpose**: Password hashing/verification (bcrypt via `passlib`), JWT creation/decoding (`python-jose`), and standardized application errors (`AppError`).
- **Main Flow**:
  - `hash_password` / `verify_password`: Hash plain passwords with bcrypt (`$2b$`) and verify them at login.
  - `create_access_token` / `decode_access_token`: Sign HS256 JWTs containing `sub` (user ID), `role`, and `exp` (60 minutes).
  - `AppError`: Carries `status_code`, `detail`, and `code`, caught by FastAPI's global exception handler in `main.py` to return `{ "detail": ..., "code": ... }`.
- **Key Decisions**:
  - Password length is capped at 72 characters in schemas because bcrypt silently truncates inputs past 72 bytes.
  - Using `AppError` instead of bare `HTTPException` guarantees every error response includes a machine-readable `code`.
- **Likely Examiner Questions**:
  1. *Why use bcrypt instead of SHA-256 for passwords?*
     Bcrypt is intentionally slow and includes a built-in random salt per password, making brute-force and rainbow-table attacks much harder than fast hashes like SHA-256.
  2. *What is inside the JWT payload and why not put the password or full profile in it?*
     Only `sub` (user ID), `role`, and `exp`. JWTs are base64-encoded (not encrypted), so anyone can decode them; keeping them minimal avoids leaking sensitive data and keeps token size small.
  3. *Why use a custom `AppError` class instead of FastAPI's `HTTPException`?*
     It enforces a consistent `{ "detail": "...", "code": "..." }` JSON contract across the entire API so the frontend can handle errors reliably by `code`.

---

### 2. `app/utils/dependencies.py` (`get_current_user` & `require_role`)
- **Purpose**: FastAPI dependencies for authenticating Bearer JWT tokens and enforcing role-based access control (RBAC).
- **Main Flow**:
  - `get_current_user`: Extracts the Bearer token -> decodes JWT -> converts `sub` to `ObjectId` -> queries `db.users` -> checks `is_active` -> returns the full user document.
  - `require_role(*allowed_roles)`: Wraps `get_current_user` and raises `403 FORBIDDEN` if `user["role"]` is not in `allowed_roles`.
- **Key Decisions**:
  - Loading the user from MongoDB on every protected request (instead of trusting the JWT blindly) ensures deleted or deactivated (`is_active: false`) users are immediately blocked.
  - `HTTPBearer(auto_error=False)` is used so missing tokens return our standard `401 TOKEN_INVALID` instead of FastAPI's default `403`.
- **Likely Examiner Questions**:
  1. *If JWTs are stateless, why does `get_current_user` query the database?*
     To enforce immediate revocation when an admin disables an account (`is_active = false`) or a user is deleted—otherwise an old valid token would keep working until it expires.
  2. *What happens if someone passes a malformed `sub` in a token?*
     `ObjectId(sub)` raises `InvalidId`, which is caught alongside `JWTError` and returns `401 TOKEN_INVALID` instead of a 500 error.
  3. *How does `require_role("NGO")` work under the hood?*
     It is a dependency factory: it returns an inner `async def` function (`role_checker`) that depends on `get_current_user`, checks `current_user["role"]`, and raises `403 FORBIDDEN` if unauthorized.

---

### 3. `app/schemas/user.py`
- **Purpose**: Pydantic v2 validation and serialization models for registration, login, profile updates, and user responses.
- **Main Flow**:
  - Input models (`Address`, `NgoProfileIn`, `UserRegister`, `UserLogin`, `UserUpdate`) validate types, string lengths (`min_length=1`, `max_length=72` on password), 6-digit pincode (`^\d{6}$`), and cross-field rules (`model_validator`).
  - Output models (`UserResponse`, `NgoProfileOut`) shape API responses and omit `password_hash`.
- **Key Decisions**:
  - `extra="forbid"` is set on **input** schemas so clients cannot sneak in privileged fields like `role`, `is_active`, or `verification_status` (`422` rejected).
  - `extra="forbid"` is **not** set on **response** schemas so internal DB fields like `password_hash` or future audit fields are safely ignored rather than causing a `500`.
- **Likely Examiner Questions**:
  1. *Why put `extra="forbid"` on input schemas but not on response schemas?*
     Input schemas must reject unexpected fields to prevent privilege escalation; response schemas read full MongoDB documents that contain extra internal fields (`password_hash`, `_id`), which Pydantic safely drops by default.
  2. *How do you enforce that NGOs must provide `ngo_profile` and `registration_number`, while Donors and Volunteers do not?*
     Using `@model_validator(mode="after")` on `UserRegister` (tying `role` to `ngo_profile`) and `NgoProfileIn` (requiring `registration_number` only when `org_type == "NGO"`).
  3. *Why does `UserUpdate` only allow `name`, `phone`, and `address`?*
     Allowing `email`, `role`, `is_active`, or `ngo_profile` in a general profile update would let users change their privileges or bypass NGO verification.

---

### 4. `app/routers/auth.py` (`/api/v1/auth`)
- **Purpose**: Handles user registration (`POST /register`) and login (`POST /login`).
- **Main Flow**:
  - `register_user`: Normalizes email to lowercase -> checks for duplicate email -> hashes password -> sets `is_active=True`, `created_at=updated_at=now`, and (for NGOs) `verification_status="PENDING"`, `verified_by=None`, `verified_at=None` -> inserts into `db.users` (catching `DuplicateKeyError` for race conditions) -> returns `UserResponse` (`201`).
  - `login_user`: Normalizes email -> fetches user -> verifies password -> checks `is_active` (`403 ACCOUNT_DISABLED`) -> returns signed JWT (`200`).
- **Key Decisions**:
  - Unknown email and wrong password return the exact same `401 INVALID_CREDENTIALS` error so attackers cannot enumerate registered emails.
  - Checking for existing email in code *and* catching `DuplicateKeyError` handles concurrent registration requests safely via MongoDB's unique index.
- **Likely Examiner Questions**:
  1. *Why check for an existing email in Python if MongoDB already has a unique index?*
     Checking in code handles the common case cleanly, while catching `DuplicateKeyError` protects against a race condition where two requests register the same email at the exact same millisecond.
  2. *Why do unknown email and wrong password return the same error message?*
     To prevent user enumeration—an attacker shouldn't be able to probe `/login` to discover which email addresses have accounts.
  3. *Why normalize email to lowercase before storing and querying?*
     Email addresses are case-insensitive in practice; storing lowercase ensures `User@Example.com` and `user@example.com` cannot create duplicate accounts.

---

### 5. `app/routers/users.py` (`/api/v1/users`)
- **Purpose**: Authenticated profile retrieval (`GET /me`) and partial profile updates (`PATCH /me`).
- **Main Flow**:
  - `GET /me`: Uses `get_current_user` and converts the MongoDB document via `user_to_response`.
  - `PATCH /me`: Uses `model_dump(exclude_unset=True)` and strips `None` values -> raises `422 VALIDATION_ERROR` if empty -> updates `updated_at` -> runs `update_one` filtered by `current_user["_id"]` -> returns updated `UserResponse`.
- **Key Decisions**:
  - Both `exclude_unset=True` and filtering out `None` values are required so omitted fields or explicit `null` values (e.g. `{"name": null}`) do not overwrite required database fields.
  - `user_to_response` converts both `_id` and `ngo_profile.verified_by` from `ObjectId` to `str` because Pydantic v2 rejects raw `ObjectId` values for `str` fields.
- **Likely Examiner Questions**:
  1. *Why use `model_dump(exclude_unset=True)` in `PATCH /me`?*
     Without `exclude_unset=True`, optional fields not sent in the request default to `None` and would overwrite existing values in MongoDB.
  2. *Why also filter out `None` values after `exclude_unset=True`?*
     If a client explicitly sends `{"name": null}`, `exclude_unset=True` keeps it because the key was sent; filtering `None` prevents wiping required fields and causing a `500` on the next `GET /me`.
  3. *How do you prevent a user from editing someone else's profile?*
     The `update_one` filter always uses `current_user["_id"]` extracted from the verified JWT, never an ID from the URL or request body.

---

## Phase B: Donation Schemas & Donor Routes

### 6. `app/schemas/donation.py`
- **Purpose**: Pydantic v2 validation and response serialization for food donations (`DonationCreate`, `DonationUpdate`, `DonationResponse`, `PaginatedDonations`).
- **Main Flow**:
  - `DonationCreate` validates `title`, `food_type`, `quantity > 0`, `quantity_unit`, optional `description`, `pickup_address` (reusing `Address`), and enforces via `@model_validator(mode="after")` that `expires_at` is both after `available_from` and in the future.
  - `DonationUpdate` makes every field optional with `extra="forbid"` and checks `expires_at > available_from` when both are sent.
  - `DonationResponse` shapes the API output including `donor_id`, `accepted_by`, `status_history`, and all stage timestamps.
- **Key Decisions**:
  - `extra="forbid"` is set on `DonationCreate` and `DonationUpdate` so donors cannot inject `status`, `donor_id`, `accepted_by`, or timestamps.
  - Reusing `Address` from `schemas/user.py` keeps address and 6-digit pincode validation consistent across users and donations.
- **Likely Examiner Questions**:
  1. *Why normalize datetimes to UTC in `_ensure_utc` before comparing?*
     Clients may send timezone-aware ISO strings or naive timestamps; comparing naive and aware `datetime` objects in Python raises a `TypeError`, so normalizing to UTC makes comparisons safe.
  2. *Why forbid extra fields on `DonationCreate` and `DonationUpdate`?*
     To prevent a donor from setting `status: "COMPLETED"` or `donor_id` to another user's ID in the request body.
  3. *Why does `DonationResponse` not have `extra="forbid"`?*
     MongoDB documents contain `_id` and may include internal fields; Pydantic ignores extra keys by default so the response won't fail with a 500.

---

### 7. `app/routers/donor.py` (`/api/v1/donations`)
- **Purpose**: Donor-only endpoints to create (`POST /donations`), list (`GET /donations/mine`), edit (`PUT /donations/{id}`), and cancel (`POST /donations/{id}/cancel`) food donations.
- **Main Flow**:
  - All routes use `Depends(require_role("DONOR"))`.
  - `POST /donations`: Initializes `status="AVAILABLE"`, `donor_id=current_user["_id"]`, and `status_history` with the initial `AVAILABLE` entry.
  - `GET /donations/mine`: Queries `db.donations` filtered by `donor_id` (and optional `status`), sorted newest first, paginated with `{ items, total, page, limit }`.
  - `PUT /donations/{id}` & `POST /donations/{id}/cancel`: Query by `{"_id": oid, "donor_id": current_user["_id"]}` (`404 NOT_FOUND` if missing), enforce `status == "AVAILABLE"` (`409 INVALID_STATUS_TRANSITION`), and atomically update/cancel.
- **Key Decisions**:
  - Registering `/donations/mine` **before** `/donations/{donation_id}` prevents FastAPI from treating `"mine"` as a `donation_id` path parameter (which would fail `ObjectId` parsing with `400`).
  - Filtering by both `_id` and `donor_id` returns `404 NOT_FOUND` instead of `403` when another donor owns the donation, so we don't leak whether an ID exists.
- **Likely Examiner Questions**:
  1. *Why must `GET /donations/mine` be defined before `PUT /donations/{donation_id}` or `GET /donations/{donation_id}`?*
     FastAPI matches routes in registration order; if `/{donation_id}` came first, `/donations/mine` could be captured as `donation_id="mine"`.
  2. *Why return `404 NOT_FOUND` instead of `403 FORBIDDEN` when Donor B tries to edit Donor A's donation?*
     Returning `403` confirms to Donor B that the donation ID exists; returning `404` hides other users' resource existence.
  3. *Why does `cancel_donation` include `"status": "AVAILABLE"` inside the `update_one` filter?*
     To make cancellation atomic—if an NGO accepts the donation in the millisecond between `find_one` and `update_one`, `matched_count` will be `0` and we return `409 INVALID_STATUS_TRANSITION` instead of overwriting an accepted donation.
