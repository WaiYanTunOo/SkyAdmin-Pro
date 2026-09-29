"""Custom exceptions for SkyAgent services."""


class SkyAgentError(Exception):
    """Base exception for SkyAgent errors."""


class DatabaseReadOnlyError(SkyAgentError):
    """Raised when a non-SELECT query is attempted."""


class LLMProviderError(SkyAgentError):
    """Raised when an LLM provider fails."""


class RAGIndexError(SkyAgentError):
    """Raised when RAG index operations fail."""
