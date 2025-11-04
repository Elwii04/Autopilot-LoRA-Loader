"""
Civitai API integration utilities
Fetches LoRA metadata from Civitai using SHA256 hash lookup.
"""
import json
import re
import time
from html import unescape
from pathlib import Path
from statistics import median
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

import requests


CIVITAI_API_BASE = "https://civitai.com/api/v1"
CACHE_DIR = Path(__file__).parent.parent / 'data' / 'civitai_cache'
IMAGE_CACHE_DIR = Path(__file__).parent.parent / 'data' / 'civitai_images'


def ensure_cache_dir():
    """Ensure the Civitai cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def ensure_image_cache_dir():
    """Ensure the Civitai image cache directory exists."""
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def strip_html_to_text(html: Optional[str]) -> str:
    """Convert HTML content to plain text."""
    if not html:
        return ""

    text = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"<\s*p\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)

    # Normalize whitespace and collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def is_video_url(url: Optional[str]) -> bool:
    """Return True if URL points to a video file."""
    if not url:
        return False
    path = urlparse(url).path.lower()
    return path.endswith(".mp4") or path.endswith(".webm")


def extract_prompt_from_meta(meta: Dict[str, Any]) -> Tuple[str, str]:
    """Extract prompt and negative prompt strings from image metadata."""
    prompt = (
        meta.get("prompt")
        or meta.get("Prompt")
        or ""
    )
    negative = (
        meta.get("negativePrompt")
        or meta.get("Negative prompt")
        or meta.get("Negative Prompt")
        or ""
    )

    if not prompt:
        parameters = meta.get("parameters") or meta.get("Parameters")
        if isinstance(parameters, str) and "Negative prompt:" in parameters:
            try:
                before_neg, after_neg = parameters.split("Negative prompt:", 1)
                prompt = before_neg.strip()
                if "Steps:" in after_neg:
                    negative = after_neg.split("Steps:", 1)[0].strip()
                else:
                    negative = after_neg.strip()
            except ValueError:
                pass

    return prompt.strip(), negative.strip()


def extract_usage_tips(description_text: str) -> str:
    """
    Extract usage tips or recommended strengths from description text.
    Looks for lines mentioning weight, strength, trigger, or usage guidance.
    """
    if not description_text:
        return ""

    keywords = ("recommend", "recommended", "strength", "weight", "trigger", "tip", "use at", "usage")
    tips: List[str] = []

    for line in description_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(keyword in lower for keyword in keywords):
            tips.append(stripped)
        if len(tips) >= 4:
            break

    return "\n".join(tips)


def collect_resource_weights(resources: Any, version_id: Optional[int]) -> List[float]:
    """
    Collect LoRA weight values from image metadata resources.
    Filters entries referencing the current model version id.
    """
    if not isinstance(resources, list):
        return []

    weights: List[float] = []
    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "lora":
            continue
        if version_id and res.get("modelVersionId") not in (version_id, str(version_id)):
            continue
        weight = res.get("weight")
        if weight is None:
            continue
        try:
            weights.append(float(weight))
        except (TypeError, ValueError):
            continue

    return weights


def sanitize_cache_key(text: str) -> str:
    """Sanitize text to use as filesystem-friendly cache key."""
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', text)
    return safe[:80] if len(safe) > 80 else safe


def download_civitai_image(
    url: str,
    cache_key: str,
    index: int,
    timeout: float = 30.0
) -> Optional[Path]:
    """
    Download a Civitai gallery image and cache it locally.
    
    Args:
        url: Image URL
        cache_key: Identifier (e.g., model hash) used for directory name
        index: Image sequence number (1-based)
        timeout: HTTP timeout
        
    Returns:
        Path to cached image or None on failure
    """
    if not url:
        return None
    
    ensure_image_cache_dir()
    safe_key = sanitize_cache_key(cache_key or "default")
    target_dir = IMAGE_CACHE_DIR / safe_key
    target_dir.mkdir(parents=True, exist_ok=True)
    
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.webp'}:
        ext = '.jpg'
    
    file_path = target_dir / f"{index:02d}{ext}"
    if file_path.exists():
        return file_path
    
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            print(f"[Civitai] Failed to download image {url} (HTTP {response.status_code})")
            return None
        file_path.write_bytes(response.content)
        return file_path
    except requests.RequestException as exc:
        print(f"[Civitai] Error downloading image {url}: {exc}")
    except Exception as exc:
        print(f"[Civitai] Unexpected error saving image {url}: {exc}")
    
    return None


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


def _request_json_with_retries(
    url: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    timeout: float = 15.0
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
    """
    Perform a GET request with retries.
    
    Returns:
        Tuple (success, data, http_status)
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            status = response.status_code
            
            if status == 200:
                return True, response.json(), status
            
            if status == 404:
                return False, None, status
            
            if status == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"[Civitai] Rate limited ({url}), waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            print(f"[Civitai] HTTP {status} for {url}")
            return False, None, status
        
        except requests.RequestException as exc:
            print(f"[Civitai] Request error for {url} (attempt {attempt + 1}/{max_retries}): {exc}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False, None, None
    
    return False, None, None


def fetch_model_version_by_id(
    version_id: int,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Optional[Dict[str, Any]]:
    """Fetch Civitai model version details by version id."""
    url = f"{CIVITAI_API_BASE}/model-versions/{version_id}"
    success, data, status = _request_json_with_retries(url, max_retries, retry_delay)
    if success:
        return data
    if status == 404:
        print(f"[Civitai] Version not found: {version_id}")
    return None


def fetch_model_by_id(
    model_id: int,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Optional[Dict[str, Any]]:
    """Fetch Civitai model details by model id."""
    url = f"{CIVITAI_API_BASE}/models/{model_id}"
    success, data, status = _request_json_with_retries(url, max_retries, retry_delay)
    if success:
        return data
    if status == 404:
        print(f"[Civitai] Model not found: {model_id}")
    return None


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
    
    resolve_url = f"{CIVITAI_API_BASE}/model-versions/by-hash/{sha256_hash}"
    success, data, status = _request_json_with_retries(resolve_url, max_retries, retry_delay, timeout=10.0)
    
    if not success:
        if status == 404:
            marker = {'error': 'not_found', 'hash': sha256_hash}
            save_civitai_cache(sha256_hash, marker)
            return None
        return None
    
    version_data = data or {}
    version_data['_resolved_hash'] = sha256_hash
    
    version_id = version_data.get('id')
    model_id = version_data.get('modelId')
    if not model_id and isinstance(version_data.get('model'), dict):
        model_id = version_data['model'].get('id')
    
    # Refresh version payload via canonical endpoint for full gallery metadata
    if version_id:
        fetched_version = fetch_model_version_by_id(version_id, max_retries, retry_delay)
        if fetched_version:
            fetched_version['_resolved_hash'] = sha256_hash
            version_data = fetched_version
            if not model_id:
                model_id = version_data.get('modelId')
    
    # Attach full model metadata
    if model_id:
        model_payload = fetch_model_by_id(model_id, max_retries, retry_delay)
        if model_payload:
            version_data['model'] = model_payload
    
    save_civitai_cache(sha256_hash, version_data)
    return version_data


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
    
    extracted: Dict[str, Any] = {}
    
    model_info = civitai_data.get('model')
    if not isinstance(model_info, dict):
        model_info = {}
    
    # Model name
    model_name = model_info.get('name')
    if isinstance(model_name, str) and model_name.strip():
        extracted['model_name'] = model_name.strip()
    
    # Version name
    version_name = civitai_data.get('name')
    if isinstance(version_name, str) and version_name.strip():
        extracted['version_name'] = version_name.strip()
    
    # Display name (combine model + version)
    display_parts: List[str] = []
    if extracted.get('model_name'):
        display_parts.append(extracted['model_name'])
    if extracted.get('version_name') and extracted['version_name'] != extracted.get('model_name'):
        display_parts.append(extracted['version_name'])
    extracted['display_name'] = ' - '.join(display_parts) if display_parts else 'Unknown'
    
    # Base model
    base_model = civitai_data.get('baseModel')
    if isinstance(base_model, str) and base_model.strip():
        extracted['base_model'] = base_model.strip()
    
    # Trained words / trigger words
    trained_words = civitai_data.get('trainedWords')
    if isinstance(trained_words, list):
        extracted['trained_words'] = [
            w.strip() for w in trained_words
            if isinstance(w, str) and w.strip()
        ]
    else:
        extracted['trained_words'] = []
    
    # Descriptions
    version_desc_html = civitai_data.get('description')
    model_desc_html = model_info.get('description')
    
    version_desc = strip_html_to_text(version_desc_html)
    model_desc = strip_html_to_text(model_desc_html)
    
    if version_desc:
        extracted['version_description'] = version_desc
    if model_desc:
        extracted['model_description'] = model_desc
    
    description_parts: List[str] = []
    if version_desc:
        description_parts.append(version_desc)
    if model_desc and model_desc not in description_parts:
        description_parts.append(model_desc)
    extracted['description'] = "\n\n".join(description_parts)
    
    # Tags (from model)
    tags = model_info.get('tags')
    if isinstance(tags, list):
        cleaned_tags: List[str] = []
        seen: set[str] = set()
        for tag in tags:
            if not isinstance(tag, str):
                continue
            stripped = tag.strip()
            if not stripped or stripped in seen:
                continue
            seen.add(stripped)
            cleaned_tags.append(stripped)
        extracted['tags'] = cleaned_tags
    else:
        extracted['tags'] = []
    
    # Images (sample images with prompts)
    images_data: List[Dict[str, Any]] = []
    strength_samples: List[float] = []
    images = civitai_data.get('images')
    version_id = civitai_data.get('id')
    
    if isinstance(images, list):
        for img in images:
            if len(images_data) >= 5:
                break
            if not isinstance(img, dict):
                continue
            url = img.get('url')
            if not isinstance(url, str) or not url or is_video_url(url):
                continue
            meta = img.get('meta') or {}
            if not isinstance(meta, dict):
                meta = {}
            prompt, negative = extract_prompt_from_meta(meta)
            strength_samples.extend(collect_resource_weights(meta.get('resources'), version_id))
            images_data.append({
                'url': url,
                'width': img.get('width'),
                'height': img.get('height'),
                'prompt': prompt,
                'negative_prompt': negative
            })
    extracted['images'] = images_data
    
    if strength_samples:
        extracted['suggested_strength'] = round(float(median(strength_samples)), 4)
    
    # Download URL
    download_url = civitai_data.get('downloadUrl')
    if isinstance(download_url, str) and download_url:
        extracted['download_url'] = download_url
    
    # Civitai page URL
    model_id = model_info.get('id')
    if model_id:
        extracted['civitai_url'] = f"https://civitai.com/models/{model_id}"
    
    # Version ID
    if version_id:
        extracted['version_id'] = version_id
    
    # Stats (optional)
    stats = civitai_data.get('stats')
    if isinstance(stats, dict):
        extracted['download_count'] = stats.get('downloadCount', 0)
        extracted['rating'] = stats.get('rating', 0)
    
    # Usage tips inferred from description text
    usage_tips = extract_usage_tips(extracted.get('description', ''))
    if usage_tips:
        extracted['usage_tips'] = usage_tips
    
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
    
    meta = extract_civitai_metadata(civitai_data)
    if not meta:
        return ""
    
    parts: List[str] = []
    
    display_name = meta.get('display_name')
    if display_name:
        parts.append(f"Model: {display_name}")
    
    base_model = meta.get('base_model')
    if base_model:
        parts.append(f"Base Model: {base_model}")
    
    trained_words = meta.get('trained_words') or []
    if trained_words:
        parts.append("Trained Words: " + ', '.join(trained_words))
    
    tags = meta.get('tags') or []
    if tags:
        parts.append("Tags: " + ', '.join(tags[:10]))
    
    description = meta.get('description', '')
    if description:
        trimmed = description.strip()
        if len(trimmed) > 1200:
            trimmed = trimmed[:1200] + "..."
        parts.append(f"Description:\n{trimmed}")
    
    usage_tips = meta.get('usage_tips')
    if usage_tips:
        parts.append(f"Usage Tips:\n{usage_tips}")
    
    suggested_strength = meta.get('suggested_strength')
    if suggested_strength is not None:
        parts.append(f"Suggested Strength: {suggested_strength}")
    
    images = meta.get('images') or []
    if images:
        image_lines: List[str] = ["Sample Images (creator gallery):"]
        for idx, img in enumerate(images, 1):
            prompt = img.get('prompt') or ""
            negative = img.get('negative_prompt') or ""
            image_lines.append(f"{idx}. Prompt: {prompt if prompt else '[missing prompt]'}")
            if negative:
                image_lines.append(f"   Negative: {negative}")
            image_lines.append(f"   URL: {img.get('url')}")
        parts.append("\n".join(image_lines))
    
    return '\n\n'.join(parts)
