import asyncio
from app.database import client

async def test_connection():
    try:
        result = await client.admin.command("ping")
        print("MongoDB connected successfully!")
        print("Ping result:", result)

    except Exception as error:
        print("\nMongoDB connection failed!")
        print(f"Error Type: {type(error).__name__}")
        print(f"Details: {error}")
        print("\n" + "=" * 60)
        print("TROUBLESHOOTING TIP:")
        print("If you see 'SSL: TLSV1_ALERT_INTERNAL_ERROR' or 'ServerSelectionTimeoutError',")
        print("ensure your current public IP is added to the MongoDB Atlas Network Access list:")
        print("1. Log in to MongoDB Atlas (https://cloud.mongodb.com)")
        print("2. Navigate to 'Network Access' -> 'IP Access List'")
        print("3. Click 'Add IP Address' -> 'Add Current IP Address' (or 0.0.0.0/0 for dev)")
        print("=" * 60)

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
