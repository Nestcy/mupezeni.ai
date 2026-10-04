"""Central service registry for Mupezeni.

Services are composed here and injected where needed.
"""
from app.analytics.services import BusinessAnalyticsService
from app.conversations.services import ConversationService
from app.crm.customers import CustomerManagementService as CustomerService
from app.marketing.services import CampaignService

# Phase 9 Commerce Completion Services
from app.addresses.services import CustomerAddressService
from app.checkout.services import CheckoutService
from app.payments.services import PaymentService
from app.fulfillment.services import FulfillmentService
from app.delivery.services import DeliveryService

analytics_service = BusinessAnalyticsService()
conversation_service = ConversationService()
customer_service = CustomerService()
campaign_service = CampaignService()

address_service = CustomerAddressService()
checkout_service = CheckoutService()
payment_service = PaymentService()
fulfillment_service = FulfillmentService()
delivery_service = DeliveryService()

# AI models (provider-agnostic; configured via LLM_* / IMAGE_* env vars)
from app.ai import ImageClient, LLMGateway

llm_gateway = LLMGateway.from_settings()
image_client = ImageClient.from_settings()
