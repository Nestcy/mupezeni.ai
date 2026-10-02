from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from supabase import Client, create_client

from app.core.config import settings


class DatabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client: Client | None = None
        if url and key:
            self.client = create_client(url, key)

    def get_client(self) -> Client:
        if self.client is None:
            raise RuntimeError("Supabase client has not been configured")
        return self.client


supabase_client = DatabaseClient(settings.supabase_url, settings.supabase_anon_key)


def get_database_client() -> Client:
    return supabase_client.get_client()


def get_service_role_client() -> Client:
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def require_auth() -> dict[str, Any]:
    from app.core.security import get_current_user

    return await get_current_user(request=None)  # type: ignore[arg-type]


async def require_business_member_for_id(
    business_id: str,
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    from app.core.security import get_current_user

    _ = get_current_user
    if not business_id:
        raise HTTPException(status_code=400, detail="Business ID is required")
    return {"id": user.get("id"), "business_id": business_id}
