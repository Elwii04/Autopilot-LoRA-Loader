"""
SmartPowerLoRALoader Node
Main ComfyUI custom node that auto-selects LoRAs and generates prompts using LLMs.
"""
import json
from typing import Any, Dict, List, Tuple, Optional
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from utils.config_manager import config
from utils.lora_catalog import lora_catalog
from utils.base_model_mapping import base_model_mapper
from utils.indexing_llm import index_with_llm, suggest_base_family_with_llm
from utils.prompting_llm import prompt_with_llm
from utils.lora_selector import (
    get_candidates_for_autoselect,
    merge_manual_and_auto_loras,
    resolve_selected_loras_from_llm
)
from utils.lora_applicator import apply_loras_to_model_clip
from utils.prompt_builder import build_final_prompt, build_prompt_from_llm_output
from utils.show_info_generator import generate_info_files_for_catalog
from utils.civitai_utils import build_civitai_summary_text

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
        
        # Get all LoRA filenames for allowlist and manual selection
        try:
            all_loras = [entry['file'] for entry in lora_catalog.get_all_entries()]
            if not all_loras:
                all_loras = ["No LoRAs indexed yet"]
        except:
            all_loras = ["Error loading LoRAs"]
        
        # LLM provider options
        providers = ["groq", "gemini"]
        
        # Get models for each provider (simplified - will be dynamic in practice)
        groq_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "deepseek-r1-distill-llama-70b",
            "qwen-qwq-32b",
            "gemma2-9b-it"
        ]
        
        groq_vision_models = [
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct"
        ]
        
        gemini_models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash-exp"
        ]
        
        return {
            "required": {
                "base_context": ("STRING", {
                    "multiline": True,
                    "default": "A beautiful landscape at sunset",
                    "tooltip": "Your idea/context for image generation"
                }),
                "base_model": (families, {
                    "default": families[0] if families else "Unknown",
                    "tooltip": "Select the base model family"
                }),
                "autoselect": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Enable automatic LoRA selection"
                }),
                "indexing_provider": (providers, {
                    "default": "groq",
                    "tooltip": "LLM provider for indexing new LoRAs"
                }),
                "indexing_model": (groq_models, {
                    "default": "llama-3.1-8b-instant",
                    "tooltip": "Model for indexing (text-only)"
                }),
                "prompting_provider": (providers, {
                    "default": "groq",
                    "tooltip": "LLM provider for prompt generation"
                }),
                "prompting_model": (groq_vision_models + gemini_models, {
                    "default": "gemini-1.5-flash",
                    "tooltip": "Model for prompting (can support vision)"
                }),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "Input model to apply LoRAs to"}),
                "clip": ("CLIP", {"tooltip": "Input CLIP to apply LoRAs to"}),
                "init_image": ("IMAGE", {"tooltip": "Optional reference image for vision models"}),
                "allowlist_loras": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Comma-separated list of LoRAs allowed for auto-selection (empty = all)"
                }),
                "manual_loras": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Comma-separated list of LoRAs to always apply (e.g., character LoRAs)"
                }),
                "system_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Override system prompt for the prompting LLM (empty = use default)"
                }),
                "custom_instruction": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Custom instruction for prompt style/format (empty = use default)"
                }),
                "reindex_on_run": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Detect and index new LoRA files on each run"
                }),
                "temperature": ("FLOAT", {
                    "default": 0.85,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "LLM temperature for prompt generation"
                }),
                "max_loras": ("INT", {
                    "default": 6,
                    "min": 1,
                    "max": 20,
                    "tooltip": "Maximum LoRAs to auto-select"
                }),
                "trigger_position": (["start", "end", "llm_decides"], {
                    "default": "llm_decides",
                    "tooltip": "Where to place trigger words in prompt"
                }),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "final_prompt", "negative_prompt", "selected_loras_json")
    FUNCTION = "process"
    CATEGORY = "loaders"
    DESCRIPTION = "Smart LoRA loader with automatic selection and LLM-powered prompt generation"
    
    def __init__(self):
        """Initialize the node."""
        self.indexing_done = False
    
    def process(
        self,
        base_context: str,
        base_model: str,
        autoselect: bool,
        indexing_provider: str,
        indexing_model: str,
        prompting_provider: str,
        prompting_model: str,
        model: Any = None,
        clip: Any = None,
        init_image: Any = None,
        allowlist_loras: str = "",
        manual_loras: str = "",
        system_prompt: str = "",
        custom_instruction: str = "",
        reindex_on_run: bool = True,
        temperature: float = 0.85,
        max_loras: int = 6,
        trigger_position: str = "llm_decides"
    ) -> Tuple[Any, Any, str, str, str]:
        """
        Main processing function.
        
        Returns:
            Tuple of (MODEL, CLIP, final_prompt, negative_prompt, selected_loras_json)
        """
        print("\n" + "="*60)
        print("SmartPowerLoRALoader Processing")
        print("="*60)
        
        # Step 1: Reindex if needed
        if reindex_on_run and not self.indexing_done:
            self._reindex_new_loras(indexing_provider, indexing_model)
            self.indexing_done = True
        
        # Step 2: Parse manual LoRAs
        manual_lora_list = self._parse_lora_list(manual_loras)
        manual_lora_entries = lora_catalog.filter_by_names(manual_lora_list)
        print(f"Manual LoRAs: {len(manual_lora_entries)}")
        
        # Step 3: Auto-select LoRAs (if enabled)
        auto_selected_entries = []
        final_prompt = base_context
        negative_prompt = ""
        
        if autoselect:
            auto_selected_entries = self._autoselect_loras(
                base_context=base_context,
                base_model=base_model,
                allowlist_loras=allowlist_loras,
                prompting_provider=prompting_provider,
                prompting_model=prompting_model,
                init_image=init_image,
                temperature=temperature,
                max_loras=max_loras,
                system_prompt=system_prompt,
                custom_instruction=custom_instruction
            )
            
            print(f"Auto-selected LoRAs: {len(auto_selected_entries)}")
        
        # Step 4: Merge manual + auto LoRAs
        all_selected = merge_manual_and_auto_loras(manual_lora_entries, auto_selected_entries)
        print(f"Total LoRAs to apply: {len(all_selected)}")
        
        # Step 5: Build prompt
        if trigger_position == "llm_decides" and autoselect:
            # LLM already generated the prompt
            final_prompt = getattr(self, '_llm_generated_prompt', base_context)
            negative_prompt = getattr(self, '_llm_generated_negative', "")
        else:
            # Build prompt with triggers
            final_prompt = build_final_prompt(
                base_context=base_context,
                selected_loras=all_selected,
                insert_position=trigger_position if trigger_position != "llm_decides" else "start"
            )
        
        # Step 6: Apply LoRAs to model and clip
        if model is not None and clip is not None and all_selected:
            model, clip = apply_loras_to_model_clip(model, clip, all_selected)
        elif model is None or clip is None:
            print("[SmartPowerLoRALoader] Warning: MODEL or CLIP not provided, LoRAs not applied")
        
        # Step 7: Build selection JSON for debugging
        selection_json = self._build_selection_json(all_selected, manual_lora_list)
        
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
                    known_families=known_families
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
                        is_character=False  # TODO: Add character detection heuristic
                    )
                    print(f"[Indexing] ✅ Successfully indexed: {entry.get('display_name', file_path.name)}")
                else:
                    print(f"[Indexing] ❌ LLM extraction failed: {error}")
            else:
                print(f"[Indexing] ⚠️ No Civitai data available, indexed with basic metadata only")
            
            # Save after each LoRA (preserve progress)
            lora_catalog.save_catalog()
            print(f"[Indexing] Progress: {idx}/{total_files} LoRAs processed")
        
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
        custom_instruction: str = ""
    ) -> List[Dict[str, Any]]:
        """Auto-select LoRAs using LLM."""
        print("\n[Auto-Select] Starting LoRA selection...")
        
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
            custom_instruction=custom_instruction
        )
        
        if not success:
            print(f"[Auto-Select] LLM error: {error}")
            return []
        
        # Store LLM-generated prompt
        self._llm_generated_prompt = result['prompt']
        self._llm_generated_negative = result.get('negative_prompt', '')
        
        # Resolve selected LoRAs
        selected = resolve_selected_loras_from_llm(
            llm_selection=result['selected_loras'][:max_loras],
            catalog_entries=candidates
        )
        
        return selected
    
    def _build_selection_json(self, selected_loras: List[Dict[str, Any]], manual_list: List[str]) -> str:
        """Build JSON string of selected LoRAs for debugging."""
        output = {
            "manual_loras": manual_list,
            "selected_loras": []
        }
        
        for lora in selected_loras:
            output["selected_loras"].append({
                "file": lora['file'],
                "display_name": lora.get('display_name', ''),
                "weight": lora.get('default_weight', 1.0),
                "triggers": lora.get('trained_words', [])
            })
        
        return json.dumps(output, indent=2)


# Node registration
NODE_CLASS_MAPPINGS = {
    "SmartPowerLoRALoader": SmartPowerLoRALoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SmartPowerLoRALoader": "Smart Power LoRA Loader"
}
