"""
SmartPowerLoRALoader - ComfyUI Custom Node
Automatically selects relevant LoRAs and generates prompts using LLMs.
"""

# Perform startup checks (minimal console output)
from . import startup

# Import node mappings from both nodes
from .nodes.smart_power_lora_loader import NODE_CLASS_MAPPINGS as LOADER_MAPPINGS
from .nodes.smart_power_lora_loader import NODE_DISPLAY_NAME_MAPPINGS as LOADER_DISPLAY_MAPPINGS
from .nodes.lora_manager import NODE_CLASS_MAPPINGS as MANAGER_MAPPINGS
from .nodes.lora_manager import NODE_DISPLAY_NAME_MAPPINGS as MANAGER_DISPLAY_MAPPINGS

# Merge mappings
NODE_CLASS_MAPPINGS = {**LOADER_MAPPINGS, **MANAGER_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**LOADER_DISPLAY_MAPPINGS, **MANAGER_DISPLAY_MAPPINGS}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
