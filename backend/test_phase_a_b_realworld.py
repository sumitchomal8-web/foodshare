import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient
from jose import jwt
from mongomock_motor import AsyncMongoMockClient

import app.database as database
import app.routers.auth as auth_router
import app.routers.donor as donor_router
import app.routers.users as users_router
import app.utils.dependencies as dependencies
from app.config import settings
from app.main import app
from app.utils.security import ALGORITHM


def _patch_db(mock_db):
    database.db = mock_db
    auth_router.db = mock_db
    users_router.db = mock_db
    donor_router.db = mock_db
    dependencies.db = mock_db


def _make_token(sub: str, role: str, delta: timedelta = timedelta(minutes=30)) -> str:
    exp = datetime.now(timezone.utc) + delta
    return jwt.encode({"sub": sub, "role": role, "exp": exp}, settings.secret_key, algorithm=ALGORITHM)


def run_realworld_suite():
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["foodshare_test"]
    _patch_db(mock_db)

    @asynccontextmanager
    async def test_lifespan(app_instance):
        await mock_db.users.create_index("email", unique=True)
        await mock_db.users.create_index("role")
        await mock_db.donations.create_index([("status", 1), ("created_at", -1)])
        await mock_db.donations.create_index("donor_id")
        yield

    orig_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    try:
        with TestClient(app) as client:
            base_addr = {
                "street": "12 MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
            }

            # =========================================================
            # PHASE A: AUTHENTICATION, SECURITY & USER PROFILE
            # =========================================================

            # 1. Input validation edge cases -> 422 VALIDATION_ERROR
            bad_payloads = [
                {
                    "name": "Donor",
                    "email": "p1@example.com",
                    "password": "a" * 73,  # >72 bytes bcrypt limit
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": base_addr,
                },
                {
                    "name": "Donor",
                    "email": "p2@example.com",
                    "password": "password123",
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": {**base_addr, "pincode": "56001"},  # 5 digits
                },
                {
                    "name": "",
                    "email": "p3@example.com",
                    "password": "password123",
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": base_addr,
                },
                {
                    "name": "Sneaky Admin",
                    "email": "p4@example.com",
                    "password": "password123",
                    "phone": "9876543210",
                    "role": "ADMIN",  # cannot self-register as ADMIN
                    "address": base_addr,
                },
                {
                    "name": "Sneaky Donor",
                    "email": "p5@example.com",
                    "password": "password123",
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": base_addr,
                    "is_active": False,  # extra="forbid"
                },
                {
                    "name": "Bad NGO",
                    "email": "p6@example.com",
                    "password": "password123",
                    "phone": "9876543210",
                    "role": "NGO",
                    "address": base_addr,
                    "ngo_profile": {
                        "organization_name": "Helping Hands",
                        "org_type": "NGO",
                        "registration_number": "   ",  # blank for NGO
                    },
                },
            ]
            for idx, payload in enumerate(bad_payloads, start=1):
                r = client.post("/api/v1/auth/register", json=payload)
                assert r.status_code == 422, f"Bad payload #{idx} expected 422, got {r.status_code}"
                assert r.json()["code"] == "VALIDATION_ERROR"

            # 2. Register Donor 1 with mixed-case email
            r = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Aarav Patel",
                    "email": "Aarav.Patel@Example.COM",
                    "password": "strongpassword123",
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": base_addr,
                },
            )
            assert r.status_code == 201
            donor1 = r.json()
            assert donor1["email"] == "aarav.patel@example.com"
            assert donor1["created_at"] == donor1["updated_at"]
            assert "password" not in donor1 and "password_hash" not in donor1

            # 3. Duplicate email (case-insensitive) -> 409 EMAIL_EXISTS
            r_dup = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Aarav Clone",
                    "email": "aarav.patel@example.com",
                    "password": "strongpassword123",
                    "phone": "9876543210",
                    "role": "DONOR",
                    "address": base_addr,
                },
            )
            assert r_dup.status_code == 409
            assert r_dup.json()["code"] == "EMAIL_EXISTS"

            # 4. Register Volunteer without registration_number -> 201
            r_vol = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Riya Volunteer",
                    "email": "riya.vol@example.com",
                    "password": "strongpassword123",
                    "phone": "9123456780",
                    "role": "NGO",
                    "address": base_addr,
                    "ngo_profile": {
                        "organization_name": "City Volunteers",
                        "org_type": "VOLUNTEER",
                    },
                },
            )
            assert r_vol.status_code == 201
            vol_data = r_vol.json()
            assert vol_data["ngo_profile"]["verification_status"] == "PENDING"
            assert vol_data["ngo_profile"]["verified_by"] is None
            assert vol_data["ngo_profile"]["verified_at"] is None

            # 5. Login enumeration protection (unknown email vs wrong password)
            r_unknown = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "wrongpassword"},
            )
            r_wrong_pw = client.post(
                "/api/v1/auth/login",
                json={"email": "aarav.patel@example.com", "password": "wrongpassword"},
            )
            assert r_unknown.status_code == 401 and r_wrong_pw.status_code == 401
            assert r_unknown.json() == r_wrong_pw.json()
            assert r_unknown.json()["code"] == "INVALID_CREDENTIALS"

            # 6. Successful login
            r_login1 = client.post(
                "/api/v1/auth/login",
                json={"email": "AARAV.PATEL@EXAMPLE.COM", "password": "strongpassword123"},
            )
            assert r_login1.status_code == 200
            donor1_token = r_login1.json()["access_token"]
            h_donor1 = {"Authorization": f"Bearer {donor1_token}"}

            # 7. Token failure modes -> 401 TOKEN_INVALID
            tampered = donor1_token[:-1] + ("a" if donor1_token[-1] != "a" else "b")
            expired = _make_token(donor1["id"], "DONOR", delta=timedelta(minutes=-1))
            bad_sub = _make_token("not-an-objectid", "DONOR")
            deleted_sub = _make_token(str(ObjectId()), "DONOR")

            for bad_headers in [
                {},
                {"Authorization": f"Bearer {tampered}"},
                {"Authorization": f"Bearer {expired}"},
                {"Authorization": f"Bearer {bad_sub}"},
                {"Authorization": f"Bearer {deleted_sub}"},
            ]:
                r_tok = client.get("/api/v1/users/me", headers=bad_headers)
                assert r_tok.status_code == 401
                assert r_tok.json()["code"] == "TOKEN_INVALID"

            # 8. Account deactivation blocks existing tokens immediately -> 403 ACCOUNT_DISABLED
            asyncio.run(
                mock_db.users.update_one(
                    {"_id": ObjectId(donor1["id"])},
                    {"$set": {"is_active": False}},
                )
            )
            assert client.get("/api/v1/users/me", headers=h_donor1).json()["code"] == "ACCOUNT_DISABLED"
            assert client.post(
                "/api/v1/auth/login",
                json={"email": "aarav.patel@example.com", "password": "strongpassword123"},
            ).status_code == 403
            asyncio.run(
                mock_db.users.update_one(
                    {"_id": ObjectId(donor1["id"])},
                    {"$set": {"is_active": True}},
                )
            )

            # 9. Verified NGO (ObjectId verified_by) & ADMIN calling /users/me -> 200
            admin_oid = ObjectId()
            now = datetime.now(timezone.utc)
            asyncio.run(
                mock_db.users.insert_one(
                    {
                        "_id": admin_oid,
                        "name": "Super Admin",
                        "email": "admin@foodshare.org",
                        "password_hash": "unused",
                        "role": "ADMIN",
                        "phone": "9000000000",
                        "address": base_addr,
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
            )
            asyncio.run(
                mock_db.users.update_one(
                    {"_id": ObjectId(vol_data["id"])},
                    {
                        "$set": {
                            "ngo_profile.verification_status": "VERIFIED",
                            "ngo_profile.verified_by": admin_oid,
                            "ngo_profile.verified_at": now,
                        }
                    },
                )
            )
            vol_token = _make_token(vol_data["id"], "NGO")
            admin_token = _make_token(str(admin_oid), "ADMIN")
            r_vol_me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {vol_token}"})
            assert r_vol_me.status_code == 200
            assert r_vol_me.json()["ngo_profile"]["verified_by"] == str(admin_oid)

            r_admin_me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {admin_token}"})
            assert r_admin_me.status_code == 200
            assert r_admin_me.json()["role"] == "ADMIN"

            # 10. PATCH /users/me: null-wiping prevention, forbid protected fields, partial update
            for bad_patch in [{}, {"name": None}, {"role": "ADMIN"}, {"email": "x@y.com"}, {"is_active": False}]:
                r_p = client.patch("/api/v1/users/me", headers=h_donor1, json=bad_patch)
                assert r_p.status_code == 422
                assert r_p.json()["code"] == "VALIDATION_ERROR"

            r_ok_patch = client.patch("/api/v1/users/me", headers=h_donor1, json={"phone": "9999999999"})
            assert r_ok_patch.status_code == 200
            assert r_ok_patch.json()["name"] == "Aarav Patel"
            assert r_ok_patch.json()["phone"] == "9999999999"

            # =========================================================
            # PHASE B: DONATION SCHEMAS & DONOR ROUTES
            # =========================================================

            future_start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            future_end = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
            past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

            valid_donation = {
                "title": "Wedding Biryani Surplus",
                "food_type": "COOKED_MEALS",
                "quantity": 40,
                "quantity_unit": "servings",
                "description": "Packed cleanly in foil trays",
                "pickup_address": base_addr,
                "available_from": future_start,
                "expires_at": future_end,
            }

            # 11. Role checks: NGO and Admin cannot access donor routes -> 403 FORBIDDEN
            assert client.post(
                "/api/v1/donations",
                headers={"Authorization": f"Bearer {vol_token}"},
                json=valid_donation,
            ).status_code == 403
            assert client.get(
                "/api/v1/donations/mine",
                headers={"Authorization": f"Bearer {admin_token}"},
            ).status_code == 403

            # 12. Invalid donation payloads -> 422 VALIDATION_ERROR
            for bad_don in [
                {**valid_donation, "expires_at": past_time},
                {**valid_donation, "available_from": future_end, "expires_at": future_start},
                {**valid_donation, "quantity": 0},
                {**valid_donation, "status": "COMPLETED"},
                {**valid_donation, "pickup_address": {**base_addr, "pincode": "12345"}},
            ]:
                r_bad = client.post("/api/v1/donations", headers=h_donor1, json=bad_don)
                assert r_bad.status_code == 422
                assert r_bad.json()["code"] == "VALIDATION_ERROR"

            # 13. Create 3 donations for pagination & ordering
            created_ids = []
            for i in range(1, 4):
                r_c = client.post(
                    "/api/v1/donations",
                    headers=h_donor1,
                    json={**valid_donation, "title": f"Donation Batch #{i}"},
                )
                assert r_c.status_code == 201
                body = r_c.json()
                assert body["status"] == "AVAILABLE"
                assert body["donor_id"] == donor1["id"]
                assert len(body["status_history"]) == 1
                assert body["status_history"][0]["changed_by"] == donor1["id"]
                created_ids.append(body["id"])

            # 14. Pagination (newest first)
            r_page1 = client.get("/api/v1/donations/mine?page=1&limit=2", headers=h_donor1)
            assert r_page1.status_code == 200
            p1 = r_page1.json()
            assert p1["total"] == 3 and p1["page"] == 1 and p1["limit"] == 2
            assert len(p1["items"]) == 2
            assert p1["items"][0]["title"] == "Donation Batch #3"

            r_page2 = client.get("/api/v1/donations/mine?page=2&limit=2", headers=h_donor1)
            assert len(r_page2.json()["items"]) == 1
            assert r_page2.json()["items"][0]["title"] == "Donation Batch #1"

            # 15. Cross-donor isolation -> 404 NOT_FOUND (not 403)
            r_d2 = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Donor Two",
                    "email": "donor2@example.com",
                    "password": "strongpassword123",
                    "phone": "9888888888",
                    "role": "DONOR",
                    "address": base_addr,
                },
            )
            donor2_token = _make_token(r_d2.json()["id"], "DONOR")
            h_donor2 = {"Authorization": f"Bearer {donor2_token}"}

            assert client.put(
                f"/api/v1/donations/{created_ids[0]}",
                headers=h_donor2,
                json={"quantity": 10},
            ).json()["code"] == "NOT_FOUND"
            assert client.post(
                f"/api/v1/donations/{created_ids[0]}/cancel",
                headers=h_donor2,
            ).status_code == 404

            # 16. Malformed ID -> 400 INVALID_ID
            r_bad_id = client.put(
                "/api/v1/donations/not-a-valid-id",
                headers=h_donor1,
                json={"quantity": 10},
            )
            assert r_bad_id.status_code == 400 and r_bad_id.json()["code"] == "INVALID_ID"

            # 17. Valid edit & past expires_at rejection
            assert client.put(
                f"/api/v1/donations/{created_ids[0]}",
                headers=h_donor1,
                json={"expires_at": past_time},
            ).status_code == 422

            r_edit = client.put(
                f"/api/v1/donations/{created_ids[0]}",
                headers=h_donor1,
                json={"quantity": 55},
            )
            assert r_edit.status_code == 200 and r_edit.json()["quantity"] == 55

            # 18. Cancel & post-cancel immutability -> 409 INVALID_STATUS_TRANSITION
            r_cancel = client.post(f"/api/v1/donations/{created_ids[0]}/cancel", headers=h_donor1)
            assert r_cancel.status_code == 200
            c_body = r_cancel.json()
            assert c_body["status"] == "CANCELLED"
            assert c_body["cancelled_at"] is not None
            assert len(c_body["status_history"]) == 2
            assert c_body["status_history"][1]["status"] == "CANCELLED"

            assert client.put(
                f"/api/v1/donations/{created_ids[0]}",
                headers=h_donor1,
                json={"quantity": 60},
            ).json()["code"] == "INVALID_STATUS_TRANSITION"
            assert client.post(
                f"/api/v1/donations/{created_ids[0]}/cancel",
                headers=h_donor1,
            ).status_code == 409

            print("ALL 18 REAL-WORLD PHASE A & PHASE B SCENARIOS PASSED!")
    finally:
        app.router.lifespan_context = orig_lifespan


if __name__ == "__main__":
    run_realworld_suite()
