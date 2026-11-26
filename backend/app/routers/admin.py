"""
app/routers/admin.py  — Person B
Spec Section 7: Admin routes.

Routes owned here:
  GET   /api/v1/admin/users                  List all users (filter: role, is_active)
  PATCH /api/v1/admin/users/{id}/status      Activate / deactivate a user
  GET   /api/v1/admin/ngos/pending           List pending NGO verifications
  POST  /api/v1/admin/ngos/{id}/verify       Approve / reject an NGO
  GET   /api/v1/admin/donations              List all donations (filter: status, city, food_type)
  GET   /api/v1/admin/stats                  Platform statistics

All routes require role ADMIN, enforced via require_role("ADMIN").
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import db
from app.schemas.admin import (
    NgoVerificationRequest,
    PaginatedUsersResponse,
    PlatformStats,
    UserAdminResponse,
    UserStatusUpdate,
)
from app.schemas.donation import PaginatedDonationsResponse
from app.services.admin_service import (
    admin_list_donations,
    list_pending_ngos,
    list_users,
    set_user_active,
    verify_ngo,
)
from app.services.stats_service import get_platform_stats
from app.utils.dependencies import require_role

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get("/users", response_model=PaginatedUsersResponse)
async def admin_list_users(
    role: Optional[str] = Query(None, description="Filter by role: DONOR, NGO, ADMIN"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    GET /api/v1/admin/users
    Paginated user list. Optionally filter by role and/or is_active.
    """
    return await list_users(
        actor=current_user,
        role=role,
        is_active=is_active,
        page=page,
        limit=limit,
        db=db,
    )


@router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
async def update_user_status(
    user_id: str,
    body: UserStatusUpdate,
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    PATCH /api/v1/admin/users/{id}/status
    Activate or deactivate a user. Body: { "is_active": true|false }
    """
    return await set_user_active(
        actor=current_user,
        target_user_id=user_id,
        is_active=body.is_active,
        db=db,
    )


# ---------------------------------------------------------------------------
# NGO verification
# ---------------------------------------------------------------------------

@router.get("/ngos/pending", response_model=PaginatedUsersResponse)
async def list_ngos_pending_verification(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    GET /api/v1/admin/ngos/pending
    Lists NGO accounts with verification_status=PENDING, oldest first.
    """
    return await list_pending_ngos(
        actor=current_user,
        page=page,
        limit=limit,
        db=db,
    )


@router.post("/ngos/{user_id}/verify", response_model=UserAdminResponse)
async def verify_ngo_account(
    user_id: str,
    body: NgoVerificationRequest,
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    POST /api/v1/admin/ngos/{id}/verify
    Approve or reject an NGO's verification. Body: { "approve": true|false }
    Sets ngo_profile.verification_status to VERIFIED or REJECTED and
    records verified_by and verified_at.
    """
    return await verify_ngo(
        actor=current_user,
        target_user_id=user_id,
        approve=body.approve,
        db=db,
    )


# ---------------------------------------------------------------------------
# Admin donation management
# ---------------------------------------------------------------------------

@router.get("/donations", response_model=PaginatedDonationsResponse)
async def admin_donations(
    status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    food_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    GET /api/v1/admin/donations
    Admin view of all donations across all statuses, with optional filters.
    """
    return await admin_list_donations(
        actor=current_user,
        status=status,
        city=city,
        food_type=food_type,
        page=page,
        limit=limit,
        db=db,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=PlatformStats)
async def platform_stats(
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    GET /api/v1/admin/stats
    Platform-wide counts: users by role, donations by status.
    All aggregation queries run concurrently via asyncio.gather.
    """
    return await get_platform_stats(actor=current_user, db=db)
