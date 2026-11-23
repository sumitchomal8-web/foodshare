import asyncio
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from app.main import app
import app.database as database
import app.routers.auth as auth_router

def run_all_seven_tests():
    print("=" * 60)
    print("STARTING AUTH TEST SUITE (7 TESTS)")
    print("=" * 60)

    # Use mock db for deterministic testing
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["FoodShare"]

    # Patch database in auth router and database module
    orig_db = auth_router.db
    auth_router.db = mock_db
    database.db = mock_db

    @asynccontextmanager
    async def test_lifespan(app_instance):
        await mock_db.users.create_index("email", unique=True)
        await mock_db.users.create_index("role")
        yield

    orig_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    results = {}

    with TestClient(app) as client:
        # ---------------------------------------------------------
        # Test 1: Register a donor. Expect 201, with no password or hash in response.
        # ---------------------------------------------------------
        donor_payload = {
            "name": "Aarav Patel",
            "email": "Aarav.Patel@Example.COM",
            "password": "strongpassword123",
            "phone": "9876543210",
            "role": "DONOR",
            "address": {
                "street": "123 Green Park",
                "city": "New Delhi",
                "state": "Delhi",
                "pincode": "110016"
            }
        }
        res1 = client.post("/api/v1/auth/register", json=donor_payload)
        donor_resp = res1.json()
        test1_pass = (
            res1.status_code == 201
            and "password" not in donor_resp
            and "password_hash" not in donor_resp
            and donor_resp.get("email") == "aarav.patel@example.com"
            and donor_resp.get("role") == "DONOR"
            and "id" in donor_resp
        )
        print(f"\n[Test 1] Register donor: Status={res1.status_code}")
        print(f"Response: {donor_resp}")
        assert test1_pass, f"Test 1 failed: {donor_resp}"
        results["Test 1"] = "PASSED (201 Created, password and password_hash excluded from response)"

        # ---------------------------------------------------------
        # Test 2: In Atlas/Database, check password_hash starts with $2b$,
        # email is lowercase, and updated_at appears.
        # ---------------------------------------------------------
        stored_donor = asyncio.run(mock_db.users.find_one({"email": "aarav.patel@example.com"}))
        pwd_hash = stored_donor.get("password_hash", "")
        test2_pass = (
            stored_donor is not None
            and pwd_hash.startswith("$2b$")
            and stored_donor.get("email") == "aarav.patel@example.com"
            and "created_at" in stored_donor
            and "updated_at" in stored_donor
            and stored_donor.get("created_at") == stored_donor.get("updated_at")
        )
        print(f"\n[Test 2] Database document check for donor:")
        print(f"  email: {stored_donor.get('email')}")
        print(f"  password_hash prefix: {pwd_hash[:7]}...")
        print(f"  created_at: {stored_donor.get('created_at')}")
        print(f"  updated_at: {stored_donor.get('updated_at')}")
        assert test2_pass, f"Test 2 failed: {stored_donor}"
        results["Test 2"] = "PASSED (hash starts with $2b$, email is lowercase, updated_at appears)"

        # ---------------------------------------------------------
        # Test 3: Register the same email again. Expect 409 with EMAIL_EXISTS.
        # ---------------------------------------------------------
        res3 = client.post("/api/v1/auth/register", json=donor_payload)
        res3_json = res3.json()
        test3_pass = (
            res3.status_code == 409
            and res3_json.get("code") == "EMAIL_EXISTS"
            and res3_json.get("detail") == "Email already registered"
        )
        print(f"\n[Test 3] Duplicate registration: Status={res3.status_code}")
        print(f"Response: {res3_json}")
        assert test3_pass, f"Test 3 failed: {res3_json}"
        results["Test 3"] = "PASSED (409 Conflict with code: EMAIL_EXISTS)"

        # ---------------------------------------------------------
        # Test 4: Register role: 'ADMIN'. Expect 422.
        # ---------------------------------------------------------
        admin_payload = donor_payload.copy()
        admin_payload["email"] = "admin@example.com"
        admin_payload["role"] = "ADMIN"
        res4 = client.post("/api/v1/auth/register", json=admin_payload)
        res4_json = res4.json()
        test4_pass = (
            res4.status_code == 422
            and res4_json.get("code") == "VALIDATION_ERROR"
        )
        print(f"\n[Test 4] Register ADMIN role: Status={res4.status_code}")
        print(f"Response: {res4_json}")
        assert test4_pass, f"Test 4 failed: {res4_json}"
        results["Test 4"] = "PASSED (422 Unprocessable Entity with code: VALIDATION_ERROR)"

        # ---------------------------------------------------------
        # Test 5: Register an NGO with no ngo_profile. Expect 422.
        # ---------------------------------------------------------
        ngo_no_profile_payload = {
            "name": "Seva Foundation",
            "email": "contact@sevafoundation.org",
            "password": "strongpassword123",
            "phone": "9876501234",
            "role": "NGO",
            "address": {
                "street": "45 Temple Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        }
        res5 = client.post("/api/v1/auth/register", json=ngo_no_profile_payload)
        res5_json = res5.json()
        test5_pass = (
            res5.status_code == 422
            and res5_json.get("code") == "VALIDATION_ERROR"
        )
        print(f"\n[Test 5] Register NGO without ngo_profile: Status={res5.status_code}")
        print(f"Response: {res5_json}")
        assert test5_pass, f"Test 5 failed: {res5_json}"
        results["Test 5"] = "PASSED (422 Unprocessable Entity with code: VALIDATION_ERROR)"

        # ---------------------------------------------------------
        # Test 6: Register an NGO. Check verification_status is PENDING,
        # and verified_by and verified_at are null.
        # Also verifies registration_number is required when org_type is NGO (Fix 6).
        # ---------------------------------------------------------
        # Check registration_number empty for NGO fails validation (Fix 6)
        ngo_empty_reg = ngo_no_profile_payload.copy()
        ngo_empty_reg["ngo_profile"] = {
            "organization_name": "Seva Foundation",
            "org_type": "NGO",
            "registration_number": ""
        }
        res6_empty = client.post("/api/v1/auth/register", json=ngo_empty_reg)
        assert res6_empty.status_code == 422, "NGO with empty registration_number should fail 422"

        # Register valid NGO
        valid_ngo_payload = ngo_no_profile_payload.copy()
        valid_ngo_payload["ngo_profile"] = {
            "organization_name": "Seva Foundation",
            "org_type": "NGO",
            "registration_number": "NGO-BLR-2026-99"
        }
        res6 = client.post("/api/v1/auth/register", json=valid_ngo_payload)
        ngo_resp = res6.json()
        print(f"\n[Test 6] Register valid NGO: Status={res6.status_code}")
        print(f"Response: {ngo_resp}")
        assert res6.status_code == 201, f"Failed NGO registration: {ngo_resp}"

        stored_ngo = asyncio.run(mock_db.users.find_one({"email": "contact@sevafoundation.org"}))
        profile = stored_ngo.get("ngo_profile", {})
        test6_pass = (
            profile.get("verification_status") == "PENDING"
            and profile.get("verified_by") is None
            and profile.get("verified_at") is None
            and "updated_at" in stored_ngo
        )
        print(f"Database document check for NGO profile:")
        print(f"  verification_status: {profile.get('verification_status')}")
        print(f"  verified_by: {profile.get('verified_by')}")
        print(f"  verified_at: {profile.get('verified_at')}")
        assert test6_pass, f"Test 6 failed: {stored_ngo}"
        results["Test 6"] = "PASSED (verification_status: PENDING, verified_by: null, verified_at: null)"

        # ---------------------------------------------------------
        # Test 7: Log in with wrong password and unknown email.
        # Both should return 401 INVALID_CREDENTIALS.
        # ---------------------------------------------------------
        # 7a: Wrong password
        res7_wrong_pw = client.post("/api/v1/auth/login", json={
            "email": "aarav.patel@example.com",
            "password": "wrongpassword999"
        })
        json7_wrong_pw = res7_wrong_pw.json()

        # 7b: Unknown email
        res7_unknown_email = client.post("/api/v1/auth/login", json={
            "email": "nonexistent.user@example.com",
            "password": "somepassword123"
        })
        json7_unknown_email = res7_unknown_email.json()

        test7_pass = (
            res7_wrong_pw.status_code == 401
            and res7_unknown_email.status_code == 401
            and json7_wrong_pw == json7_unknown_email == {
                "detail": "Invalid email or password",
                "code": "INVALID_CREDENTIALS"
            }
        )
        print(f"\n[Test 7] Login failure tests:")
        print(f"  Wrong password: status={res7_wrong_pw.status_code}, body={json7_wrong_pw}")
        print(f"  Unknown email:  status={res7_unknown_email.status_code}, body={json7_unknown_email}")
        assert test7_pass, f"Test 7 failed: {json7_wrong_pw} vs {json7_unknown_email}"
        results["Test 7"] = "PASSED (both return 401 with code: INVALID_CREDENTIALS and identical detail)"

        # ---------------------------------------------------------
        # Protected Route (/test-protected) & dependencies.py test
        # ---------------------------------------------------------
        # Successful login to get JWT token
        login_res = client.post("/api/v1/auth/login", json={
            "email": "aarav.patel@example.com",
            "password": "strongpassword123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.json()}"
        token = login_res.json()["access_token"]

        # Call /test-protected with Bearer token
        prot_res = client.get("/test-protected", headers={"Authorization": f"Bearer {token}"})
        assert prot_res.status_code == 200, f"Protected route failed: {prot_res.json()}"
        prot_data = prot_res.json()
        assert prot_data["message"] == "Authenticated!"
        assert prot_data["user"]["role"] == "DONOR"
        print(f"\n[/test-protected with token] Status={prot_res.status_code}, user={prot_data['user']}")

        # Call /test-protected with no token
        no_token_res = client.get("/test-protected")
        assert no_token_res.status_code == 401
        assert no_token_res.json()["code"] == "NOT_AUTHENTICATED"
        print(f"[/test-protected without token] Status={no_token_res.status_code}, body={no_token_res.json()}")

        # Call /test-protected with invalid token
        bad_token_res = client.get("/test-protected", headers={"Authorization": "Bearer bad.token.here"})
        assert bad_token_res.status_code == 401
        assert bad_token_res.json()["code"] == "INVALID_TOKEN"
        print(f"[/test-protected with invalid token] Status={bad_token_res.status_code}, body={bad_token_res.json()}")

    # Restore orig_db and lifespan
    auth_router.db = orig_db
    database.db = orig_db
    app.router.lifespan_context = orig_lifespan

    print("\n" + "=" * 60)
    print("ALL 7 TESTS + PROTECTED ROUTE TESTS PASSED!")
    print("=" * 60)
    for k, v in results.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    run_all_seven_tests()
