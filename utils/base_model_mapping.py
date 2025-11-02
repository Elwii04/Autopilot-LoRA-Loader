"""
Base Model Family Normalization
Maps various base model names to standardized families for LoRA compatibility.
"""
from typing import Optional, List, Set


# Base model family definitions
BASE_MODEL_FAMILIES = {
    'Flux-1': [
        'flux', 'flux-1', 'flux.1', 'flux 1', 'flux-dev', 'flux-schnell',
        'flux dev', 'flux schnell', 'flux.1-dev', 'flux.1-schnell',
        'flux krea', 'flux kontext', 'flux-krea', 'flux-kontext'
    ],
    'SD1.x': [
        'sd 1', 'sd1', 'sd 1.4', 'sd1.4', 'sd 1.5', 'sd1.5',
        'stable diffusion 1', 'stable diffusion 1.4', 'stable diffusion 1.5',
        'sd 1.5 lcm', 'sd1.5 lcm', 'sd 1.5 hyper', 'sd1.5 hyper',
        'sd15', 'sd14'
    ],
    'SD2.x': [
        'sd 2', 'sd2', 'sd 2.0', 'sd2.0', 'sd 2.1', 'sd2.1',
        'stable diffusion 2', 'stable diffusion 2.0', 'stable diffusion 2.1',
        'sd20', 'sd21'
    ],
    'SDXL': [
        'sdxl', 'sd xl', 'sd-xl', 'sdxl 1.0', 'sdxl1.0',
        'stable diffusion xl', 'stable diffusion xl 1.0',
        'sdxl lightning', 'sdxl-lightning', 'sdxl turbo', 'sdxl-turbo',
        'sdxl hyper', 'sdxl-hyper'
    ],
    'Qwen-Image': [
        'qwen', 'qwen2', 'qwen 2', 'qwen-image', 'qwen2-image',
        'qwen-vl', 'qwen2-vl'
    ],
    'Wan-Video 1.x': [
        'wan', 'wan 1', 'wan1', 'wan 1.3', 'wan1.3', 'wan 1.3b', 'wan1.3b',
        'wan 14b', 'wan14b', 'wan-1.3b', 'wan-14b'
    ],
    'Wan-Video 2.2': [
        'wan 2.2', 'wan2.2', 'wan 2.2 t2v', 'wan 2.2 i2v',
        'wan-2.2', 'wan-2.2-t2v', 'wan-2.2-i2v',
        'wan 2.2 5b', 'wan2.2-5b'
    ],
    'Wan-Video 2.5': [
        'wan 2.5', 'wan2.5', 'wan 2.5 t2v', 'wan 2.5 i2v',
        'wan-2.5', 'wan-2.5-t2v', 'wan-2.5-i2v'
    ],
    'AuraFlow': [
        'aura', 'aura flow', 'aura-flow', 'auraflow'
    ],
    'PixArt': [
        'pixart', 'pix art', 'pix-art', 'pixart-alpha', 'pixart-sigma'
    ],
    'Kolors': [
        'kolors', 'kolor'
    ],
    'Hunyuan': [
        'hunyuan', 'hunyuan dit', 'hunyuan-dit', 'hunyuandit'
    ],
    'Lumina': [
        'lumina', 'lumina-text2img'
    ],
    'Playground': [
        'playground', 'playground v2', 'playground v2.5', 'playgroundv2'
    ],
    'CogVideoX': [
        'cogvideo', 'cogvideox', 'cog video', 'cog video x',
        'cogvideox-2b', 'cogvideox-5b'
    ],
    'Mochi': [
        'mochi', 'mochi 1'
    ],
    'LTX-Video': [
        'ltx', 'ltx video', 'ltx-video', 'ltxvideo'
    ]
}


class BaseModelMapper:
    """Handles base model name normalization and family mapping."""
    
    def __init__(self):
        """Initialize the base model mapper with family definitions."""
        self.families = BASE_MODEL_FAMILIES
        
        # Create reverse lookup: normalized_name -> family
        self.name_to_family = {}
        for family, names in self.families.items():
            for name in names:
                self.name_to_family[name.lower()] = family
    
    def normalize_to_family(self, base_model_name: str) -> Optional[str]:
        """
        Normalize a base model name to its family.
        
        Args:
            base_model_name: Raw base model name from metadata
            
        Returns:
            Normalized family name or 'Unknown' if no match
        """
        if not base_model_name:
            return 'Unknown'
        
        # Clean and lowercase
        clean_name = base_model_name.strip().lower()
        
        # Direct lookup
        if clean_name in self.name_to_family:
            return self.name_to_family[clean_name]
        
        # Fuzzy matching: check if any family keyword is in the name
        for family, keywords in self.families.items():
            for keyword in keywords:
                if keyword in clean_name:
                    return family
        
        # No match found
        return 'Unknown'
    
    def get_all_families(self) -> List[str]:
        """
        Get list of all known base model families.
        
        Returns:
            List of family names
        """
        return list(self.families.keys())
    
    def get_families_in_catalog(self, catalog_entries: List[dict]) -> List[str]:
        """
        Get list of base model families present in the catalog.
        
        Args:
            catalog_entries: List of LoRA catalog entries
            
        Returns:
            Sorted list of family names present in catalog
        """
        families_found = set()
        
        for entry in catalog_entries:
            base_compat = entry.get('base_compat', [])
            if isinstance(base_compat, list):
                families_found.update(base_compat)
            elif isinstance(base_compat, str):
                families_found.add(base_compat)
        
        # Remove 'Unknown' if other families exist
        families_list = list(families_found)
        if len(families_list) > 1 and 'Unknown' in families_list:
            families_list.remove('Unknown')
        
        return sorted(families_list)
    
    def suggest_family_for_llm(self, civitai_text: str, known_families: List[str]) -> str:
        """
        Suggest a base model family for LLM to choose from known families.
        Used during indexing to guide LLM selection.
        
        Args:
            civitai_text: Raw text from Civitai metadata
            known_families: List of families already indexed
            
        Returns:
            Best matching family or 'Unknown'
        """
        civitai_lower = civitai_text.lower()
        
        # Check each known family
        for family in known_families:
            # Get keywords for this family
            keywords = self.families.get(family, [])
            for keyword in keywords:
                if keyword in civitai_lower:
                    return family
        
        # Check all families (even if not known yet)
        for family, keywords in self.families.items():
            for keyword in keywords:
                if keyword in civitai_lower:
                    return family
        
        return 'Unknown'
    
    def is_compatible(self, lora_families: List[str], target_family: str) -> bool:
        """
        Check if a LoRA is compatible with the target base model family.
        
        Args:
            lora_families: List of families the LoRA supports
            target_family: Target family to check against
            
        Returns:
            True if compatible
        """
        if not lora_families:
            return False
        
        # Special handling for Wan Video versions (cross-compatible)
        wan_families = {'Wan-Video 1.x', 'Wan-Video 2.2', 'Wan-Video 2.5'}
        if target_family in wan_families:
            if any(f in wan_families for f in lora_families):
                return True
        
        return target_family in lora_families


# Global mapper instance
base_model_mapper = BaseModelMapper()
