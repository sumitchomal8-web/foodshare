"""
tests/test_admin_api.py  — Person B
API-level tests for admin routes.

Uses FastAPI dependency_overrides for auth and service-layer mocks.
No live DB or JWT required.

Covered routes:
  GET   /api/v1/admin/users
  PATCH /api/v1/admin/users/{id}/status
  GET   /api/v1/admin/ngos/pending
  POST  /api/v1/admin/ngos/{id}/verify
  GET   /api/v1/admin/donations
  GET   /api/v1/admin/stats
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from bson import ObjectId

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.dependencies import get_current_user, require_role
from app.services.donation_service import FoodShareAPIException


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
ADMIN_ID  = str(ObjectId())
NGO_ID    = str(ObjectId())
DONOR_ID  = str(ObjectId())

ADMIN_USER = {
    "_id": ADMIN_ID, "id": ADMIN_ID,
    "role": "ADMIN", "is_active": True,
    "ngo_profile": None,
}

SAMPLE_USER = {
    "id":         NGO_ID,
    "name":       "Food Bank NGO",
    "email":      "ngo@example.com",
    "role":       "NGO",
    "phone":      "9876543210",
    "address":    {"street": "1 Park St", "city": "Chennai", "state": "TN", "pincode": "600001"},
    "ngo_profile": {
        "organization_name":   "Food Bank",
        "org_type":            "NGO",
        "registration_number": "REG123",
        "verification_status": "PENDING",
        "verified_by":         None,
        "verified_at":         None,
    },
    "is_active":   True,
    "created_at":  MOCK_NOW.isoformat(),
    "updated_at":  MOCK_NOW.isoformat(),
}

SAMPLE_STATS = {
    "users": {
        "total": 50, "donors": 30, "ngos": 18,
        "verified_ngos": 12, "admins": 2,
    },
    "donations": {
        "total": 200, "available": 40, "accepted": 20,
        "picked_up": 15, "distributed": 10,
        "completed": 100, "cancelled": 10, "expired": 5,
    },
    "computed_at": MOCK_NOW.isoformat(),
}

PAGINATED_USERS = {"items": [SAMPLE_USER], "total": 1, "page": 1, "limit": 20}
PAGINATED_ZERO  = {"items": [],            "total": 0, "page": 1, "limit": 20}


def override_as_admin():
    async def _user():
        return ADMIN_USER
    def _role(*roles):
        async def _checker():
            return ADMIN_USER
        return _checker
    return {get_current_user: _user, require_role: _role}


def override_as_ngo():
    ngo = {"_id": NGO_ID, "id": NGO_ID, "role": "NGO", "is_active": True}
    async def _user():
        return ngo
    def _role(*roles):
        async def _checker():
            if "NGO" not in roles:
                from fastapi import HTTPException
                raise HTTPException(403, detail={"detail": "Forbidden", "code": "FORBIDDEN"})
            return ngo
        return _checker
    return {get_current_user: _user, require_role: _role}


@pytest.fixture(autouse=True)
def no_lifespan_db(monkeypatch):
    """Patch create_indexes so TestClient startup never touches MongoDB."""
    monkeypatch.setattr("app.main.create_indexes", AsyncMock())


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users
# ---------------------------------------------------------------------------

def test_admin_list_users_returns_200():
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.list_users", new=AsyncMock(return_value=PAGINATED_USERS)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/users")
    app.dependency_overrides = {}
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == NGO_ID


def test_admin_list_users_with_role_filter():
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.list_users", new=AsyncMock(return_value=PAGINATED_USERS)) as m:
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/users?role=NGO&is_active=true")
    app.dependency_overrides = {}
    assert res.status_code == 200
    m.assert_called_once()
    kw = m.call_args.kwargs
    assert kw["role"] == "NGO"
    assert kw["is_active"] is True


def test_non_admin_cannot_list_users():
    app.dependency_overrides = override_as_ngo()
    with patch("app.routers.admin.list_users", new=AsyncMock(return_value=PAGINATED_ZERO)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/users")
    app.dependency_overrides = {}
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/users/{id}/status
# ---------------------------------------------------------------------------

def test_admin_deactivate_user():
    deactivated = {**SAMPLE_USER, "is_active": False}
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.set_user_active", new=AsyncMock(return_value=deactivated)):
        with TestClient(app) as client:
            res = client.patch(f"/api/v1/admin/users/{NGO_ID}/status", json={"is_active": False})
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_admin_activate_user():
    activated = {**SAMPLE_USER, "is_active": True}
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.set_user_active", new=AsyncMock(return_value=activated)):
        with TestClient(app) as client:
            res = client.patch(f"/api/v1/admin/users/{NGO_ID}/status", json={"is_active": True})
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["is_active"] is True


def test_admin_status_user_not_found_returns_404():
    app.dependency_overrides = override_as_admin()
    with patch(
        "app.routers.admin.set_user_active",
        new=AsyncMock(side_effect=FoodShareAPIException(404, "NOT_FOUND", "User not found.")),
    ):
        with TestClient(app) as client:
            res = client.patch(f"/api/v1/admin/users/{str(ObjectId())}/status", json={"is_active": False})
    app.dependency_overrides = {}
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /api/v1/admin/ngos/pending
# ---------------------------------------------------------------------------

def test_admin_list_pending_ngos():
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.list_pending_ngos", new=AsyncMock(return_value=PAGINATED_USERS)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/ngos/pending")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_admin_pending_ngos_empty():
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.list_pending_ngos", new=AsyncMock(return_value=PAGINATED_ZERO)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/ngos/pending")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /api/v1/admin/ngos/{id}/verify
# ---------------------------------------------------------------------------

def test_admin_approve_ngo():
    verified = {
        **SAMPLE_USER,
        "ngo_profile": {**SAMPLE_USER["ngo_profile"], "verification_status": "VERIFIED"},
    }
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.verify_ngo", new=AsyncMock(return_value=verified)):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/admin/ngos/{NGO_ID}/verify", json={"approve": True})
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["ngo_profile"]["verification_status"] == "VERIFIED"


def test_admin_reject_ngo():
    rejected = {
        **SAMPLE_USER,
        "ngo_profile": {**SAMPLE_USER["ngo_profile"], "verification_status": "REJECTED"},
    }
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.verify_ngo", new=AsyncMock(return_value=rejected)):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/admin/ngos/{NGO_ID}/verify", json={"approve": False})
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["ngo_profile"]["verification_status"] == "REJECTED"


def test_admin_verify_ngo_not_found_returns_404():
    app.dependency_overrides = override_as_admin()
    with patch(
        "app.routers.admin.verify_ngo",
        new=AsyncMock(side_effect=FoodShareAPIException(404, "NOT_FOUND", "NGO user not found.")),
    ):
        with TestClient(app) as client:
            res = client.post(f"/api/v1/admin/ngos/{str(ObjectId())}/verify", json={"approve": True})
    app.dependency_overrides = {}
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /api/v1/admin/donations
# ---------------------------------------------------------------------------

def test_admin_list_all_donations():
    paged = {"items": [], "total": 0, "page": 1, "limit": 20}
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.admin_list_donations", new=AsyncMock(return_value=paged)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/donations")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_admin_list_donations_with_filters():
    paged = {"items": [], "total": 0, "page": 1, "limit": 20}
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.admin_list_donations", new=AsyncMock(return_value=paged)) as m:
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/donations?status=AVAILABLE&city=Mumbai")
    app.dependency_overrides = {}
    assert res.status_code == 200
    kw = m.call_args.kwargs
    assert kw["status"] == "AVAILABLE"
    assert kw["city"] == "Mumbai"


# ---------------------------------------------------------------------------
# GET /api/v1/admin/stats
# ---------------------------------------------------------------------------

def test_admin_stats_returns_platform_data():
    app.dependency_overrides = override_as_admin()
    with patch("app.routers.admin.get_platform_stats", new=AsyncMock(return_value=SAMPLE_STATS)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/stats")
    app.dependency_overrides = {}
    assert res.status_code == 200
    body = res.json()
    assert body["users"]["total"] == 50
    assert body["donations"]["completed"] == 100
    assert body["donations"]["total"] == 200


def test_admin_stats_non_admin_forbidden():
    app.dependency_overrides = override_as_ngo()
    with patch("app.routers.admin.get_platform_stats", new=AsyncMock(return_value=SAMPLE_STATS)):
        with TestClient(app) as client:
            res = client.get("/api/v1/admin/stats")
    app.dependency_overrides = {}
    assert res.status_code == 403
