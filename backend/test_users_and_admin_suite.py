from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from app.main import app
import app.database as database
import app.routers.auth as auth_router
import app.routers.users as users_router
import app.routers.admin as admin_router
from app.utils.security import hash_password, create_access_token
from datetime import datetime, timezone
from bson import ObjectId

def run_users_and_admin_suite():
    print("=" * 60)
    print("STARTING USERS & ADMIN TEST SUITE")
    print("=" * 60)

    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["FoodShare"]

    # Patch db across all modules
    database.db = mock_db
    auth_router.db = mock_db
    users_router.db = mock_db
    admin_router.db = mock_db

    @asynccontextmanager
    async def test_lifespan(app_instance):
        await mock_db.users.create_index("email", unique=True)
        await mock_db.users.create_index("role")
        yield

    orig_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    with TestClient(app) as client:
        # 1. Setup donor, NGO, and admin users
        now = datetime.now(timezone.utc)
        donor_payload = {
            "name": "Kavita Rao",
            "email": "kavita@example.com",
            "password": "securepassword123",
            "phone": "9811223344",
            "role": "DONOR",
            "address": {
                "street": "12 Residency Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560025"
            }
        }
        res_d = client.post("/api/v1/auth/register", json=donor_payload)
        assert res_d.status_code == 201
        donor_id = res_d.json()["id"]

        # Login to get donor token
        tok_d = client.post("/api/v1/auth/login", json={"email": "kavita@example.com", "password": "securepassword123"}).json()["access_token"]

        # Register NGO
        ngo_payload = {
            "name": "Food For All Foundation",
            "email": "contact@foodforall.org",
            "password": "securepassword123",
            "phone": "9822334455",
            "role": "NGO",
            "address": {
                "street": "77 Brigade Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "ngo_profile": {
                "organization_name": "Food For All",
                "org_type": "NGO",
                "registration_number": "KA-NGO-8821"
            }
        }
        res_n = client.post("/api/v1/auth/register", json=ngo_payload)
        assert res_n.status_code == 201
        ngo_id = res_n.json()["id"]
        tok_n = client.post("/api/v1/auth/login", json={"email": "contact@foodforall.org", "password": "securepassword123"}).json()["access_token"]

        # Seed an admin user
        admin_doc = {
            "_id": ObjectId(),
            "name": "Platform Admin",
            "email": "admin@foodshare.org",
            "password_hash": hash_password("adminpass123"),
            "role": "ADMIN",
            "phone": "9999988888",
            "address": {
                "street": "HQ Tower",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "ngo_profile": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        import asyncio
        asyncio.run(mock_db.users.insert_one(admin_doc))
        admin_id = str(admin_doc["_id"])
        tok_a = create_access_token(user_id=admin_id, role="ADMIN")

        # -------------------------------------------------------------
        # Test 1: GET /api/v1/users/me for Donor, NGO, and Admin
        # -------------------------------------------------------------
        # Donor
        me_d = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tok_d}"})
        assert me_d.status_code == 200, me_d.json()
        assert me_d.json()["name"] == "Kavita Rao"
        assert me_d.json()["role"] == "DONOR"
        print("[Pass] GET /users/me as DONOR")

        # Admin (Verifies Problem 1: ADMIN role in UserResponse)
        me_a = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tok_a}"})
        assert me_a.status_code == 200, me_a.json()
        assert me_a.json()["role"] == "ADMIN"
        assert me_a.json()["name"] == "Platform Admin"
        print("[Pass] GET /users/me as ADMIN")

        # NGO
        me_n = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tok_n}"})
        assert me_n.status_code == 200, me_n.json()
        assert me_n.json()["ngo_profile"]["verification_status"] == "PENDING"
        print("[Pass] GET /users/me as NGO")

        # -------------------------------------------------------------
        # Test 2: PATCH /api/v1/users/me (Update profile)
        # -------------------------------------------------------------
        patch_res = client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {tok_d}"},
            json={
                "name": "Kavita Rao-Sharma",
                "phone": "9811998877",
                "address": {
                    "city": "Mysuru",
                    "pincode": "570001"
                }
            }
        )
        assert patch_res.status_code == 200, patch_res.json()
        updated_data = patch_res.json()
        assert updated_data["name"] == "Kavita Rao-Sharma"
        assert updated_data["phone"] == "9811998877"
        assert updated_data["address"]["city"] == "Mysuru"
        assert updated_data["address"]["pincode"] == "570001"
        assert updated_data["address"]["street"] == "12 Residency Road" # preserved
        print("[Pass] PATCH /users/me updated name, phone, and address")

        # Test extra fields on PATCH rejected (extra="forbid")
        patch_extra = client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {tok_d}"},
            json={"role": "ADMIN"}
        )
        assert patch_extra.status_code == 422
        assert patch_extra.json()["code"] == "VALIDATION_ERROR"
        print("[Pass] PATCH /users/me rejects forbidden extra fields")

        # -------------------------------------------------------------
        # Test 3: Role-based access control (RBAC) on Admin endpoints
        # -------------------------------------------------------------
        # Donor calling admin endpoint should receive 403 FORBIDDEN
        donor_admin_res = client.get("/api/v1/admin/ngos/pending", headers={"Authorization": f"Bearer {tok_d}"})
        assert donor_admin_res.status_code == 403
        assert donor_admin_res.json()["code"] == "FORBIDDEN"
        print("[Pass] RBAC: Donor blocked from admin endpoints with 403 FORBIDDEN")

        # NGO calling admin endpoint should receive 403 FORBIDDEN
        ngo_admin_res = client.get("/api/v1/admin/ngos/pending", headers={"Authorization": f"Bearer {tok_n}"})
        assert ngo_admin_res.status_code == 403
        assert ngo_admin_res.json()["code"] == "FORBIDDEN"
        print("[Pass] RBAC: NGO blocked from admin endpoints with 403 FORBIDDEN")

        # -------------------------------------------------------------
        # Test 4: Admin lists pending NGOs
        # -------------------------------------------------------------
        pending_res = client.get("/api/v1/admin/ngos/pending", headers={"Authorization": f"Bearer {tok_a}"})
        assert pending_res.status_code == 200, pending_res.json()
        pending_list = pending_res.json()
        assert len(pending_list) >= 1
        assert any(item["id"] == ngo_id for item in pending_list)
        print(f"[Pass] Admin listed {len(pending_list)} pending NGO(s)")

        # -------------------------------------------------------------
        # Test 5: Admin verifies NGO (PATCH /admin/ngos/{id}/verify)
        # -------------------------------------------------------------
        verify_res = client.patch(
            f"/api/v1/admin/ngos/{ngo_id}/verify",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"status": "VERIFIED"}
        )
        assert verify_res.status_code == 200, verify_res.json()
        verified_data = verify_res.json()
        assert verified_data["ngo_profile"]["verification_status"] == "VERIFIED"
        print("[Pass] Admin verified NGO successfully")

        # -------------------------------------------------------------
        # Test 6: Verified NGO calls GET /users/me
        # Verifies that extra fields in DB (verified_by, verified_at, updated_at)
        # do NOT cause validation failure (Fix 2)
        # -------------------------------------------------------------
        me_verified_ngo = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tok_n}"})
        assert me_verified_ngo.status_code == 200, me_verified_ngo.json()
        assert me_verified_ngo.json()["ngo_profile"]["verification_status"] == "VERIFIED"
        print("[Pass] Verified NGO GET /users/me returned cleanly with ignored extra fields")

    # Restore orig lifespan
    app.router.lifespan_context = orig_lifespan

    print("=" * 60)
    print("ALL USERS & ADMIN TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_users_and_admin_suite()
