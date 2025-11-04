"""
Base Model Mapping
Maps various base model names to standardized model identifiers for LoRA compatibility.
"""
from typing import Optional, List, Set


# Base model definitions with their alternative names/identifiers
BASE_MODELS = {
    'Aura Flow': ['aura', 'aura flow', 'aura-flow', 'auraflow'],
    'Chroma': ['chroma'],
    'CogVideoX': ['cogvideo', 'cogvideox', 'cog video', 'cog video x', 'cogvideox-2b', 'cogvideox-5b'],
    'Flux .1 S': ['flux s', 'flux.1 s', 'flux-s', 'flux.1s', 'flux1s', 'flux .1 s', 'flux schnell'],
    'Flux .1 D': ['flux d', 'flux.1 d', 'flux-d', 'flux.1d', 'flux1d', 'flux .1 d', 'flux dev', 'flux-dev'],
    'Flux .1 Krea': ['flux krea', 'flux.1 krea', 'flux-krea', 'flux.1krea', 'flux1krea', 'flux .1 krea'],
    'Flux .1 Kontext': ['flux kontext', 'flux.1 kontext', 'flux-kontext', 'flux.1kontext', 'flux1kontext', 'flux .1 kontext'],
    'HiDream': ['hidream', 'hi dream', 'hi-dream'],
    'Hunyuan 1': ['hunyuan', 'hunyuan 1', 'hunyuan1', 'hunyuan dit', 'hunyuan-dit', 'hunyuandit'],
    'Hunyuan Video': ['hunyuan video', 'hunyuan-video', 'hunyuanvideo'],
    'Illustrious': ['illustrious'],
    'Kolors': ['kolors', 'kolor'],
    'LTXV': ['ltx', 'ltxv', 'ltx video', 'ltx-video', 'ltxvideo'],
    'Lumina': ['lumina', 'lumina-text2img'],
    'Mochi': ['mochi', 'mochi 1', 'mochi1'],
    'NoobAI': ['noobai', 'noob ai', 'noob-ai'],
    'Other': ['other', 'unknown', 'custom'],
    'PixArt α': ['pixart', 'pix art', 'pix-art', 'pixart-alpha', 'pixart alpha', 'pixartα'],
    'PixArt Σ': ['pixart sigma', 'pixart-sigma', 'pixartσ', 'pixart σ'],
    'Pony V6': ['pony', 'pony diffusion', 'pony-diffusion', 'pony v6', 'ponyv6', 'pony-v6', 'pony diffusion v6'],
    'Pony V7': ['pony v7', 'ponyv7', 'pony-v7', 'pony diffusion v7'],
    'Qwen Image': ['qwen', 'qwen image', 'qwen-image', 'qwen2-image', 'qwen-vl', 'qwen-vl', 'qwen image'],
    'Qwen-Image-Edit': ['qwen image edit', 'qwen-image-edit', 'qwenimageedit', 'qwen-edit', 'qwen edit'],
    'SD 1.4': ['sd 1.4', 'sd1.4', 'sd14', 'stable diffusion 1.4', 'stablediffusion 1.4'],
    'SD 1.5': ['sd 1.5', 'sd1.5', 'sd15', 'stable diffusion 1.5', 'stablediffusion 1.5', 'sd 1.5 base'],
    'SD 1.5 LCM': ['sd 1.5 lcm', 'sd1.5 lcm', 'sd15 lcm', 'sd1.5lcm', 'sd 1.5-lcm'],
    'SD 1.5 Hyper': ['sd 1.5 hyper', 'sd1.5 hyper', 'sd15 hyper', 'sd1.5hyper', 'sd 1.5-hyper'],
    'SD 2.0': ['sd 2', 'sd2', 'sd 2.0', 'sd2.0', 'sd20', 'stable diffusion 2', 'stable diffusion 2.0'],
    'SD 2.1': ['sd 2.1', 'sd2.1', 'sd21', 'stable diffusion 2.1', 'stablediffusion 2.1'],
    'SDXL 1.0': ['sdxl', 'sd xl', 'sd-xl', 'sdxl 1.0', 'sdxl1.0', 'stable diffusion xl', 'stable diffusion xl 1.0'],
    'SDXL Lightning': ['sdxl lightning', 'sdxl-lightning', 'sdxl lightning 1.0'],
    'SDXL Hyper': ['sdxl hyper', 'sdxl-hyper', 'sdxl turbo', 'sdxl-turbo'],
    'Wan 1.3B t2v': ['wan 1.3b', 'wan1.3b', 'wan 1.3b t2v', 'wan-1.3b', 'wan-1.3b-t2v', 'wan video 1.3b'],
    'Wan 2.1 14B t2v': ['wan 1.4b', 'wan1.4b', 'wan 14b', 'wan14b', 'wan-14b', 'wan-1.4b', 'wan video 14b', 'wan video 1.4b'],
    'Wan 2.1 14B i2v 480p': ['wan 1.4b 480p', 'wan 14b 480p', 'wan14b 480p', 'wan-14b-480p', 'wan 1.4b i2v 480p'],
    'Wan 2.1 14B i2v 720p': ['wan 1.4b 720p', 'wan 14b 720p', 'wan14b 720p', 'wan-14b-720p', 'wan 1.4b i2v 720p'],
    'Wan 2.2 TI2V-5B': ['wan 2.2 5b', 'wan2.2-5b', 'wan 2.2 ti2v', 'wan-2.2-ti2v-5b', 'wan 2.2 text-image 5b'],
    'Wan 2.2 I2V-A14B': ['wan 2.2 i2v', 'wan2.2 i2v', 'wan-2.2-i2v', 'wan 2.2 i2v a14b', 'wan 2.2 14b'],
    'Wan 2.2 T2V-A14B': ['wan 2.2 t2v a14b', 'wan2.2 t2v a14b', 'wan 2.2 t2v 14b'],
    'Wan 2.5 T2V': ['wan 2.5', 'wan2.5', 'wan 2.5 t2v', 'wan-2.5', 'wan-2.5-t2v', 'wan 2.5 text'],
    'Wan 2.5 I2V': ['wan 2.5 i2v', 'wan2.5 i2v', 'wan-2.5-i2v', 'wan 2.5 image'],
}


class BaseModelMapper:
    """Handles base model name normalization and mapping."""
    
    def __init__(self):
        """Initialize the base model mapper with model definitions."""
        self.models = BASE_MODELS
        
        # Create reverse lookup: normalized_name -> model
        self.name_to_model = {}
        for model, names in self.models.items():
            for name in names:
                self.name_to_model[name.lower()] = model
    
    def normalize_to_model(self, base_model_name: str) -> str:
        """
        Normalize a base model name to its standard model identifier.
        
        Args:
            base_model_name: Raw base model name from metadata
            
        Returns:
            Normalized model name or 'Other' if no match
        """
        if not base_model_name:
            return 'Other'
        
        # Clean and lowercase
        clean_name = base_model_name.strip().lower()
        
        # Direct lookup
        if clean_name in self.name_to_model:
            return self.name_to_model[clean_name]
        
        # Fuzzy matching: check if any model keyword is in the name
        for model, keywords in self.models.items():
            for keyword in keywords:
                if keyword in clean_name:
                    return model
        
        # No match found
        return 'Other'
    
    def get_all_models(self) -> List[str]:
        """
        Get list of all known base models.
        
        Returns:
            List of model names
        """
        return sorted(list(self.models.keys()))
    
    def get_models_in_catalog(self, catalog_entries: List[dict]) -> List[str]:
        """
        Get list of base models present in the catalog.
        
        Args:
            catalog_entries: List of LoRA catalog entries
            
        Returns:
            Sorted list of model names present in catalog
        """
        models_found = set()
        
        for entry in catalog_entries:
            base_compat = entry.get('base_compat', [])
            if isinstance(base_compat, list):
                models_found.update(base_compat)
            elif isinstance(base_compat, str):
                models_found.add(base_compat)
        
        # Remove 'Other' if other models exist
        models_list = list(models_found)
        if len(models_list) > 1 and 'Other' in models_list:
            models_list.remove('Other')
        
        return sorted(models_list)
    
    def suggest_model_for_llm(self, civitai_text: str, known_models: List[str]) -> str:
        """
        Suggest a base model for LLM to choose from known models.
        Used during indexing to guide LLM selection.
        
        Args:
            civitai_text: Raw text from Civitai metadata
            known_models: List of models already indexed
            
        Returns:
            Best matching model or 'Other'
        """
        civitai_lower = civitai_text.lower()
        
        # Check each known model
        for model in known_models:
            # Get keywords for this model
            keywords = self.models.get(model, [])
            for keyword in keywords:
                if keyword in civitai_lower:
                    return model
        
        # Check all models (even if not known yet)
        for model, keywords in self.models.items():
            for keyword in keywords:
                if keyword in civitai_lower:
                    return model
        
        return 'Other'
    
    def is_compatible(self, lora_models: List[str], target_model: str) -> bool:
        """
        Check if a LoRA is compatible with the target base model.
        
        Args:
            lora_models: List of models the LoRA supports
            target_model: Target model to check against
            
        Returns:
            True if compatible
        """
        if not lora_models:
            return False
        
        return target_model in lora_models
    
    # Backward compatibility aliases
    def normalize_to_family(self, base_model_name: str) -> str:
        """Alias for normalize_to_model for backward compatibility."""
        return self.normalize_to_model(base_model_name)
    
    def get_all_families(self) -> List[str]:
        """Alias for get_all_models for backward compatibility."""
        return self.get_all_models()
    
    def get_families_in_catalog(self, catalog_entries: List[dict]) -> List[str]:
        """Alias for get_models_in_catalog for backward compatibility."""
        return self.get_models_in_catalog(catalog_entries)
    
    def suggest_family_for_llm(self, civitai_text: str, known_families: List[str]) -> str:
        """Alias for suggest_model_for_llm for backward compatibility."""
        return self.suggest_model_for_llm(civitai_text, known_families)


# Global mapper instance
base_model_mapper = BaseModelMapper()

# Global mapper instance
base_model_mapper = BaseModelMapper()
