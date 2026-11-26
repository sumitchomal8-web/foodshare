"""
app/routers/auth.py  — Person A
Spec Section 7: POST /api/v1/auth/register  and  POST /api/v1/auth/login
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.database import db
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.donation_service import FoodShareAPIException
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _serialize_user(doc: dict) -> dict:
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    out.pop("password_hash", None)
    if out.get("ngo_profile") and out["ngo_profile"].get("verified_by"):
        out["ngo_profile"]["verified_by"] = str(out["ngo_profile"]["verified_by"])
    return out


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest):
    # Validate role restrictions
    if body.role.value == "NGO" and not body.ngo_profile:
        raise FoodShareAPIException(400, "VALIDATION_ERROR", "ngo_profile is required when role is NGO.")
    if body.role.value == "DONOR" and body.ngo_profile:
        raise FoodShareAPIException(400, "VALIDATION_ERROR", "ngo_profile must be absent when role is DONOR.")

    # Duplicate email check
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise FoodShareAPIException(409, "EMAIL_EXISTS", "An account with this email already exists.")

    now = datetime.now(timezone.utc)
    doc: dict = {
        "name":         body.name,
        "email":        body.email.lower(),
        "password_hash": hash_password(body.password),
        "role":         body.role.value,
        "phone":        body.phone,
        "address":      body.address.model_dump(),
        "ngo_profile":  None,
        "is_active":    True,
        "created_at":   now,
        "updated_at":   now,
    }

    if body.ngo_profile:
        doc["ngo_profile"] = {
            "organization_name":   body.ngo_profile.organization_name,
            "org_type":            body.ngo_profile.org_type.value,
            "registration_number": body.ngo_profile.registration_number,
            "verification_status": "PENDING",
            "verified_by":         None,
            "verified_at":         None,
        }

    result = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": result.inserted_id})
    return _serialize_user(created)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise FoodShareAPIException(401, "INVALID_CREDENTIALS", "Incorrect email or password.")

    if not user.get("is_active", True):
        raise FoodShareAPIException(403, "ACCOUNT_DISABLED", "Your account has been disabled.")

    token = create_access_token(str(user["_id"]), user["role"])
    return {"access_token": token, "token_type": "bearer"}
