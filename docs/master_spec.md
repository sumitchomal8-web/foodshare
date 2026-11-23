# FoodShare API Specification

## 4. User Management & Authentication

### 4.1 User Document Schema
Users are stored in the `users` MongoDB collection.

#### Fields
- `_id`: ObjectId - Auto-generated MongoDB document ID
- `name`: string, min length 1 - User's full name
- `email`: string, lowercase, unique index - User's email address
- `password_hash`: string - Bcrypt hashed password (starts with `$2b$`)
- `role`: string enum (`"DONOR"`, `"NGO"`, `"ADMIN"`) - User role
- `phone`: string - Contact phone number
- `address`: object
  - `street`: string, min length 1
  - `city`: string, min length 1
  - `state`: string, min length 1
  - `pincode`: string, 6 digits (`^\d{6}$`)
- `ngo_profile`: object | null (required when role is `"NGO"`, null for `"DONOR"`)
  - `organization_name`: string, min length 1
  - `org_type`: string enum (`"NGO"`, `"VOLUNTEER"`)
  - `registration_number`: string | null (required when `org_type` is `"NGO"`, optional for `"VOLUNTEER"`)
  - `verification_status`: string enum (`"PENDING"`, `"VERIFIED"`, `"REJECTED"`) - initialized to `"PENDING"` on registration
  - `verified_by`: ObjectId / string | null - initialized to `null` until verified by an Admin
  - `verified_at`: datetime | null - initialized to `null` until verified by an Admin
- `is_active`: boolean - default `true`
- `created_at`: UTC datetime - set to current UTC time on creation
- `updated_at`: UTC datetime - set to current UTC time on creation and updated on modification

---

### 4.2 Endpoints

#### Authentication (`/api/v1/auth`)
- `POST /register`: Register a new donor or NGO account (status 201).
- `POST /login`: Authenticate email and password, returning JWT access token (status 200).

#### Users (`/api/v1/users`)
- `GET /me`: Retrieve the authenticated user's profile (`UserResponse`).
- `PATCH /me`: Update profile details (`name`, `phone`, `address`).

#### Administration (`/api/v1/admin`)
- `GET /ngos/pending`: List all NGO accounts with `verification_status: "PENDING"` (Admin only).
- `PATCH /ngos/{ngo_id}/verify`: Set NGO verification status to `"VERIFIED"` or `"REJECTED"`, recording `verified_by` and `verified_at` (Admin only).

---

## 5. Food Donation Listings (`/api/v1/listings`)

### 5.1 Listing Document Schema
Stored in the `listings` MongoDB collection.

#### Fields
- `_id`: ObjectId - Auto-generated MongoDB document ID
- `donor_id`: string - User ID of the donor who created the listing
- `title`: string (3 to 120 characters) - Title of the donation
- `description`: string (5 to 1000 characters) - Detailed description
- `food_type`: string enum (`"COOKED_MEALS"`, `"RAW_INGREDIENTS"`, `"PACKAGED_FOOD"`, `"BAKERY"`, `"FRUITS_VEGETABLES"`)
- `quantity_servings`: integer (>= 1) - Estimated number of servings
- `dietary_flags`: list of string enums (`"VEGETARIAN"`, `"NON_VEGETARIAN"`, `"VEGAN"`, `"HALAL"`, `"JAIN"`)
- `best_before`: UTC datetime - Must be in the future at the time of creation
- `pickup_address`: object (`street`, `city`, `state`, `pincode`)
- `pickup_instructions`: string | null - Instructions for pickup volunteers
- `status`: string enum (`"AVAILABLE"`, `"CLAIMED"`, `"PICKED_UP"`, `"CANCELLED"`, `"EXPIRED"`)
- `claimed_by`: string | null - User ID of the NGO claiming the donation
- `claimed_at`: UTC datetime | null - Timestamp when claimed
- `completed_at`: UTC datetime | null - Timestamp when marked picked up
- `created_at`: UTC datetime
- `updated_at`: UTC datetime

### 5.2 Listing Lifecycle & State Machine

```
              ┌───────────────┐
              │   AVAILABLE   │
              └───────┬───────┘
                      │
            ┌─────────┴─────────┐
            │ (Claim by NGO)    │ (Cancel by Donor)
            ▼                   ▼
    ┌───────────────┐   ┌───────────────┐
    │    CLAIMED    │   │   CANCELLED   │
    └───────┬───────┘   └───────────────┘
            │
            │ (Complete Pickup)
            ▼
    ┌───────────────┐
    │   PICKED_UP   │
    └───────────────┘
```

### 5.3 Listing Endpoints
- `POST /api/v1/listings`: Create a new food donation listing (Donor only, status 201).
- `GET /api/v1/listings`: Search & browse available listings with filters (`status`, `city`, `food_type`).
- `GET /api/v1/listings/my-donations`: List all food donations posted by the current donor.
- `GET /api/v1/listings/my-claims`: List all food donations claimed by the current NGO.
- `GET /api/v1/listings/{id}`: Retrieve detailed listing data.
- `PATCH /api/v1/listings/{id}`: Modify listing details (Donor only, allowed while `status == "AVAILABLE"`).
- `DELETE /api/v1/listings/{id}`: Cancel a listing (Donor or Admin only, allowed while `status == "AVAILABLE"`).
- `POST /api/v1/listings/{id}/claim`: Claim a food listing (Verified NGO only, atomic status transition).
- `POST /api/v1/listings/{id}/complete`: Confirm food handover / pickup (Donor, claimant NGO, or Admin).

---

## 8. Error Handling & Response Formats

All API errors adhere to a standardized JSON response body containing `detail` and `code`:

```json
{
  "detail": "<error message or validation details>",
  "code": "<ERROR_CODE>"
}
```

### Standard Status Codes and Error Codes

| HTTP Status | Error Code | Description |
|:---|:---|:---|
| 400 Bad Request | `INVALID_ID` | Malformed ObjectId string provided |
| 400 Bad Request | `CANNOT_EDIT_CLAIMED_LISTING` | Attempted to modify a listing that is not in `AVAILABLE` state |
| 400 Bad Request | `CANNOT_CANCEL_LISTING` | Attempted to cancel a listing that is already claimed or completed |
| 400 Bad Request | `LISTING_NOT_CLAIMED` | Attempted to complete a pickup on a listing that was not claimed |
| 401 Unauthorized | `INVALID_CREDENTIALS` | Invalid email or password during login |
| 401 Unauthorized | `INVALID_TOKEN` | Token is expired, malformed, or missing required claims |
| 401 Unauthorized | `NOT_AUTHENTICATED` | Bearer authentication token was not provided |
| 403 Forbidden | `ACCOUNT_DISABLED` | User account is inactive / disabled (`is_active: false`) |
| 403 Forbidden | `FORBIDDEN` | User does not have sufficient role permissions |
| 403 Forbidden | `NGO_NOT_VERIFIED` | NGO account has not been approved by an administrator |
| 404 Not Found | `USER_NOT_FOUND` / `NGO_NOT_FOUND` / `LISTING_NOT_FOUND` | Requested entity does not exist |
| 409 Conflict | `EMAIL_EXISTS` | Email address is already registered |
| 409 Conflict | `LISTING_ALREADY_CLAIMED` | Concurrent or duplicate claim on non-available listing |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Request body or query parameters failed schema validation |
