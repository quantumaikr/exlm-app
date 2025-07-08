"""
Anthropic Claude API client implementation
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import anthropic
from anthropic import AsyncAnthropic

from app.core.llm_clients.base import LLMClient, LLMResponse
from app.core.logging import logger


class AnthropicClient(LLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = "claude-2.1",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion"""
        # Claude uses messages format, convert prompt
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, model, max_tokens, temperature, top_p, stop, **kwargs)
    
    async def generate_stream(
        self,
        prompt: str,
        model: str = "claude-2.1",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate text completion with streaming"""
        # Claude uses messages format, convert prompt
        messages = [{"role": "user", "content": prompt}]
        async for chunk in self.chat_stream(messages, model, max_tokens, temperature, top_p, stop, **kwargs):
            yield chunk
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-2.1",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """Chat completion"""
        if not self.validate_messages(messages):
            raise ValueError("Invalid message format")
        
        try:
            # Extract system message if present
            system_message = None
            filtered_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    filtered_messages.append(msg)
            
            response = await self.client.messages.create(
                model=model,
                messages=filtered_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                system=system_message,
                **kwargs
            )
            
            # Calculate usage
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
            
            return LLMResponse(
                text=response.content[0].text,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "stop",
                metadata={
                    "id": response.id,
                    "role": response.role
                }
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-2.1",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Chat completion with streaming"""
        if not self.validate_messages(messages):
            raise ValueError("Invalid message format")
        
        try:
            # Extract system message if present
            system_message = None
            filtered_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    filtered_messages.append(msg)
            
            async with self.client.messages.stream(
                model=model,
                messages=filtered_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                system=system_message,
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        # Anthropic doesn't have a list models endpoint
        # Return hardcoded list of available models
        return [
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "context_window": 200000,
                "max_output": 4096
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "context_window": 200000,
                "max_output": 4096
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "context_window": 200000,
                "max_output": 4096
            },
            {
                "id": "claude-2.1",
                "name": "Claude 2.1",
                "context_window": 200000,
                "max_output": 4096
            },
            {
                "id": "claude-2.0",
                "name": "Claude 2.0",
                "context_window": 100000,
                "max_output": 4096
            },
            {
                "id": "claude-instant-1.2",
                "name": "Claude Instant 1.2",
                "context_window": 100000,
                "max_output": 4096
            }
        ]