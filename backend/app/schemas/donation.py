from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class FoodType(str, Enum):
    COOKED = "COOKED"
    PACKAGED = "PACKAGED"
    RAW = "RAW"
    BAKERY = "BAKERY"
    OTHER = "OTHER"


class QuantityUnit(str, Enum):
    PLATES = "PLATES"
    KG = "KG"
    PACKETS = "PACKETS"
    ITEMS = "ITEMS"


class DonationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    ACCEPTED = "ACCEPTED"
    PICKED_UP = "PICKED_UP"
    DISTRIBUTED = "DISTRIBUTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class AddressSchema(BaseModel):
    street: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)
    pincode: str = Field(..., min_length=1)


class StatusHistoryEntry(BaseModel):
    status: DonationStatus
    changed_by: str  # User ID string
    changed_at: datetime


class DonationCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    food_type: FoodType
    quantity: float = Field(..., gt=0)
    quantity_unit: QuantityUnit
    description: Optional[str] = None
    pickup_address: AddressSchema
    available_from: datetime
    expires_at: datetime


class DonationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=120)
    food_type: Optional[FoodType] = None
    quantity: Optional[float] = Field(None, gt=0)
    quantity_unit: Optional[QuantityUnit] = None
    description: Optional[str] = None
    pickup_address: Optional[AddressSchema] = None
    available_from: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class DonationResponse(BaseModel):
    id: str
    donor_id: str
    title: str
    food_type: FoodType
    quantity: float
    quantity_unit: QuantityUnit
    description: Optional[str] = None
    pickup_address: AddressSchema
    available_from: datetime
    expires_at: datetime
    status: DonationStatus
    accepted_by: Optional[str] = None
    accepted_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    distributed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    status_history: List[StatusHistoryEntry] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedDonationsResponse(BaseModel):
    items: List[DonationResponse]
    total: int
    page: int
    limit: int
