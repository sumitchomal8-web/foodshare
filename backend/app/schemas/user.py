"""
app/schemas/user.py  — Person A
Pydantic models for auth and user/profile routes.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRole(str, Enum):
    DONOR = "DONOR"
    NGO = "NGO"


class OrgType(str, Enum):
    NGO = "NGO"
    VOLUNTEER = "VOLUNTEER"


class AddressIn(BaseModel):
    street: str = Field(..., min_length=1)
    city:   str = Field(..., min_length=1)
    state:  str = Field(..., min_length=1)
    pincode: str = Field(..., min_length=4)


class NgoProfileIn(BaseModel):
    organization_name: str
    org_type: OrgType
    registration_number: Optional[str] = None


class RegisterRequest(BaseModel):
    name:    str = Field(..., min_length=1)
    email:   EmailStr
    password: str = Field(..., min_length=8)
    phone:   str = Field(..., min_length=1)
    role:    UserRole
    address: AddressIn
    ngo_profile: Optional[NgoProfileIn] = None


class LoginRequest(BaseModel):
    email:    str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class UserResponse(BaseModel):
    id:         str
    name:       str
    email:      str
    role:       str
    phone:      str
    address:    AddressIn
    ngo_profile: Optional[dict] = None
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
