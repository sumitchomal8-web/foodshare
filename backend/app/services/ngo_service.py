"""
app/services/ngo_service.py — Person B
Service functions and verification rules for the NGO/volunteer module.
Spec Section 4.1, 5, 7.
"""
from typing import Any, Dict, Optional

from app.services.donation_service import (
    FoodShareAPIException,
    list_ngo_donations,
)


def is_ngo_verified(user: Dict[str, Any]) -> bool:
    """
    Check if the user is an active NGO with verification_status == 'VERIFIED'.
    """
    if user.get("role") != "NGO" or not user.get("is_active", True):
        return False
    profile = user.get("ngo_profile") or {}
    return profile.get("verification_status") == "VERIFIED"


def assert_ngo_verified(user: Dict[str, Any]) -> None:
    """
    Ensures the user is an active, verified NGO.
    Raises 403 FORBIDDEN, 403 ACCOUNT_DISABLED, or 403 NGO_NOT_VERIFIED.
    """
    if not user.get("is_active", True):
        raise FoodShareAPIException(
            status_code=403,
            code="ACCOUNT_DISABLED",
            detail="Your account is disabled.",
        )
    if user.get("role") != "NGO":
        raise FoodShareAPIException(
            status_code=403,
            code="FORBIDDEN",
            detail="Only NGOs can perform this action.",
        )
    profile = user.get("ngo_profile") or {}
    if profile.get("verification_status") != "VERIFIED":
        raise FoodShareAPIException(
            status_code=403,
            code="NGO_NOT_VERIFIED",
            detail="NGO must be verified by an administrator before accepting donations.",
        )
