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
  - `verified_by`: ObjectId | null - initialized to `null` until verified
  - `verified_at`: datetime | null - initialized to `null` until verified
- `is_active`: boolean - default `true`
- `created_at`: UTC datetime - set to current UTC time on creation
- `updated_at`: UTC datetime - set to current UTC time on creation and updated on modification

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
| 401 Unauthorized | `INVALID_CREDENTIALS` | Invalid email or password during login |
| 401 Unauthorized | `INVALID_TOKEN` | Token is expired, malformed, or missing required claims |
| 401 Unauthorized | `NOT_AUTHENTICATED` | Bearer authentication token was not provided |
| 403 Forbidden | `ACCOUNT_DISABLED` | User account is inactive / disabled (`is_active: false`) |
| 409 Conflict | `EMAIL_EXISTS` | Email address is already registered |
| 422 Unprocessable Entity | `VALIDATION_ERROR` | Request body or query parameters failed schema validation |

> Note on Fix 7: Previously specified as 400 VALIDATION_ERROR. Updated to 422 Unprocessable Entity to match FastAPI's native validation pipeline while guaranteeing the standard `{detail, code}` payload structure via custom `RequestValidationError` handling.
