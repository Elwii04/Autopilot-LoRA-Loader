"""
Groq LLM Provider
Implements Groq API integration using OpenAI-compatible endpoints.
"""
import json
import time
from typing import List, Dict, Any, Optional, tuple
import requests
from PIL import Image

from . import BaseLLMProvider
from ..utils.utils import encode_image_to_base64


# Groq API configuration
GROQ_API_BASE = "https://api.groq.com/openai/v1"

# Available models (as of the research)
GROQ_TEXT_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "qwen-qwq-32b",
    "gemma2-9b-it",
    "llama3-8b-8192",
    "llama3-70b-8192",
]

GROQ_VISION_MODELS = [
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]


class GroqProvider(BaseLLMProvider):
    """Groq API provider implementation."""
    
    def __init__(self, api_key: str):
        """Initialize Groq provider."""
        super().__init__(api_key)
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def list_models(self) -> List[str]:
        """
        List available models from Groq.
        
        Returns:
            List of model names
        """
        # Try to fetch from API
        try:
            url = f"{GROQ_API_BASE}/models"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    models = [model['id'] for model in data['data']]
                    # Merge with defaults to ensure we have common models
                    all_models = list(set(models + GROQ_TEXT_MODELS + GROQ_VISION_MODELS))
                    return sorted(all_models)
        except Exception as e:
            print(f"[Groq] Error fetching models: {e}")
        
        # Fallback to hardcoded list
        return GROQ_TEXT_MODELS + GROQ_VISION_MODELS
    
    def supports_vision(self, model: str) -> bool:
        """Check if model supports vision."""
        return model in GROQ_VISION_MODELS or 'llama-4' in model.lower()
    
    def generate_text(
        self,
        prompt: str,
        model: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 2,
        **kwargs
    ) -> tuple[bool, str, str]:
        """
        Generate text using Groq API.
        
        Args:
            prompt: User prompt
            model: Model name
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            max_retries: Number of retry attempts
            
        Returns:
            Tuple of (success, response_text, error_message)
        """
        url = f"{GROQ_API_BASE}/chat/completions"
        
        # Build messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": kwargs.get("top_p", 1.0),
            "stream": False
        }
        
        # Add seed if provided
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        return True, content, ""
                    else:
                        return False, "", "No choices in response"
                
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    print(f"[Groq] Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    return False, "", error_msg
            
            except Exception as e:
                error_msg = f"Request error: {str(e)}"
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False, "", error_msg
        
        return False, "", "Failed after all retries"
    
    def generate_with_image(
        self,
        prompt: str,
        image: Image.Image,
        model: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        max_retries: int = 2,
        **kwargs
    ) -> tuple[bool, str, str]:
        """
        Generate text with image using Groq vision model.
        
        Args:
            prompt: User prompt
            image: PIL Image
            model: Vision model name
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            max_retries: Number of retry attempts
            
        Returns:
            Tuple of (success, response_text, error_message)
        """
        if not self.supports_vision(model):
            return False, "", f"Model {model} does not support vision"
        
        url = f"{GROQ_API_BASE}/chat/completions"
        
        # Encode image to base64
        base64_image = encode_image_to_base64(image, format='JPEG')
        image_url = f"data:image/jpeg;base64,{base64_image}"
        
        # Build messages with image
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # User message with image
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
            ]
        })
        
        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        return True, content, ""
                    else:
                        return False, "", "No choices in response"
                
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    print(f"[Groq] Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    return False, "", error_msg
            
            except Exception as e:
                error_msg = f"Request error: {str(e)}"
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False, "", error_msg
        
        return False, "", "Failed after all retries"
