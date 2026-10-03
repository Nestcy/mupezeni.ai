from __future__ import annotations

from app.crm.services import CustomerManagementService, CustomerInteractionService
from app.conversations.services import ConversationProcessingService, ConversationContextService, MessageProcessingQueue, MessageRecord
from app.communications.service import CommunicationService, InboundMessageNormalizer, OutboundMessageNormalizer

__all__ = [
    "CustomerManagementService",
    "CustomerInteractionService",
    "ConversationProcessingService",
    "ConversationContextService",
    "MessageProcessingQueue",
    "MessageRecord",
    "CommunicationService",
    "InboundMessageNormalizer",
    "OutboundMessageNormalizer",
]
