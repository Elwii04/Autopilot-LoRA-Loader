# Changelog

All notable changes to SmartPowerLoRALoader will be documented in this file.

## [1.2.0] - 2025-11-02

### Added - Major UI Overhaul 🎨

**JavaScript UI Extensions:**
- **LoRA Catalog Browser**: Full-screen searchable catalog of all indexed LoRAs
  - Visual cards with summary, base model, and trigger count
  - Real-time search filtering
  - Click any LoRA to view detailed info
- **Manual LoRA Dropdown Selection**: Replaced text input with interactive dropdowns
  - `➕ Add Manual LoRA` button opens searchable LoRA chooser
  - `📋 Manage Manual LoRAs` button shows management dialog
  - Per-LoRA actions: Show Info (`ℹ️`) and Remove (`🗑️`)
- **LoRA Info Dialog**: Comprehensive metadata viewer
  - Summary, trigger words, tags, base model compatibility
  - Default weight, Civitai link
  - Styled like rgthree's Power LoRA Loader
- **Show LoRA Catalog Button**: Main button at bottom of node
  - Quick access to full catalog browser
  - Also available via node context menu

**API Endpoints:**
- `GET /autopilot_lora/catalog` - Returns full LoRA catalog as JSON
- `GET /autopilot_lora/info?file=<name>` - Returns metadata for specific LoRA
- Registered automatically on ComfyUI startup

**Files Created:**
- `web/smart_power_lora_loader.js` - Complete UI extension (~700 lines)
- `server.py` - API endpoint implementations
- `UI_FEATURES.md` - Comprehensive UI documentation

### Changed - UX Improvements 🔧

**Parameter Simplification:**
- Removed `indexing_provider` and `prompting_provider` dropdowns
- Merged into single `indexing_model` and `prompting_model` dropdowns
- Models now prefixed with provider: `"groq: llama-3.1-8b-instant"`, `"gemini: gemini-1.5-flash"`
- Dynamic model fetching from APIs with fallback to hardcoded lists

**Parameter Renaming:**
- `base_context` → `prompt` (clearer, more intuitive)
- `init_image` → `image` (simpler, less technical)
- `mark_as_character` → `disable_lora` (more general purpose)

**Feature Changes:**
- Removed `autoselect` parameter (always enabled now)
- Removed `allowlist_loras` parameter (use `disable_lora` flag instead)
- Added `enable_negative_prompt` toggle (default: False)
- Added `max_index_count` to LoRA Manager (default: 999)
- Changed `reindex_on_run` default to False (performance)

**Enhanced Tooltips:**
- All parameters now have detailed 3-5 sentence descriptions
- Include examples, recommendations, and technical details
- Following rgthree style patterns

### Added - Backend Infrastructure

**Model Fetcher Utility:**
- New `utils/model_fetcher.py` module
- `fetch_all_available_models()` - Queries Groq and Gemini APIs
- `parse_model_string()` - Parses "provider: model-name" format
- Graceful fallbacks when APIs unavailable

**Updated Files:**
- `__init__.py` - Registers server.py and defines WEB_DIRECTORY
- `nodes/smart_power_lora_loader.py` - Complete INPUT_TYPES refactor
- `nodes/lora_manager.py` - Updated all method signatures
- `README.md` - Updated with new parameter names
- Fixed duplicate code (save_catalog called twice)

### Documentation 📚

- **REFACTORING_SUMMARY.md**: Complete change overview with technical details
- **TESTING_GUIDE.md**: Comprehensive testing procedures (10 phases, 40+ tests)
- **UI_FEATURES.md**: Full UI feature guide with workflows and comparisons
- Updated README.md with new parameter names and examples

### Technical Details

**JavaScript Integration:**
- Manual LoRAs stored as array internally, converted to comma-separated string for Python
- Fully backward compatible with old text input format
- Caching of LoRA info to minimize API calls
- Modal dialogs with search, hover effects, keyboard shortcuts

**API Architecture:**
- Uses aiohttp web server (ComfyUI's built-in)
- JSON responses with error handling
- Reads from existing `data/lora_index.json` catalog

**Breaking Changes:**
- None for end users (parameter changes handled internally)
- Developers: `indexing_provider`/`prompting_provider` parameters removed from API

### Inspired By

UI design patterns inspired by **rgthree's Power LoRA Loader**, adapted for:
- AI-powered auto-selection
- Integrated catalog system
- Hybrid manual + automatic workflow

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

### Added
- Civitai ingest now fetches full model metadata, including sanitized descriptions, tags, usage tips, and suggested strengths inferred from gallery resources.
- Up to five creator gallery images are cached locally with their prompts so the indexing LLM can reason about the LoRA's visual style.
- Indexing pipeline automatically routes through a vision-capable LLM when gallery assets are available and feeds it the prompt context.

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
