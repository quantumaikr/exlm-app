"""
LLM Client Factory
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from app.core.llm_clients.base import LLMClient
from app.core.llm_clients.openai_client import OpenAIClient
from app.core.llm_clients.anthropic_client import AnthropicClient
from app.core.llm_clients.google_client import GoogleClient
from app.core.config import settings


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class LLMClientFactory:
    """Factory for creating LLM clients"""
    
    _clients: Dict[str, LLMClient] = {}
    
    @classmethod
    def get_client(
        cls,
        provider: LLMProvider,
        api_key: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """Get or create an LLM client"""
        
        # Use cached client if available
        if provider in cls._clients and not api_key:
            return cls._clients[provider]
        
        # Create new client
        if provider == LLMProvider.OPENAI:
            api_key = api_key or settings.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OpenAI API key not provided")
            client = OpenAIClient(api_key, **kwargs)
            
        elif provider == LLMProvider.ANTHROPIC:
            api_key = api_key or settings.ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError("Anthropic API key not provided")
            client = AnthropicClient(api_key, **kwargs)
            
        elif provider == LLMProvider.GOOGLE:
            api_key = api_key or settings.GOOGLE_API_KEY
            if not api_key:
                raise ValueError("Google API key not provided")
            client = GoogleClient(api_key, **kwargs)
            
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        # Cache client if using default API key
        if not api_key:
            cls._clients[provider] = client
        
        return client
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List available LLM providers"""
        return [provider.value for provider in LLMProvider]


# Convenience function
def get_llm_client(provider: str, api_key: Optional[str] = None, **kwargs) -> LLMClient:
    """Get an LLM client by provider name"""
    return LLMClientFactory.get_client(LLMProvider(provider), api_key, **kwargs)


__all__ = [
    "LLMClient",
    "LLMProvider",
    "LLMClientFactory",
    "get_llm_client",
    "OpenAIClient",
    "AnthropicClient",
    "GoogleClient"
]