"""Mupezeni API entrypoint.

Run (from apps/api):
    DEBUG=true MUPEZENI_DEV_AUTH=true uvicorn app.main:app --reload

IMPORTANT: commerce state (checkouts, payments, fulfillments, deliveries) lives in
process memory today, so run a single worker and expect a restart to wipe it.

Environment (repo-root .env):
    SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY   real auth
    ALLOW_ORIGINS                                                comma-separated CORS origins
    DEBUG=true                                                   enables /docs
    MUPEZENI_DEV_AUTH=true                                       local-only auth bypass; needs DEBUG=true too.
                                                                 Identity from X-Dev-User, role from X-Dev-Role.
    PAYMENT_WEBHOOK_SECRET_<PROVIDER>, DELIVERY_WEBHOOK_SECRET_<PROVIDER>   HMAC-SHA256 secrets, e.g. ..._MOCK
    PAYMENT_PROVIDER, DELIVERY_PROVIDER                          default "mock"
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import services as svc
from app.core.commerce_errors import DuplicateWebhook, UnauthorizedError
from app.core.config import settings
from app.core.dependencies import require_business_membership
from app.core.errors import MupezeniError
from app.core.security import get_current_user
from app.delivery.models import DeliveryMode
from app.delivery.webhooks import DeliveryWebhookProcessor
from app.payments.models import PaymentStatus
from app.payments.webhooks import WebhookProcessor

logger = logging.getLogger("mupezeni.api")

# Two switches on purpose: a stray env var alone must never disable auth in production.
DEV_AUTH = settings.debug and os.getenv("MUPEZENI_DEV_AUTH", "").lower() in {"1", "true", "yes"}
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock")
DELIVERY_PROVIDER = os.getenv("DELIVERY_PROVIDER", "mock")

_payment_webhooks = WebhookProcessor(svc.payment_service.idempotency_store)
_delivery_webhooks = DeliveryWebhookProcessor()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if DEV_AUTH:
        logger.warning("DEV AUTH ENABLED: authentication is bypassed. Never use this outside local development.")
    if not (settings.supabase_url and settings.supabase_anon_key):
        logger.warning("Supabase is not configured: authenticated routes will reject all requests.")
    logger.warning("Commerce services are in-memory and use stub catalog/analytics data.")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allow_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

# ── Errors ────────────────────────────────────────────────────────────────────

_STATUS_BY_CODE = {
    "UNAUTHORIZED": 401,
    "PAYMENT_FAILED": 402,
    "CART_NOT_FOUND": 404, "DELIVERY_NOT_FOUND": 404, "FULFILLMENT_NOT_FOUND": 404,
    "CHECKOUT_ALREADY_COMPLETED": 409, "INVENTORY_UNAVAILABLE": 409, "INVALID_ORDER_TRANSITION": 409,
    "ORDER_ALREADY_CANCELLED": 409, "PAYMENT_PENDING": 409, "PAYMENT_ALREADY_PROCESSED": 409,
    "INVALID_FULFILLMENT_TRANSITION": 409, "DUPLICATE_WEBHOOK": 409,
    "CHECKOUT_EXPIRED": 410,
    "CART_EMPTY": 422, "INVALID_VARIANT": 422, "INVALID_ADDRESS": 422, "INVALID_CURRENCY": 422,
    "DELIVERY_CREATION_FAILED": 502, "PROVIDER_UNAVAILABLE": 503, "DELIVERY_UNAVAILABLE": 503,
    "PROVIDER_TIMEOUT": 504,
}


@app.exception_handler(MupezeniError)
async def domain_error_handler(_: Request, exc: MupezeniError) -> JSONResponse:
    status = _STATUS_BY_CODE.get(exc.code, exc.status_code)
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": exc.message}})


# ── Auth & tenancy ────────────────────────────────────────────────────────────

async def current_user(request: Request) -> dict[str, Any]:
    if DEV_AUTH:
        return {"id": request.headers.get("x-dev-user", "dev-user"), "email": "dev@localhost"}
    return await get_current_user(request)


async def business_access(
    business_id: str, request: Request, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    """Caller must be a member of {business_id}. Never trust the client for tenancy."""
    if DEV_AUTH:
        return {"user": user, "role": request.headers.get("x-dev-role", "owner"), "business_id": business_id}
    return await require_business_membership(request, business_id, user)


async def admin_access(access: dict[str, Any] = Depends(business_access)) -> dict[str, Any]:
    if access.get("role") not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Owner or admin role required")
    return access


# ── Onboarding & connector auth ───────────────────────────────────────────────

async def _inbound_handler(event) -> None:
    """TODO: hand off to the conversation/worker pipeline. Business id is already tenant-verified."""
    logger.info("inbound business=%s channel=%s msg=%s", event.business_id, event.channel, event.external_message_id)


def _mount_onboarding() -> None:
    from app.db.client import get_service_role_client
    from app.onboarding.crypto import CredentialCipher, CryptoConfigError
    from app.onboarding.meta import GraphMetaClient
    from app.onboarding.routes import build_router
    from app.onboarding.service import OnboardingService
    from app.onboarding.store import SupabaseStore
    from app.onboarding.verifiers import HttpCatalogVerifier

    try:
        if not settings.oauth_state_secret:
            raise CryptoConfigError("OAUTH_STATE_SECRET is not configured")
        service = OnboardingService(
            SupabaseStore(get_service_role_client()),
            CredentialCipher(settings.connector_encryption_keys),
            GraphMetaClient(settings.meta_app_id, settings.meta_app_secret, settings.meta_redirect_uri, settings.meta_graph_version),
            HttpCatalogVerifier(),
            settings.oauth_state_secret,
        )
    except (CryptoConfigError, RuntimeError) as exc:
        logger.warning("Onboarding routes NOT mounted: %s", exc)  # fail closed: no half-secured connector endpoints
        return
    app.include_router(build_router(
        service=service, current_user=current_user, business_access=business_access, admin_access=admin_access,
        inbound_handler=_inbound_handler, meta_app_secret=settings.meta_app_secret,
        meta_verify_token=settings.meta_webhook_verify_token))


_mount_onboarding()


@contextmanager
def _state_guard():
    """State machines raise bare ValueError on illegal transitions; that is a 409, not a 500."""
    try:
        yield
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


def _scoped_key(business_id: str, body_key: str | None, header_key: str | None) -> str | None:
    """Namespace idempotency keys per business so tenants can never collide."""
    key = body_key or header_key
    return f"{business_id}:{key}" if key else None


def _require_order(business_id: str, order_id: str) -> None:
    """An order exists only once a checkout for this business completed with that order_id."""
    sessions = svc.checkout_service._sessions.values()  # TODO: expose a lookup on the service
    if not any(s.order_id == order_id and s.business_id == business_id for s in sessions):
        raise _not_found("Order")


# ── Request models ────────────────────────────────────────────────────────────

IdKey = Field(None, min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_\-:.]+$")


class CartItemIn(BaseModel):
    # Deliberately no price/discount fields: the server prices every line item.
    product_id: str = Field(min_length=1, max_length=64)
    variant_id: str | None = Field(None, max_length=64)
    variant_name: str | None = Field(None, max_length=120)
    quantity: int = Field(gt=0, le=1000)


class CheckoutCreateIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    cart_id: str = Field(min_length=1, max_length=64)
    items: list[CartItemIn] = Field(min_length=1, max_length=100)
    currency: str = Field("ZMW", min_length=3, max_length=3)
    shipping_minor: int = Field(0, ge=0)  # staff-entered; integer minor units
    idempotency_key: str | None = IdKey


class PaymentCreateIn(BaseModel):
    checkout_id: str
    payment_method_type: str = Field("card", max_length=40)
    idempotency_key: str | None = IdKey


class FulfillmentItemIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1000)
    sku: str | None = Field(None, max_length=64)


class FulfillmentCreateIn(BaseModel):
    items: list[FulfillmentItemIn] = Field(min_length=1, max_length=100)
    notes: str | None = Field(None, max_length=1000)


class DeliveryCreateIn(BaseModel):
    delivery_mode: DeliveryMode = DeliveryMode.EXTERNAL_PROVIDER
    pickup_address: dict[str, Any] | None = None
    delivery_address: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "supabase_configured": bool(settings.supabase_url and settings.supabase_anon_key),
        "dev_auth": DEV_AUTH,
    }


B = "/api/v1/businesses/{business_id}"

# Checkout --------------------------------------------------------------------

@app.post(f"{B}/checkouts", status_code=201, tags=["checkout"])
async def create_checkout(
    business_id: str,
    body: CheckoutCreateIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    _: dict = Depends(business_access),
):
    cart = {
        "id": body.cart_id,
        "business_id": business_id,
        "customer_id": body.customer_id,
        "is_active": True,
        "items": [i.model_dump(exclude_none=True) for i in body.items],
    }
    return svc.checkout_service.create_checkout(
        business_id=business_id,
        customer_id=body.customer_id,
        cart_id=body.cart_id,
        cart_data=cart,
        currency=body.currency.upper(),
        shipping_minor=body.shipping_minor,
        idempotency_key=_scoped_key(business_id, body.idempotency_key, idempotency_key),
    )


@app.get(f"{B}/checkouts/{{checkout_id}}", tags=["checkout"])
async def get_checkout(business_id: str, checkout_id: str, _: dict = Depends(business_access)):
    session = svc.checkout_service.get_checkout(business_id, checkout_id)
    if not session:
        raise _not_found("Checkout")
    return session


@app.post(f"{B}/checkouts/{{checkout_id}}/validate", tags=["checkout"])
async def validate_checkout(business_id: str, checkout_id: str, _: dict = Depends(business_access)):
    with _state_guard():
        return svc.checkout_service.validate_checkout(business_id, checkout_id)


@app.post(f"{B}/checkouts/{{checkout_id}}/complete", tags=["checkout"])
async def complete_checkout(business_id: str, checkout_id: str, _: dict = Depends(business_access)):
    """Creates the order. The order id is minted by the server, never by the client."""
    with _state_guard():
        return svc.checkout_service.complete_checkout(business_id, checkout_id, f"ord_{uuid.uuid4().hex[:12]}")


@app.post(f"{B}/checkouts/{{checkout_id}}/cancel", tags=["checkout"])
async def cancel_checkout(business_id: str, checkout_id: str, _: dict = Depends(business_access)):
    with _state_guard():
        return svc.checkout_service.cancel_or_expire(business_id, checkout_id)


# Payments --------------------------------------------------------------------

@app.post(f"{B}/payments", status_code=201, tags=["payments"])
async def create_payment(
    business_id: str,
    body: PaymentCreateIn,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    _: dict = Depends(business_access),
):
    """Amount, currency, order and customer all come from the completed checkout, not the request."""
    session = svc.checkout_service.get_checkout(business_id, body.checkout_id)
    if not session:
        raise _not_found("Checkout")
    if not session.order_id:
        raise HTTPException(status_code=409, detail="Complete the checkout before creating a payment")

    key = body.idempotency_key or idempotency_key
    live = {PaymentStatus.PENDING, PaymentStatus.PROCESSING, PaymentStatus.PAID}
    for p in svc.payment_service._payments.values():  # TODO: expose a lookup on the service
        if p.business_id == business_id and p.order_id == session.order_id and p.status in live:
            if key and p.idempotency_key == key:
                return p  # safe replay of the same request
            raise HTTPException(status_code=409, detail="This order already has an active or paid payment")

    return await svc.payment_service.create_payment(
        business_id=business_id,
        order_id=session.order_id,
        checkout_id=session.id,
        customer_id=session.customer_id,
        amount_minor=session.grand_total,
        currency=session.currency,
        provider=PAYMENT_PROVIDER,
        payment_method_type=body.payment_method_type,
        idempotency_key=key,
    )


@app.get(f"{B}/payments/{{payment_id}}", tags=["payments"])
async def get_payment(business_id: str, payment_id: str, _: dict = Depends(business_access)):
    payment = svc.payment_service.get_payment(business_id, payment_id)
    if not payment:
        raise _not_found("Payment")
    return payment


@app.post(f"{B}/payments/{{payment_id}}/refund", tags=["payments"])
async def refund_payment(business_id: str, payment_id: str, _: dict = Depends(admin_access)):
    """Full refunds only, owner/admin only. Partial refunds are not exposed until the service supports them."""
    return await svc.payment_service.refund_payment(business_id, payment_id)


# Fulfillment -----------------------------------------------------------------

@app.post(f"{B}/orders/{{order_id}}/fulfillment", status_code=201, tags=["fulfillment"])
async def create_fulfillment(
    business_id: str, order_id: str, body: FulfillmentCreateIn, _: dict = Depends(business_access)
):
    _require_order(business_id, order_id)
    return svc.fulfillment_service.create_fulfillment(
        business_id=business_id,
        order_id=order_id,
        items=[i.model_dump() for i in body.items],
        notes=body.notes,
    )


@app.get(f"{B}/fulfillments/{{fulfillment_id}}", tags=["fulfillment"])
async def get_fulfillment(business_id: str, fulfillment_id: str, _: dict = Depends(business_access)):
    result = svc.fulfillment_service.get_fulfillment(business_id, fulfillment_id)
    if not result:
        raise _not_found("Fulfillment")
    return result


@app.post(f"{B}/fulfillments/{{fulfillment_id}}/{{action}}", tags=["fulfillment"])
async def advance_fulfillment(
    business_id: str,
    fulfillment_id: str,
    action: Literal["processing", "ready", "fulfilled"],
    _: dict = Depends(business_access),
):
    mark = {
        "processing": svc.fulfillment_service.mark_processing,
        "ready": svc.fulfillment_service.mark_ready,
        "fulfilled": svc.fulfillment_service.mark_fulfilled,
    }[action]
    with _state_guard():
        return mark(business_id, fulfillment_id)


# Delivery --------------------------------------------------------------------

@app.post(f"{B}/orders/{{order_id}}/delivery", status_code=201, tags=["delivery"])
async def create_delivery(
    business_id: str, order_id: str, body: DeliveryCreateIn, _: dict = Depends(business_access)
):
    _require_order(business_id, order_id)
    return await svc.delivery_service.create_delivery(
        business_id=business_id,
        order_id=order_id,
        provider=DELIVERY_PROVIDER,
        delivery_mode=body.delivery_mode,
        pickup_address=body.pickup_address,
        delivery_address=body.delivery_address,
        metadata=body.metadata,
    )


@app.get(f"{B}/deliveries/{{delivery_id}}", tags=["delivery"])
async def get_delivery(business_id: str, delivery_id: str, _: dict = Depends(business_access)):
    result = svc.delivery_service.get_delivery(business_id, delivery_id)
    if not result:
        raise _not_found("Delivery")
    return result


@app.get(f"{B}/deliveries/{{delivery_id}}/tracking", tags=["delivery"])
async def get_tracking(business_id: str, delivery_id: str, _: dict = Depends(business_access)):
    return svc.delivery_service.get_tracking(business_id, delivery_id)


# Analytics (stub data) ---------------------------------------------------------

PeriodQ = Query("last_7_days", pattern=r"^[a-z0-9_]{1,32}$")


def _stub(data: Any) -> dict[str, Any]:
    """The analytics service returns hard-coded sample numbers; say so in every response."""
    return {"data": data, "meta": {"data_source": "stub"}}


@app.get(f"{B}/analytics/overview", tags=["analytics"])
async def analytics_overview(business_id: str, period: str = PeriodQ, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.business_overview(business_id, period))


@app.get(f"{B}/analytics/sales", tags=["analytics"])
async def analytics_sales(business_id: str, period: str = PeriodQ, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.sales_summary(business_id, period))


@app.get(f"{B}/analytics/commerce", tags=["analytics"])
async def analytics_commerce(business_id: str, period: str = PeriodQ, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.commerce_completion_analytics(business_id, period))


@app.get(f"{B}/analytics/inventory", tags=["analytics"])
async def analytics_inventory(business_id: str, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.inventory_summary(business_id))


@app.get(f"{B}/analytics/customers", tags=["analytics"])
async def analytics_customers(business_id: str, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.customer_insights(business_id))


@app.get(f"{B}/analytics/marketing", tags=["analytics"])
async def analytics_marketing(business_id: str, period: str = PeriodQ, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.marketing_performance(business_id, period))


@app.get(f"{B}/analytics/anomalies", tags=["analytics"])
async def analytics_anomalies(business_id: str, period: str = PeriodQ, _: dict = Depends(business_access)):
    return _stub(svc.analytics_service.detect_anomalies(business_id, period))


# Webhooks (provider -> us; authenticated by HMAC signature, not by user) ----------

_PROVIDER = Path(..., pattern=r"^[a-z0-9_]{2,32}$")


async def _verified_webhook(kind: str, provider: str, request: Request, header: str | None):
    """Return (raw_body, parsed_json, signature, secret). Fails closed on every problem."""
    secret = os.getenv(f"{kind}_WEBHOOK_SECRET_{provider.upper()}", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook not configured for this provider")
    if not header:
        raise UnauthorizedError("Missing signature")  # the processor itself would skip the check
    raw = await request.body()
    signature = header.removeprefix("sha256=")
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise UnauthorizedError("Invalid signature")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Body must be JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")
    return raw, payload, signature, secret


def _require_str_fields(payload: dict[str, Any], *names: str) -> None:
    missing = [n for n in names if not isinstance(payload.get(n), str) or not payload[n]]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing or invalid fields: {', '.join(missing)}")


@app.post("/api/v1/webhooks/payments/{provider}", tags=["webhooks"])
async def payment_webhook(
    request: Request, provider: str = _PROVIDER, x_signature: str | None = Header(None)
):
    raw, p, signature, secret = await _verified_webhook("PAYMENT", provider, request, x_signature)
    _require_str_fields(p, "external_event_id", "event_type", "provider_payment_id")
    try:
        result = _payment_webhooks.process_webhook(
            provider=provider,
            external_event_id=p["external_event_id"],
            event_type=p["event_type"],
            provider_payment_id=p["provider_payment_id"],
            payload_bytes=raw,
            signature=signature,
            secret=secret,
            payment_service=svc.payment_service,
        )
    except DuplicateWebhook:
        return {"success": True, "duplicate": True}  # providers retry; acknowledge, don't error
    if result.get("payment_id") is None:
        logger.warning("payment webhook for unknown payment %s:%s", provider, p["provider_payment_id"])
    return result


@app.post("/api/v1/webhooks/delivery/{provider}", tags=["webhooks"])
async def delivery_webhook(
    request: Request, provider: str = _PROVIDER, x_signature: str | None = Header(None)
):
    _, p, _, _ = await _verified_webhook("DELIVERY", provider, request, x_signature)
    _require_str_fields(p, "external_event_id", "provider_delivery_id", "status")
    event_data = p.get("event_data") or {}
    if not isinstance(event_data, dict):
        raise HTTPException(status_code=422, detail="event_data must be an object")
    return _delivery_webhooks.process_webhook(
        provider=provider,
        external_event_id=p["external_event_id"],
        provider_delivery_id=p["provider_delivery_id"],
        status_str=p["status"],
        event_data=event_data,
        delivery_service=svc.delivery_service,
    )


__all__ = ["app"]
