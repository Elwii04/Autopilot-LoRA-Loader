"""
Indexing LLM Logic
Uses LLM providers to extract structured metadata from Civitai text.
"""
import json
from typing import Dict, Any, Optional, List, Tuple

from ..llm_providers.groq_provider import GroqProvider
from ..llm_providers.gemini_provider import GeminiProvider
from .utils import safe_json_loads, validate_json_schema
from .base_model_mapping import base_model_mapper


# JSON schema for indexing output
INDEXING_SCHEMA_FIELDS = ['summary', 'trainedWords', 'tags']


# JSON template example for indexing
INDEXING_JSON_TEMPLATE = """{
  "summary": "A single concise sentence describing what this LoRA does (max 100 chars)",
  "trainedWords": ["exact_trigger_word_1", "exact_trigger_word_2", "exact_trigger_word_3"],
  "tags": ["style_tag", "category_tag", "theme_tag", "feature_tag", "quality_tag"]
}"""


INDEXING_SYSTEM_PROMPT = """You are a metadata extraction specialist. Your task is to extract structured information from LoRA model descriptions.

Extract the following information:
1. summary: A single concise sentence (max 100 characters) describing what the LoRA does
2. trainedWords: An array of exact trigger words needed to activate this LoRA (from the text, not made up)
3. tags: An array of 5-10 descriptive tags/keywords for this LoRA

IMPORTANT RULES:
- Output ONLY valid JSON matching this exact format
- trainedWords must be EXACT words from the description, not invented
- If no trigger words are mentioned, use an empty array []
- Summary must be ONE sentence, under 100 characters
- Tags should be lowercase, single words or short phrases
- Do NOT add any explanation, just the JSON object

REQUIRED JSON OUTPUT FORMAT:
{
  "summary": "One sentence description here",
  "trainedWords": ["trigger1", "trigger2"],
  "tags": ["tag1", "tag2", "tag3"]
}"""


def create_indexing_prompt(civitai_text: str, known_families: List[str], filename: str = "") -> str:
    """
    Create the indexing prompt with context.
    
    Args:
        civitai_text: Text from Civitai metadata
        known_families: List of already known base model families
        filename: Optional filename of the LoRA for additional context
        
    Returns:
        Full prompt for LLM
    """
    filename_context = f"\n\nLoRA Filename: {filename}" if filename else ""
    
    prompt = f"""Extract structured metadata from this LoRA description:

{civitai_text}{filename_context}

Known base model families (for reference): {', '.join(known_families) if known_families else 'None yet'}

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
    
    # Clean and normalize
    result = {
        'summary': data['summary'].strip()[:200],  # Max 200 chars
        'trainedWords': [w.strip() for w in data['trainedWords'] if isinstance(w, str) and w.strip()],
        'tags': [t.strip().lower() for t in data['tags'] if isinstance(t, str) and t.strip()][:15]  # Max 15 tags
    }
    
    return result


def index_with_llm(
    civitai_text: str,
    provider_name: str,
    model_name: str,
    api_key: str,
    known_families: List[str],
    filename: str = ""
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
    
    # Build prompt with filename
    prompt = create_indexing_prompt(civitai_text, known_families, filename)
    
    # Generate with LLM
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
