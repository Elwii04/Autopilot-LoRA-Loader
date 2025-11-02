"""
Utility functions for SmartPowerLoRALoader
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import numpy as np
from PIL import Image
import io
import base64


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hash as hex string prefixed with 'sha256:'
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return f"sha256:{sha256_hash.hexdigest()}"


def fuzzy_token_overlap(text1: str, text2: str) -> float:
    """
    Calculate fuzzy token overlap between two texts.
    Used for pre-ranking LoRA candidates against base_context.
    
    Args:
        text1: First text (e.g., base_context)
        text2: Second text (e.g., LoRA tags/triggers/name)
        
    Returns:
        Overlap score (0.0 to 1.0)
    """
    # Normalize: lowercase and split into tokens
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def rank_candidates_by_relevance(
    base_context: str,
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Rank LoRA candidates by relevance to base_context using fuzzy token overlap.
    
    Args:
        base_context: User's input text
        candidates: List of LoRA catalog entries
        
    Returns:
        Sorted list of candidates (highest relevance first)
    """
    scored_candidates = []
    
    for candidate in candidates:
        # Build searchable text from candidate
        searchable = " ".join([
            candidate.get('display_name', ''),
            candidate.get('summary', ''),
            " ".join(candidate.get('trained_words', [])),
            " ".join(candidate.get('tags', []))
        ])
        
        score = fuzzy_token_overlap(base_context, searchable)
        scored_candidates.append((score, candidate))
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    return [candidate for score, candidate in scored_candidates]


def tensor_to_pil(tensor: Any) -> Image.Image:
    """
    Convert ComfyUI image tensor to PIL Image.
    
    Args:
        tensor: ComfyUI image tensor [batch, height, width, channels] or [height, width, channels]
        
    Returns:
        PIL Image
    """
    # Handle batch dimension
    if len(tensor.shape) == 4:
        tensor = tensor[0]  # Take first image from batch
    
    # Convert to numpy
    image_np = tensor.cpu().numpy() if hasattr(tensor, 'cpu') else tensor
    
    # Scale from [0, 1] to [0, 255] if needed
    if image_np.max() <= 1.0:
        image_np = (image_np * 255).astype(np.uint8)
    else:
        image_np = image_np.astype(np.uint8)
    
    # Convert to PIL
    image = Image.fromarray(image_np)
    
    # Convert RGBA to RGB if needed
    if image.mode == 'RGBA':
        # Create white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
        image = background
    
    return image


def encode_image_to_base64(image: Image.Image, format: str = 'JPEG') -> str:
    """
    Encode PIL Image to base64 string.
    
    Args:
        image: PIL Image
        format: Image format (JPEG or PNG)
        
    Returns:
        Base64 encoded string
    """
    buffered = io.BytesIO()
    
    # Convert RGBA to RGB for JPEG
    if format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else None)
        image = background
    
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, str]:
    """
    Validate that JSON data contains required fields.
    
    Args:
        data: JSON data to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, ""


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON, handling common formatting issues.
    
    Args:
        text: JSON string to parse
        
    Returns:
        Parsed dict or None if parsing fails
    """
    try:
        # Try direct parse
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end != -1:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass
        
        # Try to find JSON object in text
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
    
    return None


def merge_lists_unique(list1: List[str], list2: List[str]) -> List[str]:
    """
    Merge two lists, preserving order and removing duplicates.
    Items from list1 come first.
    
    Args:
        list1: First list
        list2: Second list
        
    Returns:
        Merged list with unique items
    """
    seen = set()
    result = []
    
    for item in list1 + list2:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


def normalize_lora_name(filename: str) -> str:
    """
    Normalize LoRA filename for display.
    Removes .safetensors extension and replaces underscores with spaces.
    
    Args:
        filename: LoRA filename
        
    Returns:
        Normalized display name
    """
    name = filename
    
    # Remove extension
    if name.endswith('.safetensors'):
        name = name[:-12]
    
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    
    return name
