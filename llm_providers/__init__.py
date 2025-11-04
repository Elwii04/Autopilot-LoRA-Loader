"""
Base LLM Provider Interface
Defines the abstract interface that all LLM providers must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from PIL import Image


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str):
        """
        Initialize the provider with an API key.
        
        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """
        List available models from the provider.
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        model: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> tuple[bool, str, str]:
        """
        Generate text from a text-only prompt.
        
        Args:
            prompt: User prompt
            model: Model name to use
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Tuple of (success, response_text, error_message)
        """
        pass
    
    @abstractmethod
    def generate_with_image(
        self,
        prompt: str,
        image: Image.Image | List[Image.Image],
        model: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> tuple[bool, str, str]:
        """
        Generate text from a prompt with an image (vision models).
        
        Args:
            prompt: User prompt
            image: PIL Image or list of PIL Images
            model: Model name to use (must support vision)
            system_message: Optional system message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Tuple of (success, response_text, error_message)
        """
        pass
    
    def supports_vision(self, model: str) -> bool:
        """
        Check if a model supports vision inputs.
        Default implementation returns False; override in subclasses.
        
        Args:
            model: Model name
            
        Returns:
            True if model supports vision
        """
        return False
