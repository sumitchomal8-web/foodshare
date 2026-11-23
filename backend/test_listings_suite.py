import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app
import app.database as database
import app.routers.auth as auth_router
import app.routers.users as users_router
import app.routers.admin as admin_router
import app.routers.listings as listings_router
from app.utils.security import hash_password, create_access_token

def run_listings_suite():
    print("=" * 60)
    print("STARTING FOOD LISTINGS & CLAIMS TEST SUITE")
    print("=" * 60)

    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["FoodShare"]

    # Patch db across all routers
    database.db = mock_db
    auth_router.db = mock_db
    users_router.db = mock_db
    admin_router.db = mock_db
    listings_router.db = mock_db

    @asynccontextmanager
    async def test_lifespan(app_instance):
        await mock_db.users.create_index("email", unique=True)
        await mock_db.users.create_index("role")
        await mock_db.listings.create_index([("status", 1), ("created_at", -1)])
        yield

    orig_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    with TestClient(app) as client:
        now = datetime.now(timezone.utc)

        # 1. Setup donor user
        donor_doc = {
            "_id": ObjectId(),
            "name": "Taj Caterers",
            "email": "caterer@taj.com",
            "password_hash": hash_password("pass123"),
            "role": "DONOR",
            "phone": "9876543210",
            "address": {
                "street": "100 MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "ngo_profile": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        asyncio.run(mock_db.users.insert_one(donor_doc))
        donor_id = str(donor_doc["_id"])
        donor_token = create_access_token(user_id=donor_id, role="DONOR")

        # 2. Setup unverified NGO user
        ngo_doc = {
            "_id": ObjectId(),
            "name": "Robin Hood Army",
            "email": "robin@army.org",
            "password_hash": hash_password("pass123"),
            "role": "NGO",
            "phone": "9876500000",
            "address": {
                "street": "12 Indiranagar",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560038"
            },
            "ngo_profile": {
                "organization_name": "Robin Hood Army",
                "org_type": "NGO",
                "registration_number": "RHA-101",
                "verification_status": "PENDING",
                "verified_by": None,
                "verified_at": None
            },
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        asyncio.run(mock_db.users.insert_one(ngo_doc))
        ngo_id = str(ngo_doc["_id"])
        ngo_token = create_access_token(user_id=ngo_id, role="NGO")

        # 3. Setup second NGO (for concurrency/double claim tests)
        ngo2_doc = {
            "_id": ObjectId(),
            "name": "Food Bank BLR",
            "email": "contact@foodbank.org",
            "password_hash": hash_password("pass123"),
            "role": "NGO",
            "phone": "9876511111",
            "address": {
                "street": "50 Koramangala",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560034"
            },
            "ngo_profile": {
                "organization_name": "Food Bank BLR",
                "org_type": "NGO",
                "registration_number": "FB-202",
                "verification_status": "VERIFIED",
                "verified_by": "admin",
                "verified_at": now
            },
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        asyncio.run(mock_db.users.insert_one(ngo2_doc))
        ngo2_id = str(ngo2_doc["_id"])
        ngo2_token = create_access_token(user_id=ngo2_id, role="NGO")

        # 4. Setup admin user
        admin_doc = {
            "_id": ObjectId(),
            "name": "Head Admin",
            "email": "headadmin@foodshare.org",
            "password_hash": hash_password("adminpass"),
            "role": "ADMIN",
            "phone": "9999999999",
            "address": {"street": "Admin St", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"},
            "ngo_profile": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        asyncio.run(mock_db.users.insert_one(admin_doc))
        admin_token = create_access_token(user_id=str(admin_doc["_id"]), role="ADMIN")

        # -------------------------------------------------------------
        # Test 1: Donor creates food listing
        # -------------------------------------------------------------
        valid_listing_data = {
            "title": "Fresh Cooked Rice and Dal",
            "description": "50 nutritious lunch packets prepared for a banquet. Untouched and hot-packed.",
            "food_type": "COOKED_MEALS",
            "quantity_servings": 50,
            "dietary_flags": ["VEGETARIAN"],
            "best_before": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
            "pickup_address": {
                "street": "100 MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "pickup_instructions": "Collect from kitchen back entrance, ask for Chef Ramesh"
        }
        res_create = client.post(
            "/api/v1/listings",
            headers={"Authorization": f"Bearer {donor_token}"},
            json=valid_listing_data,
        )
        assert res_create.status_code == 201, res_create.json()
        listing_1 = res_create.json()
        listing_id = listing_1["id"]
        assert listing_1["status"] == "AVAILABLE"
        assert listing_1["donor_id"] == donor_id
        assert listing_1["quantity_servings"] == 50
        print(f"[Pass] Test 1: Donor created food listing (ID: {listing_id})")

        # -------------------------------------------------------------
        # Test 2: Validation rejects past best_before datetime
        # -------------------------------------------------------------
        past_data = valid_listing_data.copy()
        past_data["best_before"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        res_past = client.post(
            "/api/v1/listings",
            headers={"Authorization": f"Bearer {donor_token}"},
            json=past_data,
        )
        assert res_past.status_code == 422
        assert res_past.json()["code"] == "VALIDATION_ERROR"
        print("[Pass] Test 2: Past best_before rejected with 422 VALIDATION_ERROR")

        # -------------------------------------------------------------
        # Test 3: Browse available listings with city filter
        # -------------------------------------------------------------
        browse_res = client.get("/api/v1/listings?city=Bengaluru&status=AVAILABLE")
        assert browse_res.status_code == 200
        listings_list = browse_res.json()
        assert len(listings_list) >= 1
        assert any(l["id"] == listing_id for l in listings_list)
        print(f"[Pass] Test 3: Browsed {len(listings_list)} available listing(s) in Bengaluru")

        # -------------------------------------------------------------
        # Test 4: Unverified NGO attempts to claim food listing -> Rejected
        # -------------------------------------------------------------
        claim_unverified = client.post(
            f"/api/v1/listings/{listing_id}/claim",
            headers={"Authorization": f"Bearer {ngo_token}"},
        )
        assert claim_unverified.status_code == 403, claim_unverified.json()
        assert claim_unverified.json()["code"] == "NGO_NOT_VERIFIED"
        print("[Pass] Test 4: Unverified NGO rejected from claiming food listing with 403 NGO_NOT_VERIFIED")

        # -------------------------------------------------------------
        # Test 5: Admin verifies the NGO
        # -------------------------------------------------------------
        verify_ngo_res = client.patch(
            f"/api/v1/admin/ngos/{ngo_id}/verify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": "VERIFIED"},
        )
        assert verify_ngo_res.status_code == 200
        print("[Pass] Test 5: Admin verified NGO account")

        # -------------------------------------------------------------
        # Test 6: Verified NGO claims food listing -> Success
        # -------------------------------------------------------------
        claim_verified = client.post(
            f"/api/v1/listings/{listing_id}/claim",
            headers={"Authorization": f"Bearer {ngo_token}"},
        )
        assert claim_verified.status_code == 200, claim_verified.json()
        claimed_doc = claim_verified.json()
        assert claimed_doc["status"] == "CLAIMED"
        assert claimed_doc["claimed_by"] == ngo_id
        assert claimed_doc["claimed_at"] is not None
        print(f"[Pass] Test 6: Verified NGO successfully claimed listing")

        # -------------------------------------------------------------
        # Test 7: Another NGO attempts to claim already-claimed listing -> 409 Conflict
        # -------------------------------------------------------------
        double_claim = client.post(
            f"/api/v1/listings/{listing_id}/claim",
            headers={"Authorization": f"Bearer {ngo2_token}"},
        )
        assert double_claim.status_code == 409, double_claim.json()
        assert double_claim.json()["code"] == "LISTING_ALREADY_CLAIMED"
        print("[Pass] Test 7: Double claim rejected with 409 LISTING_ALREADY_CLAIMED")

        # -------------------------------------------------------------
        # Test 8: Donor attempts to edit claimed listing -> 400 Bad Request
        # -------------------------------------------------------------
        edit_claimed = client.patch(
            f"/api/v1/listings/{listing_id}",
            headers={"Authorization": f"Bearer {donor_token}"},
            json={"quantity_servings": 30},
        )
        assert edit_claimed.status_code == 400
        assert edit_claimed.json()["code"] == "CANNOT_EDIT_CLAIMED_LISTING"
        print("[Pass] Test 8: Editing claimed listing rejected with 400 CANNOT_EDIT_CLAIMED_LISTING")

        # -------------------------------------------------------------
        # Test 9: Complete pickup
        # -------------------------------------------------------------
        complete_res = client.post(
            f"/api/v1/listings/{listing_id}/complete",
            headers={"Authorization": f"Bearer {ngo_token}"},
        )
        assert complete_res.status_code == 200, complete_res.json()
        completed_listing = complete_res.json()
        assert completed_listing["status"] == "PICKED_UP"
        assert completed_listing["completed_at"] is not None
        print("[Pass] Test 9: Completed pickup, status is PICKED_UP")

        # -------------------------------------------------------------
        # Test 10: Cancel an available listing
        # -------------------------------------------------------------
        res_create_2 = client.post(
            "/api/v1/listings",
            headers={"Authorization": f"Bearer {donor_token}"},
            json=valid_listing_data,
        )
        assert res_create_2.status_code == 201
        listing_2_id = res_create_2.json()["id"]

        cancel_res = client.delete(
            f"/api/v1/listings/{listing_2_id}",
            headers={"Authorization": f"Bearer {donor_token}"},
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"
        print("[Pass] Test 10: Cancelled listing successfully")

    # Restore orig lifespan
    app.router.lifespan_context = orig_lifespan

    print("=" * 60)
    print("ALL FOOD LISTING & CLAIM TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_listings_suite()
