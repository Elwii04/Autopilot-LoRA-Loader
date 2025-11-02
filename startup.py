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
        from .utils.utils import compute_file_hash, normalize_lora_name
        
        # Auto-populate catalog with ALL LoRAs
        lora_folder = lora_catalog.get_lora_directory()
        if lora_folder and lora_folder.exists():
            lora_files = list(lora_folder.glob("*.safetensors")) + list(lora_folder.glob("*.ckpt"))
            
            # Add any missing LoRAs to catalog (with basic metadata)
            added_count = 0
            for lora_file in lora_files:
                file_hash = compute_file_hash(lora_file)
                
                # If not in catalog, add it with minimal metadata
                if file_hash not in lora_catalog.catalog:
                    lora_catalog.catalog[file_hash] = {
                        'file_hash': file_hash,
                        'file': str(lora_file.name),
                        'full_path': str(lora_file),
                        'display_name': normalize_lora_name(lora_file.name),
                        'sha256': file_hash,
                        'available': True,
                        'summary': '',
                        'trained_words': [],
                        'tags': [],
                        'is_character': False,
                        'enabled': True,  # Default to enabled
                        'base_compat': ['Unknown'],
                        'default_weight': 1.0,
                        'source': {'kind': 'unknown'},
                        'indexed_at': None,
                        'indexed_by_llm': False
                    }
                    added_count += 1
                else:
                    # Mark existing as available
                    lora_catalog.catalog[file_hash]['available'] = True
            
            # Save catalog if we added new LoRAs
            if added_count > 0:
                lora_catalog.save_catalog()
                print(f"\033[33m⚡ Autopilot LoRA: Added {added_count} new LoRA(s) to catalog\033[0m")
            
            # Report status
            indexed_count = sum(1 for entry in lora_catalog.catalog.values() if entry.get('indexed_by_llm', False))
            total_count = len(lora_catalog.catalog)
            
            if indexed_count > 0:
                print(f"\033[92m⚡ Autopilot LoRA: {indexed_count}/{total_count} LoRA(s) fully indexed\033[0m")
            else:
                print(f"\033[33m⚡ Autopilot LoRA: {total_count} LoRA(s) in catalog (0 indexed)\033[0m")
        
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
