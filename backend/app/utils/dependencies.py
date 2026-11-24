from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.database import db
from app.utils.errors import AppError
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise AppError(
            status_code=401,
            detail="Missing authentication token",
            code="TOKEN_INVALID",
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            raise AppError(
                status_code=401,
                detail="Invalid access token",
                code="TOKEN_INVALID",
            )
        user_id = ObjectId(sub)
    except (JWTError, InvalidId):
        raise AppError(
            status_code=401,
            detail="Invalid or expired access token",
            code="TOKEN_INVALID",
        )

    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise AppError(
            status_code=401,
            detail="User not found",
            code="TOKEN_INVALID",
        )

    if not user.get("is_active", False):
        raise AppError(
            status_code=403,
            detail="Account is disabled",
            code="ACCOUNT_DISABLED",
        )

    return user


def require_role(*allowed_roles: str):
    async def role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise AppError(
                status_code=403,
                detail="Insufficient permissions",
                code="FORBIDDEN",
            )
        return current_user

    return role_checker

