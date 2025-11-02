"""
Model List Fetcher
Fetches and combines available models from all LLM providers.
"""
from typing import List, Tuple
from ..utils.config_manager import config


def fetch_all_available_models() -> Tuple[List[str], List[str]]:
    """
    Fetch all available models from Groq and Gemini.
    
    Returns:
        Tuple of (all_models_list, vision_capable_models_list)
    """
    all_models = []
    vision_models = []
    
    # Try Groq
    try:
        groq_key = config.get_groq_api_key()
        if groq_key:
            from ..llm_providers.groq_provider import GroqProvider
            provider = GroqProvider(groq_key)
            groq_model_list = provider.list_models()
            
            for model in groq_model_list:
                prefixed = f"groq: {model}"
                all_models.append(prefixed)
                
                # Check if vision capable
                if provider.supports_vision(model):
                    vision_models.append(prefixed)
    except Exception as e:
        print(f"[ModelFetcher] Could not fetch Groq models: {e}")
        # Add fallback models
        fallback_groq = [
            "groq: llama-3.1-8b-instant",
            "groq: llama-3.3-70b-versatile",
            "groq: deepseek-r1-distill-llama-70b",
            "groq: gemma2-9b-it"
        ]
        all_models.extend(fallback_groq)
    
    # Try Gemini
    try:
        gemini_key = config.get_gemini_api_key()
        if gemini_key:
            from ..llm_providers.gemini_provider import GeminiProvider
            provider = GeminiProvider(gemini_key)
            gemini_model_list = provider.list_models()
            
            for model in gemini_model_list:
                prefixed = f"gemini: {model}"
                all_models.append(prefixed)
                
                # Check if vision capable
                if provider.supports_vision(model):
                    vision_models.append(prefixed)
    except Exception as e:
        print(f"[ModelFetcher] Could not fetch Gemini models: {e}")
        # Add fallback models
        fallback_gemini = [
            "gemini: gemini-1.5-pro",
            "gemini: gemini-1.5-flash",
            "gemini: gemini-1.5-flash-8b",
            "gemini: gemini-2.0-flash-exp"
        ]
        all_models.extend(fallback_gemini)
        vision_models.extend(fallback_gemini)  # Most Gemini models support vision
    
    # Ensure we have at least some models
    if not all_models:
        all_models = [
            "groq: llama-3.1-8b-instant",
            "gemini: gemini-1.5-flash"
        ]
        vision_models = ["gemini: gemini-1.5-flash"]
    
    return all_models, vision_models


def parse_model_string(model_string: str) -> Tuple[str, str]:
    """
    Parse a prefixed model string into provider and model name.
    
    Args:
        model_string: String like "groq: llama-3.1-8b-instant"
        
    Returns:
        Tuple of (provider_name, model_name)
    """
    if ": " in model_string:
        parts = model_string.split(": ", 1)
        return parts[0].strip(), parts[1].strip()
    
    # Fallback - try to guess provider
    if "gemini" in model_string.lower():
        return "gemini", model_string
    else:
        return "groq", model_string
