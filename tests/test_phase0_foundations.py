"""Phase 0 Foundations tests.

Covers:
  - Root main.py entry point import & /health probe endpoint
  - LLMGateway: reasoning_effort, fallback model on 429/503, budget_guard hook
  - ImageClient: protocol selection (openai vs gemini), Gemini payload parsing
"""
from __future__ import annotations

import json
import pytest
import httpx
from fastapi.testclient import TestClient

from app.ai.errors import AIProviderError
from app.ai.image import ImageClient, ImageResult, _GeminiImageClient, _OpenAIImageClient
from app.ai.llm import LLMGateway
from main import app


# ── 1. Root main.py & /health endpoint ────────────────────────────────────────

def test_root_main_app_import():
    assert app is not None
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_check_endpoint():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "db" in data
    assert "supabase_configured" in data
    assert "llm_configured" in data
    assert "image_configured" in data
    assert "dev_auth" in data


# ── 2. LLMGateway: reasoning_effort, fallback, budget_guard ──────────────────

@pytest.mark.asyncio
async def test_llm_gateway_reasoning_effort():
    captured_request: dict = {}

    def handler(request: httpx.Request):
        nonlocal captured_request
        captured_request = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello", "tool_calls": []}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "model": "qwen/qwen3.8-27b",
            },
        )

    transport = httpx.MockTransport(handler)
    gw = LLMGateway(
        api_key="test-key",
        model="qwen/qwen3.8-27b",
        base_url="https://api.groq.com/openai/v1",
        default_reasoning_effort="none",
        transport=transport,
    )

    # Call with reasoning_effort="low"
    res = await gw.chat([{"role": "user", "content": "hi"}], reasoning_effort="low")
    assert res.content == "Hello"
    assert captured_request.get("reasoning_effort") == "low"
    assert res.fallback_used is False


@pytest.mark.asyncio
async def test_llm_gateway_fallback_model():
    requests_received = []

    def handler(request: httpx.Request):
        body = json.loads(request.content.decode())
        requests_received.append(body["model"])
        if body["model"] == "qwen/qwen3.8-27b":
            # Primary model fails with 429 Too Many Requests
            return httpx.Response(429, text="Rate limit exceeded")
        # Fallback model succeeds
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Fallback response", "tool_calls": []}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4},
                "model": "llama-3.3-70b-versatile",
            },
        )

    transport = httpx.MockTransport(handler)
    gw = LLMGateway(
        api_key="test-key",
        model="qwen/qwen3.8-27b",
        fallback_model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        transport=transport,
    )

    res = await gw.chat([{"role": "user", "content": "hi"}])
    assert res.content == "Fallback response"
    assert res.fallback_used is True
    assert requests_received == ["qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]


@pytest.mark.asyncio
async def test_llm_gateway_budget_guard():
    def reject_budget():
        raise RuntimeError("Daily LLM budget of $5.00 exceeded")

    gw = LLMGateway(
        api_key="test-key",
        model="test-model",
        base_url="https://api.openai.com/v1",
    )

    with pytest.raises(RuntimeError, match="Daily LLM budget"):
        await gw.chat([{"role": "user", "content": "hi"}], budget_guard=reject_budget)


# ── 3. ImageClient: protocol adapter & Gemini parser ─────────────────────────

def test_image_client_protocol_selection():
    client_openai = ImageClient(
        api_key="key",
        model="dall-e-3",
        protocol="openai",
    )
    assert isinstance(client_openai, _OpenAIImageClient)

    client_gemini = ImageClient(
        api_key="key",
        model="gemini-3.1-flash-lite-image",
        protocol="gemini",
    )
    assert isinstance(client_gemini, _GeminiImageClient)


@pytest.mark.asyncio
async def test_gemini_image_generation():
    def handler(request: httpx.Request):
        assert "key=gemini-key" in str(request.url)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "inlineData": {
                                        "mimeType": "image/png",
                                        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = ImageClient(
        api_key="gemini-key",
        model="gemini-3.1-flash-lite-image",
        protocol="gemini",
        transport=transport,
    )

    results = await client.generate("a fresh cup of Zambian coffee")
    assert len(results) == 1
    assert results[0].b64_json is not None
    assert results[0].mime_type == "image/png"


# ── 4. Connected Shopify store capability execution (Phase 0 Gate) ───────────

@pytest.mark.asyncio
async def test_shopify_capability_execution_end_to_end():
    from unittest.mock import AsyncMock, MagicMock
    from app.capabilities.models import (
        ActorContext,
        ActorType,
        CapabilityExecutionRequest,
        CapabilityResultStatus,
    )
    from app.capabilities.runtime import CapabilityRuntime
    from app.connectors.registry import ConnectorRegistry

    business_id = "biz_shopify_test"

    # Mock DB queries that CapabilityRuntime performs for authorization & permissions
    mock_db = MagicMock()

    # Step 3: Resolve business connector
    conn_query = MagicMock()
    conn_query.select.return_value = conn_query
    conn_query.eq.return_value = conn_query
    conn_query.execute.return_value = MagicMock(
        data=[
            {
                "id": "conn_shopify_1",
                "connector_definition_id": "def_shopify_cat",
                "status": "connected",
                "connector_definitions": {
                    "capability": "catalog",
                    "provider": "shopify",
                },
            }
        ]
    )

    # Step 5: Check capability support
    cap_query = MagicMock()
    cap_query.select.return_value = cap_query
    cap_query.eq.return_value = cap_query
    cap_query.single.return_value = cap_query
    cap_query.execute.return_value = MagicMock(data={"id": "cap_1"})

    # Step 6: Check business permissions
    perm_query = MagicMock()
    perm_query.select.return_value = perm_query
    perm_query.eq.return_value = perm_query
    perm_query.single.return_value = perm_query
    perm_query.execute.return_value = MagicMock(data={"enabled": True})

    # Step 7: Check approval required
    appr_query = MagicMock()
    appr_query.select.return_value = appr_query
    appr_query.eq.return_value = appr_query
    appr_query.single.return_value = appr_query
    appr_query.execute.return_value = MagicMock(data={"requires_approval": False})

    # Step 9: Record execution
    exec_query = MagicMock()
    exec_query.insert.return_value = exec_query
    exec_query.execute.return_value = MagicMock(data=[])

    def table_router(name: str):
        if name == "business_connectors":
            return conn_query
        elif name == "connector_capabilities":
            return cap_query
        elif name == "business_connector_permissions":
            return perm_query
        elif name == "capability_executions":
            return exec_query
        return MagicMock()

    mock_db.table.side_effect = table_router

    # Build CapabilityRuntime with mock DB and real ConnectorRegistry
    runtime = CapabilityRuntime(db=mock_db, connector_registry=ConnectorRegistry())

    req = CapabilityExecutionRequest(
        business_id=business_id,
        capability="catalog.search_products",
        input={"query": "Sneakers"},
        actor=ActorContext(
            actor_type=ActorType.AGENT,
            actor_id="agent_1",
            business_id=business_id,
        ),
    )

    result = await runtime.execute(req)
    assert result.status == CapabilityResultStatus.SUCCESS
    assert result.capability == "catalog.search_products"
    assert "products" in result.data
    assert len(result.data["products"]) > 0
    assert "Shopify" in result.data["products"][0]["title"]
