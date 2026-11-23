from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import Literal
from datetime import datetime

class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: str
    city: str
    state: str
    pincode: str

class NgoProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    organization_name: str
    org_type: Literal["NGO", "VOLUNTEER"]
    registration_number: str | None = None
    
class NgoProfileOut(BaseModel):
    organization_name: str
    org_type: Literal["NGO", "VOLUNTEER"]
    registration_number: str | None = None
    verification_status: Literal["PENDING", "VERIFIED", "REJECTED"]

class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str
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
    password: str

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

class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    access_token: str
    token_type: str
