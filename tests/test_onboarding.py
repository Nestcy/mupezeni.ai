"""Onboarding / connector auth tests."""
import hashlib
import hmac
import json

import pytest

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.onboarding.crypto import CredentialCipher, CryptoConfigError, StateError, sign_state, verify_state
from app.onboarding.inbound import verify_meta_signature
from app.onboarding.meta import ProviderAuthError
from app.onboarding.routes import build_router
from app.onboarding.service import OnboardingError, OnboardingService
from app.onboarding.store import InMemoryStore
from app.onboarding.verifiers import CatalogVerificationError

SECRET, APP_SECRET = "state-secret", "meta-app-secret"


class FakeMeta:
    """Owns accounts per user token, like Meta does."""
    def __init__(self):
        self.owned = {"tok-alice": {"PN1"}, "tok-bob": {"PN1", "PN2"}}  # bob also "claims" PN1 -> conflict test

    def authorize_url(self, provider, state):
        return f"https://fb.example/dialog?state={state}"

    async def exchange_code(self, code):
        if code not in self.owned and not code.startswith("tok-"):
            raise ProviderAuthError("bad code")
        return {"access_token": code, "expires_in": 5000}

    async def verify_account(self, provider, token, ext_id):
        if ext_id not in self.owned.get(token, set()):
            raise ProviderAuthError("Authenticated user does not manage that account")
        return {"external_account_id": ext_id, "token": "long-" + token, "name": "Shop"}


class FakeVerifier:
    async def verify(self, provider, config, secrets):
        if secrets.get("access_token") != "good":
            raise CatalogVerificationError("rejected (401)")
        return {"verified": True}


@pytest.fixture
def env():
    store = InMemoryStore()
    svc = OnboardingService(store, CredentialCipher(Fernet.generate_key().decode()), FakeMeta(), FakeVerifier(), SECRET)
    return store, svc


def new_biz(svc, path="mupezeni_managed", user="alice"):
    return svc.start_business(user, name="Zed Shop", path=path, country="ZM", currency="ZMW")["business_id"]


async def go_active(store, svc, bid, user="alice"):
    store.product_counts[bid] = 3
    await svc.connect_catalog(bid, user, "mupezeni", {}, {})
    svc.connect_web(bid, user, ["https://shop.example"])
    return svc.activate(bid)


# ── crypto / state ───────────────────────────────────────────────────────────
def test_cipher_roundtrip_and_rotation():
    k1, k2 = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    old = CredentialCipher(k1).encrypt("secret")
    assert old != "secret"
    assert CredentialCipher(f"{k2},{k1}").decrypt(old) == "secret"       # rotated key set still reads old data
    with pytest.raises(CryptoConfigError):
        CredentialCipher(k2).decrypt(old)
    with pytest.raises(CryptoConfigError):
        CredentialCipher("")


def test_state_tamper_and_expiry():
    tok, _, _ = sign_state(SECRET, business_id="b", user_id="u", provider="whatsapp")
    assert verify_state(SECRET, tok)["business_id"] == "b"
    with pytest.raises(StateError):
        verify_state("other", tok)
    with pytest.raises(StateError):
        verify_state(SECRET, tok[:-2] + "xx")
    old, _, _ = sign_state(SECRET, business_id="b", user_id="u", provider="x", ttl=-1)
    with pytest.raises(StateError):
        verify_state(SECRET, old)


# ── paths ────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_path_restricts_catalog_providers(env):
    _, svc = env
    managed, retail = new_biz(svc), new_biz(svc, "existing_retail")
    with pytest.raises(OnboardingError) as e:
        await svc.connect_catalog(managed, "alice", "shopify", {"shop_domain": "a.myshopify.com"}, {"access_token": "good"})
    assert e.value.status_code == 422
    with pytest.raises(OnboardingError):
        await svc.connect_catalog(retail, "alice", "mupezeni", {}, {})


@pytest.mark.asyncio
async def test_managed_needs_products_before_connecting(env):
    store, svc = env
    bid = new_biz(svc)
    with pytest.raises(OnboardingError) as e:
        await svc.connect_catalog(bid, "alice", "mupezeni", {}, {})
    assert e.value.status_code == 409 and not svc.checklist(bid)["catalog_connected"]
    store.product_counts[bid] = 1
    assert (await svc.connect_catalog(bid, "alice", "mupezeni", {}, {}))["catalog_connected"]


@pytest.mark.asyncio
async def test_retail_catalog_verified_and_secret_encrypted(env):
    store, svc = env
    bid = new_biz(svc, "existing_retail")
    with pytest.raises(OnboardingError):
        await svc.connect_catalog(bid, "alice", "shopify", {"shop_domain": "a.myshopify.com"}, {"access_token": "bad"})
    assert not svc.checklist(bid)["catalog_connected"]
    out = await svc.connect_catalog(bid, "alice", "shopify", {"shop_domain": "a.myshopify.com"}, {"access_token": "good"})
    assert out["catalog_provider"] == "shopify"
    assert all("good" not in c["secret_ciphertext"] for c in store.credentials)


# ── channel OAuth ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_oauth_happy_path_then_state_is_single_use(env):
    store, svc = env
    bid = new_biz(svc)
    state = svc.authorize_url(bid, "alice", "whatsapp")["state"]
    out = await svc.complete_oauth(bid, "alice", "whatsapp", code="tok-alice", state=state, external_account_id="PN1")
    assert "whatsapp" in out["channels_connected"]
    assert "long-tok-alice" not in json.dumps(store.credentials)           # encrypted at rest
    with pytest.raises(OnboardingError, match="already used"):
        await svc.complete_oauth(bid, "alice", "whatsapp", code="tok-alice", state=state, external_account_id="PN1")


@pytest.mark.asyncio
async def test_oauth_state_bound_to_user_business_provider(env):
    _, svc = env
    a, b = new_biz(svc), new_biz(svc, user="mallory")
    state = svc.authorize_url(a, "alice", "whatsapp")["state"]
    for args in [(a, "mallory", "whatsapp"), (b, "alice", "whatsapp"), (a, "alice", "facebook")]:
        with pytest.raises(OnboardingError, match="does not match"):
            await svc.complete_oauth(*args, code="tok-alice", state=state, external_account_id="PN1")


@pytest.mark.asyncio
async def test_cannot_claim_account_you_dont_control(env):
    _, svc = env
    bid = new_biz(svc)
    state = svc.authorize_url(bid, "alice", "whatsapp")["state"]
    with pytest.raises(OnboardingError):
        await svc.complete_oauth(bid, "alice", "whatsapp", code="tok-alice", state=state, external_account_id="PN2")


@pytest.mark.asyncio
async def test_same_account_cannot_attach_to_two_businesses(env):
    _, svc = env
    a, b = new_biz(svc), new_biz(svc, user="bob")
    s1 = svc.authorize_url(a, "alice", "whatsapp")["state"]
    await svc.complete_oauth(a, "alice", "whatsapp", code="tok-alice", state=s1, external_account_id="PN1")
    s2 = svc.authorize_url(b, "bob", "whatsapp")["state"]
    with pytest.raises(OnboardingError) as e:
        await svc.complete_oauth(b, "bob", "whatsapp", code="tok-bob", state=s2, external_account_id="PN1")
    assert e.value.status_code == 409


# ── activation + worker credential access ────────────────────────────────────
@pytest.mark.asyncio
async def test_activation_gate_and_worker_credentials(env):
    store, svc = env
    bid = new_biz(svc)
    with pytest.raises(OnboardingError):
        svc.activate(bid)                                                   # nothing connected
    state = svc.authorize_url(bid, "alice", "whatsapp")["state"]
    await svc.complete_oauth(bid, "alice", "whatsapp", code="tok-alice", state=state, external_account_id="PN1")
    with pytest.raises(OnboardingError):
        svc.activate(bid)                                                   # channel but no catalog
    with pytest.raises(OnboardingError, match="not active"):
        svc.get_credential(bid, "whatsapp")                                 # workers locked out until active
    store.product_counts[bid] = 2
    await svc.connect_catalog(bid, "alice", "mupezeni", {}, {})
    assert svc.activate(bid)["status"] == "active"
    assert svc.get_credential(bid, "whatsapp") == "long-tok-alice"


@pytest.mark.asyncio
async def test_disconnect_demotes_active_and_revokes_secret(env):
    store, svc = env
    bid = new_biz(svc)
    await go_active(store, svc, bid)
    assert svc.disconnect(bid, "web")["status"] == "channels_pending"
    with pytest.raises(OnboardingError):
        svc.get_credential(bid, "web", require_active=False)


def test_web_origins_validated(env):
    _, svc = env
    bid = new_biz(svc)
    with pytest.raises(OnboardingError):
        svc.connect_web(bid, "alice", ["http://evil.example"])
    assert svc.connect_web(bid, "alice", ["https://shop.example/"])["site_key"].startswith("wk_")


# ── HTTP: webhooks + auth wiring ─────────────────────────────────────────────
def make_client(env):
    store, svc = env
    events = []

    async def handler(ev):
        events.append(ev)

    async def current_user():
        return {"id": "alice"}

    async def admin():
        return {"user": {"id": "alice"}, "role": "owner"}

    app_ = FastAPI()
    app_.include_router(build_router(service=svc, current_user=current_user, business_access=admin, admin_access=admin,
                                     inbound_handler=handler, meta_app_secret=APP_SECRET, meta_verify_token="vt"))
    return TestClient(app_), events


def wa_payload(phone_id, biz_claim=None):
    body = {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"value": {
        "metadata": {"phone_number_id": phone_id},
        "messages": [{"id": "m1", "from": "260971", "type": "text", "text": {"body": "hi"}, "timestamp": "1"}]}}]}]}
    if biz_claim:
        body["business_id"] = biz_claim
    return json.dumps(body).encode()


def sig(raw, secret=APP_SECRET):
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_meta_webhook_auth_and_tenant_routing(env):
    store, svc = env
    bid = new_biz(svc)
    state = svc.authorize_url(bid, "alice", "whatsapp")["state"]
    await svc.complete_oauth(bid, "alice", "whatsapp", code="tok-alice", state=state, external_account_id="PN1")
    client, events = make_client(env)

    raw = wa_payload("PN1", biz_claim="someone-elses-business")
    assert client.post("/api/v1/webhooks/meta", content=raw).status_code == 401                         # unsigned
    assert client.post("/api/v1/webhooks/meta", content=raw, headers={"X-Hub-Signature-256": sig(raw, "x")}).status_code == 401
    r = client.post("/api/v1/webhooks/meta", content=raw, headers={"X-Hub-Signature-256": sig(raw)})
    assert r.json() == {"routed": 1, "dropped": 0}
    assert events[0].business_id == bid                                                                 # from our DB, not payload

    raw2 = wa_payload("UNKNOWN")
    r = client.post("/api/v1/webhooks/meta", content=raw2, headers={"X-Hub-Signature-256": sig(raw2)})
    assert r.json() == {"routed": 0, "dropped": 1} and len(events) == 1


def test_meta_verify_challenge(env):
    client, _ = make_client(env)
    ok = client.get("/api/v1/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"})
    assert ok.text == "42"
    assert client.get("/api/v1/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"}).status_code == 403


def test_web_channel_origin_allowlist_and_start_flow(env):
    client, events = make_client(env)
    r = client.post("/api/v1/onboarding/businesses", json={"name": "Zed Shop", "path": "mupezeni_managed", "country": "ZM"})
    assert r.status_code == 201 and r.json()["next_step"] == "connect_catalog"
    bid = r.json()["business_id"]
    key = client.post(f"/api/v1/businesses/{bid}/connectors/web", json={"allowed_origins": ["https://shop.example"]}).json()["site_key"]
    msg = {"session_id": "sess-12345678", "message_id": "w1", "content": "hello"}
    assert client.post(f"/api/v1/channels/web/{key}/messages", json=msg, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post(f"/api/v1/channels/web/{key}/messages", json=msg).status_code == 403
    assert client.post(f"/api/v1/channels/web/{key}/messages", json=msg, headers={"Origin": "https://shop.example"}).status_code == 202
    assert events[0].business_id == bid
    assert client.post("/api/v1/onboarding/businesses", json={"name": "x", "path": "bogus"}).status_code == 422


def test_signature_helper_fails_closed():
    assert not verify_meta_signature("", b"x", "sha256=00")
    assert not verify_meta_signature("s", b"x", None)
    assert not verify_meta_signature("s", b"x", "md5=00")
