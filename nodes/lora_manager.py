"""
LoRA Manager Node
Provides UI for manually managing LoRAs: indexing, editing metadata, and viewing catalog.
"""
import json
from typing import Any, Dict, List, Tuple
from pathlib import Path

# Import utilities
from ..utils.config_manager import config
from ..utils.lora_catalog import lora_catalog
from ..utils.base_model_mapping import base_model_mapper
from ..utils.indexing_llm import index_with_llm, suggest_base_family_with_llm
from ..utils.show_info_generator import generate_info_files_for_catalog
from ..utils.model_fetcher import fetch_all_available_models, parse_model_string


class LoRAManager:
    """
    LoRA Manager Node
    
    Provides manual control over LoRA indexing and metadata editing.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        
        # Fetch all available models from both providers
        all_models, vision_models = fetch_all_available_models()
        
        # Get indexed LoRA names
        try:
            lora_names = [entry['file'] for entry in lora_catalog.get_all_entries()]
            if not lora_names:
                lora_names = ["No LoRAs indexed"]
        except:
            lora_names = ["Error loading LoRAs"]
        
        # Get base model families
        families = base_model_mapper.get_all_families() + ["Unknown"]
        
        return {
            "required": {
                "action": (["Scan & Index New LoRAs", "Re-index Selected LoRA", "Generate Info Files", "View Catalog Stats"], {
                    "default": "Scan & Index New LoRAs",
                    "tooltip": "Choose what action to perform: Scan & Index finds new LoRAs and processes them with AI. Re-index updates a specific LoRA. Generate Info Files creates rgthree-compatible files. View Stats shows your collection overview."
                }),
                "indexing_model": (all_models, {
                    "default": all_models[0] if all_models else "groq: llama-3.1-8b-instant",
                    "tooltip": "LLM model for analyzing LoRA metadata. Extracts summaries, triggers, and tags from Civitai descriptions. Recommended: groq: llama-3.1-8b-instant for speed and accuracy."
                }),
            },
            "optional": {
                "selected_lora": (lora_names, {
                    "default": lora_names[0] if lora_names else "No LoRAs indexed",
                    "tooltip": "Select a specific LoRA to re-index or edit. Only used with 'Re-index Selected LoRA' action."
                }),
                "force_reindex": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Force re-indexing even if LoRA was already processed. Use this to update metadata with a better model or after manual Civitai updates."
                }),
                "max_index_count": ("INT", {
                    "default": 999,
                    "min": 1,
                    "max": 999,
                    "tooltip": "Maximum number of LoRAs to index at once. Use a lower number (e.g., 10) for testing to avoid long processing times or API rate limits."
                }),
                "edit_base_model": (families, {
                    "default": "Unknown",
                    "tooltip": "Manually override the base model family for the selected LoRA. Choose the model family this LoRA was trained for (e.g., Flux-1, SDXL, SD1.5)."
                }),
                "edit_summary": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Manually edit the LoRA's description/summary. Describe what this LoRA does in one concise sentence."
                }),
                "edit_triggers": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "tooltip": "Manually edit trigger words (comma-separated). These are the activation words needed to use this LoRA. Example: 'cyberpunk style, neon lights, futuristic'"
                }),
                "edit_tags": ("STRING", {
                    "multiline": False,
                    "default": "",
                    "tooltip": "Manually edit tags (comma-separated). Keywords describing the LoRA's style, theme, or features. Example: 'scifi, urban, lighting, atmosphere'"
                }),
                "edit_weight": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                    "tooltip": "Default weight/strength for this LoRA. Most LoRAs work best at 0.7-1.0. Lower values (0.3-0.7) for subtle effects, higher (1.0-1.5) for strong effects."
                }),
                "disable_lora": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Disable this LoRA from auto-selection. Disabled LoRAs won't be chosen by the AI but can still be manually applied. Use this instead of deleting LoRAs you don't want auto-selected."
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status_message",)
    FUNCTION = "manage_loras"
    CATEGORY = "loaders/Autopilot LoRA"
    DESCRIPTION = "Manually manage LoRA indexing and metadata editing"
    OUTPUT_NODE = True
    
    def manage_loras(
        self,
        action: str,
        indexing_model: str,
        selected_lora: str = "",
        force_reindex: bool = False,
        max_index_count: int = 999,
        edit_base_model: str = "Unknown",
        edit_summary: str = "",
        edit_triggers: str = "",
        edit_tags: str = "",
        edit_weight: float = 1.0,
        disable_lora: bool = False
    ) -> Tuple[str]:
        """
        Manage LoRA catalog.
        
        Returns:
            Tuple containing status message
        """
        print("\n" + "="*60)
        print("LoRA Manager")
        print("="*60)
        
        if action == "Scan & Index New LoRAs":
            return self._scan_and_index(indexing_model, max_index_count)
        
        elif action == "Re-index Selected LoRA":
            return self._reindex_selected(
                selected_lora,
                indexing_model,
                force_reindex,
                edit_base_model,
                edit_summary,
                edit_triggers,
                edit_tags,
                edit_weight,
                disable_lora
            )
        
        elif action == "Generate Info Files":
            return self._generate_info_files()
        
        elif action == "View Catalog Stats":
            return self._view_stats()
        
        else:
            return (f"Unknown action: {action}",)
    
    def _scan_and_index(self, indexing_model: str, max_count: int) -> Tuple[str]:
        """Scan for new LoRAs and index them."""
        print("[Manager] Scanning for new LoRAs...")
        
        # Parse provider and model from prefixed string
        provider, model_name = parse_model_string(indexing_model)
        
        new_files = lora_catalog.detect_new_loras()
        
        if not new_files:
            msg = "✅ No new LoRAs detected. Catalog is up to date."
            print(msg)
            return (msg,)
        
        # Limit by max_count
        if len(new_files) > max_count:
            print(f"[Manager] Limiting to first {max_count} of {len(new_files)} LoRAs")
            new_files = new_files[:max_count]
        
        print(f"[Manager] Found {len(new_files)} new LoRA(s) to index")
        
        # Get API key
        if provider == "groq":
            api_key = config.get_groq_api_key()
        elif provider == "gemini":
            api_key = config.get_gemini_api_key()
        else:
            return (f"❌ Unknown provider: {provider}",)
        
        if not api_key:
            msg = f"⚠️ No API key for {provider}. Indexed {len(new_files)} LoRA(s) with basic metadata only."
            print(msg)
            for file_path in new_files:
                lora_catalog.index_lora_basic(file_path)
            lora_catalog.save_catalog()
            return (msg,)
        
        # Get known families
        known_families = lora_catalog.get_known_base_families()
        
        # Index each file
        success_count = 0
        for idx, file_path in enumerate(new_files, 1):
            print(f"\n[Manager] Indexing {idx}/{len(new_files)}: {file_path.name}")
            
            # Basic indexing
            file_hash = lora_catalog.index_lora_basic(file_path)
            entry = lora_catalog.get_entry(file_hash)
            
            if not entry:
                print(f"[Manager] ❌ Failed to index {file_path.name}")
                continue
            
            # LLM indexing if Civitai data available
            civitai_text = entry.get('civitai_text', '')
            if civitai_text:
                success, extracted, error = index_with_llm(
                    civitai_text=civitai_text,
                    provider_name=provider,
                    model_name=model_name,
                    api_key=api_key,
                    known_families=known_families,
                    filename=file_path.name
                )
                
                if success and extracted:
                    # Determine base model
                    base_family = suggest_base_family_with_llm(
                        civitai_text=civitai_text,
                        known_families=known_families,
                        provider_name=provider,
                        model_name=model_name,
                        api_key=api_key
                    )
                    
                    base_compat = [base_family] if base_family != 'Unknown' else ['Unknown']
                    
                    # Update catalog
                    lora_catalog.mark_llm_indexed(
                        file_hash=file_hash,
                        summary=extracted['summary'],
                        trained_words=extracted['trainedWords'],
                        tags=extracted['tags'],
                        base_compat=base_compat
                    )
                    print(f"[Manager] ✅ Successfully indexed: {entry.get('display_name', file_path.name)}")
                    success_count += 1
                else:
                    print(f"[Manager] ⚠️ LLM extraction failed: {error}")
            else:
                print(f"[Manager] ⚠️ No Civitai data available")
            
            lora_catalog.save_catalog()
        
        msg = f"✅ Indexed {success_count}/{len(new_files)} LoRA(s) successfully with LLM"
        print(f"\n{msg}")
        return (msg,)
    
    def _reindex_selected(
        self,
        lora_name: str,
        indexing_model: str,
        force: bool,
        base_model: str,
        summary: str,
        triggers: str,
        tags: str,
        weight: float,
        is_disabled: bool
    ) -> Tuple[str]:
        """Re-index or edit a selected LoRA."""
        if not lora_name or lora_name == "No LoRAs indexed":
            return ("⚠️ No LoRA selected",)
        
        # Parse provider and model from prefixed string
        provider, model_name = parse_model_string(indexing_model)
        
        # Find entry by filename
        entry = None
        for e in lora_catalog.get_all_entries():
            if e['file'] == lora_name:
                entry = e
                break
        
        if not entry:
            return (f"❌ LoRA not found: {lora_name}",)
        
        file_hash = entry.get('sha256', '')
        
        # Manual edits take precedence
        if summary or triggers or tags or base_model != "Unknown" or weight != 1.0:
            print(f"[Manager] Applying manual edits to {lora_name}")
            
            # Parse triggers and tags
            trigger_list = [t.strip() for t in triggers.split(',')] if triggers else entry.get('trained_words', [])
            tag_list = [t.strip().lower() for t in tags.split(',')] if tags else entry.get('tags', [])
            
            # Update entry
            lora_catalog.mark_llm_indexed(
                file_hash=file_hash,
                summary=summary if summary else entry.get('summary', ''),
                trained_words=trigger_list,
                tags=tag_list,
                base_compat=[base_model] if base_model != "Unknown" else entry.get('base_compat', ['Unknown'])
            )
            
            # Update weight and disabled status
            if file_hash in lora_catalog.catalog:
                lora_catalog.catalog[file_hash]['default_weight'] = weight
                lora_catalog.catalog[file_hash]['disabled'] = is_disabled
            
            lora_catalog.save_catalog()
            
            msg = f"✅ Updated metadata for {lora_name}"
            print(msg)
            return (msg,)
        
        # Otherwise, re-index with LLM
        if not force and entry.get('indexed_by_llm'):
            return (f"⚠️ {lora_name} already indexed. Enable 'force_reindex' to re-index.",)
        
        print(f"[Manager] Re-indexing {lora_name} with LLM...")
        
        # Get API key
        if provider == "groq":
            api_key = config.get_groq_api_key()
        elif provider == "gemini":
            api_key = config.get_gemini_api_key()
        else:
            return (f"❌ Unknown provider: {provider}",)
        
        if not api_key:
            return (f"❌ No API key for {provider}",)
        
        civitai_text = entry.get('civitai_text', '')
        if not civitai_text:
            return (f"⚠️ No Civitai data available for {lora_name}",)
        
        known_families = lora_catalog.get_known_base_families()
        
        success, extracted, error = index_with_llm(
            civitai_text=civitai_text,
            provider_name=provider,
            model_name=model_name,
            api_key=api_key,
            known_families=known_families,
            filename=lora_name
        )
        
        if not success or not extracted:
            return (f"❌ LLM indexing failed: {error}",)
        
        # Determine base model
        base_family = suggest_base_family_with_llm(
            civitai_text=civitai_text,
            known_families=known_families,
            provider_name=provider,
            model_name=model_name,
            api_key=api_key
        )
        
        base_compat = [base_family] if base_family != 'Unknown' else ['Unknown']
        
        # Update catalog with disabled status
        lora_catalog.mark_llm_indexed(
            file_hash=file_hash,
            summary=extracted['summary'],
            trained_words=extracted['trainedWords'],
            tags=extracted['tags'],
            base_compat=base_compat
        )
        
        # Set disabled status
        if file_hash in lora_catalog.catalog:
            lora_catalog.catalog[file_hash]['disabled'] = is_disabled
        
        lora_catalog.save_catalog()
        
        msg = f"✅ Successfully re-indexed: {lora_name}"
        print(msg)
        return (msg,)
    
    def _generate_info_files(self) -> Tuple[str]:
        """Generate .rgthree-info.json files for all LoRAs."""
        print("[Manager] Generating info files...")
        
        lora_dir = lora_catalog.get_lora_directory()
        if not lora_dir:
            return ("❌ Could not find LoRA directory",)
        
        entries = lora_catalog.get_all_entries()
        count = generate_info_files_for_catalog(entries, lora_dir)
        
        msg = f"✅ Generated {count} .rgthree-info.json files"
        print(msg)
        return (msg,)
    
    def _view_stats(self) -> Tuple[str]:
        """View catalog statistics."""
        entries = lora_catalog.get_all_entries()
        
        total = len(entries)
        available = sum(1 for e in entries if e.get('available', True))
        llm_indexed = sum(1 for e in entries if e.get('indexed_by_llm'))
        characters = sum(1 for e in entries if e.get('is_character'))
        
        # Count by base model
        families = {}
        for entry in entries:
            base_compat = entry.get('base_compat', ['Unknown'])
            for family in base_compat:
                families[family] = families.get(family, 0) + 1
        
        stats = f"""📊 LoRA Catalog Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total LoRAs: {total}
Available: {available}
Unavailable: {total - available}
LLM-indexed: {llm_indexed}
Character LoRAs: {characters}
Concept LoRAs: {total - characters}

Base Model Distribution:
"""
        for family, count in sorted(families.items(), key=lambda x: -x[1]):
            stats += f"  • {family}: {count}\n"
        
        print(stats)
        return (stats,)


# Node registration
NODE_CLASS_MAPPINGS = {
    "LoRAManager": LoRAManager
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRAManager": "⚙️ LoRA Manager (Autopilot)"
}
