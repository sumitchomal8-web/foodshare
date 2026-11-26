"""
app/services/stats_service.py  — Person B
Analytics / reporting for the admin dashboard.
Spec Section 7: GET /api/v1/admin/stats
"""
from datetime import datetime, timezone
from typing import Any, Dict

from app.services.donation_service import FoodShareAPIException


async def get_platform_stats(
    actor: Dict[str, Any],
    db=None,
) -> Dict[str, Any]:
    """
    GET /api/v1/admin/stats
    Returns platform-wide user and donation counts, broken down by
    role / verification / status. All counts run as parallel aggregation
    pipelines in a single round-trip via asyncio.gather.
    """
    import asyncio

    if actor.get("role") != "ADMIN":
        raise FoodShareAPIException(403, "FORBIDDEN", "Admins only.")

    now = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Run all count queries concurrently
    # ------------------------------------------------------------------
    (
        total_users,
        total_donors,
        total_ngos,
        verified_ngos,
        total_admins,
        donation_counts,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"role": "DONOR"}),
        db.users.count_documents({"role": "NGO"}),
        db.users.count_documents({"role": "NGO", "ngo_profile.verification_status": "VERIFIED"}),
        db.users.count_documents({"role": "ADMIN"}),
        _aggregate_donation_counts(db),
    )

    return {
        "users": {
            "total":         total_users,
            "donors":        total_donors,
            "ngos":          total_ngos,
            "verified_ngos": verified_ngos,
            "admins":        total_admins,
        },
        "donations": donation_counts,
        "computed_at": now,
    }


async def _aggregate_donation_counts(db) -> Dict[str, Any]:
    """
    Single aggregation pipeline that counts donations by status.
    Returns a dict keyed by status name plus a 'total' key.
    """
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    cursor = db.donations.aggregate(pipeline)
    rows = await cursor.to_list(length=None)

    # Build lookup and total
    by_status: Dict[str, int] = {r["_id"]: r["count"] for r in rows}
    total = sum(by_status.values())

    statuses = ["AVAILABLE", "ACCEPTED", "PICKED_UP", "DISTRIBUTED", "COMPLETED", "CANCELLED", "EXPIRED"]
    return {
        "total":       total,
        **{s.lower(): by_status.get(s, 0) for s in statuses},
    }
