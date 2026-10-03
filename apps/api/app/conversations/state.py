from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationStateModel(BaseModel):
    current_goal: str | None = None
    current_product_id: str | None = None
    current_variant_id: str | None = None
    cart_id: str | None = None
    last_tool: str | None = None
    last_action: str | None = None
    state: str = "browsing"


class ConversationStateService:
    """Persistent conversation state tracking."""

    def __init__(self):
        self._states: dict[str, ConversationStateModel] = {}

    def get(self, conversation_id: str) -> ConversationStateModel:
        if conversation_id not in self._states:
            self._states[conversation_id] = ConversationStateModel()
        return self._states[conversation_id]

    def update(self, conversation_id: str, **kwargs: Any) -> ConversationStateModel:
        state = self.get(conversation_id)
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


__all__ = ["ConversationStateModel", "ConversationStateService"]
