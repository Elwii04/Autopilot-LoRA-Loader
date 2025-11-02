"""
LoRA Selection Logic
Filters and ranks LoRAs for auto-selection.
"""
from typing import List, Dict, Any, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.utils import rank_candidates_by_relevance
from utils.base_model_mapping import base_model_mapper


def filter_by_base_model(
    catalog_entries: List[Dict[str, Any]],
    base_model_family: str
) -> List[Dict[str, Any]]:
    """
    Filter catalog entries by base model family compatibility.
    
    Args:
        catalog_entries: List of catalog entries
        base_model_family: Target base model family
        
    Returns:
        Filtered list
    """
    filtered = []
    
    for entry in catalog_entries:
        base_compat = entry.get('base_compat', [])
        if base_model_mapper.is_compatible(base_compat, base_model_family):
            filtered.append(entry)
    
    return filtered


def filter_by_allowlist(
    catalog_entries: List[Dict[str, Any]],
    allowlist: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter catalog entries by allowlist of filenames.
    
    Args:
        catalog_entries: List of catalog entries
        allowlist: List of allowed filenames
        
    Returns:
        Filtered list
    """
    if not allowlist:
        return catalog_entries
    
    # Normalize allowlist
    normalized_allowlist = set()
    for name in allowlist:
        if name.endswith('.safetensors'):
            normalized_allowlist.add(name)
        else:
            normalized_allowlist.add(f"{name}.safetensors")
    
    filtered = []
    for entry in catalog_entries:
        if entry['file'] in normalized_allowlist:
            filtered.append(entry)
    
    return filtered


def filter_non_character(
    catalog_entries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Filter out character LoRAs (only concept LoRAs for auto-selection).
    
    Args:
        catalog_entries: List of catalog entries
        
    Returns:
        Filtered list (non-character only)
    """
    return [entry for entry in catalog_entries if not entry.get('is_character', False)]


def get_candidates_for_autoselect(
    catalog_entries: List[Dict[str, Any]],
    base_model_family: str,
    allowlist: List[str],
    base_context: str,
    max_candidates: int = 30
) -> List[Dict[str, Any]]:
    """
    Get and rank candidates for auto-selection.
    
    Args:
        catalog_entries: Full catalog
        base_model_family: Target base model
        allowlist: Allowed LoRA filenames (empty = all allowed)
        base_context: User's context for relevance ranking
        max_candidates: Maximum candidates to return
        
    Returns:
        Ranked list of candidates
    """
    # Filter by base model
    candidates = filter_by_base_model(catalog_entries, base_model_family)
    
    # Filter by allowlist
    if allowlist:
        candidates = filter_by_allowlist(candidates, allowlist)
    
    # Filter out characters
    candidates = filter_non_character(candidates)
    
    # Rank by relevance to base_context
    candidates = rank_candidates_by_relevance(base_context, candidates)
    
    # Take top N
    return candidates[:max_candidates]


def merge_manual_and_auto_loras(
    manual_loras: List[Dict[str, Any]],
    auto_loras: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge manual and auto-selected LoRAs, with deduplication.
    Manual LoRAs come first.
    
    Args:
        manual_loras: Manually selected LoRAs from catalog
        auto_loras: Auto-selected LoRAs from catalog
        
    Returns:
        Merged list (manual first, then auto, deduplicated)
    """
    seen_files = set()
    merged = []
    
    # Add manual LoRAs first
    for lora in manual_loras:
        file = lora['file']
        if file not in seen_files:
            seen_files.add(file)
            merged.append(lora)
    
    # Add auto LoRAs
    for lora in auto_loras:
        file = lora['file']
        if file not in seen_files:
            seen_files.add(file)
            merged.append(lora)
    
    return merged


def resolve_selected_loras_from_llm(
    llm_selection: List[Dict[str, str]],
    catalog_entries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Resolve LLM-selected LoRA names to full catalog entries.
    
    Args:
        llm_selection: List of selected LoRAs from LLM (with 'name' field)
        catalog_entries: Full catalog entries
        
    Returns:
        List of resolved catalog entries
    """
    # Build lookup by filename
    catalog_by_file = {entry['file']: entry for entry in catalog_entries}
    
    resolved = []
    for selected in llm_selection:
        name = selected['name']
        if name in catalog_by_file:
            resolved.append(catalog_by_file[name])
        else:
            print(f"[LoRASelector] Warning: Could not resolve LoRA: {name}")
    
    return resolved
