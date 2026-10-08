from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from app.db.client import get_database_client, get_service_role_client


class MarketingRepositoryProtocol(Protocol):
    async def create_campaign(
        self,
        business_id: str,
        name: str,
        objective: str,
        status: str = "draft",
        budget_minor: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        channels: list[str] | None = None,
        plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def get_campaign(
        self, campaign_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_campaigns(
        self, business_id: str, status: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def update_campaign_status(
        self, campaign_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def create_content(
        self,
        campaign_id: str,
        business_id: str,
        channel: str,
        body: str,
        status: str = "draft",
        publish_at: str | None = None,
        content_hash: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_content(
        self, content_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_content(
        self,
        business_id: str,
        campaign_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def update_content(
        self, content_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    async def create_approval(
        self,
        business_id: str,
        action_type: str,
        resource_id: str,
        risk_level: str,
        content_hash: str | None = None,
        batch_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_approval(
        self, approval_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None: ...

    async def list_approvals(
        self, business_id: str, status: str = "pending"
    ) -> list[dict[str, Any]]: ...

    async def decide_approval(
        self,
        approval_id: str,
        status: str,
        decided_by: str,
        rejection_reason: str | None = None,
    ) -> dict[str, Any] | None: ...


class SupabaseMarketingRepository:
    def __init__(self, db: Any = None) -> None:
        self._db = db

    def _client(self) -> Any:
        return self._db or get_service_role_client()

    async def create_campaign(
        self,
        business_id: str,
        name: str,
        objective: str,
        status: str = "draft",
        budget_minor: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        channels: list[str] | None = None,
        plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "name": name,
            "objective": objective,
            "status": status,
            "budget_minor": budget_minor,
            "start_date": start_date,
            "end_date": end_date,
            "channels": channels or [],
            "plan": plan or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("marketing_campaigns").insert(data).execute()
        return res.data[0] if res.data else data

    async def get_campaign(
        self, campaign_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("marketing_campaigns").select("*").eq("id", campaign_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def list_campaigns(
        self, business_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        q = (
            self._client()
            .table("marketing_campaigns")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
        )
        if status:
            q = q.eq("status", status)
        res = q.execute()
        return res.data or []

    async def update_campaign_status(
        self, campaign_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        updates = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
        q = self._client().table("marketing_campaigns").update(updates).eq("id", campaign_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def create_content(
        self,
        campaign_id: str,
        business_id: str,
        channel: str,
        body: str,
        status: str = "draft",
        publish_at: str | None = None,
        content_hash: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "campaign_id": campaign_id,
            "business_id": business_id,
            "channel": channel,
            "body": body,
            "status": status,
            "publish_at": publish_at,
            "content_hash": content_hash,
            "image_url": image_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("marketing_content").insert(data).execute()
        return res.data[0] if res.data else data

    async def get_content(
        self, content_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("marketing_content").select("*").eq("id", content_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def list_content(
        self,
        business_id: str,
        campaign_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        q = (
            self._client()
            .table("marketing_content")
            .select("*")
            .eq("business_id", business_id)
            .order("created_at", desc=True)
        )
        if campaign_id:
            q = q.eq("campaign_id", campaign_id)
        if status:
            q = q.eq("status", status)
        res = q.execute()
        return res.data or []

    async def update_content(
        self, content_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = self._client().table("marketing_content").update(updates).eq("id", content_id).execute()
        return res.data[0] if res.data else None

    async def create_approval(
        self,
        business_id: str,
        action_type: str,
        resource_id: str,
        risk_level: str,
        content_hash: str | None = None,
        batch_id: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "business_id": business_id,
            "action_type": action_type,
            "resource_id": resource_id,
            "risk_level": risk_level,
            "content_hash": content_hash,
            "batch_id": batch_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("marketing_approvals").insert(data).execute()
        return res.data[0] if res.data else data

    async def get_approval(
        self, approval_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        q = self._client().table("marketing_approvals").select("*").eq("id", approval_id)
        if business_id:
            q = q.eq("business_id", business_id)
        res = q.execute()
        return res.data[0] if res.data else None

    async def list_approvals(
        self, business_id: str, status: str = "pending"
    ) -> list[dict[str, Any]]:
        res = (
            self._client()
            .table("marketing_approvals")
            .select("*")
            .eq("business_id", business_id)
            .eq("status", status)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    async def decide_approval(
        self,
        approval_id: str,
        status: str,
        decided_by: str,
        rejection_reason: str | None = None,
    ) -> dict[str, Any] | None:
        updates = {
            "status": status,
            "decided_by": decided_by,
            "rejection_reason": rejection_reason,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
        res = self._client().table("marketing_approvals").update(updates).eq("id", approval_id).execute()
        return res.data[0] if res.data else None


class InMemoryMarketingRepository:
    def __init__(self) -> None:
        self.campaigns: dict[str, dict[str, Any]] = {}
        self.contents: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

    async def create_campaign(
        self,
        business_id: str,
        name: str,
        objective: str,
        status: str = "draft",
        budget_minor: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        channels: list[str] | None = None,
        plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        campaign = {
            "id": cid,
            "business_id": business_id,
            "name": name,
            "objective": objective,
            "status": status,
            "budget_minor": budget_minor,
            "start_date": start_date,
            "end_date": end_date,
            "channels": channels or [],
            "plan": plan or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.campaigns[cid] = campaign
        return campaign

    async def get_campaign(
        self, campaign_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        c = self.campaigns.get(campaign_id)
        if not c:
            return None
        if business_id and c.get("business_id") != business_id:
            return None
        return dict(c)

    async def list_campaigns(
        self, business_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        results = [
            c for c in self.campaigns.values() if c.get("business_id") == business_id
        ]
        if status:
            results = [c for c in results if c.get("status") == status]
        return results

    async def update_campaign_status(
        self, campaign_id: str, status: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        c = self.campaigns.get(campaign_id)
        if not c:
            return None
        if business_id and c.get("business_id") != business_id:
            return None
        c["status"] = status
        c["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(c)

    async def create_content(
        self,
        campaign_id: str,
        business_id: str,
        channel: str,
        body: str,
        status: str = "draft",
        publish_at: str | None = None,
        content_hash: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        cid = str(uuid.uuid4())
        content = {
            "id": cid,
            "campaign_id": campaign_id,
            "business_id": business_id,
            "channel": channel,
            "body": body,
            "status": status,
            "publish_at": publish_at,
            "content_hash": content_hash,
            "image_url": image_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.contents[cid] = content
        return content

    async def get_content(
        self, content_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        item = self.contents.get(content_id)
        if not item:
            return None
        if business_id and item.get("business_id") != business_id:
            return None
        return dict(item)

    async def list_content(
        self,
        business_id: str,
        campaign_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        results = [
            i for i in self.contents.values() if i.get("business_id") == business_id
        ]
        if campaign_id:
            results = [i for i in results if i.get("campaign_id") == campaign_id]
        if status:
            results = [i for i in results if i.get("status") == status]
        return results

    async def update_content(
        self, content_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        item = self.contents.get(content_id)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(item)

    async def create_approval(
        self,
        business_id: str,
        action_type: str,
        resource_id: str,
        risk_level: str,
        content_hash: str | None = None,
        batch_id: str | None = None,
    ) -> dict[str, Any]:
        aid = str(uuid.uuid4())
        appr = {
            "id": aid,
            "business_id": business_id,
            "action_type": action_type,
            "resource_id": resource_id,
            "risk_level": risk_level,
            "content_hash": content_hash,
            "batch_id": batch_id,
            "status": "pending",
            "decided_by": None,
            "rejection_reason": None,
            "decided_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.approvals[aid] = appr
        return appr

    async def get_approval(
        self, approval_id: str, business_id: str | None = None
    ) -> dict[str, Any] | None:
        item = self.approvals.get(approval_id)
        if not item:
            return None
        if business_id and item.get("business_id") != business_id:
            return None
        return dict(item)

    async def list_approvals(
        self, business_id: str, status: str = "pending"
    ) -> list[dict[str, Any]]:
        return [
            a for a in self.approvals.values()
            if a.get("business_id") == business_id and a.get("status") == status
        ]

    async def decide_approval(
        self,
        approval_id: str,
        status: str,
        decided_by: str,
        rejection_reason: str | None = None,
    ) -> dict[str, Any] | None:
        item = self.approvals.get(approval_id)
        if not item:
            return None
        item["status"] = status
        item["decided_by"] = decided_by
        item["rejection_reason"] = rejection_reason
        item["decided_at"] = datetime.now(timezone.utc).isoformat()
        return dict(item)
