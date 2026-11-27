from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.database import client, create_indexes
from app.utils.errors import AppError
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.donor import router as donor_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield
    client.close()

app = FastAPI(title="FoodShare API", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(donor_router, prefix="/api/v1")

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.code,
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "code": "VALIDATION_ERROR",
        },
    )

@app.get("/health")
async def health():
    await client.admin.command("ping")

    return {
        "status": "ok",
        "database": "connected"
    }
