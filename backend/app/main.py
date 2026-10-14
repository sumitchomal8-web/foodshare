from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import client, create_indexes

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield
    client.close()

app = FastAPI(title="FoodShare API", lifespan=lifespan)

@app.get("/health")
async def health():
    await client.admin.command("ping")

    return{
        "status": "ok",
        "database": "connected"
    }

