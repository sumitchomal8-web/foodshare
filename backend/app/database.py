from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.db_name]

async def create_indexes():
    # Users indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")

    # Listings indexes
    await db.listings.create_index([("status", 1), ("created_at", -1)])
    await db.listings.create_index("donor_id")
    await db.listings.create_index("claimed_by")
    await db.listings.create_index("pickup_address.city")

    print("Database indexes created successfully!")
