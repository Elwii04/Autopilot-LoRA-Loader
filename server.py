"""
Server API endpoints for Autopilot LoRA Loader.
Provides catalog information to the web UI.
"""

import json
from pathlib import Path
from aiohttp import web
import server
from server import PromptServer
from .utils.config_manager import config
from .utils.lora_catalog import lora_catalog
from .utils.indexing_llm import index_with_llm

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
        max_loras_raw = data.get('max_loras', 10)
        try:
            max_loras = int(max_loras_raw)
        except (TypeError, ValueError):
            max_loras = 10
        max_loras = max(1, min(max_loras, 500))
        
        requested_model = data.get('indexing_model')
        if isinstance(requested_model, str) and requested_model.strip():
            indexing_model_value = requested_model.strip()
            # Persist the most recent choice to keep UI and API aligned
            config.set('indexing_model', indexing_model_value)
        else:
            stored_value = config.get('indexing_model', 'groq: llama-3.1-8b-instant')
            indexing_model_value = str(stored_value) if stored_value else 'groq: llama-3.1-8b-instant'
        
        provider_name = 'groq'
        model_name = 'llama-3.1-8b-instant'
        if isinstance(indexing_model_value, str):
            parts = indexing_model_value.split(':', 1)
            if len(parts) == 2:
                maybe_provider = parts[0].strip().lower()
                maybe_model = parts[1].strip()
                if maybe_provider:
                    provider_name = maybe_provider
                if maybe_model:
                    model_name = maybe_model
            else:
                maybe_model = indexing_model_value.strip()
                if maybe_model:
                    model_name = maybe_model
        provider_name = provider_name.lower()
        api_key = config.get_api_key(provider_name)
        api_key_warning_logged = False
        
        print(f"[Autopilot LoRA API] Starting batch indexing (max: {max_loras})")
        print(f"[Autopilot LoRA API] Using indexing model: {provider_name}:{model_name}")
        
        # Get all LoRA files from folder_paths (support multiple directories)
        import folder_paths
        lora_dirs = folder_paths.get_folder_paths("loras") or []
        lora_paths = []
        for dir_path in lora_dirs:
            try:
                path_obj = Path(dir_path)
            except Exception:
                continue
            if path_obj.exists():
                lora_paths.append(path_obj)
        
        if not lora_paths:
            return web.json_response({
                "error": "LoRA folder not found",
                "paths": lora_dirs
            }, status=404)
        
        # Find all safetensors files (deduplicate across directories)
        all_lora_files = []
        seen_paths = set()
        for lora_path in lora_paths:
            for file_path in lora_path.glob("**/*.safetensors"):
                try:
                    resolved = str(file_path.resolve()).lower()
                except Exception:
                    resolved = str(file_path).lower()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                all_lora_files.append(file_path)
        
        print(f"[Autopilot LoRA API] Discovered {len(all_lora_files)} LoRA files across {len(lora_paths)} folder(s)")
        
        # Reload the global catalog from disk to get latest state (including enabled/disabled changes)
        lora_catalog.load_catalog()
        
        def normalize_path(path_value):
            if not path_value:
                return None
            try:
                return str(Path(path_value).resolve()).lower()
            except Exception:
                try:
                    return str(Path(path_value)).lower()
                except Exception:
                    return str(path_value).lower()
        
        # Build quick lookup tables to match catalog entries by path or fallback to filename
        catalog_by_path = {}
        catalog_by_name = {}
        for entry in lora_catalog.catalog.values():
            normalized_entry_path = normalize_path(entry.get('full_path') or entry.get('file_path'))
            if normalized_entry_path:
                catalog_by_path[normalized_entry_path] = entry
            else:
                file_name = (entry.get('file') or '').lower()
                if file_name:
                    catalog_by_name.setdefault(file_name, []).append(entry)
        
        # Find unindexed LoRAs that need to be processed
        # Include LoRAs that:
        # 1. Are not in catalog at all (new LoRAs)
        # 2. Are in catalog, enabled, and haven't been attempted for indexing yet (indexing_attempted is False or missing)
        # Skip LoRAs that:
        # 1. Are disabled (enabled = False)
        # 2. Have already been attempted for indexing (indexing_attempted = True)
        unindexed = []
        for lora_file in all_lora_files:
            normalized_file_path = normalize_path(str(lora_file))
            catalog_entry = None
            if normalized_file_path:
                catalog_entry = catalog_by_path.get(normalized_file_path)
            
            if catalog_entry is None:
                name_key = lora_file.name.lower()
                name_matches = catalog_by_name.get(name_key, [])
                if name_matches:
                    catalog_entry = name_matches[0]
                    if normalized_file_path:
                        catalog_by_path.setdefault(normalized_file_path, catalog_entry)
            
            # Skip if disabled
            if catalog_entry and not catalog_entry.get('enabled', True):
                continue
            
            # Add to unindexed if:
            # 1. Not in catalog at all (new LoRA)
            # 2. In catalog but indexing_attempted is False or missing (not yet tried)
            if catalog_entry is None:
                unindexed.append((lora_file, None))
            elif not catalog_entry.get('indexing_attempted', False):
                unindexed.append((lora_file, catalog_entry))
        
        print(f"[Autopilot LoRA API] Found {len(unindexed)} unindexed LoRAs")
        
        # Limit to max_loras
        to_index = unindexed[:max_loras]
        
        indexed_count = 0
        failed_count = 0
        skipped_due_to_limit = max(0, len(unindexed) - len(to_index))
        skipped_no_data = 0
        
        # Index each LoRA
        for lora_file, _ in to_index:
            try:
                print(f"[Autopilot LoRA API] Indexing: {lora_file.name}")
                
                # First index basic metadata
                file_hash = lora_catalog.index_lora_basic(lora_file)
                
                # Get the entry to check if it has Civitai data
                entry = lora_catalog.get_entry(file_hash)
                
                if entry and entry.get('civitai_text'):
                    # Has Civitai data - process with LLM
                    print(f"[Autopilot LoRA API] Processing with LLM: {lora_file.name}")
                    
                    if not api_key:
                        if not api_key_warning_logged:
                            print(f"[Autopilot LoRA API] No API key for provider '{provider_name}', recording basic metadata only")
                            api_key_warning_logged = True
                        entry['indexed_by_llm'] = False
                        entry['indexing_attempted'] = True
                        indexed_count += 1
                        continue
                    
                    # Get known models
                    known_models = lora_catalog.get_known_base_families()
                    
                    # Call indexing LLM
                    success, extracted, error_msg = index_with_llm(
                        entry['civitai_text'],
                        provider_name,
                        model_name,
                        api_key,
                        known_models,
                        entry.get('file', lora_file.name),
                        image_entries=entry.get('images', []),
                        cache_key=file_hash
                    )
                    
                    if success and extracted:
                        # Mark as indexed with LLM data
                        lora_catalog.mark_llm_indexed(
                            file_hash,
                            extracted['summary'],
                            extracted['trainedWords'],
                            extracted['tags'],
                            entry.get('base_compat', ['Other']),
                            extracted.get('recommendedStrength')
                        )
                        indexed_count += 1
                        print(f"[Autopilot LoRA API] [OK] Indexed with LLM: {lora_file.name}")
                    else:
                        failed_count += 1
                        print(f"[Autopilot LoRA API] [ERR] LLM failed to produce usable JSON: {lora_file.name}")
                        print(f"[Autopilot LoRA API]   Error: {error_msg}")
                        # Do not mark indexing_attempted so we can retry later
                        continue
                else:
                    # No Civitai data - mark as indexing_attempted to prevent re-trying
                    lora_catalog.mark_indexing_attempted(file_hash)
                    skipped_no_data += 1
                    print(f"[Autopilot LoRA API] [SKIP] Skipped (no Civitai data): {lora_file.name}")
                    print(f"[Autopilot LoRA API]   Basic metadata saved, can be edited manually in catalog")
                    
            except Exception as e:
                failed_count += 1
                print(f"[Autopilot LoRA API] [ERR] Error indexing {lora_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save the updated catalog using lora_catalog's save method to persist all changes
        lora_catalog.save_catalog()
        
        return web.json_response({
            "success": True,
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_due_to_limit + skipped_no_data,
            "skipped_due_to_limit": skipped_due_to_limit,
            "skipped_no_data": skipped_no_data,
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

