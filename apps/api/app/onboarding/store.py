"""Persistence for onboarding. InMemoryStore backs tests; SupabaseStore uses the service-role client."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

CAPABILITY = {
    "mupezeni": "catalog", "shopify": "catalog", "woocommerce": "catalog",
    "web": "messaging", "whatsapp": "messaging", "facebook": "messaging", "instagram": "messaging",
}


class StoreConflict(Exception):
    """External account is already connected to another business."""


class OnboardingStore(Protocol):
    def create_business(self, user_id: str, name: str, path: str, country: str | None, currency: str,
                        phone: str | None, email: str | None) -> str: ...
    def get_business(self, business_id: str) -> dict[str, Any] | None: ...
    def set_status(self, business_id: str, status: str) -> None: ...
    def upsert_connector(self, business_id: str, provider: str, *, status: str, user_id: str,
                         external_account_id: str | None = None, scopes: list[str] | None = None,
                         configuration: dict[str, Any] | None = None, last_error: str | None = None) -> dict[str, Any]: ...
    def get_connector(self, business_id: str, provider: str) -> dict[str, Any] | None: ...
    def list_connectors(self, business_id: str) -> list[dict[str, Any]]: ...
    def find_live_connector(self, provider: str, external_account_id: str) -> dict[str, Any] | None: ...
    def save_credential(self, connector_id: str, credential_type: str, ciphertext: str, key_version: int,
                        expires_at: str | None) -> None: ...
    def get_credentials(self, connector_id: str) -> list[dict[str, Any]]: ...
    def revoke_connector(self, business_id: str, provider: str) -> bool: ...
    def catalog_product_count(self, business_id: str) -> int: ...
    def save_oauth_state(self, nonce: str, business_id: str, user_id: str, provider: str, expires_at: int) -> None: ...
    def consume_oauth_state(self, nonce: str) -> dict[str, Any] | None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryStore:
    def __init__(self) -> None:
        self.businesses: dict[str, dict[str, Any]] = {}
        self.members: list[dict[str, Any]] = []
        self.connectors: dict[str, dict[str, Any]] = {}
        self.credentials: list[dict[str, Any]] = []
        self.states: dict[str, dict[str, Any]] = {}
        self.product_counts: dict[str, int] = {}

    def create_business(self, user_id, name, path, country, currency, phone, email):
        bid = str(uuid.uuid4())
        self.businesses[bid] = {"id": bid, "name": name, "onboarding_path": path, "onboarding_status": "catalog_pending",
                                "country": country, "currency": currency, "created_by": user_id}
        self.members.append({"business_id": bid, "user_id": user_id, "role": "owner"})
        return bid

    def get_business(self, business_id):
        return self.businesses.get(business_id)

    def set_status(self, business_id, status):
        self.businesses[business_id]["onboarding_status"] = status

    def get_connector(self, business_id, provider):
        return next((c for c in self.connectors.values()
                     if c["business_id"] == business_id and c["provider"] == provider), None)

    def list_connectors(self, business_id):
        return [c for c in self.connectors.values() if c["business_id"] == business_id]

    def find_live_connector(self, provider, external_account_id):
        return next((c for c in self.connectors.values()
                     if c["provider"] == provider and c["external_account_id"] == external_account_id
                     and c["status"] in ("connecting", "connected")), None)

    def upsert_connector(self, business_id, provider, *, status, user_id, external_account_id=None,
                         scopes=None, configuration=None, last_error=None):
        if external_account_id:  # mirrors uq_business_connectors_external_account
            other = self.find_live_connector(provider, external_account_id)
            if other and other["business_id"] != business_id and status in ("connecting", "connected"):
                raise StoreConflict(f"{provider} account already connected to another business")
        row = self.get_connector(business_id, provider)
        if row is None:
            row = {"id": str(uuid.uuid4()), "business_id": business_id, "provider": provider,
                   "capability": CAPABILITY[provider], "configuration": {}, "scopes": []}
            self.connectors[row["id"]] = row
        row.update(status=status, connected_by=user_id, last_error=last_error)
        if external_account_id is not None:
            row["external_account_id"] = external_account_id
        row.setdefault("external_account_id", None)
        if scopes is not None:
            row["scopes"] = scopes
        if configuration is not None:
            row["configuration"] = configuration
        if status == "connected":
            row["connected_at"] = _now()
        return row

    def save_credential(self, connector_id, credential_type, ciphertext, key_version, expires_at):
        for c in self.credentials:
            if c["business_connector_id"] == connector_id and c["credential_type"] == credential_type:
                c["status"] = "revoked"
        self.credentials.append({"business_connector_id": connector_id, "credential_type": credential_type,
                                 "secret_ciphertext": ciphertext, "key_version": key_version,
                                 "expires_at": expires_at, "status": "active"})

    def get_credentials(self, connector_id):
        return [c for c in self.credentials if c["business_connector_id"] == connector_id and c["status"] == "active"]

    def revoke_connector(self, business_id, provider):
        row = self.get_connector(business_id, provider)
        if not row:
            return False
        row["status"] = "inactive"
        for c in self.credentials:
            if c["business_connector_id"] == row["id"]:
                c["status"] = "revoked"
        return True

    def catalog_product_count(self, business_id):
        return self.product_counts.get(business_id, 0)

    def save_oauth_state(self, nonce, business_id, user_id, provider, expires_at):
        self.states[nonce] = {"business_id": business_id, "user_id": user_id, "provider": provider, "used": False}

    def consume_oauth_state(self, nonce):
        st = self.states.get(nonce)
        if not st or st["used"]:
            return None
        st["used"] = True
        return st


class SupabaseStore:
    """Service-role client: bypasses RLS, so every query is explicitly scoped by business_id."""

    def __init__(self, client: Any) -> None:
        self.db = client

    def _def_id(self, provider: str) -> str:
        r = self.db.table("connector_definitions").select("id").eq("provider", provider) \
            .eq("capability", CAPABILITY[provider]).limit(1).execute()
        if not r.data:
            raise LookupError(f"Unknown connector provider: {provider}")
        return r.data[0]["id"]

    def _shape(self, row: dict[str, Any], provider: str) -> dict[str, Any]:
        return {**row, "provider": provider, "capability": CAPABILITY[provider]}

    def create_business(self, user_id, name, path, country, currency, phone, email):
        r = self.db.rpc("create_business_with_owner", {
            "p_user_id": user_id, "p_name": name, "p_path": path, "p_country": country,
            "p_currency": currency, "p_phone": phone, "p_email": email}).execute()
        return r.data

    def get_business(self, business_id):
        r = self.db.table("businesses").select("*").eq("id", business_id).limit(1).execute()
        return r.data[0] if r.data else None

    def set_status(self, business_id, status):
        self.db.table("businesses").update({"onboarding_status": status}).eq("id", business_id).execute()

    def get_connector(self, business_id, provider):
        r = self.db.table("business_connectors").select("*") \
            .eq("business_id", business_id).eq("connector_definition_id", self._def_id(provider)).limit(1).execute()
        return self._shape(r.data[0], provider) if r.data else None

    def list_connectors(self, business_id):
        r = self.db.table("business_connectors").select("*, connector_definitions(provider, capability)") \
            .eq("business_id", business_id).execute()
        out = []
        for row in r.data or []:
            d = row.pop("connector_definitions", None) or {}
            out.append({**row, "provider": d.get("provider"), "capability": d.get("capability")})
        return out

    def find_live_connector(self, provider, external_account_id):
        r = self.db.table("business_connectors").select("*") \
            .eq("connector_definition_id", self._def_id(provider)).eq("external_account_id", external_account_id) \
            .in_("status", ["connecting", "connected"]).limit(1).execute()
        return self._shape(r.data[0], provider) if r.data else None

    def upsert_connector(self, business_id, provider, *, status, user_id, external_account_id=None,
                         scopes=None, configuration=None, last_error=None):
        row: dict[str, Any] = {"business_id": business_id, "connector_definition_id": self._def_id(provider),
                               "status": status, "connected_by": user_id, "last_error": last_error}
        if external_account_id is not None:
            row["external_account_id"] = external_account_id
        if scopes is not None:
            row["scopes"] = scopes
        if configuration is not None:
            row["configuration"] = configuration
        if status == "connected":
            row["connected_at"] = _now()
        try:
            r = self.db.table("business_connectors").upsert(row, on_conflict="business_id,connector_definition_id").execute()
        except Exception as exc:  # unique-violation on uq_business_connectors_external_account
            if "uq_business_connectors_external_account" in str(exc) or "23505" in str(exc):
                raise StoreConflict(f"{provider} account already connected to another business") from exc
            raise
        return self._shape(r.data[0], provider)

    def save_credential(self, connector_id, credential_type, ciphertext, key_version, expires_at):
        self.db.table("connector_credentials").update({"status": "revoked"}) \
            .eq("business_connector_id", connector_id).eq("credential_type", credential_type).execute()
        self.db.table("connector_credentials").insert({
            "business_connector_id": connector_id, "credential_type": credential_type,
            "secret_ciphertext": ciphertext, "key_version": key_version, "expires_at": expires_at,
            "status": "active"}).execute()

    def get_credentials(self, connector_id):
        r = self.db.table("connector_credentials").select("*") \
            .eq("business_connector_id", connector_id).eq("status", "active").execute()
        return r.data or []

    def revoke_connector(self, business_id, provider):
        row = self.get_connector(business_id, provider)
        if not row:
            return False
        self.db.table("connector_credentials").update({"status": "revoked"}).eq("business_connector_id", row["id"]).execute()
        self.db.table("business_connectors").update({"status": "inactive"}).eq("id", row["id"]).execute()
        return True

    def catalog_product_count(self, business_id):
        stores = self.db.table("stores").select("id").eq("business_id", business_id).execute().data or []
        if not stores:
            return 0
        r = self.db.table("products").select("id", count="exact").in_("store_id", [s["id"] for s in stores]).limit(1).execute()
        return r.count or 0

    def save_oauth_state(self, nonce, business_id, user_id, provider, expires_at):
        self.db.table("connector_oauth_states").insert({
            "nonce": nonce, "business_id": business_id, "user_id": user_id, "provider": provider,
            "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat()}).execute()

    def consume_oauth_state(self, nonce):
        # Conditional update is the atomic single-use gate: only one caller can flip used_at from NULL.
        r = self.db.table("connector_oauth_states").update({"used_at": _now()}) \
            .eq("nonce", nonce).is_("used_at", "null").execute()
        return r.data[0] if r.data else None
