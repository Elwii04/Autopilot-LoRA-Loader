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
        
        # Quick check: report catalog status
        lora_dirs = lora_catalog.get_lora_directories()
        if lora_dirs:
            # Recursively find all LoRA files in all directories (matching the scan behavior)
            lora_files = []
            for lora_dir in lora_dirs:
                if lora_dir.exists():
                    lora_files.extend(list(lora_dir.rglob("*.safetensors")))
            
            # Report status
            indexed_count = sum(1 for entry in lora_catalog.catalog.values() if entry.get('indexed_by_llm', False))
            total_count = len(lora_catalog.catalog)
            total_files = len(lora_files)
            
            print(f"[Debug] Found {len(lora_dirs)} LoRA path(s)")
            for i, lora_dir in enumerate(lora_dirs, 1):
                dir_count = len(list(lora_dir.rglob("*.safetensors"))) if lora_dir.exists() else 0
                print(f"[Debug]   Path {i}: {lora_dir} ({dir_count} files)")
            print(f"[Debug] Total: {total_files} .safetensors files")
            print(f"[Debug] Catalog has {total_count} entries")
            print(f"[Debug] Indexed by LLM: {indexed_count}")
            
            if indexed_count > 0:
                print(f"\033[92m⚡ Autopilot LoRA: {indexed_count}/{total_files} LoRA(s) fully indexed\033[0m")
            else:
                print(f"\033[33m⚡ Autopilot LoRA: {total_files} LoRA(s) available (0 indexed)\033[0m")
        
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
