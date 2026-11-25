from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.database import db
from app.schemas.user import UserResponse, UserUpdate
from app.utils.dependencies import get_current_user
from app.utils.errors import AppError

router = APIRouter(prefix="/users", tags=["Users"])


def user_to_response(doc: dict) -> UserResponse:
    user_data = doc.copy()
    user_data["id"] = str(user_data["_id"])

    ngo_profile = user_data.get("ngo_profile")
    if ngo_profile and ngo_profile.get("verified_by") is not None:
        user_data["ngo_profile"] = ngo_profile.copy()
        user_data["ngo_profile"]["verified_by"] = str(ngo_profile["verified_by"])

    return UserResponse(**user_data)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    raw_changes = update_data.model_dump(exclude_unset=True)
    changes = {k: v for k, v in raw_changes.items() if v is not None}

    if not changes:
        raise AppError(
            status_code=422,
            detail="No fields to update",
            code="VALIDATION_ERROR",
        )

    changes["updated_at"] = datetime.now(timezone.utc)

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": changes},
    )

    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    if not updated_user:
        raise AppError(
            status_code=404,
            detail="User not found",
            code="USER_NOT_FOUND",
        )
    return user_to_response(updated_user)


