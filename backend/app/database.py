from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(settings.mongodb_url)
db = client[settings.db_name]

async def create_indexes():
    await db.users.create_index("email", unique=True)

    await db.users.create_index("role")

    print("Database indexes created successfully!")

