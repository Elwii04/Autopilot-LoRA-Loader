"""
LoRA Catalog System
Manages persistent catalog of indexed LoRAs with metadata.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from .utils import compute_file_hash, normalize_lora_name
from .safetensors_utils import parse_safetensors_file
from .civitai_utils import fetch_civitai_by_hash, extract_civitai_metadata, build_civitai_summary_text
from .base_model_mapping import base_model_mapper

# Try to import ComfyUI's folder_paths
try:
    import folder_paths
    HAS_COMFY = True
except ImportError:
    HAS_COMFY = False
    print("[LoRACatalog] Warning: folder_paths not available, using manual path")


CATALOG_FILE = Path(__file__).parent.parent / 'data' / 'lora_index.json'


class LoRACatalog:
    """Manages the persistent LoRA catalog with indexing capabilities."""
    
    def __init__(self):
        """Initialize the LoRA catalog."""
        self.catalog_path = CATALOG_FILE
        self.catalog: Dict[str, Dict[str, Any]] = {}
        self.load_catalog()
    
    def load_catalog(self):
        """Load catalog from JSON file."""
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, 'r', encoding='utf-8') as f:
                    self.catalog = json.load(f)
                print(f"[LoRACatalog] Loaded {len(self.catalog)} entries from catalog")
            except Exception as e:
                print(f"[LoRACatalog] Error loading catalog: {e}")
                self.catalog = {}
        else:
            print(f"[LoRACatalog] No existing catalog found, will create new one")
            self.catalog = {}
            # Ensure catalog file exists so downstream code never fails on missing file
            self.save_catalog()
    
    def save_catalog(self):
        """Save catalog to JSON file."""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(self.catalog, f, indent=2, ensure_ascii=False)
            print(f"[LoRACatalog] Saved catalog with {len(self.catalog)} entries")
        except Exception as e:
            print(f"[LoRACatalog] Error saving catalog: {e}")
    
    def get_lora_directories(self) -> List[Path]:
        """Get all LoRA directory paths (ComfyUI can have multiple)."""
        lora_dirs = []
        
        if HAS_COMFY:
            try:
                lora_paths = folder_paths.get_folder_paths("loras")
                if lora_paths:
                    lora_dirs = [Path(p) for p in lora_paths]
                    print(f"[LoRACatalog] Found {len(lora_dirs)} LoRA path(s) from ComfyUI")
                    return lora_dirs
            except Exception as e:
                print(f"[LoRACatalog] Error getting LoRA paths from ComfyUI: {e}")
        
        # Fallback: try common paths
        possible_paths = [
            Path("models/loras"),
            Path("ComfyUI/models/loras"),
            Path("../models/loras")
        ]
        
        for path in possible_paths:
            if path.exists():
                lora_dirs.append(path)
                break
        
        return lora_dirs
    
    def get_lora_directory(self) -> Optional[Path]:
        """Get the primary LoRA directory path (first one)."""
        dirs = self.get_lora_directories()
        return dirs[0] if dirs else None
    
    def scan_lora_files(self) -> List[Path]:
        """
        Scan ALL LoRA directories for .safetensors files.
        
        Returns:
            List of paths to LoRA files
        """
        lora_dirs = self.get_lora_directories()
        if not lora_dirs:
            print("[LoRACatalog] Could not find any LoRA directories")
            return []
        
        # Recursively find all .safetensors files in all directories
        lora_files = []
        for lora_dir in lora_dirs:
            dir_files = list(lora_dir.rglob("*.safetensors"))
            lora_files.extend(dir_files)
            print(f"[LoRACatalog] Found {len(dir_files)} LoRA files in {lora_dir}")
        
        print(f"[LoRACatalog] Total: {len(lora_files)} LoRA files across all paths")
        
        return lora_files
    
    def detect_new_loras(self) -> List[Path]:
        """
        Detect new or changed LoRA files not in the catalog.
        Also marks unavailable LoRAs (files that were removed).
        
        Returns:
            List of paths to new/changed LoRAs
        """
        all_files = self.scan_lora_files()
        new_files = []
        current_hashes = set()
        
        for file_path in all_files:
            # Compute hash
            file_hash = compute_file_hash(file_path)
            current_hashes.add(file_hash)
            
            # Check if in catalog
            if file_hash not in self.catalog:
                new_files.append(file_path)
            else:
                # Mark existing file as available
                self.catalog[file_hash]['available'] = True
        
        # Mark missing LoRAs as unavailable
        for file_hash, entry in self.catalog.items():
            if file_hash not in current_hashes:
                if entry.get('available', True):  # Only log if status changed
                    print(f"[LoRACatalog] Marking unavailable: {entry.get('display_name', 'Unknown')}")
                entry['available'] = False
        
        print(f"[LoRACatalog] Detected {len(new_files)} new LoRA files")
        return new_files
    
    def index_lora_basic(self, file_path: Path) -> str:
        """
        Index a LoRA file with basic metadata (no LLM processing).
        
        Args:
            file_path: Path to the LoRA file
            
        Returns:
            File hash (catalog key)
        """
        print(f"[LoRACatalog] Indexing {file_path.name}...")
        
        # Compute hash
        file_hash = compute_file_hash(file_path)
        
        # Check if already exists - preserve existing enabled state and other settings
        if file_hash in self.catalog:
            existing_entry = self.catalog[file_hash]
            print(f"[LoRACatalog] Already in catalog: {file_path.name} (enabled: {existing_entry.get('enabled', True)})")
            # Update availability and path in case file moved
            existing_entry['available'] = True
            existing_entry['full_path'] = str(file_path)
            return file_hash
        
        # Initialize entry
        entry = {
            'file_hash': file_hash,  # Add file_hash to the entry itself for easy access
            'file': str(file_path.name),
            'full_path': str(file_path),
            'display_name': normalize_lora_name(file_path.name),
            'sha256': file_hash,
            'available': True,  # Mark as available by default
            'summary': '',
            'trained_words': [],
            'tags': [],
            'enabled': True,  # Default to enabled
            'base_compat': ['Other'],
            'default_weight': 1.0,
            'source': {
                'kind': 'unknown'
            },
            'indexed_at': datetime.now().isoformat(),
            'indexed_by_llm': False,
            'indexing_attempted': False  # Track if we've tried to index this with LLM
        }
        
        # Extract safetensors metadata
        safetensors_data = parse_safetensors_file(file_path)
        if safetensors_data['metadata']:
            entry['safetensors_metadata'] = True
            
            # Merge trained words
            if safetensors_data['trained_words']:
                entry['trained_words'].extend(safetensors_data['trained_words'])
            
            # Merge base model
            if safetensors_data['base_model']:
                base_model = base_model_mapper.normalize_to_model(safetensors_data['base_model'])
                if base_model != 'Other':
                    entry['base_compat'] = [base_model]
            
            # Merge recommended weight
            if safetensors_data['recommended_weight']:
                entry['default_weight'] = safetensors_data['recommended_weight']
        
        # Fetch Civitai data
        civitai_data = fetch_civitai_by_hash(file_hash)
        if civitai_data and 'error' not in civitai_data:
            print(f"[LoRACatalog] Found Civitai data for {file_path.name}")
            entry['source']['kind'] = 'civitai'
            
            # Extract metadata
            civitai_meta = extract_civitai_metadata(civitai_data)
            
            # Merge display name
            if civitai_meta.get('display_name'):
                entry['display_name'] = civitai_meta['display_name']
            
            # Merge trained words (prioritize Civitai)
            if civitai_meta.get('trained_words'):
                # Add Civitai words first, then safetensors words
                all_words = civitai_meta['trained_words'] + entry['trained_words']
                # Remove duplicates while preserving order
                seen = set()
                unique_words = []
                for word in all_words:
                    if word not in seen:
                        seen.add(word)
                        unique_words.append(word)
                entry['trained_words'] = unique_words
            
            # Merge tags
            if civitai_meta.get('tags'):
                entry['tags'] = civitai_meta['tags']
            
            # Merge base model
            if civitai_meta.get('base_model'):
                base_model = base_model_mapper.normalize_to_model(civitai_meta['base_model'])
                if base_model != 'Other':
                    entry['base_compat'] = [base_model]
            
            # Store raw Civitai data for LLM processing
            entry['civitai_data'] = civitai_data
            entry['civitai_text'] = build_civitai_summary_text(civitai_data)
            
            # Store URLs
            if civitai_meta.get('civitai_url'):
                entry['source']['url'] = civitai_meta['civitai_url']
            if civitai_meta.get('version_id'):
                entry['source']['version_id'] = civitai_meta['version_id']
            
            # Store images
            if civitai_meta.get('images'):
                entry['images'] = civitai_meta['images']
        else:
            print(f"[LoRACatalog] No Civitai data for {file_path.name}")
            entry['source']['kind'] = 'unknown'
        
        # Add to catalog
        self.catalog[file_hash] = entry
        
        return file_hash
    
    def mark_llm_indexed(
        self,
        file_hash: str,
        summary: str,
        trained_words: List[str],
        tags: List[str],
        base_compat: List[str],
        recommended_strength: Optional[float] = None
    ):
        """
        Mark a LoRA as indexed by LLM and update its metadata.
        
        Args:
            file_hash: File hash (catalog key)
            summary: One-line summary from LLM
            trained_words: Extracted trained words
            tags: Extracted tags
            base_compat: Base model compatibility families
        """
        if file_hash not in self.catalog:
            print(f"[LoRACatalog] Hash {file_hash[:16]}... not in catalog")
            return
        
        entry = self.catalog[file_hash]
        
        # Update with LLM data
        entry['summary'] = summary
        entry['indexed_by_llm'] = True
        entry['indexing_attempted'] = True
        
        # Merge trained words (keep existing + add new)
        existing_words = set(entry.get('trained_words', []))
        all_words = list(existing_words) + [w for w in trained_words if w not in existing_words]
        entry['trained_words'] = all_words
        
        # Update tags
        entry['tags'] = tags
        
        # Update base compat (if provided and not Other)
        if base_compat and base_compat != ['Other']:
            entry['base_compat'] = base_compat
        
        # Update recommended strength if provided
        if recommended_strength is not None:
            clamped_strength = max(0.2, min(2.0, float(recommended_strength)))
            entry['default_weight'] = round(clamped_strength, 4)
        
        print(f"[LoRACatalog] Marked as LLM indexed: {entry['display_name']}")
    
    def mark_indexing_attempted(self, file_hash: str):
        """
        Mark that we've attempted to index this LoRA (even if it failed or had no Civitai data).
        This prevents re-trying LoRAs that don't have Civitai data or failed indexing.
        
        Args:
            file_hash: File hash (catalog key)
        """
        if file_hash not in self.catalog:
            print(f"[LoRACatalog] Hash {file_hash[:16]}... not in catalog")
            return
        
        entry = self.catalog[file_hash]
        entry['indexing_attempted'] = True
        print(f"[LoRACatalog] Marked indexing attempted: {entry['display_name']}")
    
    def get_entry(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get a catalog entry by hash."""
        return self.catalog.get(file_hash)
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all catalog entries as a list."""
        return list(self.catalog.values())
    
    def filter_by_base_model(self, base_model_family: str, include_unavailable: bool = False) -> List[Dict[str, Any]]:
        """
        Filter catalog entries by base model family.
        
        Args:
            base_model_family: Base model family name
            include_unavailable: Whether to include unavailable LoRAs
            
        Returns:
            List of matching entries
        """
        filtered = []
        
        for entry in self.catalog.values():
            # Skip unavailable LoRAs unless explicitly requested
            if not include_unavailable and not entry.get('available', True):
                continue
            
            base_compat = entry.get('base_compat', [])
            if base_model_family in base_compat:
                filtered.append(entry)
        
        return filtered
    
    def filter_by_names(self, lora_names: List[str], include_unavailable: bool = False) -> List[Dict[str, Any]]:
        """
        Filter catalog entries by LoRA file names.
        
        Args:
            lora_names: List of LoRA filenames (with or without .safetensors)
            include_unavailable: Whether to include unavailable LoRAs
            
        Returns:
            List of matching entries
        """
        # Normalize names
        normalized_names = set()
        for name in lora_names:
            if name.endswith('.safetensors'):
                normalized_names.add(name)
            else:
                normalized_names.add(f"{name}.safetensors")
        
        filtered = []
        for entry in self.catalog.values():
            # Skip unavailable LoRAs unless explicitly requested
            if not include_unavailable and not entry.get('available', True):
                continue
            
            if entry['file'] in normalized_names:
                filtered.append(entry)
        
        return filtered
    
    def get_non_character_loras(self) -> List[Dict[str, Any]]:
        """Get all LoRAs eligible for auto-selection (just enabled ones)."""
        return [
            entry for entry in self.catalog.values() 
            if entry.get('enabled', True)
        ]
    
    def get_known_base_families(self) -> List[str]:
        """Get list of base model families present in the catalog."""
        # Reload to ensure we catch changes written by other processes (e.g., indexing API)
        self.load_catalog()
        
        families = base_model_mapper.get_families_in_catalog(list(self.catalog.values()))
        
        if not families:
            return ['Unknown']
        
        # Always include Unknown as fallback option for manual override
        if 'Unknown' not in families:
            families.append('Unknown')
        
        return sorted(set(families))


# Global catalog instance
lora_catalog = LoRACatalog()
