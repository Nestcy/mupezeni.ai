# Mupezeni.ai Phase 9
## Commerce Completion Layer: Checkout, Payments, Fulfillment & Delivery

> **Backend engineering specification. No frontend UI in this phase.**

---

## Objective

Build the backend commerce completion layer that takes a customer from intent to a completed order:

```
"I want this"
     ↓
   Cart
     ↓
 Checkout
     ↓
   Order
     ↓
  Payment
     ↓
Fulfillment
     ↓
 Delivery
     ↓
 Completed
```

This phase must integrate cleanly with the existing:
* Commerce system
* Customer Revenue Worker
* Agent Runtime
* Capability Runtime
* Connector Runtime
* CRM
* Conversations
* Business Events
* Analytics

**Do not build frontend UI in this phase.**
The backend must be fully usable and testable through APIs, services, integration tests, and mock providers.

---

## First Principles

Every requirement in this document follows from a small set of irreducible truths. When a design question is not answered explicitly, derive the answer from these.

| Principle | Why it is true | Consequence in this phase |
|---|---|---|
| **Money is exact** | Rounding errors in currency are real losses and disputes. | Integer minor units plus currency; no floats; no silent conversion. |
| **The server is the only authority** | Clients and AI models can be wrong or malicious. | Server recalculates every total; the worker never self-reports payment success. |
| **Payment success is a fact held by the provider** | Our system can only learn it, not decide it. | Payment is "paid" only after provider confirmation (verified webhook or authoritative fetch). |
| **Networks fail and messages repeat** | Timeouts, retries, and duplicate deliveries are normal. | Idempotency keys and unique constraints make every operation safe to repeat. |
| **Distinct concepts change independently** | An order can be processing while payment is paid and delivery is pending. | Four separate status machines: order, payment, fulfillment, delivery. |
| **History must not rewrite itself** | Products, prices, and addresses change after a sale. | Snapshot product, price, and address data onto the order. |
| **Scarce stock is a shared resource** | Two buyers can race for the last unit. | Reserve inventory in the database with locks/constraints, never in application memory. |
| **The AI should hold no privileged access** | An LLM is an untrusted actor. | All actions go through Capability Runtime with authorization, risk levels, and approval policy. |
| **Providers are replaceable** | Vendors change; business rules should not. | Provider interfaces with normalized inputs and outputs; mock providers now, real ones later. |
| **Customer payments are not Mupezeni billing** | Different parties, different money flows. | Keep the commerce payment domain fully separate from subscription billing. |

---

## 1. Core Architecture

```
Customer
   ↓
Conversation / Web Channel
   ↓
Customer Revenue Worker
   ↓
Agent Runtime
   ↓
Capability Runtime
   ↓
Commerce Capabilities
   ↓
Checkout Service
   ↓
┌──────────────────────────────────────┐
│                                      │
│  Payment               Fulfillment   │
│     │                       │        │
│  Payment Provider      Delivery Provider
│                                      │
└──────────────────┬───────────────────┘
                   ↓
                 Order
                   ↓
            Business Events
                   ↓
              Analytics
```

The AI worker must never directly interact with payment or delivery providers. It must use capabilities, for example:
* `orders.create_checkout`
* `payments.create_payment`
* `payments.get_payment_status`
* `fulfillment.create`
* `delivery.get_status`

Those capabilities go through the existing Capability Runtime.

---

## 2. Critical Architectural Rule

Keep these four concepts separate. Do not use one status field for all four.

| Concept | Allowed statuses |
|---|---|
| **Order status** | `pending`, `confirmed`, `processing`, `ready`, `dispatched`, `completed`, `cancelled` |
| **Payment status** | `pending`, `processing`, `paid`, `failed`, `cancelled`, `refunded`, `partially_refunded` |
| **Fulfillment status** | `unfulfilled`, `processing`, `ready`, `fulfilled`, `cancelled` |
| **Delivery status** | `pending`, `assigned`, `picked_up`, `in_transit`, `delivered`, `failed`, `returned`, `cancelled` |

For example, the following combination is perfectly valid:
```python
order.status = "processing"
payment.status = "paid"
fulfillment.status = "processing"
delivery.status = "pending"
```

---

## 3. Create Checkout Domain

Directory layout:
```
apps/api/app/checkout/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── pricing.py
├── validation.py
├── state.py
└── errors.py
```

Checkout sessions should contain:
* `id`
* `business_id`
* `customer_id`
* `cart_id`
* `currency`
* `subtotal`
* `discount_total`
* `shipping_total`
* `tax_total`
* `fee_total`
* `grand_total`
* `status`
* `expires_at`
* `created_at`
* `updated_at`

Checkout statuses:
* `created`
* `validated`
* `payment_pending`
* `completed`
* `expired`
* `cancelled`

---

## 4. Checkout Validation

Before creating an order, validate:
* cart exists
* cart belongs to the business
* cart belongs to the customer where applicable
* cart is active
* cart contains products
* products still exist
* products are purchasable
* variants are valid
* prices are current
* inventory is available
* currency is valid
* quantities are valid
* discounts are valid
* delivery information is valid

**Never trust totals supplied by the client.**
The server must recalculate: subtotal, discounts, shipping, fees, taxes, and grand total.

---

## 5. Money Handling

* Never use floating-point numbers for money. Use integer minor units. Example: K150.50 becomes `15050`.
* Store `amount_minor` and `currency` throughout payment and order systems.
* Do not silently convert currencies.

---

## 6. Customer Addresses

Directory layout:
```
apps/api/app/addresses/
├── models.py
├── schemas.py
├── services.py
└── validation.py
```

Create an address entity containing fields such as:
* `id`
* `customer_id`
* `business_id`
* `label`
* `recipient_name`
* `phone`
* `address_line_1`
* `address_line_2`
* `city`
* `region`
* `country`
* `postal_code`
* `delivery_notes`
* `is_default`
* `created_at`
* `updated_at`

Rules:
* Business isolation is mandatory.
* Customers should be able to have multiple addresses (for example Home, Office, Other).
* Checkout should snapshot the selected address onto the order, because the customer may later edit their saved address. Historical orders must not change.

---

## 7. Order Snapshotting

When an order is created, the order must preserve:
* product name
* SKU
* variant
* unit price
* quantity
* discounts
* currency
* customer information required for fulfillment
* shipping address
* billing information where applicable

Do not rely on the current product record to reconstruct historical orders. If a product changes tomorrow, yesterday's order must remain historically accurate.

---

## 8. Payment Domain

Directory layout:
```
apps/api/app/payments/
├── __init__.py
├── models.py
├── schemas.py
├── services.py
├── providers/
│   ├── base.py
│   └── mock.py
├── webhooks.py
├── idempotency.py
└── errors.py
```

---

## 9. Payment Model

Fields:
* `id`
* `business_id`
* `order_id`
* `checkout_id`
* `customer_id`
* `provider`
* `provider_payment_id`
* `amount_minor`
* `currency`
* `status`
* `payment_method_type`
* `metadata`
* `created_at`
* `updated_at`

Payment statuses: `pending`, `processing`, `paid`, `failed`, `cancelled`, `refunded`, `partially_refunded`.

**Never assume "payment created" means "payment successful." A payment is only considered successful after the provider confirms it.**

---

## 10. Payment Provider Interface

```python
class PaymentProvider(Protocol):
    async def create_payment(...):
        ...
    async def get_payment(...):
        ...
    async def cancel_payment(...):
        ...
    async def refund_payment(...):
        ...
    async def verify_webhook(...):
        ...
```

The application must depend on this interface, not a specific provider.

---

## 11. Mock Payment Provider

Implement `MockPaymentProvider` for development and automated testing. It should support these scenarios: success, pending, failure, cancelled, refund.

Endpoints:
* `POST /payments/test/simulate-success`
* `POST /payments/test/simulate-failure`

These endpoints must be development/test-only. Do not expose test payment controls in production.

---

## 12. Payment Webhooks

Create a provider-neutral webhook processing system.

```
Payment Provider
       ↓
    Webhook
       ↓
Signature Verification
       ↓
Idempotency Check
       ↓
 Normalize Event
       ↓
  Update Payment
       ↓
   Update Order
       ↓
 Update Fulfillment
       ↓
Emit Business Event
```

**Never trust webhook payloads without verification.**

---

## 13. Payment Idempotency

* This is extremely important. The same webhook may arrive multiple times (`payment.succeeded`, `payment.succeeded`, `payment.succeeded`). The system must process it exactly once.
* Create an idempotency/event record using `provider` and `external_event_id` with a unique constraint.
* Likewise, creating a payment must support an idempotency key. A network retry must never accidentally create 2 payments for 1 order.

---

## 14. Checkout → Order Transaction

Implement a safe checkout process. Conceptually:
1. Validate checkout
2. Recalculate totals
3. Validate inventory
4. Reserve inventory
5. Create order
6. Create payment
7. Transition checkout

Use database transactions where appropriate. Be careful with external payment calls: do not hold a long database transaction open while waiting on an external provider.

Design the flow to safely recover from:
* timeout
* provider failure
* server crash
* duplicate request
* duplicate webhook
* payment succeeds but response is lost

---

## 15. Prevent Double Orders

A retry of `POST /checkout/complete` must not create another order. Use `idempotency_key` and database uniqueness constraints. The same checkout session should resolve to the same order.

---

## 16. Inventory Integration

Integrate with the existing inventory system.

| Event | Inventory effect |
|---|---|
| **Checkout begins** | `available inventory` → `reserve inventory` |
| **Payment succeeds** | `reserved inventory` → `committed to order` |
| **Payment fails or checkout expires** | `reserved inventory` → `released` |

Do not simply subtract inventory during checkout. Respect the existing `quantity`, `reserved_quantity`, and `available_quantity` model.

---

## 17. Order Lifecycle

Implement explicit transitions:
```
pending
   ↓
confirmed
   ↓
processing
   ↓
ready
   ↓
dispatched
   ↓
completed
```

Cancellation should be handled according to state. For example, `pending` → `cancelled`, `confirmed` → `cancelled`, and `processing` → `cancelled` may be allowed depending on policy. But `completed` → `cancelled` should not happen directly; use refund/return processes instead.

Create a centralized state transition service. Do not allow random code to mutate order statuses.

---

## 18. Fulfillment Domain

Directory layout:
```
apps/api/app/fulfillment/
├── models.py
├── schemas.py
├── services.py
├── providers/
│   ├── base.py
│   └── mock.py
├── state.py
└── errors.py
```

Fulfillment represents the business preparing the order:
```
unfulfilled
   ↓
processing
   ↓
ready
   ↓
fulfilled
```

---

## 19. Delivery Domain

Directory layout:
```
apps/api/app/delivery/
├── models.py
├── schemas.py
├── services.py
├── providers/
│   ├── base.py
│   └── mock.py
├── webhooks.py
├── tracking.py
└── errors.py
```

Delivery must be provider-agnostic. Possible future providers: Yango, DHL, local courier, business-owned delivery, third-party logistics provider. Do not implement those real integrations yet.

---

## 20. Delivery Provider Interface

```python
class DeliveryProvider(Protocol):
    async def create_delivery(...):
        ...
    async def get_delivery(...):
        ...
    async def cancel_delivery(...):
        ...
    async def get_tracking(...):
        ...
    async def verify_webhook(...):
        ...
```

The provider should return normalized results.

---

## 21. Delivery Entity

Fields:
* `id`
* `business_id`
* `order_id`
* `provider`
* `provider_delivery_id`
* `status`
* `tracking_number`
* `pickup_address`
* `delivery_address`
* `estimated_delivery_at`
* `actual_delivery_at`
* `metadata`
* `created_at`
* `updated_at`

Do not make the delivery provider's data model the Mupezeni data model.

---

## 22. Delivery Tracking

Support normalized tracking information: `status`, `location`, `description`, `timestamp`, `provider_event_id`.

Example normalized statuses: `picked_up`, `in_transit`, `out_for_delivery`, `delivered`, `failed`, `returned`.

Provider-specific statuses should be mapped into Mupezeni's normalized statuses.

---

## 23. Fulfillment + Delivery Flow

```
Payment
   ↓
Order confirmed
   ↓
Fulfillment created
   ↓
Business prepares order
   ↓
Order ready
   ↓
Delivery created
   ↓
Courier picks up
   ↓
Dispatched
   ↓
In transit
   ↓
Delivered
   ↓
Order completed
```

Do not automatically assume every business needs a third-party delivery provider. Support these delivery modes: `business_delivery`, `external_provider`, `customer_pickup`.

---

## 24. Commerce Capabilities

Register the following capabilities with the existing Capability Runtime:
* `checkout.create`
* `checkout.validate`
* `checkout.get`
* `orders.create`
* `orders.get`
* `orders.cancel`
* `payments.create`
* `payments.get`
* `payments.cancel`
* `payments.refund`
* `fulfillment.create`
* `fulfillment.get`
* `fulfillment.mark_ready`
* `delivery.create`
* `delivery.get`
* `delivery.get_tracking`
* `delivery.cancel`

Use the existing architecture, and do not bypass this layer:
```
Worker
  ↓
Capability
  ↓
Capability Runtime
  ↓
Authorization
  ↓
Connector Registry
  ↓
Provider
```

---

## 25. Capability Risk Levels

| Risk | Capabilities |
|---|---|
| **Low** | `checkout.get`, `orders.get`, `payments.get`, `delivery.get`, `delivery.get_tracking` |
| **Medium** | `checkout.create`, `fulfillment.create`, `delivery.create`, `orders.cancel` |
| **High** | `payments.create`, `payments.refund` |

Payment/refund actions must respect the existing approval and autonomy policies. The AI worker must never bypass approval requirements.

---

## 26. Customer Revenue Worker Integration

Extend the Customer Revenue Worker so it can handle this conversation progression:

| Customer says | Worker action |
|---|---|
| "I want the black Nike shoes." | product search |
| "I'll take size 42." | variant selection |
| "Add them to my cart." | `cart.add_item` |
| "How much is everything?" | `checkout.create` / `checkout.get` |
| "Okay, I'll buy them." | `checkout.validate` |
| "Pay for it." | payment capability |

The worker should clearly distinguish: cart created, checkout created, payment initiated, payment pending, payment successful, payment failed, order confirmed.

**Never tell the customer "Your payment was successful" unless the backend has authoritative confirmation.**

---

## 27. Conversation Continuity

```
Customer: "I'll take the black one."
Worker:   "Which size?"
Customer: "42."
Worker:   "Great. I've added the black size 42 to your cart."
Customer: "How much?"
Worker:   "Your total is..."
Customer: "Let's do it."
Worker:   "Checkout is ready."
```

The worker should use structured conversation state rather than relying exclusively on LLM memory.

---

## 28. Business Events

Extend the event system with:

| Domain | Events |
|---|---|
| **checkout** | `created`, `validated`, `expired`, `completed` |
| **payment** | `created`, `pending`, `processing`, `paid`, `failed`, `cancelled`, `refunded` |
| **order** | `created`, `confirmed`, `processing`, `ready`, `dispatched`, `completed`, `cancelled` |
| **fulfillment** | `created`, `processing`, `ready`, `fulfilled` |
| **delivery** | `created`, `assigned`, `picked_up`, `in_transit`, `delivered`, `failed`, `returned`, `cancelled` |

(Event names take the form `domain.event`, for example `checkout.created` or `payment.paid`.) Events must be business-scoped, immutable, timestamped, and idempotently processed where appropriate.

---

## 29. Analytics Integration

Extend Phase 7 analytics. The Business Management Worker should eventually be able to answer:
* How much did I sell today?
* How many orders were completed?
* How many payments failed?
* How many orders are awaiting payment?
* How many orders are being delivered?
* How many deliveries failed?
* What is my average order value?
* How much revenue came from completed orders?
* How much revenue is pending?
* How many carts reached checkout but never paid?

Be precise about: gross sales, paid sales, completed sales, refunded sales, and pending payments.
**Do not count an unpaid order as revenue.**

---

## 30. Webhook Architecture

```
External Provider
       ↓
Webhook Endpoint
       ↓
Signature Verification
       ↓
External Event ID
       ↓
  Idempotency
       ↓
Provider Adapter
       ↓
Normalized Event
       ↓
 Domain Service
       ↓
 Business Event
```

Do not put provider-specific logic throughout the application.

---

## 31. Security

* business isolation
* authorization
* webhook signature verification
* idempotency
* provider credential isolation
* no secrets in logs
* no payment credentials in database
* no raw card information
* audit logging for sensitive operations
* protected internal/test endpoints

Payment providers should handle sensitive payment credentials whenever possible. Mupezeni should store references/tokens required for integration, not raw card data.

---

## 32. Error Handling

Define explicit errors for:
* `CheckoutExpired`
* `CartEmpty`
* `InventoryUnavailable`
* `InvalidVariant`
* `InvalidAddress`
* `InvalidCurrency`
* `PaymentFailed`
* `PaymentPending`
* `PaymentAlreadyProcessed`
* `OrderAlreadyCancelled`
* `InvalidOrderTransition`
* `DeliveryCreationFailed`
* `DeliveryUnavailable`
* `DuplicateWebhook`
* `ProviderTimeout`
* `ProviderUnavailable`

Return normalized API errors. Do not leak provider internals to customers.

---

## 33. API Endpoints

Create backend endpoints approximately like the following, following the existing API conventions in the repository:

```http
POST /checkout
GET  /checkout/{checkout_id}
POST /checkout/{checkout_id}/validate
POST /checkout/{checkout_id}/complete

GET  /orders/{order_id}
POST /orders/{order_id}/cancel

GET  /payments/{payment_id}
POST /payments/{payment_id}/cancel
POST /payments/{payment_id}/refund

POST /webhooks/payments/{provider}
POST /webhooks/delivery/{provider}

GET  /deliveries/{delivery_id}
GET  /deliveries/{delivery_id}/tracking
```

---

## 34. Database Design

Create proper migrations. Tables:
* `checkout_sessions`
* `customer_addresses`
* `payments`
* `payment_events`
* `fulfillments`
* `deliveries`
* `delivery_events`

Add appropriate indexes, foreign keys, and consistent timestamps. Important uniqueness constraints include:
* `business_id` + `idempotency_key`
* `provider` + `provider_payment_id`
* `provider` + `external_event_id`
* `checkout_id` → one completed order

---

## 35. Concurrency

Pay special attention to these scenarios:
* two customers buying the last item
* customer clicks "pay" twice
* payment webhook arrives while checkout completion is running
* delivery webhook arrives twice

Use database constraints, transactions, locking where appropriate, and idempotency. Do not attempt to solve concurrency purely in Python application memory.

---

## 36. Testing

Create comprehensive tests.

| Area | Cases |
|---|---|
| **Checkout** | valid checkout, empty cart, expired cart, invalid product, invalid variant, insufficient inventory, incorrect totals |
| **Payments** | successful payment, failed payment, pending payment, duplicate payment request, duplicate webhook, refund, provider timeout |
| **Orders** | valid transitions, invalid transitions, cancellation, historical snapshot |
| **Inventory** | reservation, release, successful purchase, failed payment, concurrent purchase |
| **Delivery** | delivery creation, tracking, duplicate webhook, failed delivery, delivery completion |
| **End-to-end** | Customer → Cart → Checkout → Payment → Order → Fulfillment → Delivery → Completed |

---

## 37. End-to-End Scenario

The final automated test should simulate the following sequence, without requiring a real payment or courier account:

```
Customer asks for product
       ↓
Customer Revenue Worker finds product
       ↓
Customer selects variant
       ↓
Worker adds product to cart
       ↓
Customer requests checkout
       ↓
Checkout created
       ↓
Server validates cart
       ↓
Inventory reserved
       ↓
Order created
       ↓
Payment created
       ↓
Mock payment succeeds
       ↓
Payment webhook received
       ↓
Payment marked paid
       ↓
Order confirmed
       ↓
Fulfillment created
       ↓
Business marks order ready
       ↓
Delivery created
       ↓
Delivery picked up
       ↓
Delivery in transit
       ↓
Delivery completed
       ↓
Order completed
       ↓
Business events emitted
       ↓
Analytics updated
```

---

## 38. What NOT to Build

* real payment provider integration yet
* real Yango integration
* real DHL integration
* real WhatsApp payment flow
* Stripe-specific business logic throughout the codebase
* mobile payment UI
* frontend checkout
* advanced tax engine
* subscriptions
* Mupezeni billing
* AI-based fraud detection
* advanced logistics optimization
* cryptocurrency payments
* arbitrary payment methods

Those can come later. The architecture must make them possible without rewriting the core.

---

## 39. Important Separation: Commerce vs Mupezeni Billing

| System | Money flow |
|---|---|
| **Commerce payments (this phase)** | Customer → Retail Business |
| **Mupezeni billing (not this phase)** | Retail Business → Mupezeni |

Phase 9 is about commerce payments, not Mupezeni's subscription billing. Keep those domains completely separate.

---

## 40. Documentation

Update the architecture documentation with:
* Commerce Completion Architecture
* Payment Architecture
* Checkout Lifecycle
* Order Lifecycle
* Fulfillment Lifecycle
* Delivery Architecture
* Webhook Architecture
* Idempotency Strategy
* Failure Recovery

Document the difference between Order, Payment, Fulfillment, and Delivery. This distinction must be obvious to future developers.

---

## 41. Definition of Done

Phase 9 is complete when:
- [ ] Checkout domain exists
- [ ] Checkout validation works
- [ ] Customer addresses exist
- [ ] Order snapshots are created
- [ ] Payment domain exists
- [ ] Payment provider interface exists
- [ ] Mock payment provider works
- [ ] Payment webhooks are normalized
- [ ] Webhook signatures are verified
- [ ] Payment idempotency works
- [ ] Checkout idempotency works
- [ ] Inventory reservation integrates correctly
- [ ] Order lifecycle is enforced
- [ ] Fulfillment domain exists
- [ ] Delivery domain exists
- [ ] Delivery provider interface exists
- [ ] Mock delivery provider works
- [ ] Tracking works
- [ ] Commerce capabilities are registered
- [ ] Customer Revenue Worker can progress through checkout
- [ ] Payment approval policies are respected
- [ ] Business events are emitted
- [ ] Analytics can distinguish paid/unpaid/completed/refunded sales
- [ ] Business isolation is enforced
- [ ] Concurrency is handled
- [ ] Duplicate webhooks are safe
- [ ] End-to-end commerce test passes
- [ ] No frontend is required for the phase
- [ ] No real external payment/delivery credentials are required

---

## Final Architecture After Phase 9

```
                   MUPEZENI
                      │
        ┌─────────────┴─────────────┐
        │                           │
   AI WORKERS                   COMMERCE
        │                           │
        ↓                           ↓
  Agent Runtime                 Checkout
        │                           │
        ↓                   ┌───────┴───────┐
   LLM Gateway              │               │
        │                Payment          Order
        ↓                   │               │
Capability Runtime          ↓          Fulfillment
        │                Provider           │
        ↓                                   ↓
Connector Runtime                        Delivery
        │                                   │
  ┌─────┼────────┐                          ↓
  │     │        │                       Provider
Catalog Inventory CRM
  │     │        │
  └─────┴────────┘
        │
    PostgreSQL
        │
 Business Events
        │
    Analytics
```

---

## The Key Milestone

After Phase 9, Mupezeni's backend can take *"I want the black size 42"* all the way to *"Your payment has been confirmed and your order is being delivered,"* without the AI worker needing to know whether the underlying catalog, payment, or delivery system is Mupezeni-native or an external provider.

That is a major architectural milestone.
