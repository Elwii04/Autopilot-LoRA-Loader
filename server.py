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
    """Update information for a specific LoRA."""
    try:
        data = await request.json()
        file_hash = data.get('file_hash')
        
        if not file_hash:
            return web.json_response({"error": "No file_hash specified"}, status=400)
        
        catalog = load_catalog()
        
        if file_hash not in catalog:
            return web.json_response({"error": "LoRA not found in catalog"}, status=404)
        
        # Update allowed fields
        entry = catalog[file_hash]
        allowed_fields = ['summary', 'trained_words', 'tags', 'default_weight', 'display_name', 'is_character']
        
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
        return web.json_response({"error": str(e)}, status=500)


print("[Autopilot LoRA API] Registered API endpoints:")
print("  - GET /autopilot_lora/catalog")
print("  - GET /autopilot_lora/info?file=<filename>")
print("  - POST /autopilot_lora/update")
