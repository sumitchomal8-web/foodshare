"""
tests/test_auth_donor_api.py
Integration & unit tests for Auth, Users, Donor routes and NGO service helpers.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.donation import DonationStatus
from app.services.ngo_service import assert_ngo_verified, is_ngo_verified
from app.services.donation_service import FoodShareAPIException
from app.utils.dependencies import get_current_user, require_role
from app.utils.security import create_access_token, hash_password, verify_password


MOCK_NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
DONOR_ID = str(ObjectId())
NGO_ID = str(ObjectId())

SAMPLE_DONOR = {
    "_id": ObjectId(DONOR_ID),
    "id": DONOR_ID,
    "name": "Jane Donor",
    "email": "jane@example.com",
    "role": "DONOR",
    "phone": "9876543210",
    "address": {"street": "10 Hill Rd", "city": "Mumbai", "state": "MH", "pincode": "400050"},
    "ngo_profile": None,
    "is_active": True,
    "created_at": MOCK_NOW,
    "updated_at": MOCK_NOW,
}


@pytest.fixture(autouse=True)
def no_lifespan_db(monkeypatch):
    monkeypatch.setattr("app.main.create_indexes", AsyncMock())


# ---------------------------------------------------------------------------
# NGO Service Unit Tests
# ---------------------------------------------------------------------------

def test_is_ngo_verified_true():
    user = {"role": "NGO", "is_active": True, "ngo_profile": {"verification_status": "VERIFIED"}}
    assert is_ngo_verified(user) is True


def test_is_ngo_verified_false_when_pending_or_inactive():
    assert is_ngo_verified({"role": "NGO", "is_active": False, "ngo_profile": {"verification_status": "VERIFIED"}}) is False
    assert is_ngo_verified({"role": "NGO", "is_active": True, "ngo_profile": {"verification_status": "PENDING"}}) is False
    assert is_ngo_verified({"role": "DONOR", "is_active": True, "ngo_profile": None}) is False


def test_assert_ngo_verified_raises():
    with pytest.raises(FoodShareAPIException) as exc:
        assert_ngo_verified({"role": "DONOR", "is_active": True})
    assert exc.value.status_code == 403

    with pytest.raises(FoodShareAPIException) as exc:
        assert_ngo_verified({"role": "NGO", "is_active": False})
    assert exc.value.code == "ACCOUNT_DISABLED"

    with pytest.raises(FoodShareAPIException) as exc:
        assert_ngo_verified({"role": "NGO", "is_active": True, "ngo_profile": {"verification_status": "PENDING"}})
    assert exc.value.code == "NGO_NOT_VERIFIED"


# ---------------------------------------------------------------------------
# Security Helpers Tests
# ---------------------------------------------------------------------------

def test_password_hashing():
    pw = "SuperSecret123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_token_creation_and_payload():
    token = create_access_token(user_id=DONOR_ID, role="DONOR")
    from app.utils.security import decode_access_token
    payload = decode_access_token(token)
    assert payload["sub"] == DONOR_ID
    assert payload["role"] == "DONOR"


# ---------------------------------------------------------------------------
# Auth API Tests (Register & Login)
# ---------------------------------------------------------------------------

def test_register_donor_success():
    new_id = ObjectId()
    created_doc = {
        "_id": new_id,
        "name": "Donor Bob",
        "email": "bob@example.com",
        "role": "DONOR",
        "phone": "9998887770",
        "address": {"street": "1 Main St", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        "ngo_profile": None,
        "is_active": True,
        "created_at": MOCK_NOW,
        "updated_at": MOCK_NOW,
    }
    with patch("app.routers.auth.db") as mock_db:
        mock_db.users.find_one = AsyncMock(side_effect=[None, created_doc])
        mock_db.users.insert_one = AsyncMock(return_value=MagicMock(inserted_id=new_id))

        payload = {
            "name": "Donor Bob",
            "email": "bob@example.com",
            "password": "password123",
            "phone": "9998887770",
            "role": "DONOR",
            "address": {"street": "1 Main St", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        }
        with TestClient(app) as client:
            res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "bob@example.com"
        assert data["role"] == "DONOR"
        assert "password_hash" not in data


def test_register_ngo_requires_profile():
    payload = {
        "name": "NGO Bob",
        "email": "ngo_bob@example.com",
        "password": "password123",
        "phone": "9998887770",
        "role": "NGO",
        "address": {"street": "1 Main St", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
    }
    with TestClient(app) as client:
        res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_register_duplicate_email_returns_409():
    with patch("app.routers.auth.db") as mock_db:
        mock_db.users.find_one = AsyncMock(return_value={"_id": ObjectId()})
        payload = {
            "name": "Duplicate User",
            "email": "existing@example.com",
            "password": "password123",
            "phone": "9998887770",
            "role": "DONOR",
            "address": {"street": "1 Main St", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        }
        with TestClient(app) as client:
            res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 409
        assert res.json()["code"] == "EMAIL_EXISTS"


def test_login_success():
    pw = "mySecretPassword123"
    hashed = hash_password(pw)
    user_doc = {
        "_id": ObjectId(DONOR_ID),
        "email": "donor@example.com",
        "password_hash": hashed,
        "role": "DONOR",
        "is_active": True,
    }
    with patch("app.routers.auth.db") as mock_db:
        mock_db.users.find_one = AsyncMock(return_value=user_doc)
        with TestClient(app) as client:
            res = client.post("/api/v1/auth/login", json={"email": "donor@example.com", "password": pw})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    with patch("app.routers.auth.db") as mock_db:
        mock_db.users.find_one = AsyncMock(return_value=None)
        with TestClient(app) as client:
            res = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
        assert res.status_code == 401
        assert res.json()["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Users /me API Tests
# ---------------------------------------------------------------------------

def test_get_user_me():
    async def _user():
        return SAMPLE_DONOR
    app.dependency_overrides = {get_current_user: _user}
    with TestClient(app) as client:
        res = client.get("/api/v1/users/me")
    app.dependency_overrides = {}
    assert res.status_code == 200
    assert res.json()["id"] == DONOR_ID
    assert res.json()["email"] == "jane@example.com"


# ---------------------------------------------------------------------------
# Donor Routes Tests (/donations, /donations/mine, /donations/{id}/cancel)
# ---------------------------------------------------------------------------

def test_donor_create_donation_success():
    async def _donor():
        return SAMPLE_DONOR
    def _role(*roles):
        async def _chk():
            return SAMPLE_DONOR
        return _chk

    app.dependency_overrides = {get_current_user: _donor, require_role: _role}

    donation_payload = {
        "title": "Fresh Dal and Rice",
        "food_type": "COOKED",
        "quantity": 25.0,
        "quantity_unit": "KG",
        "description": "Hot prepared meals",
        "pickup_address": {"street": "5 Park Rd", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        "available_from": MOCK_NOW.isoformat(),
        "expires_at": (MOCK_NOW + timedelta(hours=4)).isoformat(),
    }

    new_id = ObjectId()
    created_donation_doc = {
        "_id": new_id,
        "donor_id": ObjectId(DONOR_ID),
        "title": "Fresh Dal and Rice",
        "food_type": "COOKED",
        "quantity": 25.0,
        "quantity_unit": "KG",
        "description": "Hot prepared meals",
        "pickup_address": {"street": "5 Park Rd", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        "available_from": MOCK_NOW,
        "expires_at": MOCK_NOW + timedelta(hours=4),
        "status": "AVAILABLE",
        "status_history": [],
        "created_at": MOCK_NOW,
        "updated_at": MOCK_NOW,
    }

    with patch("app.routers.donor.db") as mock_db:
        mock_db.donations.insert_one = AsyncMock(return_value=MagicMock(inserted_id=new_id))
        mock_db.donations.find_one = AsyncMock(return_value=created_donation_doc)
        with TestClient(app) as client:
            res = client.post("/api/v1/donations", json=donation_payload)
    app.dependency_overrides = {}

    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Fresh Dal and Rice"
    assert data["status"] == "AVAILABLE"
    assert data["donor_id"] == DONOR_ID


def test_donor_get_mine_donations():
    async def _donor():
        return SAMPLE_DONOR
    def _role(*roles):
        async def _chk():
            return SAMPLE_DONOR
        return _chk

    app.dependency_overrides = {get_current_user: _donor, require_role: _role}

    sample_doc = {
        "_id": ObjectId(),
        "donor_id": ObjectId(DONOR_ID),
        "title": "Fresh Bread",
        "food_type": "BAKERY",
        "quantity": 10.0,
        "quantity_unit": "ITEMS",
        "pickup_address": {"street": "1 Main St", "city": "Bengaluru", "state": "KA", "pincode": "560001"},
        "available_from": MOCK_NOW,
        "expires_at": MOCK_NOW + timedelta(hours=5),
        "status": "AVAILABLE",
        "status_history": [],
        "created_at": MOCK_NOW,
        "updated_at": MOCK_NOW,
    }

    with patch("app.routers.donor.db") as mock_db:
        mock_db.donations.count_documents = AsyncMock(return_value=1)
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=[sample_doc])
        mock_db.donations.find.return_value = cursor

        with TestClient(app) as client:
            res = client.get("/api/v1/donations/mine")
    app.dependency_overrides = {}

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Fresh Bread"
