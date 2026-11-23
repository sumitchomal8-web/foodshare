from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends

from app.database import db
from app.schemas.user import UserResponse, NgoVerificationUpdate
from app.utils.dependencies import require_role
from app.utils.errors import AppError

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/ngos/pending", response_model=list[UserResponse])
async def list_pending_ngos(admin_user: dict = Depends(require_role("ADMIN"))):
    cursor = db.users.find({
        "role": "NGO",
        "ngo_profile.verification_status": "PENDING",
    })
    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc.pop("password_hash", None)
        results.append(UserResponse(**doc))
    return results

@router.patch("/ngos/{ngo_id}/verify", response_model=UserResponse)
async def verify_ngo(
    ngo_id: str,
    verification: NgoVerificationUpdate,
    admin_user: dict = Depends(require_role("ADMIN")),
):
    try:
        oid = ObjectId(ngo_id)
    except Exception:
        raise AppError(status_code=400, detail="Invalid NGO ID", code="INVALID_ID")

    ngo = await db.users.find_one({"_id": oid, "role": "NGO"})
    if not ngo:
        raise AppError(status_code=404, detail="NGO not found", code="NGO_NOT_FOUND")

    now = datetime.now(timezone.utc)
    update_doc = {
        "ngo_profile.verification_status": verification.status,
        "ngo_profile.verified_by": admin_user["user_id"],
        "ngo_profile.verified_at": now,
        "updated_at": now,
    }

    await db.users.update_one({"_id": oid}, {"$set": update_doc})
    updated_ngo = await db.users.find_one({"_id": oid})

    updated_ngo["id"] = str(updated_ngo.pop("_id"))
    updated_ngo.pop("password_hash", None)

    return UserResponse(**updated_ngo)
