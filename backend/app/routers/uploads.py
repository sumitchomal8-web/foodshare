import asyncio

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, UploadFile

from app.config import settings
from app.services.donation_service import FoodShareAPIException
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])

MAX_IMAGE_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB max
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _upload_to_cloudinary(contents: bytes) -> dict:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
    return cloudinary.uploader.upload(
        contents,
        folder="foodshare",
        resource_type="image",
    )


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        raise FoodShareAPIException(
            status_code=503,
            code="CLOUDINARY_NOT_CONFIGURED",
            detail="Image upload is not configured. Set CLOUDINARY_* keys in backend/.env.",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise FoodShareAPIException(
            status_code=400,
            code="INVALID_FILE_TYPE",
            detail="Only JPG, PNG, and WEBP images are allowed.",
        )

    contents = await file.read()
    if not contents:
        raise FoodShareAPIException(
            status_code=400,
            code="EMPTY_FILE",
            detail="Uploaded file is empty.",
        )

    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise FoodShareAPIException(
            status_code=400,
            code="FILE_TOO_LARGE",
            detail="Image size must be 3 MB or smaller.",
        )

    try:
        result = await asyncio.to_thread(_upload_to_cloudinary, contents)
    except Exception as exc:
        raise FoodShareAPIException(
            status_code=502,
            code="UPLOAD_FAILED",
            detail=f"Failed to upload image to Cloudinary: {exc}",
        )

    return {
        "url": result["secure_url"],
        "public_id": result.get("public_id"),
    }
