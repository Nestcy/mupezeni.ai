"""Inbound channel authentication + tenant routing.

The business an inbound message belongs to is ALWAYS resolved from our own connector table
(provider + external account id). A business_id appearing in the payload is never trusted.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.onboarding.store import OnboardingStore

logger = logging.getLogger("mupezeni.inbound")


@dataclass(frozen=True)
class InboundEvent:
    business_id: str
    channel: str
    external_message_id: str
    customer_identity: str
    content: str
    message_type: str = "text"
    received_at: str | None = None


InboundHandler = Callable[[InboundEvent], Awaitable[None]]


def verify_meta_signature(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _meta_items(payload: dict[str, Any]):
    """Yield (provider, external_account_id, message_dict) from a Meta webhook body."""
    obj = payload.get("object")
    for entry in payload.get("entry", []) or []:
        if obj == "whatsapp_business_account":
            for ch in entry.get("changes", []) or []:
                v = ch.get("value", {}) or {}
                pid = (v.get("metadata") or {}).get("phone_number_id")
                for m in v.get("messages", []) or []:
                    yield "whatsapp", pid, {
                        "id": m.get("id"), "from": m.get("from"), "type": m.get("type", "text"),
                        "text": (m.get("text") or {}).get("body", ""), "ts": m.get("timestamp")}
        elif obj in ("page", "instagram"):
            provider = "facebook" if obj == "page" else "instagram"
            for m in entry.get("messaging", []) or []:
                msg = m.get("message") or {}
                if msg.get("is_echo"):
                    continue  # our own outbound message reflected back
                yield provider, entry.get("id"), {
                    "id": msg.get("mid"), "from": (m.get("sender") or {}).get("id"), "type": "text",
                    "text": msg.get("text", ""), "ts": m.get("timestamp")}


async def route_meta_payload(payload: dict[str, Any], store: OnboardingStore, handler: InboundHandler) -> dict[str, int]:
    routed = dropped = 0
    for provider, ext_id, m in _meta_items(payload):
        conn = store.find_live_connector(provider, ext_id) if ext_id else None
        if not conn or conn["status"] != "connected" or not m.get("id") or not m.get("from"):
            dropped += 1
            logger.warning("inbound_dropped provider=%s account=%s", provider, ext_id)
            continue
        await handler(InboundEvent(
            business_id=conn["business_id"], channel=provider, external_message_id=str(m["id"]),
            customer_identity=str(m["from"]), content=m["text"], message_type=m["type"],
            received_at=str(m["ts"]) if m.get("ts") else None))
        routed += 1
    return {"routed": routed, "dropped": dropped}


def resolve_web_channel(store: OnboardingStore, site_key: str, origin: str | None) -> dict[str, Any] | None:
    """Return the web connector if site_key is live and the browser Origin is allow-listed.

    NOTE: Origin is browser-enforced only. A non-browser client can forge it, so the site key must be
    treated as a public identifier; rate-limit and abuse controls belong in front of this endpoint.
    """
    conn = store.find_live_connector("web", site_key)
    if not conn or conn["status"] != "connected" or not origin:
        return None
    allowed = (conn.get("configuration") or {}).get("allowed_origins", [])
    return conn if origin.rstrip("/").lower() in allowed else None
