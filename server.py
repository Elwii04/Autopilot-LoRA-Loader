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


@PromptServer.instance.routes.get("/autopilot_lora/catalog")
async def get_catalog(request):
    """Return the full LoRA catalog as JSON."""
    try:
        catalog = load_catalog()
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


print("[Autopilot LoRA API] Registered API endpoints:")
print("  - GET /autopilot_lora/catalog")
print("  - GET /autopilot_lora/info?file=<filename>")
