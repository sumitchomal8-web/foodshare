"""
tests/test_donations_api.py  — Person B
API-level tests for donation and NGO routes.

Uses FastAPI's test client with dependency overrides and service-layer
mocks — no live database or JWT needed.

Covered routes:
  GET  /api/v1/donations
  GET  /api/v1/donations/{id}
  POST /api/v1/donations/{id}/accept
  POST /api/v1/donations/{id}/pickup
  POST /api/v1/donations/{id}/distribute
  POST /api/v1/donations/{id}/complete
  GET  /api/v1/ngo/donations
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from bson import ObjectId

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user, require_role
from app.schemas.donation import DonationStatus
from app.services.donation_service import FoodShareAPIException


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)

DONATION_ID = str(ObjectId())
DONOR_ID    = str(ObjectId())
NGO_ID      = str(ObjectId())
ADMIN_ID    = str(ObjectId())

SAMPLE_DONATION = {
    "id": DONATION_ID,
    "donor_id": DONOR_ID,
    "title": "Fresh Idly, 50 plates",
    "food_type": "COOKED",
    "quantity": 50.0,
    "quantity_unit": "PLATES",
    "description": None,
    "pickup_address": {"street": "12 MG Road", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"},
    "available_from": MOCK_NOW.isoformat(),
    "expires_at": MOCK_NOW.replace(hour=18).isoformat(),
    "status": DonationStatus.AVAILABLE.value,
    "accepted_by": None,
    "accepted_at": None,
    "picked_up_at": None,
    "distributed_at": None,
    "completed_at": None,
    "cancelled_at": None,
    "status_history": [],
    "created_at": MOCK_NOW.isoformat(),
    "updated_at": MOCK_NOW.isoformat(),
}

VERIFIED_NGO_USER = {
    "_id": NGO_ID, "id": NGO_ID,
    "role": "NGO", "is_active": True,
    "ngo_profile": {"organization_name": "Food Bank", "org_type": "NGO", "verification_status": "VERIFIED"},
}

ADMIN_USER = {
    "_id": ADMIN_ID, "id": ADMIN_ID,
    "role": "ADMIN", "is_active": True,
    "ngo_profile": None,
}


def override_as(user: dict):
    """Return dependency overrides that make the app act as `user`."""
    async def _user():
        return user

    def _role(*roles):
        async def _checker():
            if user.get("role") not in roles:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={"detail": "Forbidden", "code": "FORBIDDEN"},
                )
            return user
        return _checker

    return {get_current_user: _user, require_role: _role}


@pytest.fixture(autouse=True)
def no_lifespan_db(monkeypatch):
    """Patch create_indexes so TestClient startup never touches MongoDB."""
    monkeypatch.setattr("app.main.create_indexes", AsyncMock())


# ---------------------------------------------------------------------------
# GET /api/v1/donations  — browse
# ---------------------------------------------------------------------------

def test_browse_donations_as_ngo_returns_200():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.list_donations",
        new=AsyncMock(return_value={"items": [SAMPLE_DONATION], "total": 1, "page": 1, "limit": 20}),
    ):
        with TestClient(app) as client:
            res = client.get("/api/v1/donations")
    app.dependency_overrides = {}
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == DONATION_ID


def test_browse_donations_as_admin_returns_200():
    app.dependency_overrides = override_as(ADMIN_USER)
    with patch(
        "app.routers.donations.list_donations",
        new=AsyncMock(return_value={"items": [], "total": 0, "page": 1, "limit": 20}),
    ):
        with TestClient(app) as client:
            res = client.get("/api/v1/donations")
    app.dependency_overrides = {}
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/donations/{id}  — detail
# ---------------------------------------------------------------------------

def test_get_donation_detail_success():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.get_donation_detail",
        new=AsyncMock(return_value=SAMPLE_DONATION),
    ):
        with TestClient(app) as client:
            res = client.get(f"/api/v1/donations/{DONATION_ID}")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["id"] == DONATION_ID


def test_get_donation_detail_not_found_returns_404():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.get_donation_detail",
        new=AsyncMock(side_effect=FoodShareAPIException(404, "NOT_FOUND", "Donation not found.")),
    ):
        with TestClient(app) as client:
            res = client.get(f"/api/v1/donations/{DONATION_ID}")
    app.dependency_overrides = {}
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_get_donation_detail_forbidden_returns_403():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.get_donation_detail",
        new=AsyncMock(side_effect=FoodShareAPIException(403, "FORBIDDEN", "No permission.")),
    ):
        with TestClient(app) as client:
            res = client.get(f"/api/v1/donations/{DONATION_ID}")
    app.dependency_overrides = {}
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# POST /api/v1/donations/{id}/accept
# ---------------------------------------------------------------------------

def test_accept_donation_success_returns_200():
    accepted = {**SAMPLE_DONATION, "status": DonationStatus.ACCEPTED.value, "accepted_by": NGO_ID}
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.accept_donation",
        new=AsyncMock(return_value=accepted),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/accept")
    app.dependency_overrides = {}
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == DonationStatus.ACCEPTED.value
    assert body["accepted_by"] == NGO_ID


def test_accept_donation_already_accepted_returns_409():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.accept_donation",
        new=AsyncMock(side_effect=FoodShareAPIException(409, "ALREADY_ACCEPTED", "Already claimed.")),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/accept")
    app.dependency_overrides = {}
    assert res.status_code == 409
    assert res.json()["code"] == "ALREADY_ACCEPTED"


def test_accept_donation_unverified_ngo_returns_403():
    unverified = {**VERIFIED_NGO_USER, "ngo_profile": {"verification_status": "PENDING"}}
    app.dependency_overrides = override_as(unverified)
    with patch(
        "app.routers.donations.accept_donation",
        new=AsyncMock(side_effect=FoodShareAPIException(403, "NGO_NOT_VERIFIED", "Not verified.")),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/accept")
    app.dependency_overrides = {}
    assert res.status_code == 403
    assert res.json()["code"] == "NGO_NOT_VERIFIED"


# ---------------------------------------------------------------------------
# POST /api/v1/donations/{id}/pickup  /distribute  /complete
# ---------------------------------------------------------------------------

def test_pickup_success():
    picked_up = {**SAMPLE_DONATION, "status": DonationStatus.PICKED_UP.value}
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(return_value=picked_up),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/pickup")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["status"] == DonationStatus.PICKED_UP.value


def test_distribute_success():
    distributed = {**SAMPLE_DONATION, "status": DonationStatus.DISTRIBUTED.value}
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(return_value=distributed),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/distribute")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["status"] == DonationStatus.DISTRIBUTED.value


def test_complete_success_as_ngo():
    completed = {**SAMPLE_DONATION, "status": DonationStatus.COMPLETED.value}
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(return_value=completed),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/complete")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["status"] == DonationStatus.COMPLETED.value


def test_complete_success_as_admin():
    completed = {**SAMPLE_DONATION, "status": DonationStatus.COMPLETED.value}
    app.dependency_overrides = override_as(ADMIN_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(return_value=completed),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/complete")
    app.dependency_overrides = {}
    assert res.status_code == 200


def test_wrong_ngo_pickup_returns_403():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(side_effect=FoodShareAPIException(403, "FORBIDDEN", "Not the assigned NGO.")),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/pickup")
    app.dependency_overrides = {}
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_invalid_transition_returns_409():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.donations.transition_donation_status",
        new=AsyncMock(
            side_effect=FoodShareAPIException(409, "INVALID_STATUS_TRANSITION", "Bad transition.")
        ),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/donations/{DONATION_ID}/complete")
    app.dependency_overrides = {}
    assert res.status_code == 409
    assert res.json()["code"] == "INVALID_STATUS_TRANSITION"


# ---------------------------------------------------------------------------
# GET /api/v1/ngo/donations
# ---------------------------------------------------------------------------

def test_ngo_list_own_donations():
    accepted_donation = {**SAMPLE_DONATION, "status": DonationStatus.ACCEPTED.value, "accepted_by": NGO_ID}
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.ngo.list_ngo_donations",
        new=AsyncMock(return_value={"items": [accepted_donation], "total": 1, "page": 1, "limit": 20}),
    ):
        with TestClient(app) as client:
            res = client.get("/api/v1/ngo/donations")
    app.dependency_overrides = {}
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["accepted_by"] == NGO_ID


def test_ngo_list_filtered_by_status():
    app.dependency_overrides = override_as(VERIFIED_NGO_USER)
    with patch(
        "app.routers.ngo.list_ngo_donations",
        new=AsyncMock(return_value={"items": [], "total": 0, "page": 1, "limit": 20}),
    ) as mock_svc:
        with TestClient(app) as client:
            res = client.get("/api/v1/ngo/donations?status=COMPLETED")
    app.dependency_overrides = {}
    assert res.status_code == 200
    mock_svc.assert_called_once()
    call_kwargs = mock_svc.call_args.kwargs
    assert call_kwargs["status"] == "COMPLETED"
