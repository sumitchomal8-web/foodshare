"""
app/utils/dependencies.py  — Person A
Spec Section 6.1: FastAPI auth dependencies.

  get_current_user() -> dict
      Reads the Bearer token from Authorization header, decodes it,
      fetches the user document from MongoDB, and returns it with _id
      as ObjectId.
      Errors: 401 TOKEN_INVALID, 403 ACCOUNT_DISABLED

  require_role(*roles) -> Callable[[dict], dict]
      Dependency factory. Returns the user dict or raises 403 FORBIDDEN.
      Usage: Depends(require_role("NGO"))  or  Depends(require_role("NGO","ADMIN"))
"""
from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.database import db
from app.utils.security import decode_access_token

_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(_oauth2)) -> dict:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid or expired token.", "code": "TOKEN_INVALID"},
        )

    user_id: str = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid or expired token.", "code": "TOKEN_INVALID"},
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"detail": "Invalid or expired token.", "code": "TOKEN_INVALID"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail={"detail": "Your account has been disabled.", "code": "ACCOUNT_DISABLED"},
        )

    return user


def require_role(*roles: str):
    """
    Dependency factory.
    Usage: current_user: dict = Depends(require_role("NGO"))
    Returns the user dict or raises 403 FORBIDDEN.
    """
    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail={"detail": "You do not have permission to perform this action.", "code": "FORBIDDEN"},
            )
        return user
    return _checker
