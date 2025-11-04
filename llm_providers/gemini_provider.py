"""
Gemini LLM Provider
Implements Google Gemini API integration using google-generativeai library.
"""
import json
import time
from typing import List, Dict, Any, Optional, Tuple, Union
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
        self._vision_cache: Dict[str, bool] = {}
        
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
    
    def _heuristic_supports_vision(self, model: str) -> bool:
        """Heuristic check for Gemini vision support when API metadata is unavailable."""
        if not model:
            return False
        
        model_lower = model.lower()
        
        if model_lower in {name.lower() for name in GEMINI_VISION_MODELS}:
            return True
        
        non_vision_models = {
            "gemini-pro",
            "gemini-1.0-pro",
            "gemini-1.0-pro-001",
            "gemini-1.0-pro-latest",
        }
        if model_lower in non_vision_models:
            return False
        
        if not model_lower.startswith("gemini-"):
            return False
        
        if "embedding" in model_lower or "textonly" in model_lower:
            return False
        
        vision_keywords = (
            "vision",
            "flash",
            "pro",
            "1.5",
            "2.0",
            "2.1",
            "2.2",
            "2.5",
            "2.6",
        )
        return any(keyword in model_lower for keyword in vision_keywords)
    
    def supports_vision(self, model: str) -> bool:
        """Check if model supports vision (image inputs)."""
        if not model:
            return False
        
        cache_key = model.lower()
        if cache_key in self._vision_cache:
            return self._vision_cache[cache_key]
        
        # First try heuristics to avoid unnecessary API calls
        heuristic_result = self._heuristic_supports_vision(cache_key)
        if heuristic_result:
            self._vision_cache[cache_key] = True
            return True
        
        try:
            api_model_name = model if model.startswith("models/") else f"models/{model}"
            model_info = genai.get_model(api_model_name)
            
            input_modalities = getattr(model_info, "input_modalities", None)
            if input_modalities:
                if any(str(mod).lower() in {"image", "vision", "multimodal"} for mod in input_modalities):
                    self._vision_cache[cache_key] = True
                    return True
            
            capabilities = getattr(model_info, "capabilities", {})
            if isinstance(capabilities, dict):
                # Some versions expose capabilities as { "multimodal": True } etc.
                for key, value in capabilities.items():
                    key_lower = str(key).lower()
                    if key_lower in {"multimodal", "vision"} and bool(value):
                        self._vision_cache[cache_key] = True
                        return True
                    if key_lower == "modalities" and isinstance(value, list):
                        if any(str(mod).lower() in {"image", "vision", "multimodal"} for mod in value):
                            self._vision_cache[cache_key] = True
                            return True
            
            supported_methods = getattr(model_info, "supported_generation_methods", [])
            if supported_methods:
                for method in supported_methods:
                    if isinstance(method, str) and "image" in method.lower():
                        self._vision_cache[cache_key] = True
                        return True
            
        except Exception as exc:
            print(f"[Gemini] Warning: Could not verify vision support for {model}: {exc}")
        
        self._vision_cache[cache_key] = heuristic_result
        return heuristic_result
    
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
        image: Union[Image.Image, List[Image.Image]],
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
            image: PIL Image or list of PIL Images
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
            image_list = image if isinstance(image, list) else [image]
            
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
                    content: List[Any] = [prompt]
                    content.extend(image_list)
                    
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
