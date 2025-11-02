# Changelog

All notable changes to SmartPowerLoRALoader will be documented in this file.

## [1.1.0] - 2025-01-XX

### Added
- **Availability Tracking**: Catalog now tracks `available` field for LoRA files
  - Missing LoRAs marked as `available: false` instead of being removed
  - Preserves expensive LLM-indexed metadata even when files are temporarily unavailable
  - Selection pipeline automatically filters unavailable LoRAs
  - Files automatically reactivate when they return
- **System Prompt Input**: New optional `system_prompt` field in node inputs
  - Allows customization of LLM system prompt per workflow
  - Defaults to video generation-focused prompt when empty
  - Useful for specialized workflows (e.g., cinematic, anime, product photography)
- **Custom Instruction Input**: New optional `custom_instruction` field in node inputs
  - Allows customization of task instruction for prompting LLM
  - Defaults to detailed 80-100 word prompt generation instruction
  - Supports different prompt lengths, styles, and formats
  - Priority: custom_instruction > system_prompt > default

### Changed
- `utils/lora_catalog.py`:
  - `detect_new_loras()` now marks missing files as unavailable instead of removing
  - `filter_by_base_model()` adds `include_unavailable` parameter (default False)
  - `filter_by_names()` adds `include_unavailable` parameter (default False)
- `utils/prompting_llm.py`:
  - Added `DEFAULT_SYSTEM_PROMPT` for video generation workflows
  - Added `DEFAULT_CUSTOM_INSTRUCTION` with detailed task specifications
  - `prompt_with_llm()` accepts `system_prompt` and `custom_instruction` parameters
  - Improved logging to show which instruction source is being used
- `nodes/smart_power_lora_loader.py`:
  - Added `system_prompt` and `custom_instruction` to optional inputs
  - Updated `process()` and `_autoselect_loras()` method signatures
  - Passes custom prompts through to LLM provider

### Documentation
- Added ENHANCEMENTS.md with detailed explanation of all enhancements
- Documents default prompts and customization examples
- Includes migration notes and breaking changes (none)

### In Progress
- Manual catalog editing UI (research completed, implementation planned)
  - Backend API routes for catalog CRUD operations
  - Frontend TypeScript service and dialog component
  - Show Info button integration with node UI

## [1.0.0] - 2025-11-02

### Added
- Initial release of SmartPowerLoRALoader
- Automatic LoRA indexing with SHA256 hash-based detection
- Civitai API integration for metadata fetching with caching
- Safetensors metadata extraction (trained words, base model, etc.)
- LLM-powered LoRA selection using context matching
- Support for Groq and Google Gemini LLM providers
- Vision model support for image-based LoRA selection
- Smart prompt generation with automatic trigger word insertion
- Base model family classification and filtering (20+ families supported)
- Manual LoRA override for character LoRAs
- Allowlist system for workflow-specific LoRA filtering
- RGThree Show Info compatibility (generates .rgthree-info.json files)
- Persistent LoRA catalog (data/lora_index.json)
- Configurable trigger word insertion position
- Comprehensive error handling and logging
- Detailed README and setup documentation

### Features
- **Indexing LLM**: Extracts structured metadata (summary, triggers, tags) from Civitai data
- **Prompting LLM**: Selects relevant LoRAs and generates complete prompts
- **Base Model Awareness**: Filters LoRAs by compatibility (Flux-1, SDXL, SD1.x, etc.)
- **Fuzzy Pre-Ranking**: Token overlap scoring for efficient candidate selection
- **Deduplication**: Merges manual and auto-selected LoRAs intelligently
- **Weight Management**: Uses catalog-stored default weights or 1.0 fallback
- **Caching**: Civitai responses cached locally to avoid repeated API calls
- **Graceful Degradation**: Continues working even if APIs fail or LoRAs have no metadata

### Technical
- Python 3.8+ compatible
- Dependencies: python-dotenv, requests, groq, google-generativeai, Pillow, jsonschema
- ComfyUI integration via standard node interface
- Modular architecture with separate providers, utilities, and node logic
- JSON schema validation for LLM responses
- Retry logic with exponential backoff for API calls

### Documentation
- Comprehensive README with usage examples
- Quick setup guide (SETUP.md)
- Detailed troubleshooting section
- API key configuration instructions
- Base model family reference
- LLM model recommendations

## [Unreleased]

### Planned Features
- Character LoRA auto-detection heuristics
- Custom base model family definitions via UI
- Batch processing mode for multiple prompts
- LoRA weight adjustment suggestions from LLM
- Advanced filtering (by tags, popularity, date)
- Integration with more LLM providers (OpenAI, Claude, etc.)
- Web UI for catalog management
- Export/import catalog functionality
- Preset allowlists for common workflows
- LoRA quality scoring and recommendations
