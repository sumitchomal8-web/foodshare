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
| 401 Unauthorized | `INVALID_CREDENTIALS` | Invalid email or password during login |
| 401 Unauthorized | `INVALID_TOKEN` | Token is expired, malformed, or missing required claims |
| 401 Unauthorized | `NOT_AUTHENTICATED` | Bearer authentication token was not provided |
| 403 Forbidden | `ACCOUNT_DISABLED` | User account is inactive / disabled (`is_active: false`) |
| 403 Forbidden | `FORBIDDEN` | User does not have sufficient role permissions |
| 404 Not Found | `USER_NOT_FOUND` / `NGO_NOT_FOUND` | Requested entity does not exist |
| 409 Conflict | `EMAIL_EXISTS` | Email address is already registered |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Request body or query parameters failed schema validation |
