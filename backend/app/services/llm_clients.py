from typing import List, Dict, Optional, Any, AsyncGenerator
from abc import ABC, abstractmethod
import httpx
import json
import os
from datetime import datetime
import asyncio
import openai
from anthropic import AsyncAnthropic
import google.generativeai as genai
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class LLMClient(ABC):
    """Base class for LLM API clients"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate text completion with streaming"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        """Chat completion"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        try:
            response = await self.client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                **kwargs
            )
            return response.choices[0].text.strip()
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices[0].text:
                    yield chunk.choices[0].text
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise


class AnthropicClient(LLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model
        self.client = AsyncAnthropic(api_key=self.api_key)
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        try:
            response = await self.client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens_to_sample=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                **kwargs
            )
            return response.completion
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens_to_sample=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                yield chunk.completion
        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        try:
            # Convert messages to Claude format
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": "user" if msg["role"] == "user" else "assistant",
                        "content": msg["content"]
                    })
            
            response = await self.client.messages.create(
                model=self.model,
                messages=claude_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                system=system_message,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            raise


class GoogleClient(LLMClient):
    """Google Gemini API client"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model = model
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
            )
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Google generation error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop,
            )
            
            response = await asyncio.to_thread(
                self.client.generate_content,
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Google streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        try:
            # Convert messages to Gemini format
            chat = self.client.start_chat(history=[])
            
            for msg in messages:
                if msg["role"] == "user":
                    response = await asyncio.to_thread(
                        chat.send_message,
                        msg["content"],
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                        )
                    )
            
            return response.text
        except Exception as e:
            logger.error(f"Google chat error: {e}")
            raise


class LLMClientFactory:
    """Factory for creating LLM clients"""
    
    _clients = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "google": GoogleClient,
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """Create an LLM client instance"""
        if provider not in cls._clients:
            raise ValueError(f"Unknown provider: {provider}")
        
        client_class = cls._clients[provider]
        
        if model:
            return client_class(api_key=api_key, model=model, **kwargs)
        else:
            return client_class(api_key=api_key, **kwargs)
    
    @classmethod
    def register(cls, provider: str, client_class: type):
        """Register a new LLM client"""
        cls._clients[provider] = client_class


class DataGenerationService:
    """Service for generating synthetic data using LLMs"""
    
    def __init__(self):
        self.clients = {}
    
    def get_client(self, provider: str, api_key: Optional[str] = None) -> LLMClient:
        """Get or create an LLM client"""
        key = f"{provider}:{api_key or 'default'}"
        
        if key not in self.clients:
            self.clients[key] = LLMClientFactory.create(provider, api_key)
        
        return self.clients[key]
    
    async def generate_instruction_response_pairs(
        self,
        provider: str,
        template: str,
        variables: Dict[str, str],
        num_samples: int,
        api_key: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Generate instruction-response pairs"""
        client = self.get_client(provider, api_key)
        results = []
        
        for i in range(num_samples):
            # Format template with variables
            prompt = template.format(**variables)
            
            try:
                response = await client.generate(prompt, **kwargs)
                
                # Parse JSON response
                try:
                    data = json.loads(response)
                    data["generated_at"] = datetime.utcnow().isoformat()
                    data["provider"] = provider
                    results.append(data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response: {response}")
                    
            except Exception as e:
                logger.error(f"Generation error for sample {i}: {e}")
        
        return results
    
    async def evaluate_quality(
        self,
        data: List[Dict[str, Any]],
        provider: str = "openai",
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate quality of generated data"""
        client = self.get_client(provider, api_key)
        
        evaluation_prompt = """
        Evaluate the quality of the following instruction-response pair on a scale of 1-10:
        
        Instruction: {instruction}
        Response: {response}
        
        Consider:
        1. Relevance of response to instruction
        2. Accuracy and completeness
        3. Clarity and coherence
        4. Usefulness
        
        Return JSON: {{"score": <number>, "feedback": "<brief feedback>"}}
        """
        
        for item in data:
            if "instruction" in item and "response" in item:
                prompt = evaluation_prompt.format(
                    instruction=item["instruction"],
                    response=item["response"]
                )
                
                try:
                    result = await client.generate(prompt, temperature=0.3)
                    eval_data = json.loads(result)
                    item["quality_score"] = eval_data.get("score", 0)
                    item["quality_feedback"] = eval_data.get("feedback", "")
                except Exception as e:
                    logger.error(f"Quality evaluation error: {e}")
                    item["quality_score"] = 0
        
        return data


# Singleton instance
data_generation_service = DataGenerationService()