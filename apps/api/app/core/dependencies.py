from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request

from app.core.security import get_current_user


async def require_business_membership(
    request: Request,
    business_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    # The database-backed validation should happen here in production.
    # For this foundation, we validate that the user is a member of the business
    # by checking the business_members table through the Supabase client.
    from app.db.client import get_database_client

    client = get_database_client()
    try:
        result = (
            client.table("business_members")
            .select("role, business_id")
            .eq("business_id", business_id)
            .eq("user_id", user["id"])
            .execute()
        )
    except Exception as exc:  # pragma: no cover - DB not configured or unavailable
        raise HTTPException(status_code=403, detail="Business access validation failed") from exc

    if not result.data:
        raise HTTPException(status_code=403, detail="User is not a member of this business")

    return {"user": user, "role": result.data[0].get("role"), "business_id": business_id}
