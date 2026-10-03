from __future__ import annotations

from app.crm.models import Customer, CustomerIdentity
from app.conversations.models import Conversation, Message, ConversationContext, IncomingMessage, OutboundMessage
from app.communications.models import DeliveryResult


def test_customer_creation_and_identity_resolution():
    customer = Customer(
        id="cust_123",
        business_id="biz_123",
        external_customer_id="web_user_456",
        first_name="Mabel",
        last_name="Kawila",
        display_name="Mabel",
        email="mabel@example.com",
        phone="+260955111222",
    )
    identity = CustomerIdentity(
        id="id_1",
        customer_id=customer.id,
        channel="web",
        external_id="web_user_456",
        display_name="Mabel",
    )
    assert customer.id == "cust_123"
    assert identity.customer_id == customer.id


def test_conversation_and_message_history():
    conversation = Conversation(
        id="conv_123",
        business_id="biz_123",
        customer_id="cust_123",
        channel="web",
        current_goal="purchase",
        current_state="browsing",
    )
    message = Message(
        id="msg_1",
        conversation_id=conversation.id,
        business_id="biz_123",
        sender_type="customer",
        sender_id="cust_123",
        direction="inbound",
        content="Do you have black Nike Air Force size 42?",
    )
    assert conversation.customer_id == "cust_123"
    assert message.conversation_id == "conv_123"


def test_conversation_context_and_delivery():
    context = ConversationContext(
        conversation_id="conv_123",
        current_goal="purchase",
        current_product="prod_456",
        cart_id="cart_123",
        recent_messages=["Do you have black Nike Air Force size 42?"],
        state="product_selection",
    )
    outbound = OutboundMessage(
        business_id="biz_123",
        conversation_id="conv_123",
        recipient="web_user_456",
        message_type="text",
        content="Yes, size 42 is available.",
    )
    delivery = DeliveryResult(provider="web", status="sent", external_message_id="ext_567")
    assert context.current_product == "prod_456"
    assert outbound.content.startswith("Yes")
    assert delivery.status == "sent"


def test_duplicate_webhook_idempotency_baseline():
    first = IncomingMessage(
        business_id="biz_123",
        channel="web",
        external_message_id="evt_42",
        customer_identity="web_user_456",
        conversation_identity="conv_123",
        content="Do you have black Nike Air Force size 42?",
    )
    second = IncomingMessage(
        business_id="biz_123",
        channel="web",
        external_message_id="evt_42",
        customer_identity="web_user_456",
        conversation_identity="conv_123",
        content="Do you have black Nike Air Force size 42?",
    )
    assert first.external_message_id == second.external_message_id


def test_web_channel_message_contract() -> None:
    message = IncomingMessage(
        business_id="biz_123",
        channel="web",
        external_message_id="web_001",
        customer_identity="customer_123",
        conversation_identity="conv_123",
        content="What about size 42?",
    )
    assert message.channel == "web"
    assert message.message_type == "text"
