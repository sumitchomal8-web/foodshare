from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, IndexModel
from app.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
db = client[settings.DB_NAME]


async def create_user_indexes():
    """Created by Person A (Section 4.4)."""
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("role", ASCENDING)]),
    ])


async def create_donation_indexes():
    """Created by Person B (Section 4.4)."""
    await db.donations.create_indexes([
        IndexModel([("donor_id", ASCENDING)]),
        IndexModel([("accepted_by", ASCENDING)]),
        IndexModel([("status", ASCENDING), ("expires_at", ASCENDING)]),
        IndexModel([("pickup_address.city", ASCENDING), ("status", ASCENDING)]),
    ])


async def create_indexes():
    """Coordinates index creation across modules."""
    await create_user_indexes()
    await create_donation_indexes()
