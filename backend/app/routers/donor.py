"""
app/routers/donor.py  — Person A
Spec Section 7: Donor routes.

  POST /api/v1/donations        Create a donation
  GET  /api/v1/donations/mine   Donor's own donations (paginated)
  PUT  /api/v1/donations/{id}   Edit donation (AVAILABLE only)
  POST /api/v1/donations/{id}/cancel  Cancel donation (AVAILABLE only)

IMPORTANT: This router is registered in main.py BEFORE donations.py
(Person B's) so that GET /api/v1/donations/mine is matched before
GET /api/v1/donations/{donation_id}.
"""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.database import db
from app.schemas.donation import (
    DonationCreate,
    DonationResponse,
    DonationStatus,
    DonationUpdate,
    PaginatedDonationsResponse,
)
from app.services.donation_service import (
    FoodShareAPIException,
    serialize_donation,
    transition_donation_status,
)
from app.utils.dependencies import require_role

router = APIRouter(prefix="/api/v1/donations", tags=["Donor"])


@router.post("", response_model=DonationResponse, status_code=201)
async def create_donation(
    body: DonationCreate,
    current_user: dict = Depends(require_role("DONOR")),
):
    now = datetime.now(timezone.utc)
    if body.expires_at <= body.available_from:
        raise FoodShareAPIException(400, "VALIDATION_ERROR", "expires_at must be after available_from.")

    doc = {
        "donor_id":        current_user["_id"],
        "title":           body.title,
        "food_type":       body.food_type.value,
        "quantity":        body.quantity,
        "quantity_unit":   body.quantity_unit.value,
        "description":     body.description,
        "food_image_url":  body.food_image_url,
        "pickup_image_url": None,
        "delivery_image_url": None,
        "pickup_address":  body.pickup_address.model_dump(),
        "available_from":  body.available_from,
        "expires_at":      body.expires_at,
        "status":          DonationStatus.AVAILABLE.value,
        "accepted_by":     None,
        "accepted_at":     None,
        "picked_up_at":    None,
        "distributed_at":  None,
        "completed_at":    None,
        "cancelled_at":    None,
        "status_history": [{
            "status":     DonationStatus.AVAILABLE.value,
            "changed_by": str(current_user["_id"]),
            "changed_at": now,
        }],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.donations.insert_one(doc)
    created = await db.donations.find_one({"_id": result.inserted_id})
    return serialize_donation(created)


@router.get("/mine", response_model=PaginatedDonationsResponse)
async def my_donations(
    page:  int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("DONOR")),
):
    limit = min(max(1, limit), 100)
    skip  = (page - 1) * limit
    query = {"donor_id": current_user["_id"]}
    total  = await db.donations.count_documents(query)
    cursor = db.donations.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items  = await cursor.to_list(length=limit)
    return {"items": [serialize_donation(d) for d in items], "total": total, "page": page, "limit": limit}


@router.put("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: str,
    body: DonationUpdate,
    current_user: dict = Depends(require_role("DONOR")),
):
    if not ObjectId.is_valid(donation_id):
        raise FoodShareAPIException(404, "NOT_FOUND", "Donation not found.")

    doc = await db.donations.find_one({
        "_id":      ObjectId(donation_id),
        "donor_id": current_user["_id"],
        "status":   DonationStatus.AVAILABLE.value,
    })
    if not doc:
        raise FoodShareAPIException(404, "NOT_FOUND", "Donation not found or not editable.")

    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    for field in ("title", "food_type", "quantity", "quantity_unit", "description", "food_image_url"):
        val = getattr(body, field)
        if val is not None:
            updates[field] = val.value if hasattr(val, "value") else val
    if body.pickup_address is not None:
        updates["pickup_address"] = body.pickup_address.model_dump()
    if body.available_from is not None:
        updates["available_from"] = body.available_from
    if body.expires_at is not None:
        updates["expires_at"] = body.expires_at

    updated = await db.donations.find_one_and_update(
        {"_id": ObjectId(donation_id)},
        {"$set": updates},
        return_document=True,
    )
    return serialize_donation(updated)


@router.post("/{donation_id}/cancel", response_model=DonationResponse)
async def cancel_donation(
    donation_id: str,
    current_user: dict = Depends(require_role("DONOR")),
):
    return await transition_donation_status(
        donation_id=donation_id,
        target_status=DonationStatus.CANCELLED,
        actor=current_user,
        db=db,
    )
