"""
backend/scripts/seed.py
Database seeding script for FoodShare.
Spec Section 2: "Admin accounts are created manually in the database (seed script), never through public registration."

Usage:
  uv run python scripts/seed.py
"""
import asyncio
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.database import db, client, create_indexes
from app.utils.security import hash_password
from app.schemas.donation import DonationStatus, FoodType, QuantityUnit


async def seed():
    print("Connecting and creating indexes...")
    await create_indexes()

    now = datetime.now(timezone.utc)
    default_password_hash = hash_password("FoodShare@2026")

    # 1. Admin User
    admin = await db.users.find_one({"email": "admin@foodshare.org"})
    if not admin:
        admin_id = ObjectId()
        await db.users.insert_one({
            "_id": admin_id,
            "name": "Platform Administrator",
            "email": "admin@foodshare.org",
            "password_hash": default_password_hash,
            "role": "ADMIN",
            "phone": "9990001111",
            "address": {
                "street": "1 Admin Office Rd",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001",
            },
            "ngo_profile": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        print(" Created Admin: admin@foodshare.org / FoodShare@2026")
    else:
        admin_id = admin["_id"]
        print(" Admin already exists: admin@foodshare.org")

    # 2. Demo Verified NGO
    verified_ngo = await db.users.find_one({"email": "feedindia@ngo.org"})
    if not verified_ngo:
        ngo_id = ObjectId()
        await db.users.insert_one({
            "_id": ngo_id,
            "name": "Feed India Foundation",
            "email": "feedindia@ngo.org",
            "password_hash": default_password_hash,
            "role": "NGO",
            "phone": "9880002222",
            "address": {
                "street": "42 Community Hall Rd",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560034",
            },
            "ngo_profile": {
                "organization_name": "Feed India Foundation",
                "org_type": "NGO",
                "registration_number": "KA-NGO-2021-9981",
                "verification_status": "VERIFIED",
                "verified_by": admin_id,
                "verified_at": now,
            },
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        print(" Created Verified NGO: feedindia@ngo.org / FoodShare@2026")
    else:
        ngo_id = verified_ngo["_id"]
        print(" Verified NGO already exists: feedindia@ngo.org")

    # 3. Demo Pending NGO (for testing admin verification flow)
    pending_ngo = await db.users.find_one({"email": "hope@volunteer.org"})
    if not pending_ngo:
        await db.users.insert_one({
            "_id": ObjectId(),
            "name": "Hope Volunteers Group",
            "email": "hope@volunteer.org",
            "password_hash": default_password_hash,
            "role": "NGO",
            "phone": "9770003333",
            "address": {
                "street": "15 Green Park St",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
            },
            "ngo_profile": {
                "organization_name": "Hope Volunteers",
                "org_type": "VOLUNTEER",
                "registration_number": None,
                "verification_status": "PENDING",
                "verified_by": None,
                "verified_at": None,
            },
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        print(" Created Pending NGO: hope@volunteer.org / FoodShare@2026")
    else:
        print(" Pending NGO already exists: hope@volunteer.org")

    # 4. Demo Donor
    donor = await db.users.find_one({"email": "taj_caterers@donor.org"})
    if not donor:
        donor_id = ObjectId()
        await db.users.insert_one({
            "_id": donor_id,
            "name": "Taj Catering Services",
            "email": "taj_caterers@donor.org",
            "password_hash": default_password_hash,
            "role": "DONOR",
            "phone": "9660004444",
            "address": {
                "street": "88 Palace Rd",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560052",
            },
            "ngo_profile": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })
        print(" Created Donor: taj_caterers@donor.org / FoodShare@2026")
    else:
        donor_id = donor["_id"]
        print(" Donor already exists: taj_caterers@donor.org")

    # 5. Sample AVAILABLE Donation
    existing_available = await db.donations.find_one({"title": "Surplus Rice and Dal (100 meals)"})
    if not existing_available:
        await db.donations.insert_one({
            "_id": ObjectId(),
            "donor_id": donor_id,
            "title": "Surplus Rice and Dal (100 meals)",
            "food_type": FoodType.COOKED.value,
            "quantity": 100.0,
            "quantity_unit": QuantityUnit.PLATES.value,
            "description": "Freshly prepared vegetarian meals from banquet event.",
            "pickup_address": {
                "street": "88 Palace Rd",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560052",
            },
            "available_from": now,
            "expires_at": now + timedelta(hours=6),
            "status": DonationStatus.AVAILABLE.value,
            "accepted_by": None,
            "accepted_at": None,
            "picked_up_at": None,
            "distributed_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "status_history": [{
                "status": DonationStatus.AVAILABLE.value,
                "changed_by": str(donor_id),
                "changed_at": now,
            }],
            "created_at": now,
            "updated_at": now,
        })
        print(" Created Sample Donation: Surplus Rice and Dal (AVAILABLE)")

    client.close()
    print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
