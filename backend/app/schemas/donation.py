from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.user import Address

FoodType = Literal[
    "COOKED_MEALS",
    "RAW_INGREDIENTS",
    "PACKAGED_FOOD",
    "BAKERY",
    "FRUITS_VEGETABLES",
]

DonationStatus = Literal[
    "AVAILABLE",
    "ACCEPTED",
    "PICKED_UP",
    "DISTRIBUTED",
    "COMPLETED",
    "CANCELLED",
    "EXPIRED",
]


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StatusHistoryEntry(BaseModel):
    status: DonationStatus
    changed_by: str | None = None
    changed_at: datetime


class DonationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    food_type: FoodType
    quantity: float = Field(gt=0)
    quantity_unit: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=1000)
    pickup_address: Address
    available_from: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        avail = _ensure_utc(self.available_from)
        exp = _ensure_utc(self.expires_at)
        now = datetime.now(timezone.utc)

        if exp <= avail:
            raise ValueError("expires_at must be after available_from")
        if exp <= now:
            raise ValueError("expires_at must be in the future")

        return self


class DonationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=120)
    food_type: FoodType | None = None
    quantity: float | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=1000)
    pickup_address: Address | None = None
    available_from: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.available_from is not None and self.expires_at is not None:
            if _ensure_utc(self.expires_at) <= _ensure_utc(self.available_from):
                raise ValueError("expires_at must be after available_from")
        return self


class DonationResponse(BaseModel):
    id: str
    donor_id: str
    title: str
    food_type: FoodType
    quantity: float
    quantity_unit: str
    description: str | None = None
    pickup_address: Address
    available_from: datetime
    expires_at: datetime
    status: DonationStatus
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    picked_up_at: datetime | None = None
    distributed_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    status_history: list[StatusHistoryEntry]
    created_at: datetime
    updated_at: datetime


class PaginatedDonations(BaseModel):
    items: list[DonationResponse]
    total: int
    page: int
    limit: int
