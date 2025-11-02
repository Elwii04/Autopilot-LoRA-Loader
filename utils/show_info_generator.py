"""
RGThree Show Info Generator
Generates .rgthree-info.json files compatible with rgthree's "Show Info" dialog.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def generate_rgthree_info_file(
    lora_catalog_entry: Dict[str, Any],
    lora_dir: Path
) -> bool:
    """
    Generate .rgthree-info.json file for a LoRA.
    
    Args:
        lora_catalog_entry: LoRA entry from catalog
        lora_dir: Directory containing the LoRA file
        
    Returns:
        True if successful
    """
    lora_file = lora_catalog_entry.get('file')
    if not lora_file:
        return False
    
    # Build info file path
    lora_path = lora_dir / lora_file
    if not lora_path.exists():
        # Try using full_path from entry
        if 'full_path' in lora_catalog_entry:
            lora_path = Path(lora_catalog_entry['full_path'])
        
        if not lora_path.exists():
            print(f"[ShowInfo] LoRA file not found: {lora_file}")
            return False
    
    info_path = lora_path.with_suffix('.rgthree-info.json')
    
    # Build info structure compatible with rgthree
    info = {
        'file': lora_file,
        'name': lora_catalog_entry.get('display_name', lora_file),
        'type': 'LORA',
        'sha256': lora_catalog_entry.get('sha256', ''),
    }
    
    # Base model
    base_compat = lora_catalog_entry.get('base_compat', [])
    if base_compat and base_compat[0] != 'Unknown':
        info['baseModel'] = base_compat[0]
    
    # Trained words in rgthree format
    trained_words = lora_catalog_entry.get('trained_words', [])
    if trained_words:
        info['trainedWords'] = []
        for word in trained_words:
            info['trainedWords'].append({
                'word': word,
                'count': 100,  # Placeholder count
                'indexed': True
            })
    
    # Strength recommendations
    default_weight = lora_catalog_entry.get('default_weight', 1.0)
    info['strengthMin'] = max(0.1, default_weight - 0.5)
    info['strengthMax'] = min(2.0, default_weight + 0.5)
    
    # Summary/description
    if lora_catalog_entry.get('summary'):
        info['description'] = lora_catalog_entry['summary']
    
    # Tags
    if lora_catalog_entry.get('tags'):
        info['tags'] = lora_catalog_entry['tags']
    
    # Images (sample images from Civitai)
    if lora_catalog_entry.get('images'):
        info['images'] = lora_catalog_entry['images']
    
    # Links
    links = []
    if 'source' in lora_catalog_entry:
        source = lora_catalog_entry['source']
        if source.get('url'):
            links.append(source['url'])
    info['links'] = links
    
    # Raw data
    info['raw'] = {}
    
    # Add Civitai data if available
    if 'civitai_data' in lora_catalog_entry:
        info['raw']['civitai'] = lora_catalog_entry['civitai_data']
    
    # Add safetensors metadata flag
    if lora_catalog_entry.get('safetensors_metadata'):
        info['raw']['metadata'] = {'has_metadata': True}
    
    # User notes
    info['userNote'] = f"Indexed by SmartPowerLoRALoader"
    if lora_catalog_entry.get('indexed_by_llm'):
        info['userNote'] += " (LLM-indexed)"
    
    # Write to file
    try:
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        print(f"[ShowInfo] Generated {info_path.name}")
        return True
    except Exception as e:
        print(f"[ShowInfo] Error writing info file: {e}")
        return False


def generate_info_files_for_catalog(
    catalog_entries: List[Dict[str, Any]],
    lora_dir: Path
) -> int:
    """
    Generate .rgthree-info.json files for all entries in catalog.
    
    Args:
        catalog_entries: List of LoRA catalog entries
        lora_dir: Directory containing LoRA files
        
    Returns:
        Number of files successfully generated
    """
    success_count = 0
    
    for entry in catalog_entries:
        if generate_rgthree_info_file(entry, lora_dir):
            success_count += 1
    
    print(f"[ShowInfo] Generated {success_count}/{len(catalog_entries)} info files")
    return success_count
