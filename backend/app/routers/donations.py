"""
app/routers/donations.py  — Person B
Spec Section 7: Donations & NGO routes.

Routes owned here:
  GET  /api/v1/donations              Browse available (NGO, ADMIN)
  GET  /api/v1/donations/{id}         Detail view (access-controlled)
  POST /api/v1/donations/{id}/accept  NGO accepts
  POST /api/v1/donations/{id}/pickup  NGO marks picked-up
  POST /api/v1/donations/{id}/distribute  NGO marks distributed
  POST /api/v1/donations/{id}/complete    NGO or ADMIN marks complete

NOT owned here (Person A — routers/donor.py):
  POST /api/v1/donations              Create donation
  GET  /api/v1/donations/mine         Donor's own list

ROUTE ORDER: /mine must be registered before /{id}.
When Person A's donor.py and this router are both mounted on the same
prefix, FastAPI evaluates routes in registration order. Person A must
include their router first (or the shared prefix must be on donor.py).
See note at the bottom of this file.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import db
from app.schemas.donation import (
    DonationResponse,
    DonationStatus,
    PaginatedDonationsResponse,
)
from app.services.donation_service import (
    accept_donation,
    get_donation_detail,
    list_donations,
    transition_donation_status,
)
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/donations", tags=["Donations"])


# ---------------------------------------------------------------------------
# Browse (NGO / ADMIN)
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedDonationsResponse)
async def browse_donations(
    status: Optional[str] = Query(None, description="Filter by donation status"),
    city: Optional[str] = Query(None, description="Filter by pickup city"),
    food_type: Optional[str] = Query(None, description="Filter by food type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_role("NGO", "ADMIN")),
):
    """
    GET /api/v1/donations
    Browse available donations. NGOs default to unexpired AVAILABLE.
    ADMINs see all statuses unless filtered.
    """
    return await list_donations(
        actor=current_user,
        status=status,
        city=city,
        food_type=food_type,
        page=page,
        limit=limit,
        db=db,
    )


# ---------------------------------------------------------------------------
# Detail (owner donor, assigned NGO, ADMIN, or any NGO for AVAILABLE)
# ---------------------------------------------------------------------------

@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    GET /api/v1/donations/{id}
    Access: owner donor, assigned NGO, ADMIN, or any NGO when AVAILABLE.
    """
    return await get_donation_detail(
        donation_id=donation_id,
        actor=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Status-transition actions
# ---------------------------------------------------------------------------

@router.post("/{donation_id}/accept", response_model=DonationResponse)
async def accept(
    donation_id: str,
    current_user: dict = Depends(require_role("NGO")),
):
    """
    POST /api/v1/donations/{id}/accept
    Verified NGO claims an AVAILABLE donation (atomic, first-accept-wins).
    """
    return await accept_donation(
        donation_id=donation_id,
        actor=current_user,
        db=db,
    )


@router.post("/{donation_id}/pickup", response_model=DonationResponse)
async def mark_picked_up(
    donation_id: str,
    current_user: dict = Depends(require_role("NGO")),
):
    """
    POST /api/v1/donations/{id}/pickup
    Assigned NGO marks ACCEPTED -> PICKED_UP.
    """
    return await transition_donation_status(
        donation_id=donation_id,
        target_status=DonationStatus.PICKED_UP,
        actor=current_user,
        db=db,
    )


@router.post("/{donation_id}/distribute", response_model=DonationResponse)
async def mark_distributed(
    donation_id: str,
    current_user: dict = Depends(require_role("NGO")),
):
    """
    POST /api/v1/donations/{id}/distribute
    Assigned NGO marks PICKED_UP -> DISTRIBUTED.
    """
    return await transition_donation_status(
        donation_id=donation_id,
        target_status=DonationStatus.DISTRIBUTED,
        actor=current_user,
        db=db,
    )


@router.post("/{donation_id}/complete", response_model=DonationResponse)
async def mark_completed(
    donation_id: str,
    current_user: dict = Depends(require_role("NGO", "ADMIN")),
):
    """
    POST /api/v1/donations/{id}/complete
    Assigned NGO or ADMIN marks DISTRIBUTED -> COMPLETED.
    """
    return await transition_donation_status(
        donation_id=donation_id,
        target_status=DonationStatus.COMPLETED,
        actor=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# NOTE ON ROUTE ORDER (spec Section 7, last paragraph)
# ---------------------------------------------------------------------------
# GET /api/v1/donations/mine  (Person A, donor.py) must be registered
# BEFORE GET /api/v1/donations/{donation_id}  (this file).
# In app/main.py, include Person A's donor router BEFORE this one, or
# Person A must use a fully-qualified prefix (/api/v1/donations/mine)
# on a separate APIRouter to avoid ambiguity.
