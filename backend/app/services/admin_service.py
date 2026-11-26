"""
app/services/admin_service.py  — Person B
Business logic for admin user management and NGO verification.
Spec Section 7: Admin routes.

All functions receive the raw Motor `db` as a parameter so they are
independently testable without touching the global database handle.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.services.donation_service import FoodShareAPIException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ser_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a MongoDB user document into an API-safe dict."""
    if not doc:
        return {}
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("password_hash", None)          # never return hash
    if out.get("ngo_profile"):
        ngo = dict(out["ngo_profile"])
        if ngo.get("verified_by"):
            ngo["verified_by"] = str(ngo["verified_by"])
        out["ngo_profile"] = ngo
    return out


def _build_user_query(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if role:
        q["role"] = role
    if is_active is not None:
        q["is_active"] = is_active
    return q


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

async def list_users(
    actor: Dict[str, Any],
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
    db=None,
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/users
    Returns paginated user list, optionally filtered by role and is_active.
    """
    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    limit = min(max(1, limit), 100)
    page  = max(1, page)
    skip  = (page - 1) * limit

    query = _build_user_query(role, is_active)
    total = await db.users.count_documents(query)
    cursor = db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items  = await cursor.to_list(length=limit)

    return {
        "items": [_ser_user(u) for u in items],
        "total": total,
        "page":  page,
        "limit": limit,
    }


async def set_user_active(
    actor: Dict[str, Any],
    target_user_id: str,
    is_active: bool,
    db=None,
) -> Dict[str, Any]:
    """
    PATCH /api/v1/admin/users/{id}/status
    Activate or deactivate a user account.
    """
    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    if not ObjectId.is_valid(target_user_id):
        raise FoodShareAPIException(404, "NOT_FOUND", "User not found.")

    now = datetime.now(timezone.utc)
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(target_user_id)},
        {"$set": {"is_active": is_active, "updated_at": now}},
        return_document=True,          # ReturnDocument.AFTER == True
    )
    if not result:
        raise FoodShareAPIException(404, "NOT_FOUND", "User not found.")
    return _ser_user(result)


# ---------------------------------------------------------------------------
# NGO verification
# ---------------------------------------------------------------------------

async def list_pending_ngos(
    actor: Dict[str, Any],
    page: int = 1,
    limit: int = 20,
    db=None,
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/ngos/pending
    Returns NGO accounts awaiting verification.
    """
    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    limit = min(max(1, limit), 100)
    page  = max(1, page)
    skip  = (page - 1) * limit

    query = {
        "role": "NGO",
        "ngo_profile.verification_status": "PENDING",
    }
    total  = await db.users.count_documents(query)
    cursor = db.users.find(query).sort("created_at", 1).skip(skip).limit(limit)
    items  = await cursor.to_list(length=limit)

    return {
        "items": [_ser_user(u) for u in items],
        "total": total,
        "page":  page,
        "limit": limit,
    }


async def verify_ngo(
    actor: Dict[str, Any],
    target_user_id: str,
    approve: bool,
    db=None,
) -> Dict[str, Any]:
    """
    POST /api/v1/admin/ngos/{id}/verify
    Approve or reject an NGO's verification request.
    """
    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    if not ObjectId.is_valid(target_user_id):
        raise FoodShareAPIException(404, "NOT_FOUND", "User not found.")

    # Confirm the target is an NGO
    target = await db.users.find_one({"_id": ObjectId(target_user_id), "role": "NGO"})
    if not target:
        raise FoodShareAPIException(404, "NOT_FOUND", "NGO user not found.")

    new_status = "VERIFIED" if approve else "REJECTED"
    now = datetime.now(timezone.utc)
    actor_id = ObjectId(str(actor.get("_id") or actor.get("id")))

    result = await db.users.find_one_and_update(
        {"_id": ObjectId(target_user_id)},
        {
            "$set": {
                "ngo_profile.verification_status": new_status,
                "ngo_profile.verified_by":         actor_id,
                "ngo_profile.verified_at":          now,
                "updated_at":                       now,
            }
        },
        return_document=True,
    )
    if not result:
        raise FoodShareAPIException(404, "NOT_FOUND", "User not found.")
    return _ser_user(result)


# ---------------------------------------------------------------------------
# Admin donation management
# ---------------------------------------------------------------------------

async def admin_list_donations(
    actor: Dict[str, Any],
    status: Optional[str] = None,
    city: Optional[str] = None,
    food_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db=None,
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/donations
    Admin can see all donations with optional filters.
    """
    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    limit = min(max(1, limit), 100)
    page  = max(1, page)
    skip  = (page - 1) * limit

    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if city:
        query["pickup_address.city"] = {"$regex": f"^{city.strip()}$", "$options": "i"}
    if food_type:
        query["food_type"] = food_type

    total  = await db.donations.count_documents(query)
    cursor = db.donations.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items  = await cursor.to_list(length=limit)

    # Serialize ObjectIds in donation docs
    from app.services.donation_service import serialize_donation
    return {
        "items": [serialize_donation(d) for d in items],
        "total": total,
        "page":  page,
        "limit": limit,
    }
