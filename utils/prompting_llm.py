"""
Prompting LLM Logic
Uses LLM to select relevant LoRAs and generate final prompt with trigger words.
"""
import json
from typing import Dict, Any, Optional, List, tuple
from PIL import Image
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_providers.groq_provider import GroqProvider
from llm_providers.gemini_provider import GeminiProvider
from utils.utils import safe_json_loads, validate_json_schema, tensor_to_pil


# JSON schema for prompting output
PROMPTING_SCHEMA_FIELDS = ['prompt', 'selected_loras']


# JSON template example for prompting
PROMPTING_JSON_TEMPLATE = """{
  "prompt": "Your detailed 80-100 word video generation prompt here with trigger words naturally incorporated",
  "negative_prompt": "Optional negative prompt for quality/style control",
  "selected_loras": [
    {
      "name": "exact_lora_filename.safetensors",
      "reason": "Brief explanation why this LoRA was selected",
      "used_triggers": ["trigger_word_1", "trigger_word_2"]
    },
    {
      "name": "another_lora.safetensors",
      "reason": "Another reason for selection",
      "used_triggers": ["trigger_word_3"]
    }
  ]
}"""


# Default system prompt for prompting LLM
DEFAULT_SYSTEM_PROMPT = """You are a prompt crafting expert for video generation models. Your role is to transform brief user ideas into detailed, production-ready prompts for AI video generation systems.

Key responsibilities:
- Expand simple ideas into rich, detailed prompts
- Include specific visual details, atmosphere, lighting, and mood
- Use cinematic language appropriate for video generation
- Maintain coherent narrative flow across the prompt
- Optimize for the target model's capabilities"""


# Default custom instruction for prompting
DEFAULT_CUSTOM_INSTRUCTION = """You are a prompting expert. Transform the user's brief idea into a detailed 80-100 word prompt perfect for video generation.

INSTRUCTIONS:
1. Analyze the user's context and available LoRAs
2. Select up to 6 most relevant concept LoRAs (NEVER select character LoRAs marked as is_character=true)
3. Create a detailed, cinematic prompt that:
   - Expands the user's idea with specific visual details
   - Naturally incorporates trigger words from selected LoRAs
   - Uses vivid, descriptive language suitable for video generation
   - Maintains 80-100 word length
   - Includes atmosphere, lighting, movement, and mood
4. Output ONLY valid JSON format

OUTPUT FORMAT (copy this structure exactly):
{
  "prompt": "Your detailed 80-100 word video generation prompt here",
  "negative_prompt": "Optional quality/style negative prompt",
  "selected_loras": [
    {
      "name": "exact_lora_filename.safetensors",
      "reason": "Why you selected this LoRA",
      "used_triggers": ["trigger1", "trigger2"]
    }
  ]
}

RULES:
- Use EXACT filenames from the candidate list
- Use EXACT trigger words from LoRA metadata
- Maximum 6 LoRAs
- NEVER select is_character=true LoRAs
- Do NOT include LoRA weights
- Output valid JSON only (no markdown, no code blocks, just raw JSON)"""


# Legacy system prompt for backward compatibility
PROMPTING_SYSTEM_PROMPT = """You are an expert AI prompt generator and LoRA selector for image/video generation models.

Your task:
1. Given a user's idea/context and a list of available LoRAs, select the MOST relevant concept LoRAs (NOT character LoRAs)
2. Generate a detailed, high-quality prompt that incorporates the correct trigger words for selected LoRAs
3. Output ONLY valid JSON

RULES:
- Select maximum 6 LoRAs
- Only select from the provided candidate list (use exact names)
- NEVER select LoRAs marked as is_character=true
- Use EXACT trigger words from the LoRA metadata
- Insert trigger words naturally into the prompt
- Output format: {"prompt": "detailed prompt here", "negative_prompt": "optional negative prompt", "selected_loras": [{"name": "lora_filename.safetensors", "reason": "why selected", "used_triggers": ["trigger1"]}]}
- prompt should be detailed and high-quality for image generation
- Do NOT include LoRA weights in the output
"""


def build_candidate_list_text(candidates: List[Dict[str, Any]], max_candidates: int = 30) -> str:
    """
    Build a text representation of candidate LoRAs for the LLM.
    
    Args:
        candidates: List of LoRA catalog entries
        max_candidates: Maximum number to include
        
    Returns:
        Formatted text for LLM
    """
    lines = ["Available LoRAs:"]
    
    for i, lora in enumerate(candidates[:max_candidates]):
        # Skip character LoRAs
        if lora.get('is_character', False):
            continue
        
        triggers = ', '.join(lora.get('trained_words', [])[:5])  # Top 5 triggers
        tags = ', '.join(lora.get('tags', [])[:5])
        
        line = f"{i+1}. {lora['file']}"
        if lora.get('summary'):
            line += f" - {lora['summary']}"
        if triggers:
            line += f" | Triggers: {triggers}"
        if tags:
            line += f" | Tags: {tags}"
        
        lines.append(line)
    
    return '\n'.join(lines)


def create_prompting_prompt(
    base_context: str,
    candidates: List[Dict[str, Any]],
    has_image: bool = False
) -> str:
    """
    Create the prompting prompt.
    
    Args:
        base_context: User's input context/idea
        candidates: Pre-filtered candidate LoRAs
        has_image: Whether an image is provided
        
    Returns:
        Full prompt for LLM
    """
    candidate_text = build_candidate_list_text(candidates)
    
    image_note = ""
    if has_image:
        image_note = "\nNote: An image is provided. Consider it when selecting LoRAs and generating the prompt."
    
    prompt = f"""User's idea/context:
{base_context}
{image_note}

{candidate_text}

Task:
1. Select up to 6 most relevant LoRAs from the list above (use exact filenames)
2. Create a detailed prompt incorporating their trigger words
3. Output JSON only with this EXACT format:

{PROMPTING_JSON_TEMPLATE}

Your JSON output (no markdown, no code blocks, just raw JSON):"""
    
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
    result = {
        'prompt': data['prompt'].strip(),
        'negative_prompt': data.get('negative_prompt', '').strip(),
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
    custom_instruction: str = ""
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
        custom_instruction: Override custom instruction (empty = use DEFAULT_CUSTOM_INSTRUCTION)
        
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
    
    # Determine which system message to use
    if custom_instruction.strip():
        # User provided custom instruction - use it
        system_message = custom_instruction.strip()
        print("[PromptingLLM] Using custom instruction")
    elif system_prompt.strip():
        # User provided system prompt - use it (legacy support)
        system_message = system_prompt.strip()
        print("[PromptingLLM] Using custom system prompt")
    else:
        # Use default custom instruction
        system_message = DEFAULT_CUSTOM_INSTRUCTION
        print("[PromptingLLM] Using default custom instruction")
    
    # Build prompt
    has_image = image is not None
    prompt = create_prompting_prompt(base_context, candidates, has_image)
    
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
    
    return True, result, ""
