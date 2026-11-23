# FoodShare: Comprehensive Architecture, Implementation & Design Decisions

This document outlines the architecture, data models, security designs, implementation details, and rationale behind design decisions for the FoodShare backend.

---

## 1. Project Overview & Core Goals

**FoodShare** is a community food redistribution platform designed to bridge the gap between food donors (restaurants, caterers, grocery stores, individuals) and recipients (NGOs, community kitchens, shelters, volunteers).

### Core Stack
- **Framework:** FastAPI (Python 3.12, ASGI-based, high performance)
- **Database:** MongoDB Atlas via Motor (`motor.motor_asyncio.AsyncIOMotorClient`, async/await driver)
- **Validation & Serialization:** Pydantic v2 (`BaseModel`, `Field`, `model_validator`, `ConfigDict`)
- **Security:** Passlib (Bcrypt hashing), Python-Jose (JWT encoding/decoding)
- **Dependency Management:** UV / pyproject.toml

---

## 2. What We Have Built (Current State)

### 2.1 Database Setup (`app/database.py`)
- Asynchronous MongoDB connection using Motor.
- Automatic index creation during FastAPI lifespan:
  - `email`: Unique index (`unique=True`) ensuring uniqueness at the database engine level.
  - `role`: Secondary index for role-based queries.

### 2.2 Schemas & Data Contracts (`app/schemas/user.py`)
- **`Address`**: Embedded model validating `street`, `city`, `state` (min length 1) and `pincode` (strictly 6 digits via `^\d{6}$`).
- **`NgoProfileIn`**: Embedded model for registration input; validates `organization_name`, `org_type` (`NGO` | `VOLUNTEER`), and enforces `registration_number` when `org_type == "NGO"`.
- **`NgoProfileOut`**: Serialization model for NGO profiles containing `verification_status` (`PENDING` | `VERIFIED` | `REJECTED`).
- **`UserRegister`**: Registration payload model with `extra="forbid"`, validating donor vs. NGO requirements (NGO accounts must supply `ngo_profile`; donor accounts must not).
- **`UserLogin`**: Login credentials model (`email` + `password` with `max_length=72`).
- **`UserResponse`**: Outgoing user representation. Includes `id`, `name`, `email`, `role` (`DONOR` | `NGO` | `ADMIN`), `phone`, `address`, `ngo_profile`, `is_active`, and `created_at`.
- **`Token`**: Bearer token response schema (`access_token`, `token_type: "bearer"`).

### 2.3 Authentication Router (`app/routers/auth.py`)
- **`POST /api/v1/auth/register`**:
  - Normalizes email to lowercase.
  - Dual uniqueness check (application pre-check + `DuplicateKeyError` handling).
  - Hashes passwords using bcrypt (`$2b$`).
  - Sets `is_active: True`, `created_at: now`, `updated_at: now`.
  - For NGO accounts: initializes `verification_status: "PENDING"`, `verified_by: None`, `verified_at: None`.
  - Excludes sensitive fields (`password`, `password_hash`, `_id`) and maps `_id` to string `id`.
  - Returns HTTP 201 Created.
- **`POST /api/v1/auth/login`**:
  - Verifies password hash using constant-time comparison.
  - Unified `INVALID_CREDENTIALS` (401) response for both non-existent emails and wrong passwords.
  - Checks account status: returns `ACCOUNT_DISABLED` (403) if `is_active` is False.
  - Generates signed JWT access token containing `sub` (user_id) and `role`.

### 2.4 Centralized Error Handling (`app/utils/errors.py` & `app/main.py`)
- Standard error envelope across all endpoints:
  ```json
  {
    "detail": "<message or error list>",
    "code": "<STANDARDIZED_ERROR_CODE>"
  }
  ```
- Custom exception handlers for:
  - `AppError`: Maps business errors to custom HTTP status codes and error codes (`EMAIL_EXISTS`, `INVALID_CREDENTIALS`, `ACCOUNT_DISABLED`, `NOT_AUTHENTICATED`, `INVALID_TOKEN`).
  - `RequestValidationError`: Formats Pydantic/FastAPI request validation errors into HTTP 422 with `code: "VALIDATION_ERROR"`.

### 2.5 Security & Dependencies (`app/utils/dependencies.py`)
- `get_current_user`: Bearer token dependency using `HTTPBearer(auto_error=False)`.
  - If no token provided: raises 401 with `code: "NOT_AUTHENTICATED"`.
  - If token malformed, invalid, or expired: raises 401 with `code: "INVALID_TOKEN"`.
  - Extracts payload claims (`user_id`, `role`) for downstream authorization.
- **`/test-protected` route**: Verifies authentication integration for partner development.

---

## 3. Design Decisions & Rationale: "Why is something happening?"

### Decision 1: Why `extra="forbid"` on Input Schemas, but default `extra="ignore"` on Response Schemas?
- **For Input Schemas (`UserRegister`, `NgoProfileIn`, `Address`, `UserLogin`)**:
  - **The Risk**: External clients might send extra payload keys like `{"is_active": true, "verification_status": "VERIFIED", "role": "ADMIN"}`.
  - **The Solution**: `extra="forbid"` immediately rejects unknown fields with HTTP 422. This completely eliminates mass-assignment vulnerabilities.
- **For Response Schemas (`UserResponse`, `NgoProfileOut`)**:
  - **The Risk**: The backend database stores internal, operational, or future fields (such as `password_hash`, `updated_at`, `verified_by`, `verified_at`, internal indexes).
  - **The Solution**: Response schemas use Pydantic's default `extra="ignore"`. Pydantic automatically serializes only the explicitly declared public fields and discards all extra document keys.
  - **Why not `extra="forbid"` on response schemas?** If `extra="forbid"` were used on `UserResponse`, as soon as a document acquired `updated_at` or `verified_by`, calling `UserResponse(**doc)` would throw a runtime `ValidationError`, triggering a 500 Internal Server Error for legitimate users.
  - **Why not manual field picking?** Manually picking dictionary keys before response construction is brittle, error-prone, and duplicates schema logic.

---

### Decision 2: Why do login failures for unknown emails and wrong passwords return identical responses?
- **The Risk (User Enumeration Attacks)**: If an API returns `"User not found"` (or HTTP 404) vs. `"Incorrect password"` (HTTP 401), an attacker can automate queries to harvest registered user emails.
- **The Solution**: Both failures return HTTP 401 with identical response bodies:
  ```json
  {
    "detail": "Invalid email or password",
    "code": "INVALID_CREDENTIALS"
  }
  ```
- **Why not alternate methods?**
  - *Alternate: Return 404 for unknown email.* Rejected: Violates OWASP Authentication guidelines.
  - *Alternate: Generic 400.* Rejected: HTTP 401 Unauthorized is semantically correct for authentication failures.

---

### Decision 3: Why does registration check for existing email in code AND catch `DuplicateKeyError`?
- **The Reason (Defense-in-Depth & TOCTOU Race Conditions)**:
  1. **Application-level pre-check (`find_one`)**: Provides a fast and descriptive error path under normal sequential usage.
  2. **Database unique index + `DuplicateKeyError`**: Protects against Time-of-Check to Time-of-Use (TOCTOU) race conditions. If two registration requests with the identical email arrive simultaneously, both could pass `find_one`, but MongoDB's atomic index check will reject the second insert with `DuplicateKeyError`.
  3. Catching `DuplicateKeyError` ensures that concurrent requests still receive clean HTTP 409 `EMAIL_EXISTS` responses rather than unhandled 500 server crashes.
- **Why not alternate methods?**
  - *Alternate: Rely only on `find_one` without index.* Rejected: Guarantees duplicate records during concurrent traffic.
  - *Alternate: Rely only on DB error without pre-check.* Rejected: Parsing raw database error strings for application logic is less clean and couples router code tightly to driver exception shapes.

---

### Decision 4: Why HTTP 422 `VALIDATION_ERROR` instead of HTTP 400?
- **FastAPI Native Pipeline**: FastAPI validates request bodies through Pydantic and natively raises `RequestValidationError` with HTTP 422 Unprocessable Entity.
- **HTTP Semantics (RFC 4918)**: HTTP 400 Bad Request indicates malformed HTTP syntax (e.g., broken JSON). HTTP 422 indicates syntactically correct JSON whose semantic content violates schema constraints (e.g., password too short, invalid role).
- **The Solution**: We keep HTTP 422 and attach a custom `RequestValidationError` exception handler that standardizes the error body to the project's `{detail, code: "VALIDATION_ERROR"}` format.
- **Why not alternate methods?**
  - *Alternate: Rewriting custom middleware to intercept and convert to 400.* Rejected: Fights against FastAPI's native architecture, breaks automatic OpenAPI/Swagger documentation, and confuses frontend tooling.

---

### Decision 5: Why enforce `max_length=72` on passwords?
- **Bcrypt Truncation Limit**: The Bcrypt hashing algorithm natively processes a maximum of 72 bytes. Any characters beyond 72 bytes are silently ignored by standard bcrypt implementations.
- **Security Implications**: If a user creates a password with 100 characters, changing characters 73 through 100 would still allow login with the original password, which violates user expectations.
- **DoS Protection**: Hashing arbitrarily large strings (e.g. 10 KB strings) consumes excessive CPU cycles and exposes the server to Denial-of-Service attacks.
- **The Solution**: Enforce `password: str = Field(min_length=8, max_length=72)` at the Pydantic layer.

---

### Decision 6: Why strict string validation (`min_length=1`, regex for pincode)?
- **Empty String Prevention**: By default, `str` in Pydantic accepts `""`. This would allow users to register with empty names, cities, or addresses. Adding `Field(min_length=1)` rejects empty and whitespace-only submissions.
- **Postal Code Validation**: Indian postal codes follow a strict 6-digit numeric pattern. Enforcing `pattern=r"^\d{6}$"` prevents invalid inputs at the boundary.

---

### Decision 7: Why stateless JWT with embedded claims instead of server-side sessions?
- **Scalability**: Stateless JWTs contain the `user_id` (`sub`) and `role` signed with a secret key. Protected routes (`/test-protected`, `/users/me`) verify the token signature in-memory in microseconds without issuing database read queries.
- **Why not server-side sessions in MongoDB / Redis?**
  - For early and medium scale, maintaining session state in MongoDB introduces unnecessary database roundtrips on every request. JWT keeps API requests fast, decoupled, and horizontally scalable.

---

## 4. Git Commit History (`feature/auth`)

The following commits were made on `feature/auth`, following the atomic "one commit per problem" convention:

1. `2c1481c` - **Add user schemas, auth routes, and error handling**
   - Initial base implementation of auth system, Pydantic schemas, and error class.
2. `7613d95` - **Allow ADMIN role in user response**
   - Added `"ADMIN"` to `UserResponse.role` Literal to support admin account retrieval via `GET /users/me`.
3. `972abcc` - **Remove extra forbid from response models**
   - Removed `extra="forbid"` from `UserResponse` and `NgoProfileOut` so database documents with `updated_at`, `verified_by`, etc. are safely serialized without validation rejection.
4. `3be5d28` - **Set updated_at on registration**
   - Set `user_document["updated_at"]` to current UTC timestamp matching `created_at` in `register_user`.
5. `9628c59` - **Set verified_by and verified_at to null on NGO registration**
   - Explicitly initialized `verified_by: None` and `verified_at: None` in `user_document["ngo_profile"]` upon registration.
6. `ca72067` - **Update inactive account error code to ACCOUNT_DISABLED**
   - Renamed `ACCOUNT_INACTIVE` to `ACCOUNT_DISABLED` in `login_user` to align with the master specification.
7. `77045ea` - **Require registration_number for NGO organization type**
   - Added `check_registration_number` model validator to `NgoProfileIn` requiring a non-empty `registration_number` when `org_type == "NGO"`.
8. `929f821` - **Add RequestValidationError handler and update spec section 8**
   - Configured FastAPI `RequestValidationError` handler returning HTTP 422 with `{detail, code: "VALIDATION_ERROR"}` and documented Section 4.1 & 8 in `docs/master_spec.md`.
9. `dd4212e` - **Add password max length and string field validations**
   - Enforced `max_length=72` on password and `min_length=1` / pincode regex on address and user string fields.
10. `96332c0` - **Deduplicate EMAIL_EXISTS error handling in registration**
    - Refactored `auth.py` to instantiate `email_exists_error` once and raise it from both the existence pre-check and `DuplicateKeyError` handler.
11. `b4f017f` - **Add get_current_user dependency and test-protected route**
    - Created `app/utils/dependencies.py` with `get_current_user` and implemented `/test-protected` in `app/main.py`.

---

## 5. Verification Test Suite Results

All 7 core test scenarios plus the protected route tests were executed and passed:

| # | Test Case | Target / Expectation | Status | Result Summary |
|---|:---|:---|:---:|:---|
| 1 | Register Donor | Status 201; password / password_hash excluded | **PASSED** | 201 Created; clean response with ID, address, role; no hashes returned. |
| 2 | Check Stored Document | Hash starts with `$2b$`, lowercase email, `updated_at` set | **PASSED** | Stored doc contains `$2b$12$...`, lowercase email, matching `created_at` & `updated_at`. |
| 3 | Duplicate Registration | Status 409 with `code: "EMAIL_EXISTS"` | **PASSED** | 409 Conflict returned with `{"detail": "Email already registered", "code": "EMAIL_EXISTS"}`. |
| 4 | Register ADMIN Role | Status 422 validation failure | **PASSED** | 422 Unprocessable Entity with `code: "VALIDATION_ERROR"` (role Literal strictly allows DONOR/NGO). |
| 5 | Register NGO Without Profile | Status 422 validation failure | **PASSED** | 422 Unprocessable Entity with `code: "VALIDATION_ERROR"` (`check_role` validator rejected). |
| 6 | Register NGO With Profile | Verification status `PENDING`, `verified_by`/`verified_at` null | **PASSED** | 201 Created; database doc contains `verification_status: "PENDING"`, `verified_by: null`, `verified_at: null`. |
| 7 | Login Failures (Unknown Email & Wrong Password) | Both return identical 401 `INVALID_CREDENTIALS` | **PASSED** | Both return 401 with exact same body `{"detail": "Invalid email or password", "code": "INVALID_CREDENTIALS"}`. |
| + | `/test-protected` (Authenticated) | Valid Bearer token returns 200 with user payload | **PASSED** | 200 OK with `{"message": "Authenticated!", "user": {"user_id": ..., "role": "DONOR"}}`. |
| + | `/test-protected` (No Token) | Unauthenticated request returns 401 | **PASSED** | 401 Unauthorized with `{"detail": "Not authenticated", "code": "NOT_AUTHENTICATED"}`. |
| + | `/test-protected` (Invalid Token) | Tampered/expired token returns 401 | **PASSED** | 401 Unauthorized with `{"detail": "Invalid or expired access token", "code": "INVALID_TOKEN"}`. |
