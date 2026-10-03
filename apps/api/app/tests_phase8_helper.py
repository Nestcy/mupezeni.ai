from __future__ import annotations

from app.conversations.services import ConversationProcessingService, ConversationContextService, MessageProcessingQueue
from app.crm.services import CustomerManagementService
from app.communications.service import CommunicationService


def test_phase8_message_pipeline() -> None:
    customer_service = CustomerManagementService()
    conversation_service = ConversationProcessingService()
    context_service = ConversationContextService()
    queue = MessageProcessingQueue()
    communication = CommunicationService()

    assert customer_service is not None
    assert conversation_service is not None
    assert context_service is not None
    assert isinstance(queue.pending(), list)
    assert communication is not None


__all__ = ["test_phase8_message_pipeline"]
