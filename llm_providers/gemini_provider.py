"""
Gemini LLM Provider
Implements Google Gemini API integration using google-generativeai library.
"""
import json
import time
from typing import List, Dict, Any, Optional, tuple
from PIL import Image

from . import BaseLLMProvider

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("[Gemini] Warning: google-generativeai not installed")

# Default Gemini models
GEMINI_TEXT_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash-exp",
]

GEMINI_VISION_MODELS = [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
]


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider implementation."""
    
    def __init__(self, api_key: str):
        """Initialize Gemini provider."""
        super().__init__(api_key)
        
        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
        
        # Configure Gemini
        genai.configure(api_key=api_key, transport='rest')
    
    def list_models(self) -> List[str]:
        """
        List available models from Gemini.
        
        Returns:
            List of model names
        """
        try:
            models = genai.list_models()
            model_names = []
            
            for model in models:
                # Extract model name (remove 'models/' prefix)
                name = model.name
                if name.startswith('models/'):
                    name = name[7:]
                
                # Filter to generative models
                if 'generateContent' in model.supported_generation_methods:
                    model_names.append(name)
            
            # Merge with defaults
            all_models = list(set(model_names + GEMINI_TEXT_MODELS))
            return sorted(all_models)
        
        except Exception as e:
            print(f"[Gemini] Error fetching models: {e}")
            return GEMINI_TEXT_MODELS
    
    def supports_vision(self, model: str) -> bool:
        """Check if model supports vision."""
        # Most Gemini models support vision
        return model in GEMINI_VISION_MODELS or 'gemini-1.5' in model or 'gemini-2.0' in model
    
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
        Generate text using Gemini API.
        
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
        try:
            # Build generation config
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
            )
            
            # Create model instance
            model_instance = genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=system_message if system_message else None
            )
            
            # Retry loop
            for attempt in range(max_retries):
                try:
                    # Generate content
                    response = model_instance.generate_content(prompt)
                    
                    # Check for blocked content
                    if not response.candidates:
                        if hasattr(response, 'prompt_feedback'):
                            return False, "", f"Content blocked: {response.prompt_feedback}"
                        return False, "", "No response candidates"
                    
                    # Extract text
                    text = response.text
                    return True, text, ""
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # Check for rate limit
                    if '429' in error_msg or 'quota' in error_msg.lower():
                        wait_time = 2 ** attempt
                        print(f"[Gemini] Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    # Check for safety filter
                    if 'safety' in error_msg.lower() or 'blocked' in error_msg.lower():
                        return False, "", f"Content blocked by safety filters: {error_msg}"
                    
                    # Other errors
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    
                    return False, "", error_msg
            
            return False, "", "Failed after all retries"
        
        except Exception as e:
            return False, "", f"Gemini error: {str(e)}"
    
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
        Generate text with image using Gemini.
        
        Args:
            prompt: User prompt
            image: PIL Image
            model: Model name
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            max_retries: Number of retry attempts
            
        Returns:
            Tuple of (success, response_text, error_message)
        """
        if not self.supports_vision(model):
            return False, "", f"Model {model} does not support vision"
        
        try:
            # Build generation config
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
            )
            
            # Create model instance
            model_instance = genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config,
                system_instruction=system_message if system_message else None
            )
            
            # Retry loop
            for attempt in range(max_retries):
                try:
                    # Build content with image
                    content = [prompt, image]
                    
                    # Generate content
                    response = model_instance.generate_content(content)
                    
                    # Check for blocked content
                    if not response.candidates:
                        if hasattr(response, 'prompt_feedback'):
                            return False, "", f"Content blocked: {response.prompt_feedback}"
                        return False, "", "No response candidates"
                    
                    # Extract text
                    text = response.text
                    return True, text, ""
                
                except Exception as e:
                    error_msg = str(e)
                    
                    # Check for rate limit
                    if '429' in error_msg or 'quota' in error_msg.lower():
                        wait_time = 2 ** attempt
                        print(f"[Gemini] Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    
                    # Check for safety filter
                    if 'safety' in error_msg.lower() or 'blocked' in error_msg.lower():
                        return False, "", f"Content blocked by safety filters: {error_msg}"
                    
                    # Other errors
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    
                    return False, "", error_msg
            
            return False, "", "Failed after all retries"
        
        except Exception as e:
            return False, "", f"Gemini error: {str(e)}"
