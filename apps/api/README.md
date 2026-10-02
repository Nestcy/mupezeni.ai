# Mupezeni API foundation

This directory contains the backend foundation for Mupezeni. It is intentionally scoped to the backend-only architecture required for the next phase of development.

Architecture

Web
 ↓
FastAPI
 ↓
Services
 ↓
Capability Layer
 ↓
Connector Registry
 ↓
Provider
 ↓
Supabase / External API

Key principles

- Supabase Auth is the source of user identity.
- Business access is validated by membership checks in `business_members`.
- Every business-owned resource is protected by server-side authorization checks.
- The connector architecture isolates provider-specific logic behind capability interfaces.
- Provider secrets are never placed in business configuration JSON.
- Database access is centralized through a reusable Supabase client abstraction.

Authentication and authorization

The API expects a bearer token from Supabase Auth. Authenticated requests are validated before business-scoped routes are allowed. The backend checks that the current user is a member of the requested business and enforces role-based access on protected operations.

Business isolation

Business data is isolated by checking `business_members` before serving a request. The server never trusts the client to assert business ownership.

RLS

Supabase Row Level Security is enabled on business-owned tables to enforce user-to-business access control in the database. The application server should still validate business membership at the API layer for consistent authorization behavior and faster fail-fast checks.

Connector architecture

The capability layer exposes provider-agnostic interfaces (for example, catalog connector behavior). The `ConnectorRegistry` resolves the appropriate provider for a business and capability without the worker or API layer reaching into the database to decide provider behavior.

Provider abstraction

Provider implementations are separated behind interfaces and the registry. This ensures a worker can ask for capability execution without directly coupling to Shopify, WooCommerce, WhatsApp, Meta, Yango, or other APIs.

Secrets handling

Provider credentials should be stored in a future secret vault. The current database model stores only a `secret_reference` and keeps provider secrets out of business configuration JSON.

Database migrations

The project uses SQL migrations under `supabase/migrations/` to create the core schema. This keeps the data model auditable and consistent across environments.

Example future worker flow

```python
from app.connectors.registry import ConnectorRegistry

registry = ConnectorRegistry()
connector = registry.resolve(business_id="business-uuid", capability="catalog")
products = await connector.search_products(query="milk")
```

This keeps the worker focused on capabilities, not data access or external provider APIs.
