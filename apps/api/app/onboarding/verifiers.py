"""Verify a retailer's existing catalog credentials before trusting them. Includes SSRF guards (user supplies the host)."""
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

_SHOPIFY = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


class CatalogVerificationError(Exception):
    pass


class CatalogVerifier(Protocol):
    async def verify(self, provider: str, config: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]: ...


def _assert_public_https(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname:
        raise CatalogVerificationError("Store URL must be https")
    try:
        infos = socket.getaddrinfo(p.hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise CatalogVerificationError("Store host cannot be resolved") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise CatalogVerificationError("Store host is not publicly routable")
    return f"https://{p.hostname}"


class HttpCatalogVerifier:
    async def verify(self, provider: str, config: dict[str, Any], secrets: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as c:
            if provider == "shopify":
                domain = str(config.get("shop_domain", "")).lower()
                if not _SHOPIFY.match(domain):
                    raise CatalogVerificationError("shop_domain must look like your-store.myshopify.com")
                r = await c.get(f"https://{domain}/admin/api/2024-10/shop.json",
                                headers={"X-Shopify-Access-Token": secrets["access_token"]})
            elif provider == "woocommerce":
                base = _assert_public_https(str(config.get("site_url", "")))
                r = await c.get(f"{base}/wp-json/wc/v3/products", params={"per_page": 1},
                                auth=(secrets["consumer_key"], secrets["consumer_secret"]))
            else:
                raise CatalogVerificationError(f"No verifier for {provider}")
        if r.status_code != 200:
            raise CatalogVerificationError(f"{provider} rejected the credentials ({r.status_code})")
        return {"verified": True}
