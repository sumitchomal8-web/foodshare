"""
app/routers/users.py  — Person A
Spec Section 7:
  GET  /api/v1/users/me   — return current user's profile
  PUT  /api/v1/users/me   — update current user's profile
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from app.database import db
from app.schemas.user import AddressIn, UserResponse
from app.utils.dependencies import get_current_user
from bson import ObjectId

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


class ProfileUpdate(BaseModel):
    name:    Optional[str] = None
    phone:   Optional[str] = None
    address: Optional[AddressIn] = None


def _serialize(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("password_hash", None)
    if out.get("ngo_profile") and out["ngo_profile"].get("verified_by"):
        out["ngo_profile"]["verified_by"] = str(out["ngo_profile"]["verified_by"])
    return out


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return _serialize(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(body: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if body.name    is not None: updates["name"]    = body.name
    if body.phone   is not None: updates["phone"]   = body.phone
    if body.address is not None: updates["address"] = body.address.model_dump()

    updated = await db.users.find_one_and_update(
        {"_id": current_user["_id"]},
        {"$set": updates},
        return_document=True,
    )
    return _serialize(updated)
