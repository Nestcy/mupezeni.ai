from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.client import get_database_client
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("mupezeni.security")


class AuthenticationError(Exception):
    pass


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> dict[str, Any]:
    token = credentials.credentials if credentials else None
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1]

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        client = get_database_client()
        auth_response = client.auth.get_user(token)
        user = auth_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return {"id": user.id, "email": user.email, "raw_user": user}
    except Exception as exc:  # pragma: no cover - supabase lookup failure path
        logger.warning("auth_check_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=401, detail="Authentication failed") from exc


async def get_current_user_optional(request: Request) -> dict[str, Any] | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
