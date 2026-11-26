import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest
from bson import ObjectId
from app.schemas.donation import DonationStatus
from app.services.donation_service import (
    validate_status_transition,
    apply_status_transition,
    accept_donation,
    transition_donation_status,
    get_donation_detail,
    list_donations,
    list_ngo_donations,
    FoodShareAPIException,
)


def run_async(coro):
    """Async test runner."""
    return asyncio.run(coro)


@pytest.fixture
def mock_now():
    return datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def base_donation(mock_now):
    donor_id = str(ObjectId())
    return {
        "_id": str(ObjectId()),
        "donor_id": donor_id,
        "title": "Fresh Meals",
        "status": DonationStatus.AVAILABLE.value,
        "expires_at": mock_now + timedelta(hours=5),
        "accepted_by": None,
        "status_history": [
            {
                "status": DonationStatus.AVAILABLE.value,
                "changed_by": donor_id,
                "changed_at": mock_now - timedelta(hours=1),
            }
        ],
        "created_at": mock_now - timedelta(hours=1),
        "updated_at": mock_now - timedelta(hours=1),
    }


@pytest.fixture
def verified_ngo():
    return {
        "_id": str(ObjectId()),
        "role": "NGO",
        "is_active": True,
        "ngo_profile": {
            "organization_name": "Food Bank Org",
            "org_type": "NGO",
            "verification_status": "VERIFIED",
        },
    }


@pytest.fixture
def unverified_ngo():
    return {
        "_id": str(ObjectId()),
        "role": "NGO",
        "is_active": True,
        "ngo_profile": {
            "organization_name": "Volunteer Group",
            "org_type": "VOLUNTEER",
            "verification_status": "PENDING",
        },
    }


@pytest.fixture
def admin_user():
    return {
        "_id": str(ObjectId()),
        "role": "ADMIN",
        "is_active": True,
    }


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.donations = MagicMock()
    db.donations.find_one = AsyncMock()
    db.donations.find_one_and_update = AsyncMock()
    db.donations.update_one = AsyncMock()
    db.donations.count_documents = AsyncMock()
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=[])
    db.donations.find.return_value = cursor
    return db


# ==============================================================================
# In-Memory State Machine Tests
# ==============================================================================

def test_full_lifecycle_happy_path(base_donation, verified_ngo, mock_now):
    """AVAILABLE -> ACCEPTED -> PICKED_UP -> DISTRIBUTED -> COMPLETED"""
    # 1. Accept
    validate_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo, now=mock_now)
    apply_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo["_id"], now=mock_now)
    assert base_donation["status"] == DonationStatus.ACCEPTED.value
    assert str(base_donation["accepted_by"]) == str(verified_ngo["_id"])
    assert base_donation["accepted_at"] == mock_now
    assert len(base_donation["status_history"]) == 2

    # 2. Picked Up
    t2 = mock_now + timedelta(hours=1)
    validate_status_transition(base_donation, DonationStatus.PICKED_UP, verified_ngo, now=t2)
    apply_status_transition(base_donation, DonationStatus.PICKED_UP, verified_ngo["_id"], now=t2)
    assert base_donation["status"] == DonationStatus.PICKED_UP.value
    assert base_donation["picked_up_at"] == t2
    assert len(base_donation["status_history"]) == 3

    # 3. Distributed
    t3 = mock_now + timedelta(hours=2)
    validate_status_transition(base_donation, DonationStatus.DISTRIBUTED, verified_ngo, now=t3)
    apply_status_transition(base_donation, DonationStatus.DISTRIBUTED, verified_ngo["_id"], now=t3)
    assert base_donation["status"] == DonationStatus.DISTRIBUTED.value
    assert base_donation["distributed_at"] == t3
    assert len(base_donation["status_history"]) == 4

    # 4. Completed
    t4 = mock_now + timedelta(hours=3)
    validate_status_transition(base_donation, DonationStatus.COMPLETED, verified_ngo, now=t4)
    apply_status_transition(base_donation, DonationStatus.COMPLETED, verified_ngo["_id"], now=t4)
    assert base_donation["status"] == DonationStatus.COMPLETED.value
    assert base_donation["completed_at"] == t4
    assert len(base_donation["status_history"]) == 5


def test_donor_can_cancel_own_available_donation(base_donation, mock_now):
    donor = {
        "_id": base_donation["donor_id"],
        "role": "DONOR",
        "is_active": True,
    }
    validate_status_transition(base_donation, DonationStatus.CANCELLED, donor, now=mock_now)
    apply_status_transition(base_donation, DonationStatus.CANCELLED, donor["_id"], now=mock_now)
    assert base_donation["status"] == DonationStatus.CANCELLED.value
    assert base_donation["cancelled_at"] == mock_now


def test_admin_can_cancel_available_donation(base_donation, admin_user, mock_now):
    validate_status_transition(base_donation, DonationStatus.CANCELLED, admin_user, now=mock_now)
    apply_status_transition(base_donation, DonationStatus.CANCELLED, admin_user["_id"], now=mock_now)
    assert base_donation["status"] == DonationStatus.CANCELLED.value


def test_donor_cannot_cancel_other_donor_donation(base_donation, mock_now):
    other_donor = {
        "_id": str(ObjectId()),
        "role": "DONOR",
        "is_active": True,
    }
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.CANCELLED, other_donor, now=mock_now)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_donor_cannot_cancel_accepted_donation(base_donation, verified_ngo, mock_now):
    apply_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo["_id"], now=mock_now)
    donor = {
        "_id": base_donation["donor_id"],
        "role": "DONOR",
        "is_active": True,
    }
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.CANCELLED, donor, now=mock_now)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


def test_invalid_transition_jumps_rejected(base_donation, verified_ngo, mock_now):
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.PICKED_UP, verified_ngo, now=mock_now)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


def test_terminal_states_cannot_transition(base_donation, verified_ngo, mock_now):
    base_donation["status"] = DonationStatus.COMPLETED.value
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.AVAILABLE, verified_ngo, now=mock_now)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


def test_unverified_ngo_cannot_accept(base_donation, unverified_ngo, mock_now):
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.ACCEPTED, unverified_ngo, now=mock_now)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "NGO_NOT_VERIFIED"


def test_donor_cannot_accept_donation(base_donation, mock_now):
    donor = {"_id": str(ObjectId()), "role": "DONOR", "is_active": True}
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.ACCEPTED, donor, now=mock_now)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_inactive_ngo_cannot_accept(base_donation, verified_ngo, mock_now):
    verified_ngo["is_active"] = False
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo, now=mock_now)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCOUNT_DISABLED"


def test_other_ngo_cannot_update_assigned_donation(base_donation, verified_ngo, mock_now):
    apply_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo["_id"], now=mock_now)
    other_ngo = {
        "_id": str(ObjectId()),
        "role": "NGO",
        "is_active": True,
        "ngo_profile": {"verification_status": "VERIFIED"},
    }
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.PICKED_UP, other_ngo, now=mock_now)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_cannot_accept_expired_donation(base_donation, verified_ngo, mock_now):
    base_donation["expires_at"] = mock_now - timedelta(minutes=1)
    with pytest.raises(FoodShareAPIException) as exc_info:
        validate_status_transition(base_donation, DonationStatus.ACCEPTED, verified_ngo, now=mock_now)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


# ==============================================================================
# Database Operation Tests
# ==============================================================================

def test_accept_donation_db_success(mock_db, verified_ngo, mock_now):
    donation_id = str(ObjectId())
    accepted_doc = {
        "_id": ObjectId(donation_id),
        "donor_id": ObjectId(),
        "title": "Fresh Curry",
        "status": DonationStatus.ACCEPTED.value,
        "accepted_by": ObjectId(verified_ngo["_id"]),
        "accepted_at": mock_now,
        "status_history": [
            {"status": "ACCEPTED", "changed_by": verified_ngo["_id"], "changed_at": mock_now}
        ],
        "created_at": mock_now,
        "updated_at": mock_now,
    }
    mock_db.donations.find_one_and_update.return_value = accepted_doc

    result = run_async(accept_donation(donation_id, verified_ngo, db=mock_db))
    assert result["id"] == donation_id
    assert result["status"] == DonationStatus.ACCEPTED.value
    assert result["accepted_by"] == verified_ngo["_id"]


def test_accept_donation_db_already_accepted_raises_409(mock_db, verified_ngo, mock_now):
    donation_id = str(ObjectId())
    mock_db.donations.find_one_and_update.return_value = None
    mock_db.donations.find_one.return_value = {
        "_id": ObjectId(donation_id),
        "status": DonationStatus.ACCEPTED.value,
        "expires_at": mock_now + timedelta(hours=2),
    }

    with pytest.raises(FoodShareAPIException) as exc_info:
        run_async(accept_donation(donation_id, verified_ngo, db=mock_db, now=mock_now))

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ALREADY_ACCEPTED"


def test_accept_donation_db_expired_raises_409(mock_db, verified_ngo, mock_now):
    donation_id = str(ObjectId())
    mock_db.donations.find_one_and_update.return_value = None
    mock_db.donations.find_one.return_value = {
        "_id": ObjectId(donation_id),
        "status": DonationStatus.AVAILABLE.value,
        "expires_at": mock_now - timedelta(minutes=5),
    }

    with pytest.raises(FoodShareAPIException) as exc_info:
        run_async(accept_donation(donation_id, verified_ngo, db=mock_db, now=mock_now))

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "INVALID_STATUS_TRANSITION"


def test_transition_donation_status_db_flow(mock_db, verified_ngo, mock_now):
    donation_id = str(ObjectId())
    current_doc = {
        "_id": ObjectId(donation_id),
        "donor_id": ObjectId(),
        "status": DonationStatus.ACCEPTED.value,
        "accepted_by": ObjectId(verified_ngo["_id"]),
        "status_history": [],
    }
    updated_doc = dict(current_doc)
    updated_doc["status"] = DonationStatus.PICKED_UP.value
    updated_doc["picked_up_at"] = mock_now

    mock_db.donations.find_one.return_value = current_doc
    mock_db.donations.find_one_and_update.return_value = updated_doc

    result = run_async(transition_donation_status(
        donation_id,
        DonationStatus.PICKED_UP,
        verified_ngo,
        db=mock_db
    ))
    assert result["status"] == DonationStatus.PICKED_UP.value


def test_get_donation_detail_access_control(mock_db, verified_ngo, admin_user, mock_now):
    donation_id = str(ObjectId())
    donor_id = str(ObjectId())
    doc = {
        "_id": ObjectId(donation_id),
        "donor_id": ObjectId(donor_id),
        "status": DonationStatus.PICKED_UP.value,
        "accepted_by": ObjectId(verified_ngo["_id"]),
    }
    mock_db.donations.find_one.return_value = doc

    # 1. Admin can view
    admin_view = run_async(get_donation_detail(donation_id, admin_user, db=mock_db))
    assert admin_view["id"] == donation_id

    # 2. Assigned NGO can view
    ngo_view = run_async(get_donation_detail(donation_id, verified_ngo, db=mock_db))
    assert ngo_view["id"] == donation_id

    # 3. Owner donor can view
    donor = {"_id": donor_id, "role": "DONOR", "is_active": True}
    donor_view = run_async(get_donation_detail(donation_id, donor, db=mock_db))
    assert donor_view["id"] == donation_id

    # 4. Other NGO cannot view PICKED_UP donation
    other_ngo = {"_id": str(ObjectId()), "role": "NGO", "is_active": True}
    with pytest.raises(FoodShareAPIException) as exc_info:
        run_async(get_donation_detail(donation_id, other_ngo, db=mock_db))
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_list_donations_filters_and_pagination(mock_db, verified_ngo):
    mock_db.donations.count_documents.return_value = 1
    mock_db.donations.find().to_list.return_value = [
        {
            "_id": ObjectId(),
            "donor_id": ObjectId(),
            "title": "Bread",
            "status": DonationStatus.AVAILABLE.value,
            "pickup_address": {"city": "Bengaluru", "street": "Main", "state": "KA", "pincode": "560001"},
            "food_type": "BAKERY",
        }
    ]

    result = run_async(list_donations(
        actor=verified_ngo,
        city="Bengaluru",
        food_type="BAKERY",
        page=1,
        limit=10,
        db=mock_db
    ))
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == "Bread"
    assert result["page"] == 1
    assert result["limit"] == 10
