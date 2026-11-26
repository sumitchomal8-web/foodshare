"""
app/main.py — FoodShare FastAPI application entry point.

ROUTER REGISTRATION ORDER MATTERS (spec Section 7 note):
  1. donor.py    (Person A) — registers /api/v1/donations/mine FIRST
  2. donations.py (Person B) — registers /api/v1/donations/{id}
  FastAPI resolves the first matching route, so /mine must precede /{id}.

Person A adds their routers once feature/auth is merged.
Person B registers donations.py and ngo.py here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import client, create_indexes, db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield
    client.close()


app = FastAPI(
    title="FoodShare API",
    version="0.2.0",
    description="Connecting food donors with NGOs and volunteers.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global error handler: unwrap FoodShareAPIException so HTTPException.detail
# already has the {detail, code} shape defined in spec Section 8.
# ---------------------------------------------------------------------------
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If the detail is already our {detail, code} dict, pass it through;
    # otherwise wrap plain strings for consistency.
    if isinstance(exc.detail, dict):
        body = exc.detail
    else:
        body = {"detail": str(exc.detail), "code": "ERROR"}
    return JSONResponse(status_code=exc.status_code, content=body)


# ---------------------------------------------------------------------------
# Health check (shared, spec Phase 1)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception as exc:
        db_status = f"disconnected: {exc}"
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
    }


# ---------------------------------------------------------------------------
# Router registration order (Spec Section 7):
# 1. auth.router   (/api/v1/auth)
# 2. users.router  (/api/v1/users)
# 3. donor.router  (/api/v1/donations/mine MUST precede /api/v1/donations/{id})
# 4. donations.router (/api/v1/donations)
# 5. ngo.router    (/api/v1/ngo)
# 6. admin.router  (/api/v1/admin)
# ---------------------------------------------------------------------------
from app.routers import admin, auth, donations, donor, ngo, users

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(donor.router)   # MUST precede donations.router for /donations/mine
app.include_router(donations.router)
app.include_router(ngo.router)
app.include_router(admin.router)
