"""
Abstract interface for LLM providers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    LMSTUDIO = "lmstudio"
    OLLAMA = "ollama"
    CLAUDE = "claude"
    OPENAI = "openai"


class LLMInterface(ABC):
    """
    Abstract base class for all LLM providers
    Ensures consistent API across different backends
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            {
                "content": "generated response",
                "tokens_used": 1234,
                "model": "model-name",
                "finish_reason": "stop",
                "latency_ms": 1500
            }
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output

        Args:
            prompt: User prompt
            schema: Expected JSON schema
            system_prompt: System instructions
            **kwargs: Provider-specific parameters

        Returns:
            {
                "content": "raw response",
                "parsed_json": {...},
                "tokens_used": 1234,
                "model": "model-name"
            }
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available and reachable

        Returns:
            True if available, False otherwise
        """
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """
        Get maximum context window size in tokens

        Returns:
            Context window size
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get provider name

        Returns:
            Provider name as string
        """
        pass

    def supports_streaming(self) -> bool:
        """
        Check if provider supports streaming responses

        Returns:
            True if streaming is supported
        """
        return False
