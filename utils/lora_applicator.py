"""
LoRA Application Logic
Applies selected LoRAs to MODEL and CLIP using ComfyUI's LoraLoader.
"""
from typing import Any, List, Dict, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import comfy.sd
    from nodes import LoraLoader
    HAS_COMFY = True
except ImportError:
    HAS_COMFY = False
    print("[LoRAApplicator] Warning: ComfyUI modules not available")


def apply_loras_to_model_clip(
    model: Any,
    clip: Any,
    loras_to_apply: List[Dict[str, Any]]
) -> Tuple[Any, Any]:
    """
    Apply LoRAs to model and clip in sequence.
    
    Args:
        model: ComfyUI MODEL object
        clip: ComfyUI CLIP object
        loras_to_apply: List of LoRA catalog entries to apply
        
    Returns:
        Tuple of (modified_model, modified_clip)
    """
    if not HAS_COMFY:
        print("[LoRAApplicator] Error: ComfyUI not available, cannot apply LoRAs")
        return model, clip
    
    if not loras_to_apply:
        print("[LoRAApplicator] No LoRAs to apply")
        return model, clip
    
    current_model = model
    current_clip = clip
    
    # Create LoraLoader instance
    loader = LoraLoader()
    
    for lora_entry in loras_to_apply:
        lora_name = lora_entry['file']
        weight = lora_entry.get('default_weight', 1.0)
        
        # Ensure weight is valid
        if not isinstance(weight, (int, float)):
            weight = 1.0
        
        # Clamp weight to reasonable range
        weight = max(-2.0, min(2.0, weight))
        
        try:
            print(f"[LoRAApplicator] Applying {lora_name} with weight {weight}")
            
            # Apply LoRA (same weight for model and clip)
            result = loader.load_lora(
                model=current_model,
                clip=current_clip,
                lora_name=lora_name,
                strength_model=weight,
                strength_clip=weight
            )
            
            # Unpack result
            current_model, current_clip = result[0], result[1]
            
        except Exception as e:
            print(f"[LoRAApplicator] Error applying {lora_name}: {e}")
            # Continue with other LoRAs even if one fails
    
    return current_model, current_clip
