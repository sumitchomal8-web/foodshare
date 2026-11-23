from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends

from app.database import db
from app.schemas.user import UserResponse, UserUpdate
from app.utils.dependencies import get_current_user
from app.utils.errors import AppError

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    try:
        user_id = ObjectId(current_user["user_id"])
    except Exception:
        raise AppError(status_code=401, detail="Invalid user ID in token", code="INVALID_TOKEN")

    user = await db.users.find_one({"_id": user_id})

    if not user:
        raise AppError(status_code=404, detail="User not found", code="USER_NOT_FOUND")

    if not user.get("is_active", False):
        raise AppError(status_code=403, detail="Account is disabled", code="ACCOUNT_DISABLED")

    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)

    return UserResponse(**user)

@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        user_id = ObjectId(current_user["user_id"])
    except Exception:
        raise AppError(status_code=401, detail="Invalid user ID in token", code="INVALID_TOKEN")

    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise AppError(status_code=404, detail="User not found", code="USER_NOT_FOUND")

    if not user.get("is_active", False):
        raise AppError(status_code=403, detail="Account is disabled", code="ACCOUNT_DISABLED")

    updates = {}
    if update_data.name is not None:
        updates["name"] = update_data.name
    if update_data.phone is not None:
        updates["phone"] = update_data.phone
    if update_data.address is not None:
        addr_dict = user.get("address", {})
        if update_data.address.street is not None:
            addr_dict["street"] = update_data.address.street
        if update_data.address.city is not None:
            addr_dict["city"] = update_data.address.city
        if update_data.address.state is not None:
            addr_dict["state"] = update_data.address.state
        if update_data.address.pincode is not None:
            addr_dict["pincode"] = update_data.address.pincode
        updates["address"] = addr_dict

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.users.update_one({"_id": user_id}, {"$set": updates})
        user = await db.users.find_one({"_id": user_id})

    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)

    return UserResponse(**user)
