"""
app/schemas/admin.py  — Person B
Pydantic models for admin-facing request/response payloads.
Spec Section 7: Admin routes.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Enums (mirrored from spec Section 4.1 for user-facing serialization)
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    DONOR = "DONOR"
    NGO = "NGO"
    ADMIN = "ADMIN"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class AddressOut(BaseModel):
    street: str
    city: str
    state: str
    pincode: str


class NgoProfileOut(BaseModel):
    organization_name: str
    org_type: str
    registration_number: Optional[str] = None
    verification_status: VerificationStatus
    verified_by: Optional[str] = None   # admin user id string
    verified_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# User response (admin view — no password_hash)
# ---------------------------------------------------------------------------

class UserAdminResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    phone: str
    address: AddressOut
    ngo_profile: Optional[NgoProfileOut] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    items: List[UserAdminResponse]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class UserStatusUpdate(BaseModel):
    """PATCH /admin/users/{id}/status"""
    is_active: bool


class NgoVerificationRequest(BaseModel):
    """POST /admin/ngos/{id}/verify"""
    approve: bool


# ---------------------------------------------------------------------------
# Stats / analytics response
# ---------------------------------------------------------------------------

class DonationStats(BaseModel):
    total: int
    available: int
    accepted: int
    picked_up: int
    distributed: int
    completed: int
    cancelled: int
    expired: int


class PlatformStats(BaseModel):
    users: dict           # {total, donors, ngos, verified_ngos, admins}
    donations: DonationStats
    computed_at: datetime
