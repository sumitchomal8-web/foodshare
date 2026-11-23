from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.utils.errors import AppError
from app.main import app_error_handler


error_app = FastAPI()
error_app.add_exception_handler(AppError, app_error_handler)


@error_app.get("/test-error")
async def raise_test_error():
    raise AppError(
        status_code=409,
        detail="Email already registered",
        code="EMAIL_EXISTS",
    )


def test_app_error_response():
    client = TestClient(error_app)

    response = client.get("/test-error")

    assert response.status_code == 409
    
    assert response.json() == {
        "detail": "Email already registered",
        "code": "EMAIL_EXISTS",
    }