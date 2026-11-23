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
  - `users.email`: Unique index (`unique=True`) ensuring uniqueness at the database engine level.
  - `users.role`: Secondary index for role-based queries.
  - `listings.[status, created_at]`: Compound index for efficient browsing of available donations.
  - `listings.donor_id`: Index for donor query operations.
  - `listings.claimed_by`: Index for NGO query operations.
  - `listings.pickup_address.city`: Index for localized food discovery.

### 2.2 Schemas & Data Contracts
- **Users & Auth (`app/schemas/user.py`)**:
  - `Address`, `AddressUpdate`, `NgoProfileIn`, `NgoProfileOut`, `UserRegister`, `UserLogin`, `UserUpdate`, `NgoVerificationUpdate`, `UserResponse`, `Token`.
- **Food Listings (`app/schemas/listing.py`)**:
  - `ListingCreate`: Validates `title` (3-120 chars), `description` (5-1000 chars), `food_type`, `quantity_servings` (>= 1), `dietary_flags`, future `best_before` datetime, and pickup address.
  - `ListingUpdate`: Partial updates with future `best_before` enforcement.
  - `ListingResponse`: Serialization model with `extra="ignore"` design pattern.

### 2.3 Authentication Router (`app/routers/auth.py`)
- `POST /api/v1/auth/register`: Dual uniqueness check, password hashing, timestamping, returns HTTP 201 Created.
- `POST /api/v1/auth/login`: Constant-time verification, unified 401 on failure, disabled check, JWT token creation.

### 2.4 User Profile Router (`app/routers/users.py`)
- `GET /api/v1/users/me`: Returns `UserResponse` for authenticated user (Donors, NGOs, Admins).
- `PATCH /api/v1/users/me`: Updates profile fields (`name`, `phone`, `address`) and sets `updated_at: now`. Rejects forbidden fields (`extra="forbid"`).

### 2.5 Admin Operations Router (`app/routers/admin.py`)
- `GET /api/v1/admin/ngos/pending`: Lists all pending NGO accounts for admin review (protected by `require_role("ADMIN")`).
- `PATCH /api/v1/admin/ngos/{ngo_id}/verify`: Admin sets status to `VERIFIED` or `REJECTED`, recording `verified_by` and `verified_at`.

### 2.6 Food Donation Listings Router (`app/routers/listings.py`)
- `POST /api/v1/listings`: Donors create surplus food listings.
- `GET /api/v1/listings`: Browse available listings with optional `city`, `food_type`, `status` filters.
- `GET /api/v1/listings/my-donations`: Donor reviews their active and past donations.
- `GET /api/v1/listings/my-claims`: NGO reviews their claimed donations.
- `GET /api/v1/listings/{id}`: Full listing details.
- `PATCH /api/v1/listings/{id}`: Donors edit available listings. Rejects modifications on claimed listings.
- `DELETE /api/v1/listings/{id}`: Donors cancel available listings.
- `POST /api/v1/listings/{id}/claim`: Verified NGOs claim food donations atomically with race condition handling.
- `POST /api/v1/listings/{id}/complete`: Confirms handover/pickup, setting `status: "PICKED_UP"`.

### 2.7 Centralized Error Handling (`app/utils/errors.py` & `app/main.py`)
- Standard error envelope across all endpoints:
  ```json
  {
    "detail": "<message or error list>",
    "code": "<STANDARDIZED_ERROR_CODE>"
  }
  ```
- Custom exception handlers for:
  - `AppError`: Maps business errors to custom HTTP status codes and error codes (`EMAIL_EXISTS`, `INVALID_CREDENTIALS`, `ACCOUNT_DISABLED`, `NOT_AUTHENTICATED`, `INVALID_TOKEN`, `FORBIDDEN`, `NGO_NOT_VERIFIED`, `LISTING_ALREADY_CLAIMED`, `CANNOT_EDIT_CLAIMED_LISTING`, etc.).
  - `RequestValidationError`: Formats Pydantic/FastAPI request validation errors into HTTP 422 with `code: "VALIDATION_ERROR"`.

### 2.8 Security & Dependencies (`app/utils/dependencies.py`)
- `get_current_user`: Bearer token dependency using `HTTPBearer(auto_error=False)`.
- `require_role(*allowed_roles)`: Role-based access control factory raising 403 `FORBIDDEN` if caller does not match.

---

## 3. Design Decisions & Rationale: "Why is something happening?"

### Decision 1: Why `extra="forbid"` on Input Schemas, but default `extra="ignore"` on Response Schemas?
- **For Input Schemas**: Immediately rejects unknown fields with HTTP 422 to eliminate mass-assignment vulnerabilities.
- **For Response Schemas**: Pydantic automatically serializes only explicitly declared public fields and discards extra document keys, avoiding 500 runtime crashes when stored documents acquire internal or future fields (`updated_at`, `verified_by`).

---

### Decision 2: Why do login failures for unknown emails and wrong passwords return identical responses?
- **User Enumeration Prevention**: Returning identical HTTP 401 `INVALID_CREDENTIALS` responses prevents attackers from probing email existence.

---

### Decision 3: Why does registration check for existing email in code AND catch `DuplicateKeyError`?
- **TOCTOU Race Condition Mitigation**: Application check handles sequential flow cleanly; MongoDB unique index catches concurrent inserts and converts them to 409 `EMAIL_EXISTS`.

---

### Decision 4: Why atomic `find_one_and_update` for claiming food donations?
- **The Problem**: When surplus food is posted, multiple NGOs in the same area may attempt to claim it at the same moment.
- **The Solution**: An atomic `find_one_and_update({"_id": oid, "status": "AVAILABLE"}, ...)` operation ensures that only ONE NGO can transition the listing from `AVAILABLE` to `CLAIMED`. The second concurrent request fails the query condition and receives HTTP 409 `LISTING_ALREADY_CLAIMED`.

---

### Decision 5: Why enforce verified status for NGOs before allowing food claims?
- **Food Safety & Trust**: Anyone can register with role `"NGO"`. Allowing unverified users to claim hundreds of meals could lead to food spoilage, black-market resale, or safety hazards. Requiring `ngo_profile.verification_status == "VERIFIED"` ensures that only audited organizations can claim donations.

---

## 4. Verification Test Suites

1. `test_user_schema.py`: Validates Pydantic schema constraints.
2. `test_errors.py`: Validates centralized `AppError` and HTTP error formatting.
3. `test_auth_suite.py`: Validates the 7 authentication scenarios, bcrypt prefixes, timestamps, and protected routes.
4. `test_users_and_admin_suite.py`: Validates profile retrieval across roles, profile patching, and admin verification.
5. `test_listings_suite.py`: Validates donation creation, city filtering, verified claim enforcement, atomic race condition handling, and pickup completion.
