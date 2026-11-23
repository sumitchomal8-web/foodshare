from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.utils.errors import AppError
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise AppError(
            status_code=401,
            detail="Not authenticated",
            code="NOT_AUTHENTICATED",
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            raise AppError(
                status_code=401,
                detail="Invalid access token",
                code="INVALID_TOKEN",
            )
        return {
            "user_id": user_id,
            "role": role,
        }
    except JWTError:
        raise AppError(
            status_code=401,
            detail="Invalid or expired access token",
            code="INVALID_TOKEN",
        )
