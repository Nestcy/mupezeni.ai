from __future__ import annotations

from typing import Any

from app.db.client import get_database_client, get_service_role_client


class ProductRepository:
    @staticmethod
    async def create(catalog_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("products")
            .insert({"catalog_id": catalog_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(product_id: str, catalog_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("products")
            .select("*")
            .eq("id", product_id)
            .eq("catalog_id", catalog_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def get_by_slug(slug: str, catalog_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("products")
            .select("*")
            .eq("slug", slug)
            .eq("catalog_id", catalog_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_catalog(catalog_id: str, status: str | None = None) -> list[dict[str, Any]]:
        client = get_database_client()
        query = client.table("products").select("*").eq("catalog_id", catalog_id)
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return result.data or []

    @staticmethod
    async def search(
        catalog_id: str,
        query: str | None = None,
        status: str = "active",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search products by name/description"""
        client = get_database_client()
        # Simple text search using ilike
        db_query = client.table("products").select("*").eq("catalog_id", catalog_id).eq("status", status)
        if query:
            db_query = db_query.or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
        result = db_query.limit(limit).execute()
        return result.data or []

    @staticmethod
    async def update(product_id: str, catalog_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("products")
            .update(data)
            .eq("id", product_id)
            .eq("catalog_id", catalog_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def delete(product_id: str, catalog_id: str) -> bool:
        client = get_service_role_client()
        result = (
            client.table("products")
            .delete()
            .eq("id", product_id)
            .eq("catalog_id", catalog_id)
            .execute()
        )
        return len(result.data) > 0 if result.data else False


class ProductVariantRepository:
    @staticmethod
    async def create(product_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("product_variants")
            .insert({"product_id": product_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_by_id(variant_id: str, product_id: str) -> dict[str, Any] | None:
        client = get_database_client()
        result = (
            client.table("product_variants")
            .select("*")
            .eq("id", variant_id)
            .eq("product_id", product_id)
            .single()
            .execute()
        )
        return result.data if result.data else None

    @staticmethod
    async def list_by_product(product_id: str) -> list[dict[str, Any]]:
        client = get_database_client()
        result = (
            client.table("product_variants")
            .select("*")
            .eq("product_id", product_id)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []

    @staticmethod
    async def update(variant_id: str, product_id: str, data: dict[str, Any]) -> dict[str, Any]:
        client = get_service_role_client()
        result = (
            client.table("product_variants")
            .update(data)
            .eq("id", variant_id)
            .eq("product_id", product_id)
            .execute()
        )
        return result.data[0] if result.data else {}
