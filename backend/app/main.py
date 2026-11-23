from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from app.database import client, create_indexes
from app.utils.errors import AppError
from app.routers.auth import router as auth_router
from app.utils.dependencies import get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield
    client.close()

app = FastAPI(title="FoodShare API", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/v1")

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

@app.get("/test-protected")
async def test_protected_route(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Authenticated!",
        "user": current_user,
    }
