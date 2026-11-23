from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Literal
from datetime import datetime, timezone
from app.schemas.user import Address

FoodType = Literal[
    "COOKED_MEALS",
    "RAW_INGREDIENTS",
    "PACKAGED_FOOD",
    "BAKERY",
    "FRUITS_VEGETABLES",
]

ListingStatus = Literal[
    "AVAILABLE",
    "CLAIMED",
    "PICKED_UP",
    "CANCELLED",
    "EXPIRED",
]

DietaryFlag = Literal[
    "VEGETARIAN",
    "NON_VEGETARIAN",
    "VEGAN",
    "HALAL",
    "JAIN",
]

class ListingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=1000)
    food_type: FoodType
    quantity_servings: int = Field(ge=1, description="Estimated number of servings/meals")
    dietary_flags: list[DietaryFlag] = Field(default_factory=list)
    best_before: datetime
    pickup_address: Address
    pickup_instructions: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_best_before(self):
        # Best before must be in the future
        now = datetime.now(timezone.utc)
        if self.best_before <= now:
            raise ValueError("best_before must be a datetime in the future")
        return self

class ListingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=1000)
    food_type: FoodType | None = None
    quantity_servings: int | None = Field(default=None, ge=1)
    dietary_flags: list[DietaryFlag] | None = None
    best_before: datetime | None = None
    pickup_instructions: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_best_before(self):
        if self.best_before is not None:
            now = datetime.now(timezone.utc)
            if self.best_before <= now:
                raise ValueError("best_before must be a datetime in the future")
        return self

class ListingResponse(BaseModel):
    id: str
    donor_id: str
    title: str
    description: str
    food_type: FoodType
    quantity_servings: int
    dietary_flags: list[DietaryFlag]
    best_before: datetime
    pickup_address: Address
    pickup_instructions: str | None = None
    status: ListingStatus
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
