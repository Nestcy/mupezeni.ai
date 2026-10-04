"""Business onboarding: two paths, one connector model.

existing_retail   -> connect an external catalog (shopify/woocommerce) + channels
mupezeni_managed  -> Mupezeni builds the catalog (web app); attach it as the native connector + channels

Rules enforced here (not in routes) so workers/CLI/tests get the same guarantees:
  * a path may only use catalog providers valid for it
  * channel accounts are verified with the provider, never trusted from the browser
  * secrets are encrypted at rest and only leave via get_credential()
  * a business becomes `active` (AI workers allowed) only when catalog + >=1 channel are connected
"""
from __future__ import annotations

import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.onboarding.crypto import CredentialCipher, StateError, sign_state, verify_state
from app.onboarding.meta import MetaClient, ProviderAuthError
from app.onboarding.store import OnboardingStore, StoreConflict
from app.onboarding.verifiers import CatalogVerificationError, CatalogVerifier

PATHS = {"existing_retail", "mupezeni_managed"}
CATALOG_PROVIDERS_BY_PATH = {
    "existing_retail": {"shopify", "woocommerce"},
    "mupezeni_managed": {"mupezeni"},
}
OAUTH_CHANNELS = {"whatsapp", "facebook", "instagram"}
CHANNELS = OAUTH_CHANNELS | {"web"}


class OnboardingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message, self.status_code = message, status_code


class OnboardingService:
    def __init__(self, store: OnboardingStore, cipher: CredentialCipher, meta: MetaClient,
                 verifier: CatalogVerifier, state_secret: str):
        self.store, self.cipher, self.meta, self.verifier, self.state_secret = store, cipher, meta, verifier, state_secret

    # ── business ──────────────────────────────────────────────────────────────
    def start_business(self, user_id: str, *, name: str, path: str, country: str | None, currency: str,
                       phone: str | None = None, email: str | None = None) -> dict[str, Any]:
        if path not in PATHS:
            raise OnboardingError(f"path must be one of {sorted(PATHS)}", 422)
        bid = self.store.create_business(user_id, name.strip(), path, country, currency, phone, email)
        return self.checklist(bid)

    def _business(self, business_id: str) -> dict[str, Any]:
        b = self.store.get_business(business_id)
        if not b:
            raise OnboardingError("Business not found", 404)
        return b

    # ── catalog ───────────────────────────────────────────────────────────────
    async def connect_catalog(self, business_id: str, user_id: str, provider: str,
                              config: dict[str, Any], credentials: dict[str, str]) -> dict[str, Any]:
        b = self._business(business_id)
        if provider not in CATALOG_PROVIDERS_BY_PATH.get(b["onboarding_path"], set()):
            raise OnboardingError(f"'{provider}' is not available for a {b['onboarding_path']} business", 422)

        if provider == "mupezeni":
            # Catalog is built in the Mupezeni web app; attach it once it has products.
            ready = self.store.catalog_product_count(business_id) > 0
            self.store.upsert_connector(business_id, provider, status="connected" if ready else "connecting", user_id=user_id)
            if not ready:
                raise OnboardingError("Your Mupezeni catalog has no products yet. Add products, then connect again.", 409)
        else:
            try:
                await self.verifier.verify(provider, config, credentials)
            except (CatalogVerificationError, KeyError) as exc:
                self.store.upsert_connector(business_id, provider, status="failed", user_id=user_id, last_error=str(exc))
                raise OnboardingError(f"Could not verify {provider} credentials: {exc}", 422) from exc
            row = self.store.upsert_connector(business_id, provider, status="connected", user_id=user_id, configuration=config)
            for ctype, value in credentials.items():
                self._store_secret(row["id"], ctype, value)
        return self._advance(business_id)

    # ── channels: OAuth (WhatsApp / Facebook / Instagram) ────────────────────
    def authorize_url(self, business_id: str, user_id: str, provider: str) -> dict[str, str]:
        self._business(business_id)
        if provider not in OAUTH_CHANNELS:
            raise OnboardingError(f"'{provider}' does not use OAuth", 422)
        token, nonce, exp = sign_state(self.state_secret, business_id=business_id, user_id=user_id, provider=provider)
        self.store.save_oauth_state(nonce, business_id, user_id, provider, exp)
        return {"authorize_url": self.meta.authorize_url(provider, token), "state": token}

    async def complete_oauth(self, business_id: str, user_id: str, provider: str, *, code: str, state: str,
                             external_account_id: str) -> dict[str, Any]:
        try:
            s = verify_state(self.state_secret, state)
        except StateError as exc:
            raise OnboardingError(f"Invalid OAuth state: {exc}", 400) from exc
        # State must be bound to exactly this user + business + provider, and be unused.
        if (s["business_id"], s["user_id"], s["provider"]) != (business_id, user_id, provider):
            raise OnboardingError("OAuth state does not match this request", 400)
        if not self.store.consume_oauth_state(s["nonce"]):
            raise OnboardingError("OAuth state already used", 400)

        try:
            tok = await self.meta.exchange_code(code)
            acct = await self.meta.verify_account(provider, tok["access_token"], external_account_id)
        except ProviderAuthError as exc:
            raise OnboardingError(str(exc), 400) from exc

        try:
            row = self.store.upsert_connector(business_id, provider, status="connected", user_id=user_id,
                                              external_account_id=acct["external_account_id"],
                                              configuration={"display_name": acct.get("name")})
        except StoreConflict as exc:
            raise OnboardingError(str(exc), 409) from exc
        expires = None
        if tok.get("expires_in"):
            expires = (datetime.now(timezone.utc) + timedelta(seconds=int(tok["expires_in"]))).isoformat()
        self._store_secret(row["id"], "access_token", acct["token"], expires)
        return self._advance(business_id)

    # ── channels: website chat widget ────────────────────────────────────────
    def connect_web(self, business_id: str, user_id: str, allowed_origins: list[str]) -> dict[str, Any]:
        self._business(business_id)
        origins = [o.rstrip("/").lower() for o in allowed_origins]
        if not origins or any(not o.startswith(("https://", "http://localhost")) for o in origins):
            raise OnboardingError("allowed_origins must be https origins (http only for localhost)", 422)
        existing = self.store.get_connector(business_id, "web")
        site_key = (existing or {}).get("external_account_id") or "wk_" + _secrets.token_urlsafe(18)
        self.store.upsert_connector(business_id, "web", status="connected", user_id=user_id,
                                    external_account_id=site_key, configuration={"allowed_origins": origins})
        out = self._advance(business_id)
        out["site_key"] = site_key  # public identifier, safe to embed in the page
        return out

    def disconnect(self, business_id: str, provider: str) -> dict[str, Any]:
        if not self.store.revoke_connector(business_id, provider):
            raise OnboardingError("Connector not found", 404)
        return self._advance(business_id)

    # ── readiness ─────────────────────────────────────────────────────────────
    def checklist(self, business_id: str) -> dict[str, Any]:
        b = self._business(business_id)
        live = {c["provider"]: c for c in self.store.list_connectors(business_id) if c["status"] == "connected"}
        catalog = [p for p in live if p in CATALOG_PROVIDERS_BY_PATH.get(b["onboarding_path"], set())]
        channels = [p for p in live if p in CHANNELS]
        return {
            "business_id": business_id, "path": b["onboarding_path"], "status": b["onboarding_status"],
            "catalog_connected": bool(catalog), "catalog_provider": catalog[0] if catalog else None,
            "channels_connected": sorted(channels),
            "can_activate": bool(catalog and channels),
            "next_step": ("connect_catalog" if not catalog else "connect_channel" if not channels else "activate"
                          if b["onboarding_status"] != "active" else "done"),
        }

    def _advance(self, business_id: str) -> dict[str, Any]:
        """Recompute status after any connector change. Losing a requirement also demotes an active business."""
        c = self.checklist(business_id)
        cur = c["status"]
        if cur == "active" and not c["can_activate"]:
            new = "channels_pending" if c["catalog_connected"] else "catalog_pending"
        elif cur == "active":
            new = "active"
        else:
            new = "ready" if c["can_activate"] else "channels_pending" if c["catalog_connected"] else "catalog_pending"
        if new != cur:
            self.store.set_status(business_id, new)
        return self.checklist(business_id)

    def activate(self, business_id: str) -> dict[str, Any]:
        c = self.checklist(business_id)
        if not c["can_activate"]:
            raise OnboardingError("Connect a catalog and at least one channel before activating", 409)
        self.store.set_status(business_id, "active")
        return self.checklist(business_id)

    # ── secrets ───────────────────────────────────────────────────────────────
    def _store_secret(self, connector_id: str, ctype: str, value: str, expires_at: str | None = None) -> None:
        self.store.save_credential(connector_id, ctype, self.cipher.encrypt(value), 1, expires_at)

    def get_credential(self, business_id: str, provider: str, credential_type: str = "access_token",
                       *, require_active: bool = True) -> str:
        """For AI workers / outbound senders ONLY. Never expose through an HTTP route."""
        if require_active and self._business(business_id)["onboarding_status"] != "active":
            raise OnboardingError("Business is not active", 403)
        conn = self.store.get_connector(business_id, provider)
        if not conn or conn["status"] != "connected":
            raise OnboardingError(f"{provider} is not connected", 404)
        now = datetime.now(timezone.utc).isoformat()
        for cred in self.store.get_credentials(conn["id"]):
            if cred["credential_type"] == credential_type:
                if cred.get("expires_at") and cred["expires_at"] < now:
                    raise OnboardingError(f"{provider} credential expired; reconnect required", 409)
                return self.cipher.decrypt(cred["secret_ciphertext"])
        raise OnboardingError(f"No {credential_type} stored for {provider}", 404)
