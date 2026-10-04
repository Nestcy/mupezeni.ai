class AINotConfigured(RuntimeError):
    """LLM_API_KEY / LLM_MODEL (or the IMAGE_* equivalents) are not set."""


class AIProviderError(RuntimeError):
    """The provider returned an error or an unusable response."""
