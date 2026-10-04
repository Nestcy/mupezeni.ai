"""Meta Graph API client (WhatsApp Business, Facebook Pages, Instagram). Injectable so tests never hit the network."""
from __future__ import annotations

from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

SCOPES = {
    "whatsapp": ["whatsapp_business_management", "whatsapp_business_messaging"],
    "facebook": ["pages_show_list", "pages_messaging", "pages_manage_metadata"],
    "instagram": ["pages_show_list", "instagram_basic", "instagram_manage_messages", "pages_manage_metadata"],
}


class ProviderAuthError(Exception):
    pass


class MetaClient(Protocol):
    def authorize_url(self, provider: str, state: str) -> str: ...
    async def exchange_code(self, code: str) -> dict[str, Any]: ...
    async def verify_account(self, provider: str, user_token: str, external_account_id: str) -> dict[str, Any]: ...


class GraphMetaClient:
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str, version: str = "v21.0"):
        self.app_id, self.app_secret, self.redirect_uri = app_id, app_secret, redirect_uri
        self.base = f"https://graph.facebook.com/{version}"
        self.dialog = f"https://www.facebook.com/{version}/dialog/oauth"

    def authorize_url(self, provider: str, state: str) -> str:
        q = {"client_id": self.app_id, "redirect_uri": self.redirect_uri, "state": state,
             "scope": ",".join(SCOPES[provider]), "response_type": "code"}
        return f"{self.dialog}?{urlencode(q)}"

    async def _get(self, path: str, token: str | None = None, **params: Any) -> dict[str, Any]:
        if token:
            params["access_token"] = token
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.base}/{path}", params=params)
        if r.status_code >= 400:
            raise ProviderAuthError(f"Meta API rejected the request ({r.status_code})")
        return r.json()

    async def exchange_code(self, code: str) -> dict[str, Any]:
        short = await self._get("oauth/access_token", client_id=self.app_id, client_secret=self.app_secret,
                                redirect_uri=self.redirect_uri, code=code)
        # Upgrade to a long-lived token (~60 days).
        return await self._get("oauth/access_token", grant_type="fb_exchange_token", client_id=self.app_id,
                               client_secret=self.app_secret, fb_exchange_token=short["access_token"])

    async def verify_account(self, provider: str, user_token: str, external_account_id: str) -> dict[str, Any]:
        """Prove the token's owner controls the account. Never trust an ID supplied by the browser."""
        if provider == "whatsapp":
            info = await self._get(external_account_id, user_token, fields="id,display_phone_number,verified_name")
            return {"external_account_id": info["id"], "token": user_token, "name": info.get("verified_name")}
        pages = (await self._get("me/accounts", user_token, fields="id,name,access_token,instagram_business_account")).get("data", [])
        for p in pages:
            if provider == "facebook" and p["id"] == external_account_id:
                return {"external_account_id": p["id"], "token": p["access_token"], "name": p.get("name")}
            if provider == "instagram" and p["id"] == external_account_id and p.get("instagram_business_account"):
                return {"external_account_id": p["instagram_business_account"]["id"], "token": p["access_token"], "name": p.get("name")}
        raise ProviderAuthError("Authenticated user does not manage that account")
