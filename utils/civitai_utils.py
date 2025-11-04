"""
Civitai API integration utilities
Fetches LoRA metadata from Civitai using SHA256 hash lookup.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests


CIVITAI_API_BASE = "https://civitai.com/api/v1"
CACHE_DIR = Path(__file__).parent.parent / 'data' / 'civitai_cache'


def ensure_cache_dir():
    """Ensure the Civitai cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_civitai_data(sha256_hash: str) -> Optional[Dict[str, Any]]:
    """
    Get cached Civitai data for a hash.
    
    Args:
        sha256_hash: SHA256 hash (with or without 'sha256:' prefix)
        
    Returns:
        Cached data or None
    """
    ensure_cache_dir()
    
    # Remove prefix if present
    if sha256_hash.startswith('sha256:'):
        sha256_hash = sha256_hash[7:]
    
    cache_file = CACHE_DIR / f"{sha256_hash}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Civitai] Error reading cache file: {e}")
    
    return None


def save_civitai_cache(sha256_hash: str, data: Dict[str, Any]):
    """
    Save Civitai data to cache.
    
    Args:
        sha256_hash: SHA256 hash (with or without 'sha256:' prefix)
        data: Data to cache
    """
    ensure_cache_dir()
    
    # Remove prefix if present
    if sha256_hash.startswith('sha256:'):
        sha256_hash = sha256_hash[7:]
    
    cache_file = CACHE_DIR / f"{sha256_hash}.json"
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Civitai] Error saving cache: {e}")


def fetch_civitai_by_hash(
    sha256_hash: str,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Fetch model version data from Civitai by SHA256 hash.
    
    Args:
        sha256_hash: SHA256 hash (with or without 'sha256:' prefix)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Civitai model version data or None if not found
    """
    # Check cache first
    cached = get_cached_civitai_data(sha256_hash)
    if cached:
        return cached
    
    # Remove prefix if present
    if sha256_hash.startswith('sha256:'):
        sha256_hash = sha256_hash[7:]
    
    url = f"{CIVITAI_API_BASE}/model-versions/by-hash/{sha256_hash}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Save to cache
                save_civitai_cache(sha256_hash, data)
                return data
            
            elif response.status_code == 404:
                # Not found - save empty marker to avoid repeated requests
                marker = {'error': 'not_found', 'hash': sha256_hash}
                save_civitai_cache(sha256_hash, marker)
                return None
            
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait_time = retry_delay * (2 ** attempt)
                print(f"[Civitai] Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            else:
                print(f"[Civitai] HTTP {response.status_code} for hash {sha256_hash[:8]}...")
                
        except requests.RequestException as e:
            print(f"[Civitai] Request error (attempt {attempt + 1}/{max_retries}): {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return None


def extract_civitai_metadata(civitai_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract useful metadata from Civitai API response.
    
    Args:
        civitai_data: Raw Civitai API response
        
    Returns:
        Extracted metadata dictionary
    """
    if not civitai_data or 'error' in civitai_data:
        return {}
    
    extracted = {}
    
    # Model name
    if 'model' in civitai_data and 'name' in civitai_data['model']:
        extracted['model_name'] = civitai_data['model']['name']
    
    # Version name
    if 'name' in civitai_data:
        extracted['version_name'] = civitai_data['name']
    
    # Display name (combine model + version)
    display_parts = []
    if 'model_name' in extracted:
        display_parts.append(extracted['model_name'])
    if 'version_name' in extracted and extracted['version_name'] != extracted.get('model_name'):
        display_parts.append(extracted['version_name'])
    extracted['display_name'] = ' - '.join(display_parts) if display_parts else 'Unknown'
    
    # Base model
    if 'baseModel' in civitai_data:
        extracted['base_model'] = civitai_data['baseModel']
    
    # Trained words / trigger words
    trained_words = []
    if 'trainedWords' in civitai_data and isinstance(civitai_data['trainedWords'], list):
        trained_words = [w for w in civitai_data['trainedWords'] if w]
    extracted['trained_words'] = trained_words
    
    # Description
    if 'description' in civitai_data:
        extracted['description'] = civitai_data['description']
    elif 'model' in civitai_data and 'description' in civitai_data['model']:
        extracted['description'] = civitai_data['model']['description']
    
    # Tags (from model)
    tags = []
    if 'model' in civitai_data and 'tags' in civitai_data['model']:
        tags = civitai_data['model']['tags']
    extracted['tags'] = tags
    
    # Images (sample images)
    images = []
    if 'images' in civitai_data and isinstance(civitai_data['images'], list):
        for img in civitai_data['images'][:5]:  # Max 5 images
            if 'url' in img:
                images.append({
                    'url': img['url'],
                    'width': img.get('width'),
                    'height': img.get('height')
                })
    extracted['images'] = images
    
    # Download URL
    if 'downloadUrl' in civitai_data:
        extracted['download_url'] = civitai_data['downloadUrl']
    
    # Civitai page URL
    if 'model' in civitai_data and 'id' in civitai_data['model']:
        model_id = civitai_data['model']['id']
        extracted['civitai_url'] = f"https://civitai.com/models/{model_id}"
    
    # Version ID
    if 'id' in civitai_data:
        extracted['version_id'] = civitai_data['id']
    
    # Stats (optional)
    if 'stats' in civitai_data:
        stats = civitai_data['stats']
        extracted['download_count'] = stats.get('downloadCount', 0)
        extracted['rating'] = stats.get('rating', 0)
    
    return extracted


def build_civitai_summary_text(civitai_data: Dict[str, Any]) -> str:
    """
    Build a comprehensive text summary from Civitai data for LLM processing.
    
    Args:
        civitai_data: Raw Civitai API response
        
    Returns:
        Text summary for LLM
    """
    if not civitai_data or 'error' in civitai_data:
        return ""
    
    parts = []
    model_info = civitai_data.get('model')
    if not isinstance(model_info, dict):
        model_info = {}
    
    # Model name
    model_name = model_info.get('name')
    if isinstance(model_name, str) and model_name.strip():
        parts.append(f"Model: {model_name.strip()}")
    
    # Version name
    version_name = civitai_data.get('name')
    if isinstance(version_name, str) and version_name.strip():
        parts.append(f"Version: {version_name.strip()}")
    
    # Base model
    base_model = civitai_data.get('baseModel')
    if isinstance(base_model, str) and base_model.strip():
        parts.append(f"Base Model: {base_model.strip()}")
    
    # Trained words
    trained_words = civitai_data.get('trainedWords')
    if isinstance(trained_words, list) and trained_words:
        words = ', '.join([w for w in trained_words if isinstance(w, str) and w.strip()])
        if words:
            parts.append(f"Trained Words: {words}")
    
    # Description
    description = civitai_data.get('description')
    if isinstance(description, str) and description.strip():
        parts.append(f"Description: {description.strip()[:500]}")
    else:
        model_desc = model_info.get('description')
        if isinstance(model_desc, str) and model_desc.strip():
            parts.append(f"Description: {model_desc.strip()[:500]}")
    
    # Tags
    model_tags = model_info.get('tags')
    if isinstance(model_tags, list) and model_tags:
        tag_list = [t for t in model_tags if isinstance(t, str) and t.strip()]
        if tag_list:
            tags = ', '.join(tag_list[:10])
            parts.append(f"Tags: {tags}")
    
    return '\n'.join(parts)
