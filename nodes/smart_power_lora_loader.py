"""
SmartPowerLoRALoader Node
Main ComfyUI custom node that auto-selects LoRAs and generates prompts using LLMs.
"""
import json
from typing import Any, Dict, List, Tuple, Optional, Set
import sys
import os
from pathlib import Path

# Import utilities with relative imports
from ..utils.config_manager import config
from ..utils.lora_catalog import lora_catalog
from ..utils.base_model_mapping import base_model_mapper
from ..utils.indexing_llm import index_with_llm, suggest_base_family_with_llm
from ..utils.prompting_llm import prompt_with_llm
from ..utils.lora_selector import (
    get_candidates_for_autoselect,
    merge_manual_and_auto_loras,
    resolve_selected_loras_from_llm
)
from ..utils.lora_applicator import apply_loras_to_model_clip
from ..utils.prompt_builder import build_final_prompt, build_prompt_from_llm_output
from ..utils.show_info_generator import generate_info_files_for_catalog
from ..utils.civitai_utils import build_civitai_summary_text
from ..utils.model_fetcher import fetch_all_available_models, parse_model_string
from ..utils.flexible_input_types import FlexibleOptionalInputType, any_type

# Try to import ComfyUI modules
try:
    import folder_paths
    HAS_COMFY = True
except ImportError:
    HAS_COMFY = False


class SmartPowerLoRALoader:
    """
    SmartPowerLoRALoader Node
    
    Auto-selects relevant LoRAs based on context and generates prompts using LLMs.
    Extends the concept of rgthree's Power LoRA Loader with intelligent automation.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        
        # Get available base model families from catalog
        try:
            families = lora_catalog.get_known_base_families()
            if not families:
                families = ["Unknown"]
        except:
            families = base_model_mapper.get_all_families()
        
        # Get all LoRA filenames for manual selection
        try:
            all_loras = [entry['file'] for entry in lora_catalog.get_all_entries()]
            if not all_loras:
                all_loras = ["No LoRAs indexed yet"]
        except:
            all_loras = ["Error loading LoRAs"]
        
        # Fetch all available models from both providers
        all_models, vision_models = fetch_all_available_models()
        
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "A beautiful landscape at sunset",
                    "tooltip": "Your creative idea or prompt for image/video generation. Describe what you want to create, and the AI will select relevant LoRAs and expand this into a detailed prompt."
                }),
                "base_model": (families, {
                    "default": families[0] if families else "Unknown",
                    "tooltip": "Select your base model family (e.g., Flux-1, SDXL, Qwen-Image). This filters LoRAs to only those compatible with your chosen model. For example, Flux LoRAs won't work with SDXL models."
                }),
                "indexing_model": (all_models, {
                    "default": all_models[0] if all_models else "groq: llama-3.1-8b-instant",
                    "tooltip": "LLM model to use for indexing new LoRAs. This analyzes Civitai metadata to extract summaries, trigger words, and tags. Recommended: groq: llama-3.1-8b-instant (fast and accurate)."
                }),
                "prompting_model": (all_models, {
                    "default": "gemini: gemini-1.5-flash" if "gemini: gemini-1.5-flash" in all_models else all_models[0],
                    "tooltip": "LLM model for generating prompts and selecting LoRAs. If using an image input, choose a vision-capable model (e.g., gemini: gemini-1.5-flash). Otherwise any model works."
                }),
            },
            "optional": FlexibleOptionalInputType(type=any_type, data={
                "model": ("MODEL", {
                    "tooltip": "Input MODEL from your checkpoint loader. LoRAs will be applied to this model and returned."
                }),
                "clip": ("CLIP", {
                    "tooltip": "Input CLIP from your checkpoint loader. LoRAs will be applied to CLIP and returned."
                }),
                "image": ("IMAGE", {
                    "tooltip": "Optional reference image for vision-capable models. The AI can analyze this image to better select relevant LoRAs and generate contextual prompts. Requires a vision model (e.g., gemini: gemini-1.5-flash)."
                }),
                "custom_instruction": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Override the default prompting instructions. Define your desired prompt style, length, and format here. Example: 'Create a minimalist 50-word prompt focusing on mood'. Leave empty to use the default cinematic 80-100 word style."
                }),
                "system_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Override the system prompt that defines the LLM's role. This sets the AI's personality and capabilities. Example: 'You are a professional cinematographer'. Leave empty to use the default prompt expert role."
                }),
                "enable_negative_prompt": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Generate a negative prompt output. Enable this for older models (SD1.5, SDXL) that benefit from negative prompts. Modern models (Flux, Qwen) typically don't need this."
                }),
                "reindex_on_run": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Automatically detect and index new LoRA files when you run this node. Turn OFF after initial indexing to improve performance. Use the LoRA Manager node for manual indexing control."
                }),
                "temperature": ("FLOAT", {
                    "default": 0.85,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "LLM creativity level. Higher = more creative/varied prompts (0.8-1.2), Lower = more focused/consistent prompts (0.3-0.7). Default 0.85 works well for most cases."
                }),
                "max_loras": ("INT", {
                    "default": 6,
                    "min": 1,
                    "max": 20,
                    "tooltip": "Maximum number of LoRAs to auto-select. More LoRAs = more complex generations but can cause conflicts. Recommended: 3-6 for best results. Character LoRAs don't count toward this limit."
                }),
                "trigger_position": (["llm_decides", "start", "end"], {
                    "default": "llm_decides",
                    "tooltip": "Where to place trigger words in the prompt. 'llm_decides' (recommended): AI integrates them naturally. 'start': All triggers at beginning. 'end': All triggers at end."
                }),
            }),
            "hidden": {
                "manual_loras": ("STRING", {
                    "default": "",
                }),
            },
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "prompt", "negative_prompt", "selected_loras_json")
    FUNCTION = "process"
    CATEGORY = "loaders/Autopilot LoRA"
    DESCRIPTION = "Smart LoRA loader with automatic selection and LLM-powered prompt generation"
    OUTPUT_NODE = False
    
    def __init__(self):
        """Initialize the node."""
        self.indexing_done = False
        self._llm_prompt_request = {}
        self._llm_selection_details = []
        self._llm_prompt_model = ""
    
    def process(
        self,
        prompt: str,
        base_model: str,
        indexing_model: str,
        prompting_model: str,
        model: Any = None,
        clip: Any = None,
        image: Any = None,
        custom_instruction: str = "",
        system_prompt: str = "",
        enable_negative_prompt: bool = False,
        reindex_on_run: bool = False,
        temperature: float = 0.85,
        max_loras: int = 6,
        trigger_position: str = "llm_decides",
        manual_loras: str = "",
        **kwargs  # Capture dynamic lora_* inputs from JavaScript
    ) -> Tuple[Any, Any, str, str, str]:
        """
        Main processing function.
        Handles both manual LoRAs (via dynamic lora_* inputs) and auto-selection.
        
        Returns:
            Tuple of (MODEL, CLIP, final_prompt, negative_prompt, selected_loras_json)
        """
        print("\n" + "="*60)
        print("SmartPowerLoRALoader Processing")
        print("="*60)
        
        # Parse provider and model from prefixed strings
        indexing_provider, indexing_model_name = parse_model_string(indexing_model)
        prompting_provider, prompting_model_name = parse_model_string(prompting_model)
        
        # Step 1: Reindex if needed
        if reindex_on_run and not self.indexing_done:
            self._reindex_new_loras(indexing_provider, indexing_model_name)
            self.indexing_done = True
        
        # Step 2: Parse manual LoRAs from dynamic kwargs (lora_1, lora_2, etc.)
        manual_lora_entries: List[Dict[str, Any]] = []
        manual_lora_files: Set[str] = set()

        def add_manual_entry(file_name: str, strength_value: Optional[float] = None, strength_clip_value: Optional[float] = None):
            """Helper to add or update a manual LoRA entry."""
            if not file_name:
                return

            normalized_name = str(file_name).strip()
            if not normalized_name:
                return

            # Update existing entry if already added
            if normalized_name in manual_lora_files:
                if strength_value is not None or strength_clip_value is not None:
                    for entry in manual_lora_entries:
                        entry_file = entry.get('file')
                        if entry_file and entry_file.strip() == normalized_name:
                            if strength_value is not None:
                                try:
                                    entry['manual_strength'] = float(strength_value)
                                except (TypeError, ValueError):
                                    entry['manual_strength'] = 1.0
                            if strength_clip_value is not None:
                                try:
                                    entry['manual_strength_clip'] = float(strength_clip_value)
                                except (TypeError, ValueError):
                                    entry['manual_strength_clip'] = entry.get('manual_strength', 1.0)
                            break
                return

            entry = lora_catalog.get_entry_by_name(normalized_name)
            if not entry:
                print(f"[SmartPowerLoRALoader] Warning: Manual LoRA not found in catalog: {normalized_name}")
                return

            entry_copy = dict(entry)
            entry_file = entry_copy.get('file') or normalized_name
            entry_copy['file'] = entry_file

            if strength_value is not None:
                try:
                    entry_copy['manual_strength'] = float(strength_value)
                except (TypeError, ValueError):
                    entry_copy['manual_strength'] = entry_copy.get('manual_strength', entry_copy.get('default_weight', 1.0))

            if strength_clip_value is not None:
                try:
                    entry_copy['manual_strength_clip'] = float(strength_clip_value)
                except (TypeError, ValueError):
                    entry_copy['manual_strength_clip'] = entry_copy.get('manual_strength', entry_copy.get('default_weight', 1.0))

            manual_lora_entries.append(entry_copy)
            manual_lora_files.add(entry_file)

        for key, value in kwargs.items():
            key_upper = key.upper()
            if key_upper.startswith('LORA_') and isinstance(value, dict):
                if value.get('on') and value.get('lora'):
                    lora_file = value['lora']
                    add_manual_entry(
                        lora_file,
                        strength_value=value.get('strength', 1.0),
                        strength_clip_value=value.get('strengthTwo', value.get('strength', 1.0))
                    )

        dynamic_manual_count = len(manual_lora_files)

        # Fallback: also respect the hidden manual_loras string (legacy/serialization)
        manual_from_string = []
        if isinstance(manual_loras, str) and manual_loras.strip():
            manual_from_string = [
                token.strip()
                for token in manual_loras.split(',')
                if token and token.strip() and token.strip().lower() != "none"
            ]
            for token in manual_from_string:
                add_manual_entry(token)

        print(f"Manual LoRAs from dynamic inputs: {dynamic_manual_count}")
        added_from_string = len(manual_lora_files) - dynamic_manual_count
        if added_from_string > 0:
            print(f"Manual LoRAs from hidden field: {added_from_string}")
        
        # Step 3: Auto-select LoRAs (always enabled now)
        auto_selected_entries = []
        final_prompt = prompt
        negative_prompt = ""
        
        # Always do auto-selection
        auto_selected_entries = self._autoselect_loras(
            base_context=prompt,
            base_model=base_model,
            allowlist_loras="",  # Removed allowlist feature for now
            prompting_provider=prompting_provider,
            prompting_model=prompting_model_name,
            init_image=image,
            temperature=temperature,
            max_loras=max_loras,
            system_prompt=system_prompt,
            custom_instruction=custom_instruction,
            trigger_position=trigger_position,
            include_negative_prompt=enable_negative_prompt
        )
        
        print(f"Auto-selected LoRAs: {len(auto_selected_entries)}")
        
        # Step 4: Merge manual + auto LoRAs
        all_selected = merge_manual_and_auto_loras(manual_lora_entries, auto_selected_entries)
        print(f"Total LoRAs to apply: {len(all_selected)}")
        
        # Step 5: Build prompt
        if trigger_position == "llm_decides":
            # LLM already generated the prompt
            final_prompt = getattr(self, '_llm_generated_prompt', prompt)
            negative_prompt = getattr(self, '_llm_generated_negative', "")
        else:
            # Build prompt with triggers at specific position
            final_prompt = build_final_prompt(
                base_context=prompt,
                selected_loras=all_selected,
                insert_position=trigger_position
            )
        
        # Step 6: Apply LoRAs to model and clip
        if model is not None and clip is not None and all_selected:
            model, clip = apply_loras_to_model_clip(model, clip, all_selected)
        elif model is None or clip is None:
            print("[SmartPowerLoRALoader] Warning: MODEL or CLIP not provided, LoRAs not applied")
        
        # Step 7: Handle negative prompt
        if not enable_negative_prompt:
            negative_prompt = ""
        
        # Step 8: Build selection JSON for debugging
        manual_lora_names = [entry['file'] for entry in manual_lora_entries]
        selection_json = self._build_selection_json(all_selected, manual_lora_names)
        
        print(f"Final prompt length: {len(final_prompt)} chars")
        print("="*60 + "\n")
        
        return (model, clip, final_prompt, negative_prompt, selection_json)
    
    def _reindex_new_loras(self, indexing_provider: str, indexing_model: str):
        """Detect and index new LoRA files."""
        print("\n[Indexing] Checking for new LoRA files...")
        
        new_files = lora_catalog.detect_new_loras()
        
        if not new_files:
            print("[Indexing] No new LoRAs detected")
            return
        
        print(f"[Indexing] Found {len(new_files)} new LoRA(s)")
        
        # Get API key
        if indexing_provider == "groq":
            api_key = config.get_groq_api_key()
        elif indexing_provider == "gemini":
            api_key = config.get_gemini_api_key()
        else:
            print(f"[Indexing] Unknown provider: {indexing_provider}")
            return
        
        if not api_key:
            print(f"[Indexing] No API key for {indexing_provider}, indexing without LLM")
            # Index with basic metadata only
            for file_path in new_files:
                lora_catalog.index_lora_basic(file_path)
            lora_catalog.save_catalog()
            return
        
        # Get known families for context
        known_families = lora_catalog.get_known_base_families()
        
        # Index each file ONE BY ONE with progress tracking
        total_files = len(new_files)
        for idx, file_path in enumerate(new_files, 1):
            print(f"\n[Indexing] Processing LoRA {idx}/{total_files}: {file_path.name}")
            print("-" * 60)
            
            # Basic indexing first
            print(f"[Indexing] Step 1/4: Computing hash and extracting safetensors metadata...")
            file_hash = lora_catalog.index_lora_basic(file_path)
            entry = lora_catalog.get_entry(file_hash)
            
            if not entry:
                print(f"[Indexing] ❌ Failed to create catalog entry")
                continue
            
            print(f"[Indexing] ✓ Basic metadata extracted")
            
            # Try LLM indexing if we have Civitai text
            civitai_text = entry.get('civitai_text', '')
            if civitai_text:
                print(f"[Indexing] Step 2/4: Extracting structured data with LLM...")
                
                success, extracted, error = index_with_llm(
                    civitai_text=civitai_text,
                    provider_name=indexing_provider,
                    model_name=indexing_model,
                    api_key=api_key,
                    known_families=known_families,
                    filename=file_path.name,
                    image_entries=entry.get('images', []),
                    cache_key=file_hash
                )
                
                if success and extracted:
                    print(f"[Indexing] ✓ Extracted: {len(extracted.get('trainedWords', []))} triggers, {len(extracted.get('tags', []))} tags")
                    
                    # Suggest base family
                    print(f"[Indexing] Step 3/4: Determining base model compatibility...")
                    base_family = suggest_base_family_with_llm(
                        civitai_text=civitai_text,
                        known_families=known_families,
                        provider_name=indexing_provider,
                        model_name=indexing_model,
                        api_key=api_key
                    )
                    
                    print(f"[Indexing] ✓ Base model: {base_family}")
                    
                    base_compat = [base_family] if base_family != 'Unknown' else entry.get('base_compat', ['Unknown'])
                    
                    # Update catalog entry
                    print(f"[Indexing] Step 4/4: Saving to catalog...")
                    lora_catalog.mark_llm_indexed(
                        file_hash=file_hash,
                        summary=extracted['summary'],
                        trained_words=extracted['trainedWords'],
                        tags=extracted['tags'],
                        base_compat=base_compat,
                        recommended_strength=extracted.get('recommendedStrength')
                    )
                    print(f"[Indexing] ✅ Successfully indexed: {entry.get('display_name', file_path.name)}")
                else:
                    print(f"[Indexing] ❌ LLM extraction failed: {error}")
            else:
                print(f"[Indexing] ⚠️ No Civitai data available, indexed with basic metadata only")
            
            # Save after each LoRA (preserve progress)
            lora_catalog.save_catalog()
            print(f"[Indexing] Progress: {idx}/{total_files} LoRAs processed")
        
        # Final save (redundant but safe)
        lora_catalog.save_catalog()
        print(f"\n[Indexing] ✅ Completed indexing all {total_files} LoRAs")
        
        # Generate rgthree info files
        if HAS_COMFY:
            lora_dir = lora_catalog.get_lora_directory()
            if lora_dir:
                generate_info_files_for_catalog(lora_catalog.get_all_entries(), lora_dir)
    
    def _parse_lora_list(self, lora_string: str) -> List[str]:
        """Parse comma-separated LoRA list."""
        if not lora_string or not lora_string.strip():
            return []
        
        loras = [l.strip() for l in lora_string.split(',')]
        return [l for l in loras if l]
    
    def _autoselect_loras(
        self,
        base_context: str,
        base_model: str,
        allowlist_loras: str,
        prompting_provider: str,
        prompting_model: str,
        init_image: Any,
        temperature: float,
        max_loras: int,
        system_prompt: str = "",
        custom_instruction: str = "",
        trigger_position: str = "llm_decides",
        include_negative_prompt: bool = False
    ) -> List[Dict[str, Any]]:
        """Auto-select LoRAs using LLM."""
        print("\n[Auto-Select] Starting LoRA selection...")
        self._llm_prompt_request = {}
        self._llm_selection_details = []
        self._llm_prompt_model = f"{prompting_provider}: {prompting_model}"
        
        # Parse allowlist
        allowlist = self._parse_lora_list(allowlist_loras)
        
        # Get candidates
        candidates = get_candidates_for_autoselect(
            catalog_entries=lora_catalog.get_all_entries(),
            base_model_family=base_model,
            allowlist=allowlist,
            base_context=base_context,
            max_candidates=30
        )
        
        print(f"[Auto-Select] Found {len(candidates)} candidates")
        
        if not candidates:
            print("[Auto-Select] No candidates available")
            return []
        
        # Get API key
        if prompting_provider == "groq":
            api_key = config.get_groq_api_key()
        elif prompting_provider == "gemini":
            api_key = config.get_gemini_api_key()
        else:
            print(f"[Auto-Select] Unknown provider: {prompting_provider}")
            return []
        
        if not api_key:
            print(f"[Auto-Select] No API key for {prompting_provider}")
            return []
        
        # Call LLM
        success, result, error = prompt_with_llm(
            base_context=base_context,
            candidates=candidates,
            provider_name=prompting_provider,
            model_name=prompting_model,
            api_key=api_key,
            image=init_image,
            temperature=temperature,
            max_tokens=1024,
            system_prompt=system_prompt,
            custom_instruction=custom_instruction,
            max_loras=max_loras,
            trigger_position=trigger_position,
            include_negative_prompt=include_negative_prompt
        )
        
        if not success:
            print(f"[Auto-Select] LLM error: {error}")
            self._llm_prompt_request = {}
            self._llm_selection_details = []
            return []
        
        # Store LLM-generated prompt
        self._llm_generated_prompt = result['prompt']
        self._llm_generated_negative = result.get('negative_prompt', '')
        
        raw_prompt = result.get('raw_prompt', '')
        prompt_metadata = result.get('prompt_metadata')
        if isinstance(prompt_metadata, dict):
            debug_prompt = dict(prompt_metadata)
            debug_prompt.setdefault('composed_prompt', raw_prompt)
        else:
            debug_prompt = {"composed_prompt": raw_prompt}
        debug_prompt.setdefault('model', self._llm_prompt_model)
        self._llm_prompt_request = debug_prompt
        
        truncated_selection = []
        for entry in result.get('selected_loras', [])[:max_loras]:
            if not isinstance(entry, dict):
                continue
            entry_copy = {
                "name": entry.get('name', ''),
                "used_triggers": list(entry.get('used_triggers', [])) if isinstance(entry.get('used_triggers'), list) else []
            }
            truncated_selection.append(entry_copy)
        self._llm_selection_details = truncated_selection
        
        # Resolve selected LoRAs
        selected = resolve_selected_loras_from_llm(
            llm_selection=truncated_selection,
            catalog_entries=candidates,
            selection_metadata=truncated_selection
        )
        
        return selected
    
    def _build_selection_json(self, selected_loras: List[Dict[str, Any]], manual_list: List[str]) -> str:
        """Build JSON string of selected LoRAs for debugging."""
        prompt_debug = getattr(self, "_llm_prompt_request", {})
        if isinstance(prompt_debug, str):
            prompt_debug = {"composed_prompt": prompt_debug}
        selection_details = getattr(self, "_llm_selection_details", [])
        llm_model = getattr(self, "_llm_prompt_model", "")
        
        selection_lookup = {
            item['name']: item
            for item in selection_details
            if isinstance(item, dict) and item.get('name')
        }
        
        output = {
            "manual_loras": manual_list,
            "selected_loras": [],
            "llm_prompt": prompt_debug,
            "llm_selection_details": selection_details,
            "llm_model": llm_model
        }
        
        for lora in selected_loras:
            file_name = lora.get('file', '')
            selection_source = lora.get('selection_source', 'auto_llm')
            is_manual = file_name in manual_list or selection_source == 'manual_input'
            catalog_triggers = [
                str(trigger).strip()
                for trigger in (lora.get('trained_words') or [])
                if isinstance(trigger, str) and trigger.strip()
            ]
            catalog_tags = [
                str(tag).strip()
                for tag in (lora.get('tags') or [])
                if isinstance(tag, str) and tag.strip()
            ]
            
            llm_meta = selection_lookup.get(file_name, {})
            used_triggers = lora.get('llm_used_triggers') or llm_meta.get('used_triggers', []) or []
            used_triggers = [
                str(trigger).strip()
                for trigger in used_triggers
                if isinstance(trigger, str) and trigger.strip()
            ]

            output["selected_loras"].append({
                "file": file_name,
                "display_name": lora.get('display_name', ''),
                "selection_source": "manual_input" if is_manual else "auto_llm",
                "llm_used_triggers": used_triggers,
                "catalog_summary": lora.get('summary') or lora.get('description', ''),
                "catalog_triggers": catalog_triggers,
                "catalog_tags": catalog_tags,
                "default_weight": lora.get('default_weight', 1.0)
            })
        
        return json.dumps(output, indent=2)


# Node registration
NODE_CLASS_MAPPINGS = {
    "SmartPowerLoRALoader": SmartPowerLoRALoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SmartPowerLoRALoader": "⚡ Smart Power LoRA Loader (Autopilot)"
}
