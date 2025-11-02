"""
Safetensors metadata extraction utilities
Reads metadata from .safetensors files to extract LoRA information.
"""
import json
import struct
from pathlib import Path
from typing import Dict, Any, Optional, List


def read_safetensors_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Read metadata from a .safetensors file header.
    
    Args:
        file_path: Path to the .safetensors file
        
    Returns:
        Dictionary containing metadata or None if extraction fails
    """
    try:
        with open(file_path, 'rb') as f:
            # Read the header length (first 8 bytes)
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8:
                return None
            
            # Unpack as little-endian 64-bit unsigned integer
            header_size = struct.unpack('<Q', header_size_bytes)[0]
            
            # Read the header JSON
            header_bytes = f.read(header_size)
            if len(header_bytes) < header_size:
                return None
            
            # Parse header JSON
            header = json.loads(header_bytes.decode('utf-8'))
            
            # Extract __metadata__ if present
            metadata = header.get('__metadata__', {})
            
            return metadata if metadata else None
    
    except Exception as e:
        print(f"[Safetensors] Error reading metadata from {file_path}: {e}")
        return None


def extract_trained_words_from_metadata(metadata: Dict[str, Any]) -> List[str]:
    """
    Extract trained words from safetensors metadata.
    
    Args:
        metadata: Parsed safetensors metadata
        
    Returns:
        List of trained words/trigger words
    """
    trained_words = []
    
    # Check common metadata fields
    # Method 1: ss_tag_frequency (Kohya SS format)
    if 'ss_tag_frequency' in metadata:
        try:
            tag_freq = json.loads(metadata['ss_tag_frequency'])
            # tag_freq is usually a dict of dicts: {dataset_name: {tag: count}}
            for dataset_tags in tag_freq.values():
                if isinstance(dataset_tags, dict):
                    # Get tags sorted by frequency
                    sorted_tags = sorted(
                        dataset_tags.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    # Take top tags (most frequent)
                    for tag, count in sorted_tags[:20]:  # Top 20 most frequent
                        if count > 5:  # Only if used more than 5 times
                            trained_words.append(tag)
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
    
    # Method 2: ss_output_name or ss_session_id (sometimes contains trigger)
    if 'ss_output_name' in metadata:
        output_name = metadata['ss_output_name']
        if output_name and isinstance(output_name, str):
            # Sometimes the output name is the trigger word
            trained_words.append(output_name)
    
    # Method 3: Direct trigger_word or trained_words field
    for key in ['trigger_word', 'trigger_words', 'trained_words', 'activation_text']:
        if key in metadata:
            value = metadata[key]
            if isinstance(value, str):
                trained_words.append(value)
            elif isinstance(value, list):
                trained_words.extend(value)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_words = []
    for word in trained_words:
        word = word.strip()
        if word and word not in seen:
            seen.add(word)
            unique_words.append(word)
    
    return unique_words


def extract_base_model_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extract base model name from safetensors metadata.
    
    Args:
        metadata: Parsed safetensors metadata
        
    Returns:
        Base model name or None
    """
    # Common keys for base model
    for key in ['ss_base_model_version', 'ss_sd_model_name', 'base_model', 'model_name']:
        if key in metadata:
            value = metadata[key]
            if value and isinstance(value, str):
                return value
    
    return None


def extract_recommended_weight(metadata: Dict[str, Any]) -> Optional[float]:
    """
    Extract recommended LoRA weight from metadata if available.
    
    Args:
        metadata: Parsed safetensors metadata
        
    Returns:
        Recommended weight or None
    """
    # Check for recommended weight fields
    for key in ['ss_network_alpha', 'preferred_weight', 'recommended_weight']:
        if key in metadata:
            try:
                value = metadata[key]
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    return float(value)
            except (ValueError, TypeError):
                pass
    
    return None


def parse_safetensors_file(file_path: Path) -> Dict[str, Any]:
    """
    Parse safetensors file and extract all useful information.
    
    Args:
        file_path: Path to .safetensors file
        
    Returns:
        Dictionary with extracted information
    """
    result = {
        'metadata': None,
        'trained_words': [],
        'base_model': None,
        'recommended_weight': None
    }
    
    # Read metadata
    metadata = read_safetensors_metadata(file_path)
    if not metadata:
        return result
    
    result['metadata'] = metadata
    
    # Extract trained words
    result['trained_words'] = extract_trained_words_from_metadata(metadata)
    
    # Extract base model
    result['base_model'] = extract_base_model_from_metadata(metadata)
    
    # Extract recommended weight
    result['recommended_weight'] = extract_recommended_weight(metadata)
    
    return result
