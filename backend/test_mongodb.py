import asyncio

from app.database import client


async def test_connection():
    try:
        result = await client.admin.command("ping")
        print("MongoDB connected successfully!")
        print(result)

    except Exception as error:
        print("MongoDB connection failed!")
        print(type(error).__name__)
        print(error)

    finally:
        client.close()


asyncio.run(test_connection())
