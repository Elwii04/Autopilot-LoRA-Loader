"""
Startup checks for Autopilot LoRA Loader
Performs minimal initialization: check for new LoRAs and verify API availability
"""
import os
from pathlib import Path

def startup_check():
    """Perform startup checks with minimal console output"""
    try:
        from .utils.lora_catalog import lora_catalog
        from .utils.config_manager import config
        
        # Check for new LoRAs in folder
        lora_folder = lora_catalog.lora_folder
        if lora_folder.exists():
            lora_files = list(lora_folder.glob("*.safetensors")) + list(lora_folder.glob("*.ckpt"))
            catalog_data = lora_catalog._load_catalog()
            indexed_count = len(catalog_data.get("loras", []))
            
            new_count = len(lora_files) - indexed_count
            if new_count > 0:
                print(f"\033[33m⚡ Autopilot LoRA: {new_count} new LoRA(s) detected (run indexing to catalog)\033[0m")
            elif indexed_count > 0:
                print(f"\033[92m⚡ Autopilot LoRA: {indexed_count} LoRA(s) indexed\033[0m")
        
        # Quick API check (just verify keys exist, don't make actual API calls)
        api_status = []
        if config.groq_api_key and config.groq_api_key != "your_groq_api_key_here":
            api_status.append("Groq✓")
        if config.gemini_api_key and config.gemini_api_key != "your_gemini_api_key_here":
            api_status.append("Gemini✓")
        
        if api_status:
            print(f"\033[34m⚡ Autopilot LoRA: APIs: {', '.join(api_status)}\033[0m")
        else:
            print("\033[33m⚡ Autopilot LoRA: No API keys configured (check .env)\033[0m")
            
    except Exception as e:
        print(f"\033[91m⚡ Autopilot LoRA: Startup check failed: {str(e)}\033[0m")

# Run startup check when module is imported
startup_check()
