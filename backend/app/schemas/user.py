from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Literal
from datetime import datetime

class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    pincode: str = Field(pattern=r"^\d{6}$")

class NgoProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    organization_name: str = Field(min_length=1)
    org_type: Literal["NGO", "VOLUNTEER"]
    registration_number: str | None = None

    @model_validator(mode="after")
    def check_registration_number(self):
        if self.org_type == "NGO" and not (self.registration_number and self.registration_number.strip()):
            raise ValueError("registration_number is required for NGO")
        return self
    
class NgoProfileOut(BaseModel):
    organization_name: str
    org_type: Literal["NGO", "VOLUNTEER"]
    registration_number: str | None = None
    verification_status: Literal["PENDING", "VERIFIED", "REJECTED"]
    verified_by: str | None = None
    verified_at: datetime | None = None


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: str = Field(min_length=1)
    role: Literal["DONOR", "NGO"]
    address: Address
    ngo_profile: NgoProfileIn | None = None

    @model_validator(mode="after")
    def check_role(self):
        if self.role == "NGO" and self.ngo_profile is None:
            raise ValueError("NGO profile is required for NGO accounts")

        if self.role == "DONOR" and self.ngo_profile is not None:
            raise ValueError("Donor accounts must not include an NGO profile")

        return self


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1)
    address: Address | None = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["DONOR", "NGO", "ADMIN"]
    phone: str
    address: Address
    ngo_profile: NgoProfileOut | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
