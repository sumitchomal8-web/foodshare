from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.db_name]

async def create_donation_indexes():
    await db.donations.create_index([("status", 1), ("created_at", -1)])
    await db.donations.create_index("donor_id")
    await db.donations.create_index("accepted_by")
    await db.donations.create_index("pickup_address.city")
    await db.donations.create_index("expires_at")


async def create_indexes():
    # Users indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")

    await create_donation_indexes()

    print("Database indexes created successfully!")
