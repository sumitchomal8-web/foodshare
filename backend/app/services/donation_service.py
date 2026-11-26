from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from app.database import db as default_db
from app.schemas.donation import DonationStatus


class FoodShareAPIException(HTTPException):
    def __init__(self, status_code: int, code: str, detail: str):
        super().__init__(
            status_code=status_code,
            detail={"detail": detail, "code": code}
        )
        self.code = code
        self.raw_detail = detail


# State Transition Graph (Master Spec Section 5)
VALID_TRANSITIONS: Dict[DonationStatus, Set[DonationStatus]] = {
    DonationStatus.AVAILABLE: {
        DonationStatus.ACCEPTED,
        DonationStatus.CANCELLED,
        DonationStatus.EXPIRED,
    },
    DonationStatus.ACCEPTED: {
        DonationStatus.PICKED_UP,
    },
    DonationStatus.PICKED_UP: {
        DonationStatus.DISTRIBUTED,
    },
    DonationStatus.DISTRIBUTED: {
        DonationStatus.COMPLETED,
    },
    DonationStatus.COMPLETED: set(),
    DonationStatus.CANCELLED: set(),
    DonationStatus.EXPIRED: set(),
}


def to_object_id(val: Any) -> Any:
    if isinstance(val, ObjectId):
        return val
    if isinstance(val, str) and ObjectId.is_valid(val):
        return ObjectId(val)
    return val


def serialize_donation(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serializes MongoDB document into API JSON format (Section 3 & 4.2):
    - _id -> id (string)
    - donor_id -> string
    - accepted_by -> string or None
    - status_history[].changed_by -> string
    """
    if not doc:
        return {}

    serialized = dict(doc)
    if "_id" in serialized:
        serialized["id"] = str(serialized.pop("_id"))
    if "donor_id" in serialized and serialized["donor_id"] is not None:
        serialized["donor_id"] = str(serialized["donor_id"])
    if "accepted_by" in serialized and serialized["accepted_by"] is not None:
        serialized["accepted_by"] = str(serialized["accepted_by"])

    if "status_history" in serialized and isinstance(serialized["status_history"], list):
        history = []
        for entry in serialized["status_history"]:
            h = dict(entry)
            if "changed_by" in h and h["changed_by"] is not None:
                h["changed_by"] = str(h["changed_by"])
            history.append(h)
        serialized["status_history"] = history

    return serialized


def validate_status_transition(
    donation: Dict[str, Any],
    target_status: DonationStatus,
    actor: Dict[str, Any],
    now: datetime = None
) -> None:
    """
    Validates whether an actor can legally transition a donation to `target_status`.
    Raises FoodShareAPIException matching Section 8 error rules if invalid.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    current_status = DonationStatus(donation["status"])

    # 1. State machine graph check
    allowed_next_states = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_next_states:
        raise FoodShareAPIException(
            status_code=409,
            code="INVALID_STATUS_TRANSITION",
            detail=f"Cannot transition donation from {current_status.value} to {target_status.value}."
        )

    actor_id_str = str(actor.get("_id") or actor.get("id"))
    actor_role = actor.get("role")
    is_active = actor.get("is_active", True)

    if not is_active:
        raise FoodShareAPIException(
            status_code=403,
            code="ACCOUNT_DISABLED",
            detail="Your account is disabled."
        )

    # 2. Guard rules
    if target_status == DonationStatus.ACCEPTED:
        if actor_role != "NGO":
            raise FoodShareAPIException(
                status_code=403,
                code="FORBIDDEN",
                detail="Only NGOs can accept donations."
            )

        ngo_profile = actor.get("ngo_profile") or {}
        if ngo_profile.get("verification_status") != "VERIFIED":
            raise FoodShareAPIException(
                status_code=403,
                code="NGO_NOT_VERIFIED",
                detail="NGO must be verified by an administrator before accepting donations."
            )

        expires_at = donation.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise FoodShareAPIException(
                    status_code=409,
                    code="INVALID_STATUS_TRANSITION",
                    detail="Cannot accept an expired donation."
                )

    elif target_status in (DonationStatus.PICKED_UP, DonationStatus.DISTRIBUTED):
        if actor_role != "NGO":
            raise FoodShareAPIException(
                status_code=403,
                code="FORBIDDEN",
                detail="Only NGOs can update pickup or distribution status."
            )
        assigned_ngo = str(donation.get("accepted_by"))
        if actor_id_str != assigned_ngo:
            raise FoodShareAPIException(
                status_code=403,
                code="FORBIDDEN",
                detail="Only the NGO assigned to this donation can update its status."
            )

    elif target_status == DonationStatus.COMPLETED:
        assigned_ngo = str(donation.get("accepted_by"))
        is_assigned_ngo = (actor_role == "NGO" and actor_id_str == assigned_ngo)
        is_admin = (actor_role == "ADMIN")
        if not (is_assigned_ngo or is_admin):
            raise FoodShareAPIException(
                status_code=403,
                code="FORBIDDEN",
                detail="Only the assigned NGO or an administrator can mark a donation as completed."
            )

    elif target_status == DonationStatus.CANCELLED:
        donor_id_str = str(donation.get("donor_id"))
        is_owner_donor = (actor_role == "DONOR" and actor_id_str == donor_id_str)
        is_admin = (actor_role == "ADMIN")
        if not (is_owner_donor or is_admin):
            raise FoodShareAPIException(
                status_code=403,
                code="FORBIDDEN",
                detail="Only the donor who created the donation or an administrator can cancel it."
            )


def apply_status_transition(
    donation: Dict[str, Any],
    target_status: DonationStatus,
    actor_id: str,
    now: datetime = None
) -> Dict[str, Any]:
    """
    Applies the transition to an in-memory document, setting timestamps and appending to status_history.
    Returns the update payload for MongoDB $set and $push.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    status_timestamp_field = {
        DonationStatus.ACCEPTED: "accepted_at",
        DonationStatus.PICKED_UP: "picked_up_at",
        DonationStatus.DISTRIBUTED: "distributed_at",
        DonationStatus.COMPLETED: "completed_at",
        DonationStatus.CANCELLED: "cancelled_at",
    }.get(target_status)

    set_fields: Dict[str, Any] = {
        "status": target_status.value,
        "updated_at": now
    }

    if status_timestamp_field:
        set_fields[status_timestamp_field] = now

    if target_status == DonationStatus.ACCEPTED:
        set_fields["accepted_by"] = to_object_id(actor_id)

    history_entry = {
        "status": target_status.value,
        "changed_by": str(actor_id),
        "changed_at": now
    }

    donation.update(set_fields)
    if "status_history" not in donation:
        donation["status_history"] = []
    donation["status_history"].append(history_entry)

    return {
        "$set": set_fields,
        "$push": {"status_history": history_entry}
    }


# ==============================================================================
# Async MongoDB Database Operations (Person B)
# ==============================================================================

async def get_raw_donation_or_404(donation_id: str, db=default_db) -> Dict[str, Any]:
    """
    Fetches raw donation document by id or raises 404.
    Performs lazy expiry check if status is AVAILABLE and expires_at <= now.
    """
    if not ObjectId.is_valid(donation_id):
        raise FoodShareAPIException(
            status_code=404,
            code="NOT_FOUND",
            detail="Donation not found."
        )

    doc = await db.donations.find_one({"_id": ObjectId(donation_id)})
    if not doc:
        raise FoodShareAPIException(
            status_code=404,
            code="NOT_FOUND",
            detail="Donation not found."
        )

    # Lazy Expiration Check
    now = datetime.now(timezone.utc)
    expires_at = doc.get("expires_at")
    if doc.get("status") == DonationStatus.AVAILABLE.value and expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            updated = await db.donations.find_one_and_update(
                {"_id": doc["_id"], "status": DonationStatus.AVAILABLE.value},
                {
                    "$set": {
                        "status": DonationStatus.EXPIRED.value,
                        "updated_at": now
                    },
                    "$push": {
                        "status_history": {
                            "status": DonationStatus.EXPIRED.value,
                            "changed_by": "system",
                            "changed_at": now
                        }
                    }
                },
                return_document=ReturnDocument.AFTER
            )
            if updated:
                doc = updated

    return doc


async def accept_donation(
    donation_id: str,
    actor: Dict[str, Any],
    db=default_db,
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    NGO accepts an AVAILABLE donation.
    Enforces 'First accept wins' atomic query on status=AVAILABLE and expires_at > now.
    """
    actor_role = actor.get("role")
    is_active = actor.get("is_active", True)
    if not is_active:
        raise FoodShareAPIException(
            status_code=403,
            code="ACCOUNT_DISABLED",
            detail="Your account is disabled."
        )

    if actor_role != "NGO":
        raise FoodShareAPIException(
            status_code=403,
            code="FORBIDDEN",
            detail="Only NGOs can accept donations."
        )

    ngo_profile = actor.get("ngo_profile") or {}
    if ngo_profile.get("verification_status") != "VERIFIED":
        raise FoodShareAPIException(
            status_code=403,
            code="NGO_NOT_VERIFIED",
            detail="NGO must be verified by an administrator before accepting donations."
        )

    if not ObjectId.is_valid(donation_id):
        raise FoodShareAPIException(
            status_code=404,
            code="NOT_FOUND",
            detail="Donation not found."
        )

    if now is None:
        now = datetime.now(timezone.utc)
    actor_id = to_object_id(actor.get("_id") or actor.get("id"))

    # Atomic update
    result = await db.donations.find_one_and_update(
        {
            "_id": ObjectId(donation_id),
            "status": DonationStatus.AVAILABLE.value,
            "expires_at": {"$gt": now}
        },
        {
            "$set": {
                "status": DonationStatus.ACCEPTED.value,
                "accepted_by": actor_id,
                "accepted_at": now,
                "updated_at": now
            },
            "$push": {
                "status_history": {
                    "status": DonationStatus.ACCEPTED.value,
                    "changed_by": str(actor_id),
                    "changed_at": now
                }
            }
        },
        return_document=ReturnDocument.AFTER
    )

    if result:
        return serialize_donation(result)

    # If update failed, query document to provide precise error code
    existing = await db.donations.find_one({"_id": ObjectId(donation_id)})
    if not existing:
        raise FoodShareAPIException(
            status_code=404,
            code="NOT_FOUND",
            detail="Donation not found."
        )

    expires_at = existing.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            await db.donations.update_one(
                {"_id": ObjectId(donation_id), "status": DonationStatus.AVAILABLE.value},
                {"$set": {"status": DonationStatus.EXPIRED.value, "updated_at": now}}
            )
            raise FoodShareAPIException(
                status_code=409,
                code="INVALID_STATUS_TRANSITION",
                detail="Cannot accept an expired donation."
            )

    raise FoodShareAPIException(
        status_code=409,
        code="ALREADY_ACCEPTED",
        detail="Donation has already been accepted or is no longer available."
    )


async def transition_donation_status(
    donation_id: str,
    target_status: DonationStatus,
    actor: Dict[str, Any],
    db=default_db
) -> Dict[str, Any]:
    """
    Transitions donation status to PICKED_UP, DISTRIBUTED, COMPLETED, or CANCELLED.
    Enforces atomic status prerequisite match.
    """
    if not ObjectId.is_valid(donation_id):
        raise FoodShareAPIException(
            status_code=404,
            code="NOT_FOUND",
            detail="Donation not found."
        )

    doc = await get_raw_donation_or_404(donation_id, db=db)
    validate_status_transition(doc, target_status, actor)

    now = datetime.now(timezone.utc)
    actor_id_str = str(actor.get("_id") or actor.get("id"))

    status_timestamp_field = {
        DonationStatus.PICKED_UP: "picked_up_at",
        DonationStatus.DISTRIBUTED: "distributed_at",
        DonationStatus.COMPLETED: "completed_at",
        DonationStatus.CANCELLED: "cancelled_at",
    }.get(target_status)

    set_fields: Dict[str, Any] = {
        "status": target_status.value,
        "updated_at": now
    }
    if status_timestamp_field:
        set_fields[status_timestamp_field] = now

    push_history = {
        "status": target_status.value,
        "changed_by": actor_id_str,
        "changed_at": now
    }

    # Atomic update on matching current status to prevent concurrent conflict
    result = await db.donations.find_one_and_update(
        {
            "_id": ObjectId(donation_id),
            "status": doc["status"]
        },
        {
            "$set": set_fields,
            "$push": {"status_history": push_history}
        },
        return_document=ReturnDocument.AFTER
    )

    if not result:
        raise FoodShareAPIException(
            status_code=409,
            code="INVALID_STATUS_TRANSITION",
            detail="Donation status was updated concurrently. Please refresh."
        )

    return serialize_donation(result)


async def get_donation_detail(
    donation_id: str,
    actor: Dict[str, Any],
    db=default_db
) -> Dict[str, Any]:
    """
    GET /api/v1/donations/{id}
    Access: Owner donor, assigned NGO, ADMIN; NGO for AVAILABLE (Section 7).
    """
    doc = await get_raw_donation_or_404(donation_id, db=db)

    actor_role = actor.get("role")
    actor_id_str = str(actor.get("_id") or actor.get("id"))
    donor_id_str = str(doc.get("donor_id"))
    assigned_ngo_str = str(doc.get("accepted_by")) if doc.get("accepted_by") else None

    if actor_role == "ADMIN":
        return serialize_donation(doc)

    if actor_role == "DONOR" and actor_id_str == donor_id_str:
        return serialize_donation(doc)

    if actor_role == "NGO":
        if doc.get("status") == DonationStatus.AVAILABLE.value:
            return serialize_donation(doc)
        if assigned_ngo_str and actor_id_str == assigned_ngo_str:
            return serialize_donation(doc)

    raise FoodShareAPIException(
        status_code=403,
        code="FORBIDDEN",
        detail="You do not have permission to view this donation."
    )


async def list_donations(
    actor: Dict[str, Any],
    status: Optional[str] = None,
    city: Optional[str] = None,
    food_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=default_db
) -> Dict[str, Any]:
    """
    GET /api/v1/donations (Browse donations for NGO/ADMIN).
    Section 7: NGO, ADMIN (filters: status, city, food_type).
    """
    actor_role = actor.get("role")
    if actor_role not in ("NGO", "ADMIN"):
        raise FoodShareAPIException(
            status_code=403,
            code="FORBIDDEN",
            detail="Only NGOs and administrators can browse donations."
        )

    limit = min(max(1, limit), 100)
    page = max(1, page)
    skip = (page - 1) * limit

    query: Dict[str, Any] = {}
    now = datetime.now(timezone.utc)

    # NGOs browsing without explicit status default to unexpired AVAILABLE
    if status:
        query["status"] = status
        if status == DonationStatus.AVAILABLE.value:
            query["expires_at"] = {"$gt": now}
    elif actor_role == "NGO":
        query["status"] = DonationStatus.AVAILABLE.value
        query["expires_at"] = {"$gt": now}

    if city:
        query["pickup_address.city"] = {"$regex": f"^{city.strip()}$", "$options": "i"}

    if food_type:
        query["food_type"] = food_type

    total = await db.donations.count_documents(query)
    cursor = db.donations.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)

    return {
        "items": [serialize_donation(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit
    }


async def list_ngo_donations(
    actor: Dict[str, Any],
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=default_db
) -> Dict[str, Any]:
    """
    GET /api/v1/ngo/donations
    Section 7: NGO (accepted by me, filter by status).
    """
    if actor.get("role") != "NGO":
        raise FoodShareAPIException(
            status_code=403,
            code="FORBIDDEN",
            detail="Only NGOs can access their accepted donations."
        )

    actor_id = to_object_id(actor.get("_id") or actor.get("id"))
    limit = min(max(1, limit), 100)
    page = max(1, page)
    skip = (page - 1) * limit

    query: Dict[str, Any] = {"accepted_by": actor_id}
    if status:
        query["status"] = status

    total = await db.donations.count_documents(query)
    cursor = db.donations.find(query).sort("accepted_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)

    return {
        "items": [serialize_donation(item) for item in items],
        "total": total,
        "page": page,
        "limit": limit
    }
