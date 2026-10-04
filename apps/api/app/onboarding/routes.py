"""HTTP surface for onboarding. Auth dependencies are injected so main.py's DEV_AUTH switch keeps working
and this module has no import cycle with it."""
from __future__ import annotations

import logging
from typing import Any, Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.onboarding.inbound import InboundEvent, InboundHandler, resolve_web_channel, route_meta_payload, verify_meta_signature
from app.onboarding.service import OnboardingError, OnboardingService

logger = logging.getLogger("mupezeni.onboarding")


class BusinessIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    path: Literal["existing_retail", "mupezeni_managed"]
    country: str | None = Field(None, min_length=2, max_length=2)
    currency: str = Field("ZMW", min_length=3, max_length=3)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)


class CatalogConnectIn(BaseModel):
    provider: Literal["mupezeni", "shopify", "woocommerce"]
    config: dict[str, Any] = Field(default_factory=dict)          # shop_domain / site_url (not secret)
    credentials: dict[str, str] = Field(default_factory=dict)     # access_token / consumer_key / consumer_secret


class OAuthCompleteIn(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)
    external_account_id: str = Field(min_length=1, max_length=128)  # WABA phone_number_id or Page id; re-verified server-side


class WebConnectIn(BaseModel):
    allowed_origins: list[str] = Field(min_length=1, max_length=10)


class WebMessageIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=128)
    message_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)


def build_router(
    *,
    service: OnboardingService,
    current_user: Callable[..., Any],
    business_access: Callable[..., Any],
    admin_access: Callable[..., Any],
    inbound_handler: InboundHandler,
    meta_app_secret: str,
    meta_verify_token: str,
) -> APIRouter:
    r = APIRouter(prefix="/api/v1")

    def guard(fn):
        try:
            return fn()
        except OnboardingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    async def aguard(coro):
        try:
            return await coro
        except OnboardingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    # Any signed-in user may start a business; they become its owner atomically. Everything after needs membership.
    @r.post("/onboarding/businesses", status_code=201, tags=["onboarding"])
    async def start(body: BusinessIn, user: dict = Depends(current_user)):
        return guard(lambda: service.start_business(user["id"], **body.model_dump()))

    @r.get("/businesses/{business_id}/onboarding", tags=["onboarding"])
    async def status(business_id: str, _: dict = Depends(business_access)):
        return guard(lambda: service.checklist(business_id))

    @r.post("/businesses/{business_id}/connectors/catalog", tags=["onboarding"])
    async def connect_catalog(business_id: str, body: CatalogConnectIn, a: dict = Depends(admin_access)):
        return await aguard(service.connect_catalog(business_id, a["user"]["id"], body.provider, body.config, body.credentials))

    @r.post("/businesses/{business_id}/connectors/{provider}/authorize", tags=["onboarding"])
    async def authorize(business_id: str, provider: Literal["whatsapp", "facebook", "instagram"], a: dict = Depends(admin_access)):
        return guard(lambda: service.authorize_url(business_id, a["user"]["id"], provider))

    @r.post("/businesses/{business_id}/connectors/{provider}/complete", tags=["onboarding"])
    async def complete(business_id: str, provider: Literal["whatsapp", "facebook", "instagram"],
                       body: OAuthCompleteIn, a: dict = Depends(admin_access)):
        return await aguard(service.complete_oauth(business_id, a["user"]["id"], provider, **body.model_dump()))

    @r.post("/businesses/{business_id}/connectors/web", tags=["onboarding"])
    async def connect_web(business_id: str, body: WebConnectIn, a: dict = Depends(admin_access)):
        return guard(lambda: service.connect_web(business_id, a["user"]["id"], body.allowed_origins))

    @r.delete("/businesses/{business_id}/connectors/{provider}", tags=["onboarding"])
    async def disconnect(business_id: str, provider: str, _: dict = Depends(admin_access)):
        return guard(lambda: service.disconnect(business_id, provider))

    @r.post("/businesses/{business_id}/onboarding/activate", tags=["onboarding"])
    async def activate(business_id: str, _: dict = Depends(admin_access)):
        return guard(lambda: service.activate(business_id))

    # ── Inbound: authenticated by signature / site key, not by user ──────────
    @r.get("/webhooks/meta", tags=["webhooks"])
    async def meta_verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
                          challenge: str = Query("", alias="hub.challenge")):
        import hmac
        if mode == "subscribe" and meta_verify_token and hmac.compare_digest(token, meta_verify_token):
            return PlainTextResponse(challenge)
        raise HTTPException(status_code=403, detail="Verification failed")

    @r.post("/webhooks/meta", tags=["webhooks"])
    async def meta_inbound(request: Request, x_hub_signature_256: str | None = Header(None)):
        raw = await request.body()
        if not verify_meta_signature(meta_app_secret, raw, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="Body must be JSON")
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Body must be a JSON object")
        return await route_meta_payload(payload, service.store, inbound_handler)

    @r.post("/channels/web/{site_key}/messages", status_code=202, tags=["channels"])
    async def web_inbound(site_key: str, body: WebMessageIn, origin: str | None = Header(None)):
        conn = resolve_web_channel(service.store, site_key, origin)
        if not conn:
            raise HTTPException(status_code=403, detail="Unknown site key or origin not allowed")
        await inbound_handler(InboundEvent(business_id=conn["business_id"], channel="web",
                                           external_message_id=body.message_id, customer_identity=body.session_id,
                                           content=body.content))
        return {"accepted": True}

    return r
