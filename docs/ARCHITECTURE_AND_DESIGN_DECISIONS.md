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
- **`AddressUpdate`**: Partial address update schema (`street`, `city`, `state`, `pincode`).
- **`NgoProfileIn`**: Embedded model for registration input; validates `organization_name`, `org_type` (`NGO` | `VOLUNTEER`), and enforces `registration_number` when `org_type == "NGO"`.
- **`NgoProfileOut`**: Serialization model for NGO profiles containing `verification_status` (`PENDING` | `VERIFIED` | `REJECTED`).
- **`UserRegister`**: Registration payload model with `extra="forbid"`, validating donor vs. NGO requirements (NGO accounts must supply `ngo_profile`; donor accounts must not).
- **`UserLogin`**: Login credentials model (`email` + `password` with `max_length=72`).
- **`UserUpdate`**: Profile update model with `extra="forbid"` (`name`, `phone`, `address`).
- **`NgoVerificationUpdate`**: Admin verification model (`status: "VERIFIED" | "REJECTED"`).
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

### 2.4 User Profile Router (`app/routers/users.py`)
- **`GET /api/v1/users/me`**: Returns `UserResponse` for authenticated user (Donors, NGOs, Admins).
- **`PATCH /api/v1/users/me`**: Updates profile fields (`name`, `phone`, `address`) and sets `updated_at: now`. Rejects forbidden fields (`extra="forbid"`).

### 2.5 Admin Operations Router (`app/routers/admin.py`)
- **`GET /api/v1/admin/ngos/pending`**: Lists all pending NGO accounts for admin review (protected by `require_role("ADMIN")`).
- **`PATCH /api/v1/admin/ngos/{ngo_id}/verify`**: Admin sets status to `VERIFIED` or `REJECTED`, recording `verified_by` and `verified_at`.

### 2.6 Centralized Error Handling (`app/utils/errors.py` & `app/main.py`)
- Standard error envelope across all endpoints:
  ```json
  {
    "detail": "<message or error list>",
    "code": "<STANDARDIZED_ERROR_CODE>"
  }
  ```
- Custom exception handlers for:
  - `AppError`: Maps business errors to custom HTTP status codes and error codes (`EMAIL_EXISTS`, `INVALID_CREDENTIALS`, `ACCOUNT_DISABLED`, `NOT_AUTHENTICATED`, `INVALID_TOKEN`, `FORBIDDEN`, `USER_NOT_FOUND`, `NGO_NOT_FOUND`).
  - `RequestValidationError`: Formats Pydantic/FastAPI request validation errors into HTTP 422 with `code: "VALIDATION_ERROR"`.

### 2.7 Security & Dependencies (`app/utils/dependencies.py`)
- `get_current_user`: Bearer token dependency using `HTTPBearer(auto_error=False)`.
  - If no token provided: raises 401 with `code: "NOT_AUTHENTICATED"`.
  - If token malformed, invalid, or expired: raises 401 with `code: "INVALID_TOKEN"`.
- `require_role(*allowed_roles)`: Role-based access control factory raising 403 `FORBIDDEN` if caller does not match.

---

## 3. Design Decisions & Rationale: "Why is something happening?"

### Decision 1: Why `extra="forbid"` on Input Schemas, but default `extra="ignore"` on Response Schemas?
- **For Input Schemas (`UserRegister`, `NgoProfileIn`, `Address`, `UserLogin`, `UserUpdate`)**:
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

---

### Decision 4: Why HTTP 422 `VALIDATION_ERROR` instead of HTTP 400?
- **FastAPI Native Pipeline**: FastAPI validates request bodies through Pydantic and natively raises `RequestValidationError` with HTTP 422 Unprocessable Entity.
- **HTTP Semantics (RFC 4918)**: HTTP 400 Bad Request indicates malformed HTTP syntax (e.g., broken JSON). HTTP 422 indicates syntactically correct JSON whose semantic content violates schema constraints (e.g., password too short, invalid role).
- **The Solution**: We keep HTTP 422 and attach a custom `RequestValidationError` exception handler that standardizes the error body to the project's `{detail, code: "VALIDATION_ERROR"}` format.

---

### Decision 5: Why enforce `max_length=72` on passwords?
- **Bcrypt Truncation Limit**: The Bcrypt hashing algorithm natively processes a maximum of 72 bytes. Any characters beyond 72 bytes are silently ignored by standard bcrypt implementations.
- **Security Implications**: If a user creates a password with 100 characters, changing characters 73 through 100 would still allow login with the original password, which violates user expectations.
- **DoS Protection**: Hashing arbitrarily large strings (e.g. 10 KB strings) consumes excessive CPU cycles and exposes the server to Denial-of-Service attacks.

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

1. `2c1481c` - **Add user schemas, auth routes, and error handling**
2. `7613d95` - **Allow ADMIN role in user response**
3. `972abcc` - **Remove extra forbid from response models**
4. `3be5d28` - **Set updated_at on registration**
5. `9628c59` - **Set verified_by and verified_at to null on NGO registration**
6. `ca72067` - **Update inactive account error code to ACCOUNT_DISABLED**
7. `77045ea` - **Require registration_number for NGO organization type**
8. `929f821` - **Add RequestValidationError handler and update spec section 8**
9. `dd4212e` - **Add password max length and string field validations**
10. `96332c0` - **Deduplicate EMAIL_EXISTS error handling in registration**
11. `b4f017f` - **Add get_current_user dependency and test-protected route**
12. `5a0afc9` - **Add architecture and design decisions document and automated auth test suite**
13. `4fd364f` - **Add user profile routes and require_role dependency**
14. `260f263` - **Add admin NGO verification endpoints and test suite**
15. `602dce2` - **Update spec with users and admin endpoints**
16. `39fcb80` - **Enhance MongoDB connection test script with Atlas IP troubleshooting diagnostics**
