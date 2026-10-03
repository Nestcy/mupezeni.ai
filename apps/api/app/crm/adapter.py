from __future__ import annotations

from app.workers.customer_revenue.contracts import CustomerContext, CustomerRevenueWorkerRequest


class CustomerRevenueContextAdapter:
    """Adapt CRM and conversation state for the Customer Revenue Worker."""

    def build_request(self, *, business_id: str, customer_id: str, conversation_id: str, message: str) -> CustomerRevenueWorkerRequest:
        return CustomerRevenueWorkerRequest(
            business_id=business_id,
            customer_context=CustomerContext(
                customer_id=customer_id,
                conversation_id=conversation_id,
                current_goal="purchase",
                recent_searches=[message],
            ),
            customer_message={
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "channel": "web",
                "content": message,
                "metadata": {},
            },
        )


__all__ = ["CustomerRevenueContextAdapter"]
