"""
Indexing LLM Logic
Uses LLM providers to extract structured metadata from Civitai text.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from PIL import Image

from ..llm_providers.groq_provider import GroqProvider
from ..llm_providers.gemini_provider import GeminiProvider
from .utils import safe_json_loads, validate_json_schema
from .base_model_mapping import base_model_mapper
from .civitai_utils import download_civitai_image


# JSON schema for indexing output
INDEXING_SCHEMA_FIELDS = ['summary', 'trainedWords', 'tags', 'recommendedStrength']


# JSON template example for indexing
INDEXING_JSON_TEMPLATE = """{
  "summary": "One to three sentences (≈250-300 chars) describing what this LoRA does/adds/enhances, highlighting subject/style cues",
  "trainedWords": ["exact_trigger_word_1", "exact_trigger_word_2", "exact_trigger_word_3"],
  "tags": ["style_tag", "category_tag", "theme_tag", "feature_tag", "quality_tag"],
  "recommendedStrength": 1.0
}"""


INDEXING_SYSTEM_PROMPT = """You are a metadata extraction specialist. Your task is to extract structured information from LoRA model descriptions and their official gallery samples. Another downstream prompting assistant will rely on your JSON to decide which LoRA to use for a user's image request, so accuracy and descriptive detail are critical.

Extract the following information:
1. summary: Provide 1-3 tightly written sentences (up to ~300 characters total) that explain exactly what the LoRA does, improves or tries to add, the visual style or subject focus, and any standout use cases or also limitations. Also include prompting tips given by the creator. Dont include technical details like Base model, sampler, steps, aspect ratio, resolution etc.
2. trainedWords: An array of exact trigger words or sentences needed to activate this LoRA (from the text, not made up, may also have none)
3. tags: An array of 2-5 descriptive tags/keywords for this LoRA
4. recommendedStrength: The suggested LoRA strength value as a decimal number between 0.2 and 2.0. If no recommendation is given, default to 1.0. Never exceed this range.

IMPORTANT RULES:
- Output ONLY valid JSON matching this exact format
- Pay attention to the provided gallery images and their prompts to understand the visual style or subject matter
- trainedWords must be EXACT words from the description, not invented
- If no trigger words are mentioned, use an empty array []
- Summary must contain 2-3 sentences (≈300 characters) that clearly communicate purpose, style, and ideal usage but no technical details.
- Keep the tone factual and actionable so another model can decide whether to apply this LoRA
- Tags should be lowercase, single words or short phrases
- recommendedStrength must be a numeric value (float) and roughly between 0.2 and 2.0 inclusive
- Do NOT add any explanation, just the JSON object

REQUIRED JSON OUTPUT FORMAT:
{
  "summary": "Two crisp sentences that explain what the LoRA creates and when to use it.",
  "trainedWords": ["trigger1", "trigger2"],
  "tags": ["tag1", "tag2", "tag3"],
  "recommendedStrength": 1.0
}"""


def create_indexing_prompt(
    civitai_text: str,
    known_families: List[str],
    filename: str = "",
    image_context: str = ""
) -> str:
    """
    Create the indexing prompt with context.
    
    Args:
        civitai_text: Text from Civitai metadata
        known_families: List of already known base model families
        filename: Optional filename of the LoRA for additional context
        image_context: Optional formatted text describing gallery prompts
        
    Returns:
        Full prompt for LLM
    """
    filename_context = f"\n\nLoRA Filename: {filename}" if filename else ""
    gallery_context = f"\n\nCreator Gallery Prompts:\n{image_context}" if image_context else ""
    
    prompt = f"""Extract structured metadata from this LoRA description:

{civitai_text}{filename_context}{gallery_context}

Known base model families (for reference): {', '.join(known_families) if known_families else 'None yet'}

Remember: A downstream prompting LLM will read your summary to decide whether this LoRA should be applied to future image requests. Be descriptive about theme, subjects, and aesthetic so the other model can make informed choices.

You MUST output ONLY the following JSON format (no other text):
{INDEXING_JSON_TEMPLATE}

Your JSON output:"""
    
    return prompt


def parse_indexing_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse and validate indexing LLM response.
    
    Args:
        response_text: Raw LLM response
        
    Returns:
        Parsed and validated dict or None
    """
    # Try to parse JSON
    data = safe_json_loads(response_text)
    if not data:
        return None
    
    # Validate required fields
    is_valid, error = validate_json_schema(data, INDEXING_SCHEMA_FIELDS)
    if not is_valid:
        print(f"[IndexingLLM] Invalid schema: {error}")
        return None
    
    # Validate types
    if not isinstance(data['summary'], str):
        return None
    if not isinstance(data['trainedWords'], list):
        return None
    if not isinstance(data['tags'], list):
        return None
    # recommendedStrength can be int/float/str convertible
    recommended_raw = data['recommendedStrength']
    try:
        recommended_value = float(str(recommended_raw).strip())
    except Exception:
        recommended_value = 1.0
    # Clamp to allowed range
    recommended_value = max(0.2, min(2.0, recommended_value))
    
    # Clean and normalize
    result = {
        'summary': data['summary'].strip()[:400],  # Allow longer context-rich summary
        'trainedWords': [w.strip() for w in data['trainedWords'] if isinstance(w, str) and w.strip()],
        'tags': [t.strip().lower() for t in data['tags'] if isinstance(t, str) and t.strip()][:15],  # Max 15 tags
        'recommendedStrength': recommended_value
    }
    
    return result


def prepare_gallery_images(
    image_entries: Optional[List[Dict[str, Any]]],
    cache_key: str
) -> Tuple[List[Image.Image], str]:
    """
    Download and load gallery images for vision-capable LLMs.
    
    Args:
        image_entries: List of image metadata dicts
        cache_key: Cache directory key (typically the model hash)
        
    Returns:
        Tuple of (list of PIL Images, formatted text describing prompts)
    """
    if not image_entries:
        return [], ""
    
    prepared_images: List[Image.Image] = []
    prompt_lines: List[str] = []
    
    for idx, entry in enumerate(image_entries[:5], 1):
        url = entry.get('url', '')
        prompt_text = (entry.get('prompt') or "").strip()
        negative_text = (entry.get('negative_prompt') or "").strip()
        
        line = f"Image {idx} prompt: {prompt_text if prompt_text else '[missing prompt]'}"
        prompt_lines.append(line)
        if negative_text:
            prompt_lines.append(f"Image {idx} negative prompt: {negative_text}")
        if url:
            prompt_lines.append(f"Image {idx} url: {url}")
        
        # Try to reuse cached path if present
        local_path = entry.get('local_path')
        image_path: Optional[Path] = None
        
        if isinstance(local_path, str) and local_path:
            candidate = Path(local_path)
            if candidate.exists():
                image_path = candidate
        
        if image_path is None and url:
            downloaded = download_civitai_image(url, cache_key, idx)
            if downloaded:
                image_path = downloaded
                entry['local_path'] = str(downloaded)
        
        if not image_path:
            continue
        
        try:
            with Image.open(image_path) as img:
                converted = img.convert("RGB")
            prepared_images.append(converted)
        except Exception as exc:
            print(f"[IndexingLLM] Failed to load gallery image {image_path}: {exc}")
            continue
    
    return prepared_images, "\n".join(prompt_lines)


def index_with_llm(
    civitai_text: str,
    provider_name: str,
    model_name: str,
    api_key: str,
    known_families: List[str],
    filename: str = "",
    image_entries: Optional[List[Dict[str, Any]]] = None,
    cache_key: Optional[str] = None
) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Use LLM to index Civitai text and extract metadata.
    
    Args:
        civitai_text: Text from Civitai
        provider_name: 'groq' or 'gemini'
        model_name: Model to use
        api_key: API key for provider
        known_families: List of already known base model families
        filename: Optional filename of the LoRA for additional context
        image_entries: Optional list of gallery images with prompts
        cache_key: Cache identifier for image downloads (e.g., file hash)
        
    Returns:
        Tuple of (success, extracted_data, error_message)
    """
    # Create provider
    try:
        if provider_name.lower() == 'groq':
            provider = GroqProvider(api_key)
        elif provider_name.lower() == 'gemini':
            provider = GeminiProvider(api_key)
        else:
            return False, None, f"Unknown provider: {provider_name}"
    except Exception as e:
        return False, None, f"Provider initialization error: {str(e)}"
  
    # Prepare gallery images if available
    gallery_cache_key = cache_key or filename or "civitai_gallery"
    gallery_images, gallery_context = prepare_gallery_images(image_entries, gallery_cache_key)
    
    # Build prompt with filename and gallery context
    prompt = create_indexing_prompt(civitai_text, known_families, filename, gallery_context)
    
    # Generate with LLM (vision if images available)
    if gallery_images:
        if not provider.supports_vision(model_name):
            return False, None, f"Model {model_name} does not support vision. Please select a vision-capable model for indexing."
        
        success, response, error = provider.generate_with_image(
            prompt=prompt,
            image=gallery_images,
            model=model_name,
            system_message=INDEXING_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=512
        )
    else:
        success, response, error = provider.generate_text(
            prompt=prompt,
            model=model_name,
            system_message=INDEXING_SYSTEM_PROMPT,
            temperature=0.3,  # Low temperature for consistent extraction
            max_tokens=512
        )
    
    if not success:
        return False, None, f"LLM generation error: {error}"
    
    # Parse response
    extracted = parse_indexing_response(response)
    if not extracted:
        return False, None, "Failed to parse LLM response as valid JSON"
    
    return True, extracted, ""


def suggest_base_family_with_llm(
    civitai_text: str,
    known_families: List[str],
    provider_name: str,
    model_name: str,
    api_key: str
) -> str:
    """
    Use LLM to suggest the best base model family from known families.
    
    Args:
        civitai_text: Text from Civitai
        known_families: List of known base families to choose from
        provider_name: 'groq' or 'gemini'
        model_name: Model to use
        api_key: API key
        
    Returns:
        Suggested family name or 'Unknown'
    """
    # First try rule-based approach
    suggested = base_model_mapper.suggest_family_for_llm(civitai_text, known_families)
    if suggested != 'Unknown':
        return suggested
    
    # If no match and we have known families, ask LLM
    if not known_families:
        return 'Unknown'
    
    try:
        if provider_name.lower() == 'groq':
            provider = GroqProvider(api_key)
        elif provider_name.lower() == 'gemini':
            provider = GeminiProvider(api_key)
        else:
            return 'Unknown'
    except:
        return 'Unknown'
    
    system_msg = f"""You are a base model classifier. Choose the EXACT family name from the list that best matches this LoRA.
Available families: {', '.join(known_families)}
Output ONLY the family name, nothing else. If no match, output: Unknown"""
    
    prompt = f"""LoRA Description:
{civitai_text[:500]}

Which base model family?"""
    
    success, response, _ = provider.generate_text(
        prompt=prompt,
        model=model_name,
        system_message=system_msg,
        temperature=0.1,
        max_tokens=50
    )
    
    if success:
        # Clean response
        family = response.strip().strip('"').strip("'")
        if family in known_families:
            return family
    
    return 'Unknown'
