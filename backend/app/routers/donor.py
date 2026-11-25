from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, Query

from app.database import db
from app.schemas.donation import (
    DonationCreate,
    DonationResponse,
    DonationStatus,
    DonationUpdate,
    PaginatedDonations,
)
from app.utils.dependencies import require_role
from app.utils.errors import AppError

router = APIRouter(prefix="/donations", tags=["Donor"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise AppError(
            status_code=400,
            detail="Invalid donation ID",
            code="INVALID_ID",
        )


def donation_to_response(doc: dict) -> DonationResponse:
    data = doc.copy()
    data["id"] = str(data["_id"])
    data["donor_id"] = str(data["donor_id"])

    if data.get("accepted_by") is not None:
        data["accepted_by"] = str(data["accepted_by"])

    history = []
    for entry in data.get("status_history", []):
        item = entry.copy()
        if item.get("changed_by") is not None:
            item["changed_by"] = str(item["changed_by"])
        history.append(item)
    data["status_history"] = history

    return DonationResponse(**data)


@router.post("", response_model=DonationResponse, status_code=201)
async def create_donation(
    donation_data: DonationCreate,
    current_user: dict = Depends(require_role("DONOR")),
):
    now = datetime.now(timezone.utc)
    doc = donation_data.model_dump()
    doc["donor_id"] = current_user["_id"]
    doc["status"] = "AVAILABLE"
    doc["accepted_by"] = None
    doc["accepted_at"] = None
    doc["picked_up_at"] = None
    doc["distributed_at"] = None
    doc["completed_at"] = None
    doc["cancelled_at"] = None
    doc["status_history"] = [
        {
            "status": "AVAILABLE",
            "changed_by": current_user["_id"],
            "changed_at": now,
        }
    ]
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await db.donations.insert_one(doc)
    doc["_id"] = result.inserted_id

    return donation_to_response(doc)


@router.get("/mine", response_model=PaginatedDonations)
async def list_my_donations(
    status: DonationStatus | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_role("DONOR")),
):
    query: dict = {"donor_id": current_user["_id"]}
    if status is not None:
        query["status"] = status

    total = await db.donations.count_documents(query)
    skip = (page - 1) * limit

    cursor = (
        db.donations.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    items = [donation_to_response(doc) async for doc in cursor]

    return PaginatedDonations(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.put("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: str,
    update_data: DonationUpdate,
    current_user: dict = Depends(require_role("DONOR")),
):
    oid = _parse_object_id(donation_id)

    # Filter by both _id and donor_id so another donor gets 404 without revealing existence
    donation = await db.donations.find_one(
        {"_id": oid, "donor_id": current_user["_id"]}
    )
    if not donation:
        raise AppError(
            status_code=404,
            detail="Donation not found",
            code="NOT_FOUND",
        )

    if donation["status"] != "AVAILABLE":
        raise AppError(
            status_code=409,
            detail="Only AVAILABLE donations can be edited",
            code="INVALID_STATUS_TRANSITION",
        )

    raw_changes = update_data.model_dump(exclude_unset=True)
    changes = {k: v for k, v in raw_changes.items() if v is not None}

    if not changes:
        raise AppError(
            status_code=422,
            detail="No fields to update",
            code="VALIDATION_ERROR",
        )

    new_avail = _ensure_utc(changes.get("available_from", donation["available_from"]))
    new_exp = _ensure_utc(changes.get("expires_at", donation["expires_at"]))
    if new_exp <= new_avail:
        raise AppError(
            status_code=422,
            detail="expires_at must be after available_from",
            code="VALIDATION_ERROR",
        )
    if "expires_at" in changes and new_exp <= datetime.now(timezone.utc):
        raise AppError(
            status_code=422,
            detail="expires_at must be in the future",
            code="VALIDATION_ERROR",
        )

    changes["updated_at"] = datetime.now(timezone.utc)

    result = await db.donations.update_one(
        {"_id": oid, "donor_id": current_user["_id"], "status": "AVAILABLE"},
        {"$set": changes},
    )
    if result.matched_count == 0:
        raise AppError(
            status_code=409,
            detail="Donation is no longer AVAILABLE",
            code="INVALID_STATUS_TRANSITION",
        )

    updated = await db.donations.find_one({"_id": oid})
    if not updated:
        raise AppError(
            status_code=404,
            detail="Donation not found",
            code="NOT_FOUND",
        )
    return donation_to_response(updated)


@router.post("/{donation_id}/cancel", response_model=DonationResponse)
async def cancel_donation(
    donation_id: str,
    current_user: dict = Depends(require_role("DONOR")),
):
    oid = _parse_object_id(donation_id)

    donation = await db.donations.find_one(
        {"_id": oid, "donor_id": current_user["_id"]}
    )
    if not donation:
        raise AppError(
            status_code=404,
            detail="Donation not found",
            code="NOT_FOUND",
        )

    if donation["status"] != "AVAILABLE":
        raise AppError(
            status_code=409,
            detail="Only AVAILABLE donations can be cancelled",
            code="INVALID_STATUS_TRANSITION",
        )

    now = datetime.now(timezone.utc)
    result = await db.donations.update_one(
        {"_id": oid, "donor_id": current_user["_id"], "status": "AVAILABLE"},
        {
            "$set": {
                "status": "CANCELLED",
                "cancelled_at": now,
                "updated_at": now,
            },
            "$push": {
                "status_history": {
                    "status": "CANCELLED",
                    "changed_by": current_user["_id"],
                    "changed_at": now,
                }
            },
        },
    )

    if result.matched_count == 0:
        raise AppError(
            status_code=409,
            detail="Donation is no longer AVAILABLE",
            code="INVALID_STATUS_TRANSITION",
        )

    updated = await db.donations.find_one({"_id": oid})
    if not updated:
        raise AppError(
            status_code=404,
            detail="Donation not found",
            code="NOT_FOUND",
        )
    return donation_to_response(updated)
