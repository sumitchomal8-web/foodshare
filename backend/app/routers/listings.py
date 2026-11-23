from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from pymongo import ReturnDocument

from app.database import db
from app.schemas.listing import ListingCreate, ListingUpdate, ListingResponse
from app.utils.dependencies import get_current_user, require_role
from app.utils.errors import AppError

router = APIRouter(prefix="/listings", tags=["Listings"])

def _format_listing(doc: dict) -> ListingResponse:
    doc["id"] = str(doc.pop("_id"))
    return ListingResponse(**doc)

@router.post("", response_model=ListingResponse, status_code=201)
async def create_listing(
    payload: ListingCreate,
    current_user: dict = Depends(require_role("DONOR")),
):
    now = datetime.now(timezone.utc)
    listing_doc = payload.model_dump()

    listing_doc["donor_id"] = current_user["user_id"]
    listing_doc["status"] = "AVAILABLE"
    listing_doc["claimed_by"] = None
    listing_doc["claimed_at"] = None
    listing_doc["completed_at"] = None
    listing_doc["created_at"] = now
    listing_doc["updated_at"] = now

    result = await db.listings.insert_one(listing_doc)
    listing_doc["_id"] = result.inserted_id

    return _format_listing(listing_doc)

@router.get("", response_model=list[ListingResponse])
async def list_listings(
    status: str = Query(default="AVAILABLE", description="Filter by listing status"),
    city: str | None = Query(default=None, description="Filter by pickup city"),
    food_type: str | None = Query(default=None, description="Filter by food category"),
):
    query: dict = {"status": status}
    if city:
        query["pickup_address.city"] = {"$regex": f"^{city.strip()}$", "$options": "i"}
    if food_type:
        query["food_type"] = food_type

    cursor = db.listings.find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        results.append(_format_listing(doc))
    return results

@router.get("/my-donations", response_model=list[ListingResponse])
async def list_my_donations(
    current_user: dict = Depends(require_role("DONOR")),
):
    cursor = db.listings.find({"donor_id": current_user["user_id"]}).sort("created_at", -1)
    results = []
    async for doc in cursor:
        results.append(_format_listing(doc))
    return results

@router.get("/my-claims", response_model=list[ListingResponse])
async def list_my_claims(
    current_user: dict = Depends(require_role("NGO")),
):
    cursor = db.listings.find({"claimed_by": current_user["user_id"]}).sort("claimed_at", -1)
    results = []
    async for doc in cursor:
        results.append(_format_listing(doc))
    return results

@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: str):
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid listing ID", code="INVALID_ID")

    doc = await db.listings.find_one({"_id": oid})
    if not doc:
        raise AppError(status_code=404, detail="Listing not found", code="LISTING_NOT_FOUND")

    return _format_listing(doc)

@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: str,
    update_data: ListingUpdate,
    current_user: dict = Depends(require_role("DONOR")),
):
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid listing ID", code="INVALID_ID")

    doc = await db.listings.find_one({"_id": oid})
    if not doc:
        raise AppError(status_code=404, detail="Listing not found", code="LISTING_NOT_FOUND")

    if doc["donor_id"] != current_user["user_id"]:
        raise AppError(status_code=403, detail="You can only edit your own listings", code="FORBIDDEN")

    if doc["status"] != "AVAILABLE":
        raise AppError(
            status_code=400,
            detail=f"Cannot edit listing with status '{doc['status']}'",
            code="CANNOT_EDIT_CLAIMED_LISTING",
        )

    updates = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.listings.update_one({"_id": oid}, {"$set": updates})
        doc = await db.listings.find_one({"_id": oid})

    return _format_listing(doc)

@router.delete("/{listing_id}")
async def cancel_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid listing ID", code="INVALID_ID")

    doc = await db.listings.find_one({"_id": oid})
    if not doc:
        raise AppError(status_code=404, detail="Listing not found", code="LISTING_NOT_FOUND")

    # Only donor who created it or Admin can cancel
    if doc["donor_id"] != current_user["user_id"] and current_user.get("role") != "ADMIN":
        raise AppError(status_code=403, detail="You can only cancel your own listings", code="FORBIDDEN")

    if doc["status"] != "AVAILABLE":
        raise AppError(
            status_code=400,
            detail=f"Cannot cancel listing with status '{doc['status']}'",
            code="CANNOT_CANCEL_LISTING",
        )

    now = datetime.now(timezone.utc)
    await db.listings.update_one(
        {"_id": oid},
        {"$set": {"status": "CANCELLED", "updated_at": now}},
    )

    return {
        "message": "Listing cancelled successfully",
        "status": "CANCELLED",
    }

@router.post("/{listing_id}/claim", response_model=ListingResponse)
async def claim_listing(
    listing_id: str,
    current_user: dict = Depends(require_role("NGO")),
):
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid listing ID", code="INVALID_ID")

    # 1. Enforce verified NGO requirement
    user_doc = await db.users.find_one({"_id": ObjectId(current_user["user_id"])})
    if not user_doc:
        raise AppError(status_code=404, detail="User not found", code="USER_NOT_FOUND")

    ngo_profile = user_doc.get("ngo_profile") or {}
    if ngo_profile.get("verification_status") != "VERIFIED":
        raise AppError(
            status_code=403,
            detail="Only verified NGO accounts can claim food listings",
            code="NGO_NOT_VERIFIED",
        )

    # 2. Atomically claim listing
    now = datetime.now(timezone.utc)
    updated_doc = await db.listings.find_one_and_update(
        {"_id": oid, "status": "AVAILABLE"},
        {
            "$set": {
                "status": "CLAIMED",
                "claimed_by": current_user["user_id"],
                "claimed_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not updated_doc:
        # Check if listing exists to return accurate error code
        existing = await db.listings.find_one({"_id": oid})
        if not existing:
            raise AppError(status_code=404, detail="Listing not found", code="LISTING_NOT_FOUND")
        raise AppError(
            status_code=409,
            detail=f"Listing is not available for claiming (current status: {existing['status']})",
            code="LISTING_ALREADY_CLAIMED",
        )

    return _format_listing(updated_doc)

@router.post("/{listing_id}/complete", response_model=ListingResponse)
async def complete_pickup(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid listing ID", code="INVALID_ID")

    doc = await db.listings.find_one({"_id": oid})
    if not doc:
        raise AppError(status_code=404, detail="Listing not found", code="LISTING_NOT_FOUND")

    # Only donor, claimed NGO, or admin can mark complete
    is_donor = doc["donor_id"] == current_user["user_id"]
    is_claimant = doc.get("claimed_by") == current_user["user_id"]
    is_admin = current_user.get("role") == "ADMIN"

    if not (is_donor or is_claimant or is_admin):
        raise AppError(status_code=403, detail="Unauthorized to complete this pickup", code="FORBIDDEN")

    if doc["status"] != "CLAIMED":
        raise AppError(
            status_code=400,
            detail=f"Cannot complete pickup for listing with status '{doc['status']}'",
            code="LISTING_NOT_CLAIMED",
        )

    now = datetime.now(timezone.utc)
    await db.listings.update_one(
        {"_id": oid},
        {"$set": {"status": "PICKED_UP", "completed_at": now, "updated_at": now}},
    )

    updated_doc = await db.listings.find_one({"_id": oid})
    return _format_listing(updated_doc)
