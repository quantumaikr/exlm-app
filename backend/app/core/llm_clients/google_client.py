"""
Google Gemini API client implementation
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.core.llm_clients.base import LLMClient, LLMResponse
from app.core.logging import logger


class GoogleClient(LLMClient):
    """Google Gemini API client"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        genai.configure(api_key=api_key)
        
        # Safety settings
        self.safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            }
        ]
    
    async def generate(
        self,
        prompt: str,
        model: str = "gemini-pro",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion"""
        try:
            model_instance = genai.GenerativeModel(model)
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop
            )
            
            response = await model_instance.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            # Calculate approximate token usage
            # Gemini doesn't provide exact token counts
            prompt_tokens = len(prompt.split()) * 1.3  # Approximate
            completion_tokens = len(response.text.split()) * 1.3
            
            return LLMResponse(
                text=response.text,
                model=model,
                usage={
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens + completion_tokens)
                },
                finish_reason="stop",
                metadata={
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.prompt_feedback.safety_ratings
                    ] if hasattr(response, 'prompt_feedback') else []
                }
            )
            
        except Exception as e:
            logger.error(f"Google Gemini API error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        model: str = "gemini-pro",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate text completion with streaming"""
        try:
            model_instance = genai.GenerativeModel(model)
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop
            )
            
            response = await model_instance.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings,
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Google Gemini streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-pro",
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
            model_instance = genai.GenerativeModel(model)
            
            # Convert messages to Gemini format
            chat = model_instance.start_chat(history=[])
            
            # Process messages
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    # Gemini doesn't have system messages, prepend to first user message
                    if i + 1 < len(messages) and messages[i + 1]["role"] == "user":
                        messages[i + 1]["content"] = f"{msg['content']}\n\n{messages[i + 1]['content']}"
                elif msg["role"] == "user":
                    # For the last user message, get response
                    if i == len(messages) - 1:
                        generation_config = genai.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            stop_sequences=stop
                        )
                        
                        response = await chat.send_message_async(
                            msg["content"],
                            generation_config=generation_config,
                            safety_settings=self.safety_settings
                        )
                    else:
                        # Add to history
                        chat.history.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    # Add to history
                    chat.history.append({"role": "model", "parts": [msg["content"]]})
            
            # Calculate approximate token usage
            prompt_tokens = sum(len(m["content"].split()) for m in messages) * 1.3
            completion_tokens = len(response.text.split()) * 1.3
            
            return LLMResponse(
                text=response.text,
                model=model,
                usage={
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens + completion_tokens)
                },
                finish_reason="stop",
                metadata={
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.prompt_feedback.safety_ratings
                    ] if hasattr(response, 'prompt_feedback') else []
                }
            )
            
        except Exception as e:
            logger.error(f"Google Gemini Chat API error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-pro",
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
            model_instance = genai.GenerativeModel(model)
            chat = model_instance.start_chat(history=[])
            
            # Process messages (same as chat method)
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    if i + 1 < len(messages) and messages[i + 1]["role"] == "user":
                        messages[i + 1]["content"] = f"{msg['content']}\n\n{messages[i + 1]['content']}"
                elif msg["role"] == "user":
                    if i == len(messages) - 1:
                        generation_config = genai.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            stop_sequences=stop
                        )
                        
                        response = await chat.send_message_async(
                            msg["content"],
                            generation_config=generation_config,
                            safety_settings=self.safety_settings,
                            stream=True
                        )
                        
                        async for chunk in response:
                            if chunk.text:
                                yield chunk.text
                    else:
                        chat.history.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    chat.history.append({"role": "model", "parts": [msg["content"]]})
                    
        except Exception as e:
            logger.error(f"Google Gemini Chat streaming error: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            models = []
            for model in genai.list_models():
                models.append({
                    "id": model.name.split('/')[-1],  # Extract model ID
                    "name": model.display_name,
                    "description": model.description,
                    "input_token_limit": model.input_token_limit,
                    "output_token_limit": model.output_token_limit,
                    "supported_generation_methods": model.supported_generation_methods,
                    "temperature": {
                        "min": model.temperature.min if hasattr(model, 'temperature') else 0,
                        "max": model.temperature.max if hasattr(model, 'temperature') else 1
                    },
                    "top_p": {
                        "min": model.top_p.min if hasattr(model, 'top_p') else 0,
                        "max": model.top_p.max if hasattr(model, 'top_p') else 1
                    }
                })
            return models
        except Exception as e:
            logger.error(f"Google list models error: {e}")
            raise