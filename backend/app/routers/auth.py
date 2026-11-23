from datetime import datetime, timezone

from fastapi import APIRouter
from pymongo.errors import DuplicateKeyError

from app.database import db
from app.schemas.user import Token, UserRegister, UserResponse, UserLogin
from app.utils.errors import AppError
from app.utils.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(user_data: UserRegister):
    email = str(user_data.email).lower()

    existing_user = await db.users.find_one({"email": email})

    if existing_user:
        raise AppError(
            status_code=409,
            detail="Email already registered",
            code="EMAIL_EXISTS",
        )

    user_document = user_data.model_dump()

    password = user_document.pop("password")

    user_document["password_hash"] = hash_password(password)

    user_document["email"] = email

    user_document["is_active"] = True
    now = datetime.now(timezone.utc)
    user_document["created_at"] = now
    user_document["updated_at"] = now

    if user_document["role"] == "NGO":
        user_document["ngo_profile"]["verification_status"] = "PENDING"
        user_document["ngo_profile"]["verified_by"] = None
        user_document["ngo_profile"]["verified_at"] = None

    try:
        result = await db.users.insert_one(user_document)

    except DuplicateKeyError:
        raise AppError(
            status_code=409, 
            detail="Email already registered",
            code="EMAIL_EXISTS",
        )

    response_document = user_document.copy()

    response_document.pop("_id", None)
    response_document.pop("password_hash", None)

    response_document["id"] = str(result.inserted_id)

    return UserResponse(**response_document)

@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin):
    email = str(user_data.email).lower()

    user = await db.users.find_one({"email": email})

    if user is None or not verify_password(
        user_data.password,
        user["password_hash"],
    ):
        raise AppError(
            status_code=401,
            detail="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )

    if not user.get("is_active", False):
        raise AppError(
            status_code=403,
            detail="Account is disabled",
            code="ACCOUNT_DISABLED",
        )

    access_token = create_access_token(
        user_id=str(user["_id"]),
        role=user["role"],
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
    )
