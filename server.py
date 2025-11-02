"""
Server API endpoints for Autopilot LoRA Loader.
Provides catalog information to the web UI.
"""

import os
import json
from pathlib import Path
from aiohttp import web
import server
from server import PromptServer

# Get the directory where this file is located
NODE_DIR = Path(__file__).parent
DATA_DIR = NODE_DIR / "data"
CATALOG_FILE = DATA_DIR / "lora_index.json"


def load_catalog():
    """Load the LoRA catalog from disk."""
    if CATALOG_FILE.exists():
        try:
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Autopilot LoRA API] Error loading catalog: {e}")
            return {}
    return {}


def save_catalog(catalog):
    """Save the LoRA catalog to disk."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Autopilot LoRA API] Error saving catalog: {e}")
        return False


@PromptServer.instance.routes.get("/autopilot_lora/catalog")
async def get_catalog(request):
    """Return the full LoRA catalog as JSON."""
    try:
        catalog = load_catalog()
        # Ensure each entry has file_hash for easy access
        for file_hash, entry in catalog.items():
            if 'file_hash' not in entry:
                entry['file_hash'] = file_hash
        return web.json_response(catalog)
    except Exception as e:
        print(f"[Autopilot LoRA API] Error in /catalog endpoint: {e}")
        return web.json_response({"error": str(e)}, status=500)


@PromptServer.instance.routes.get("/autopilot_lora/info")
async def get_lora_info(request):
    """Return information for a specific LoRA file."""
    try:
        file_name = request.query.get('file', '')
        if not file_name:
            return web.json_response({"error": "No file specified"}, status=400)
        
        catalog = load_catalog()
        
        # Search for the LoRA by filename
        for file_hash, entry in catalog.items():
            if entry.get('file') == file_name:
                # Ensure file_hash is in the entry
                if 'file_hash' not in entry:
                    entry['file_hash'] = file_hash
                return web.json_response(entry)
        
        # Not found in catalog
        return web.json_response({
            "error": "LoRA not found in catalog",
            "file": file_name,
            "indexed": False
        }, status=404)
        
    except Exception as e:
        print(f"[Autopilot LoRA API] Error in /info endpoint: {e}")
        return web.json_response({"error": str(e)}, status=500)


@PromptServer.instance.routes.post("/autopilot_lora/update")
async def update_lora_info(request):
    """Update information for a specific LoRA by file_hash or filename. Creates entry if it doesn't exist."""
    try:
        data = await request.json()
        file_hash = data.get('file_hash')
        file_name = data.get('file_name')
        
        if not file_hash and not file_name:
            return web.json_response({"error": "No file_hash or file_name specified"}, status=400)
        
        catalog = load_catalog()
        
        # Find entry by file_hash or filename
        entry_hash = None
        entry = None
        
        if file_hash:
            # Look up by file_hash directly
            if file_hash in catalog:
                entry_hash = file_hash
                entry = catalog[file_hash]
        
        if not entry:
            # Look up by filename
            for hash_key, cat_entry in catalog.items():
                if cat_entry.get('file') == file_name or cat_entry.get('file_hash') == file_hash:
                    entry_hash = hash_key
                    entry = cat_entry
                    break
        
        # If entry doesn't exist, create minimal entry
        if not entry:
            # Use file_hash if provided, otherwise use filename as temporary key
            entry_hash = file_hash if file_hash else f"temp_{file_name}"
            entry = {
                'file_hash': file_hash if file_hash else entry_hash,
                'file': file_name or '',
                'full_path': '',
                'display_name': (file_name or '').replace('.safetensors', '').replace('_', ' '),
                'available': True,
                'summary': '',
                'trained_words': [],
                'tags': [],
                'enabled': True,
                'base_compat': ['Other'],
                'default_weight': 1.0,
                'source': {'kind': 'unknown'},
                'indexed_at': None,
                'indexed_by_llm': False
            }
            catalog[entry_hash] = entry
        
        # Update allowed fields
        allowed_fields = ['summary', 'trained_words', 'tags', 'default_weight', 'display_name', 'enabled', 'base_compat']
        
        for field in allowed_fields:
            if field in data:
                entry[field] = data[field]
        
        # Save the updated catalog
        if save_catalog(catalog):
            return web.json_response({"success": True, "entry": entry})
        else:
            return web.json_response({"error": "Failed to save catalog"}, status=500)
        
    except Exception as e:
        print(f"[Autopilot LoRA API] Error in /update endpoint: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


@PromptServer.instance.routes.post("/autopilot_lora/index")
async def index_loras_batch(request):
    """Index multiple unindexed LoRAs with a max limit."""
    try:
        data = await request.json()
        max_loras = data.get('max_loras', 10)
        
        print(f"[Autopilot LoRA API] Starting batch indexing (max: {max_loras})")
        
        # Import required modules
        from pathlib import Path
        from .utils.lora_catalog import lora_catalog
        from .utils.indexing_llm import index_with_llm
        
        # Get all LoRA files from folder_paths
        import folder_paths
        lora_folder = folder_paths.get_folder_paths("loras")[0]
        lora_path = Path(lora_folder)
        
        if not lora_path.exists():
            return web.json_response({
                "error": "LoRA folder not found",
                "path": str(lora_path)
            }, status=404)
        
        # Find all safetensors files
        all_lora_files = list(lora_path.glob("**/*.safetensors"))
        
        # Reload the global catalog from disk to get latest state (including enabled/disabled changes)
        lora_catalog.load_catalog()
        
        # Find unindexed LoRAs (those not yet indexed by LLM or not in catalog at all)
        # Also skip disabled LoRAs
        unindexed = []
        for lora_file in all_lora_files:
            # Check if already in catalog
            catalog_entry = None
            for entry in lora_catalog.catalog.values():
                if (entry.get('file') == lora_file.name or 
                    str(lora_file) == entry.get('file_path') or
                    str(lora_file) == entry.get('full_path')):
                    catalog_entry = entry
                    break
            
            # Skip if entry exists but is disabled
            if catalog_entry and not catalog_entry.get('enabled', True):
                continue
            
            # Add to unindexed if:
            # 1. Not in catalog at all (catalog_entry is None)
            # 2. In catalog but indexed_by_llm is None/missing (not yet processed)
            # Skip if indexed_by_llm is True (successfully indexed) or False (tried and failed/no civitai)
            if catalog_entry is None:
                unindexed.append(lora_file)
            elif 'indexed_by_llm' not in catalog_entry or catalog_entry.get('indexed_by_llm') is None:
                unindexed.append(lora_file)
        
        print(f"[Autopilot LoRA API] Found {len(unindexed)} unindexed LoRAs")
        
        # Limit to max_loras
        to_index = unindexed[:max_loras]
        
        indexed_count = 0
        failed_count = 0
        skipped_count = len(unindexed) - len(to_index)
        
        # Index each LoRA
        for lora_file in to_index:
            try:
                print(f"[Autopilot LoRA API] Indexing: {lora_file.name}")
                
                # First index basic metadata
                file_hash = lora_catalog.index_lora_basic(lora_file)
                
                # Get the entry to check if it has Civitai data
                entry = lora_catalog.get_entry(file_hash)
                
                if entry and entry.get('civitai_text'):
                    # Has Civitai data - process with LLM
                    print(f"[Autopilot LoRA API] Processing with LLM: {lora_file.name}")
                    
                    # Get config for LLM settings
                    from .utils.config_manager import config
                    
                    # Get indexing model info
                    indexing_model = config.get('indexing_model', 'groq: llama-3.1-8b-instant')
                    provider_name, model_name = indexing_model.split(': ', 1) if ': ' in indexing_model else ('groq', 'llama-3.1-8b-instant')
                    
                    # Get API key
                    api_key = config.get_api_key(provider_name)
                    
                    if not api_key:
                        print(f"[Autopilot LoRA API] No API key for {provider_name}, marking as indexed without LLM")
                        # Mark as indexed_by_llm = False to prevent re-trying
                        if entry:
                            entry['indexed_by_llm'] = False
                        indexed_count += 1
                        continue
                    
                    # Get known models
                    known_models = lora_catalog.get_known_base_families()
                    
                    # Call indexing LLM
                    from .utils.indexing_llm import index_with_llm as index_llm_func
                    success, extracted, error_msg = index_llm_func(
                        entry['civitai_text'],
                        provider_name,
                        model_name,
                        api_key,
                        known_models
                    )
                    
                    if success and extracted:
                        # Mark as indexed with LLM data
                        lora_catalog.mark_llm_indexed(
                            file_hash,
                            extracted['summary'],
                            extracted['trainedWords'],
                            extracted['tags'],
                            entry.get('base_compat', ['Other'])
                        )
                        indexed_count += 1
                        print(f"[Autopilot LoRA API] ✓ Indexed with LLM: {lora_file.name}")
                    else:
                        # LLM failed - mark as indexed_by_llm = False to prevent re-trying
                        if entry:
                            entry['indexed_by_llm'] = False
                        indexed_count += 1
                        print(f"[Autopilot LoRA API] ✓ Basic indexing only (LLM failed): {lora_file.name}")
                        print(f"[Autopilot LoRA API]   Error: {error_msg}")
                else:
                    # No Civitai data - skip LLM processing but mark as "indexed" to prevent re-trying
                    if entry:
                        entry['indexed_by_llm'] = False  # Mark as processed (won't try again)
                    indexed_count += 1
                    print(f"[Autopilot LoRA API] ⊘ Skipped (no Civitai data): {lora_file.name}")
                    print(f"[Autopilot LoRA API]   Basic metadata saved, can be edited manually in catalog")
                    
            except Exception as e:
                failed_count += 1
                print(f"[Autopilot LoRA API] ✗ Error indexing {lora_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save the updated catalog using lora_catalog's save method to persist all changes
        lora_catalog.save_catalog()
        
        return web.json_response({
            "success": True,
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "total_unindexed": len(unindexed)
        })
        
    except Exception as e:
        print(f"[Autopilot LoRA API] Error in /index endpoint: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


@PromptServer.instance.routes.get("/autopilot_lora/available")
async def get_available_loras(request):
    """Return all available LoRAs from folder_paths (for the chooser)."""
    try:
        import folder_paths
        lora_list = folder_paths.get_filename_list("loras")
        return web.json_response({"loras": lora_list})
    except Exception as e:
        print(f"[Autopilot LoRA API] Error in /available endpoint: {e}")
        return web.json_response({"error": str(e)}, status=500)


print("[Autopilot LoRA API] Registered API endpoints:")
print("  - GET /autopilot_lora/catalog")
print("  - GET /autopilot_lora/info?file=<filename>")
print("  - POST /autopilot_lora/update")
print("  - POST /autopilot_lora/index")
print("  - GET /autopilot_lora/available")

