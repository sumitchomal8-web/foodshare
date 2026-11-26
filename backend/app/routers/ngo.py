"""
app/routers/ngo.py  — Person B
Spec Section 7: NGO routes.

Routes owned here:
  GET /api/v1/ngo/donations   NGO's accepted donations, filterable by status
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import db
from app.schemas.donation import PaginatedDonationsResponse
from app.services.donation_service import list_ngo_donations
from app.utils.dependencies import require_role

router = APIRouter(prefix="/api/v1/ngo", tags=["NGO"])


@router.get("/donations", response_model=PaginatedDonationsResponse)
async def get_my_ngo_donations(
    status: Optional[str] = Query(
        None,
        description="Filter by donation status (e.g. ACCEPTED, PICKED_UP, COMPLETED)",
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("NGO")),
):
    """
    GET /api/v1/ngo/donations
    Returns all donations accepted by the calling NGO, newest first.
    Optional ?status= filter to narrow by lifecycle stage.
    """
    return await list_ngo_donations(
        actor=current_user,
        status=status,
        page=page,
        limit=limit,
        db=db,
    )
