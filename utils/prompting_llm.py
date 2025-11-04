"""
Prompting LLM Logic
Uses LLM to select relevant LoRAs and generate final prompt with trigger words.
"""
import json
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image

from ..llm_providers.groq_provider import GroqProvider
from ..llm_providers.gemini_provider import GeminiProvider
from .utils import safe_json_loads, validate_json_schema, tensor_to_pil


# JSON schema for prompting output
PROMPTING_SCHEMA_FIELDS = ['prompt', 'selected_loras']


# JSON template example for prompting
def build_prompting_json_template(include_negative_prompt: bool) -> str:
    """Build the JSON template string shown to the LLM."""
    selected_entry_template = """    {
      "name": "exact_lora_filename.safetensors",
      "reason": "Brief explanation why this LoRA helps the request",
      "used_triggers": ["trigger_word_1", "trigger_word_2"]
    }"""
    
    if include_negative_prompt:
        template = f"""{{\n  "prompt": "Detailed positive prompt that incorporates all required trigger words",\n  "negative_prompt": "Targeted negative prompt for quality/style control",\n  "selected_loras": [\n{selected_entry_template}\n  ]\n}}"""
    else:
        template = f"""{{\n  "prompt": "Detailed positive prompt that incorporates all required trigger words",\n  "selected_loras": [\n{selected_entry_template}\n  ]\n}}"""
    
    return template


# Default system prompt for prompting LLM
DEFAULT_SYSTEM_PROMPT = """You are a creative prompt engineering assistant. For every request, determine whether the user wants an original generation, an edited image, or a video, and tailor your wording appropriately. Provide precise, actionable guidance that maximizes quality while respecting the user's intent."""


DEFAULT_PROMPT_STYLE_INSTRUCTION = """Enhance the user's idea into a vivid, professional prompt. Keep wording concise but expressive (roughly 60-100 words unless the request implies otherwise). Highlight key subjects, styling cues, atmosphere, and technical details. Maintain clarity so another artist or AI model can follow it without ambiguity."""


def build_candidate_list_text(candidates: List[Dict[str, Any]], max_candidates: int = 30) -> str:
    """
    Build a text representation of candidate LoRAs for the LLM.
    
    Args:
        candidates: List of LoRA catalog entries
        max_candidates: Maximum number to include
        
    Returns:
        Formatted text for LLM
    """
    lines = ["Available LoRAs (each entry lists what it does and which trigger words to use):"]
    
    for i, lora in enumerate(candidates[:max_candidates]):
        summary = lora.get('summary') or lora.get('display_name', '')
        description = lora.get('description', '')
        base_models = lora.get('base_compat', []) or []
        default_weight = lora.get('default_weight')
        triggers = lora.get('trained_words', []) or []
        tags = lora.get('tags', []) or []
        
        lines.append(f"{i+1}. {lora['file']}")
        
        if summary:
            lines.append(f"   Summary: {summary}")
        if description:
            lines.append(f"   Details: {description}")
        if base_models:
            lines.append(f"   Base models: {', '.join(base_models)}")
        if default_weight is not None:
            lines.append(f"   Suggested strength: {default_weight}")
        if triggers:
            lines.append(f"   Trigger words: {', '.join(triggers[:8])}")
        if tags:
            lines.append(f"   Tags: {', '.join(tags[:6])}")
        
        lines.append("")
    
    return '\n'.join(lines).strip()


def create_prompting_prompt(
    base_context: str,
    candidates: List[Dict[str, Any]],
    has_image: bool = False,
    max_loras: int = 6,
    trigger_position: str = "llm_decides",
    include_negative_prompt: bool = False
) -> str:
    """
    Create the prompting prompt.
    
    Args:
        base_context: User's input context/idea
        candidates: Pre-filtered candidate LoRAs
        has_image: Whether an image is provided
        max_loras: Maximum LoRAs to select
        trigger_position: Placement rule for trigger words
        include_negative_prompt: Whether a negative prompt should be generated
        
    Returns:
        Full prompt for LLM
    """
    candidate_text = build_candidate_list_text(candidates)
    
    image_note = ""
    if has_image:
        image_note = "\nNote: An image is provided. Consider it when selecting LoRAs and generating the prompt."
    
    json_template = build_prompting_json_template(include_negative_prompt)
    
    trigger_note_map = {
        "start": "Desired trigger placement: place trigger words at the beginning of the positive prompt.",
        "end": "Desired trigger placement: place trigger words at the end of the positive prompt.",
        "llm_decides": "Desired trigger placement: integrate trigger words naturally where they fit best."
    }
    trigger_note = trigger_note_map.get(trigger_position.lower(), trigger_note_map["llm_decides"])
    
    prompt = f"""User request:
{base_context}
{image_note}

{candidate_text}

Additional context:
- Maximum LoRAs to return: {max_loras}
- {trigger_note}
- Trigger words must match the exact wording listed under each candidate's "Trigger words" line.
- Use the provided summaries/descriptions to justify each selection.

JSON TEMPLATE (copy this structure exactly, replacing placeholders with your content):
{json_template}

Return only the completed JSON object (no extra commentary)."""
    
    return prompt


def parse_prompting_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse and validate prompting LLM response.
    
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
    is_valid, error = validate_json_schema(data, PROMPTING_SCHEMA_FIELDS)
    if not is_valid:
        print(f"[PromptingLLM] Invalid schema: {error}")
        return None
    
    # Validate types
    if not isinstance(data['prompt'], str):
        return None
    if not isinstance(data['selected_loras'], list):
        return None
    
    # Clean and normalize
    negative_prompt_value = data.get('negative_prompt', '')
    if isinstance(negative_prompt_value, str):
        negative_prompt_value = negative_prompt_value.strip()
    else:
        negative_prompt_value = ""
    
    result = {
        'prompt': data['prompt'].strip(),
        'negative_prompt': negative_prompt_value,
        'selected_loras': []
    }
    
    # Validate selected_loras entries
    for lora in data['selected_loras']:
        if not isinstance(lora, dict):
            continue
        if 'name' not in lora:
            continue
        
        entry = {
            'name': lora['name'].strip(),
            'reason': lora.get('reason', '').strip(),
            'used_triggers': []
        }
        
        # Get triggers
        if 'used_triggers' in lora and isinstance(lora['used_triggers'], list):
            entry['used_triggers'] = [t.strip() for t in lora['used_triggers'] if isinstance(t, str)]
        
        result['selected_loras'].append(entry)
    
    return result


def prompt_with_llm(
    base_context: str,
    candidates: List[Dict[str, Any]],
    provider_name: str,
    model_name: str,
    api_key: str,
    image: Optional[Any] = None,
    temperature: float = 0.85,
    max_tokens: int = 1024,
    system_prompt: str = "",
    custom_instruction: str = "",
    max_loras: int = 6,
    trigger_position: str = "llm_decides",
    include_negative_prompt: bool = False
) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Use LLM to select LoRAs and generate prompt.
    
    Args:
        base_context: User's input context
        candidates: Pre-filtered candidate LoRAs
        provider_name: 'groq' or 'gemini'
        model_name: Model to use
        api_key: API key for provider
        image: Optional image tensor (ComfyUI format)
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        system_prompt: Override system prompt (empty = use DEFAULT_SYSTEM_PROMPT)
        custom_instruction: Override prompt style instruction (empty = use DEFAULT_PROMPT_STYLE_INSTRUCTION)
        max_loras: Maximum number of LoRAs the LLM may select
        trigger_position: Desired placement for trigger words
        include_negative_prompt: Whether to request a negative prompt
        
    Returns:
        Tuple of (success, result_dict, error_message)
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
    
    system_message = system_prompt.strip() if system_prompt and system_prompt.strip() else DEFAULT_SYSTEM_PROMPT
    
    if system_message == DEFAULT_SYSTEM_PROMPT:
        print("[PromptingLLM] Using default system prompt")
    else:
        print("[PromptingLLM] Using provided system prompt override")
    
    user_style_instruction = custom_instruction.strip() if custom_instruction and custom_instruction.strip() else DEFAULT_PROMPT_STYLE_INSTRUCTION
    if user_style_instruction == DEFAULT_PROMPT_STYLE_INSTRUCTION:
        print("[PromptingLLM] Using default prompt style instruction")
    else:
        print("[PromptingLLM] Using provided custom instruction for prompt style")
    
    selection_instruction = build_selection_instruction(max_loras, trigger_position, include_negative_prompt)
    instruction_block = f"{selection_instruction}\n\nPrompt Writing Style:\n{user_style_instruction}"
    
    # Build prompt
    has_image = image is not None
    prompt_body = create_prompting_prompt(
        base_context,
        candidates,
        has_image=has_image,
        max_loras=max_loras,
        trigger_position=trigger_position,
        include_negative_prompt=include_negative_prompt
    )
    prompt = f"{instruction_block}\n\n{prompt_body}"
    prompt_payload = prompt  # Keep full text sent to the LLM for debugging
    
    # Generate with LLM
    if has_image:
        # Convert tensor to PIL if needed
        if not isinstance(image, Image.Image):
            pil_image = tensor_to_pil(image)
        else:
            pil_image = image
        
        # Check if model supports vision
        if not provider.supports_vision(model_name):
            return False, None, f"Model {model_name} does not support vision. Please select a vision model or remove the image input."
        
        success, response, error = provider.generate_with_image(
            prompt=prompt,
            image=pil_image,
            model=model_name,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        success, response, error = provider.generate_text(
            prompt=prompt,
            model=model_name,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    if not success:
        return False, None, f"LLM generation error: {error}"
    
    # Parse response
    result = parse_prompting_response(response)
    if not result:
        return False, None, "Failed to parse LLM response as valid JSON"
    
    # Validate that selected LoRAs exist in candidates
    candidate_names = {c['file'] for c in candidates}
    validated_loras = []
    
    for selected in result['selected_loras']:
        if selected['name'] in candidate_names:
            validated_loras.append(selected)
        else:
            print(f"[PromptingLLM] Warning: LLM selected non-existent LoRA: {selected['name']}")
    
    result['selected_loras'] = validated_loras
    result['raw_prompt'] = prompt_payload
    
    return True, result, ""
def build_selection_instruction(max_loras: int, trigger_position: str, include_negative_prompt: bool) -> str:
    """Create the core instructions for LoRA selection and formatting."""
    trigger_position = (trigger_position or "llm_decides").lower()
    trigger_guidance_map = {
        "start": "Place all trigger words for selected LoRAs at the very beginning of the positive prompt.",
        "end": "Place all trigger words for selected LoRAs at the very end of the positive prompt.",
        "llm_decides": "Integrate trigger words naturally within the positive prompt where they make the most sense."
    }
    trigger_guidance = trigger_guidance_map.get(trigger_position, trigger_guidance_map["llm_decides"])
    
    if include_negative_prompt:
        negative_guidance = "Provide both a positive prompt and a concise negative prompt that helps avoid quality issues."
    else:
        negative_guidance = "Only provide a positive prompt. Do not include a negative prompt or a negative prompt field in the JSON."
    
    return f"""LoRA Selection Rules:
- Review the supplied catalog entries and choose up to {max_loras} LoRAs that best support the user's request.
- Each selected LoRA MUST come from the provided list (use exact filenames) and include the trigger words the LoRA expects.
- When no LoRA is appropriate, return an empty list.

Trigger Placement Requirement:
- {trigger_guidance}

Prompt Output Requirement:
- {negative_guidance}
- The JSON you return must match the template shown later exactly: include the `selected_loras` array, and for each LoRA provide `name`, `reason`, and `used_triggers` (array of trigger words).
- Ensure `used_triggers` only contains trigger words that belong to that specific LoRA."""
