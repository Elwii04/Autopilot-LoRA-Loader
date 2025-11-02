# SmartPowerLoRALoader for ComfyUI

An intelligent ComfyUI custom node that automatically selects relevant LoRAs and generates high-quality prompts using Large Language Models (LLMs).

## Features

- 🤖 **Automatic LoRA Selection**: LLM-powered selection of the most relevant LoRAs based on your creative intent
- 📝 **Smart Prompt Generation**: Automatically generates detailed prompts with correct trigger words
- 🔍 **Intelligent Indexing**: Automatically indexes new LoRAs with metadata from Civitai and safetensors
- 🎯 **Base Model Awareness**: Filters LoRAs by compatibility with your selected base model (Flux, SDXL, SD1.x, etc.)
- 👤 **Manual Override**: Supports manual LoRA selection for character LoRAs or specific use cases
- 🔌 **Multiple LLM Providers**: Supports Groq and Google Gemini APIs
- 👁️ **Vision Support**: Can analyze reference images when selecting LoRAs (with vision-capable models)
- 🔗 **RGThree Compatible**: Generates `.rgthree-info.json` files compatible with rgthree's "Show Info" feature

## Installation

### 1. Clone the Repository

Navigate to your ComfyUI custom nodes directory and clone:

```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/yourusername/ComfyUI-SmartPowerLoRALoader.git
cd ComfyUI-SmartPowerLoRALoader
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install python-dotenv requests groq google-generativeai Pillow jsonschema
```

### 3. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
```
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

**Get API Keys:**
- **Groq**: https://console.groq.com/keys (fast, free tier available)
- **Gemini**: https://aistudio.google.com/apikey (Google AI Studio)

### 4. Restart ComfyUI

Restart ComfyUI to load the new node.

## Usage

### Basic Workflow

1. **Add the Node**: Search for "Smart Power LoRA Loader" in the node menu
2. **Connect Inputs**: Connect your MODEL and CLIP inputs
3. **Set Base Context**: Write your creative idea/prompt in the `base_context` field
4. **Select Base Model**: Choose your base model family (e.g., "Flux-1", "SDXL", "SD1.x")
5. **Configure LLMs**: Select LLM provider and model for indexing and prompting
6. **Run**: The node will auto-select LoRAs and generate a complete prompt

### Inputs

#### Required
- **base_context** (STRING): Your creative idea or rough prompt
- **base_model** (DROPDOWN): Base model family (auto-populated from your LoRAs)
- **autoselect** (BOOLEAN): Enable automatic LoRA selection
- **indexing_provider** / **indexing_model**: LLM for indexing new LoRAs (text-only)
- **prompting_provider** / **prompting_model**: LLM for prompt generation (can support vision)

#### Optional
- **model** (MODEL): Input model to apply LoRAs to
- **clip** (CLIP): Input CLIP to apply LoRAs to
- **init_image** (IMAGE): Reference image for vision models
- **allowlist_loras** (STRING): Comma-separated list of LoRAs allowed for auto-selection (empty = all)
- **manual_loras** (STRING): Comma-separated list of LoRAs to always apply (e.g., character LoRAs)
- **reindex_on_run** (BOOLEAN): Detect and index new LoRA files each run
- **temperature** (FLOAT): LLM temperature for creativity (0.0-2.0)
- **max_loras** (INT): Maximum number of LoRAs to auto-select
- **trigger_position** (DROPDOWN): Where to place trigger words ("start", "end", "llm_decides")

### Outputs

- **MODEL**: Model with LoRAs applied
- **CLIP**: CLIP with LoRAs applied
- **final_prompt**: Generated prompt with trigger words
- **negative_prompt**: Generated negative prompt
- **selected_loras_json**: JSON debug info of selected LoRAs

## How It Works

### 1. Indexing Phase (First Run or New LoRAs)

When you add new LoRAs to your folder:

1. **Detection**: Scans for new `.safetensors` files using SHA256 hashing
2. **Metadata Extraction**: 
   - Reads safetensors embedded metadata (trained words, base model)
   - Fetches from Civitai API using file hash
3. **LLM Processing**: Uses your chosen indexing LLM to extract:
   - One-line summary of what the LoRA does
   - Exact trigger words
   - Descriptive tags
4. **Base Model Classification**: Normalizes base model to families (Flux-1, SDXL, etc.)
5. **Storage**: Saves to `data/lora_index.json` catalog
6. **RGThree Compatibility**: Generates `.rgthree-info.json` for each LoRA

### 2. Selection Phase (Every Run with autoselect=True)

1. **Filtering**:
   - Filter by selected base model family
   - Apply allowlist (if provided)
   - Exclude character LoRAs (reserved for manual selection)
2. **Pre-Ranking**: Fuzzy token overlap between your context and LoRA metadata
3. **LLM Selection**: 
   - Sends top 30 candidates to prompting LLM
   - LLM selects up to 6 most relevant LoRAs
   - Optionally analyzes reference image if provided
4. **Merging**: Combines manual + auto-selected LoRAs (manual first, deduplicated)

### 3. Prompt Generation

Two modes:
- **LLM Decides** (default): LLM generates complete prompt with triggers naturally integrated
- **Manual Position**: Insert collected triggers at start or end of your context

### 4. Application

Applies selected LoRAs to MODEL and CLIP using ComfyUI's standard LoraLoader, using default weights from the catalog.

## Base Model Families

The node recognizes these base model families:

- **Flux-1** (Flux Dev, Schnell, Krea, Kontext)
- **SDXL** (SDXL 1.0, Lightning, Turbo, Hyper)
- **SD1.x** (SD 1.4, 1.5, LCM, Hyper)
- **SD2.x** (SD 2.0, 2.1)
- **Qwen-Image** (Qwen, Qwen2-VL)
- **Wan-Video 1.x** (Wan 1.3B, 14B)
- **Wan-Video 2.2** (Wan 2.2 T2V/I2V)
- **Wan-Video 2.5** (Wan 2.5 T2V/I2V)
- **AuraFlow**
- **PixArt** (Alpha, Sigma)
- **Kolors**
- **Hunyuan**
- **Lumina**
- **Playground** (v2, v2.5)
- **CogVideoX**
- **Mochi**
- **LTX-Video**

## LLM Models

### Recommended Models

**For Indexing (text-only, fast):**
- Groq: `llama-3.1-8b-instant` (very fast)
- Gemini: `gemini-1.5-flash-8b` (fast, good quality)

**For Prompting (with optional vision):**
- Groq: `meta-llama/llama-4-maverick-17b-128e-instruct` (vision support)
- Gemini: `gemini-1.5-flash` or `gemini-1.5-pro` (vision support, high quality)

### Vision Model Requirements

To use the `init_image` input, you must select a vision-capable model for prompting:
- Groq: `llama-4-maverick` or `llama-4-scout`
- Gemini: `gemini-1.5-pro`, `gemini-1.5-flash`, or `gemini-2.0-flash-exp`

## Tips & Best Practices

### For Best Results

1. **Be Specific in Context**: The more detailed your `base_context`, the better the LoRA selection
2. **Use Allowlist for Control**: Create allowlists for different workflows (e.g., only clothing LoRAs)
3. **Manual for Characters**: Always use `manual_loras` for character LoRAs to ensure consistency
4. **Temperature Tuning**:
   - Lower (0.3-0.5): More conservative, consistent selection
   - Higher (0.8-1.0): More creative, varied results
5. **Vision Models**: Provide reference images for style/composition matching

### Character vs Concept LoRAs

The node distinguishes between:
- **Concept LoRAs**: Clothing, objects, styles (auto-selectable)
- **Character LoRAs**: Specific characters (manual only)

Mark character LoRAs by adding them to `manual_loras` input.

### Allowlist Examples

```
# Only style LoRAs
style_lora_1.safetensors, style_lora_2.safetensors, aesthetic_lora.safetensors

# Only clothing LoRAs
dress_lora.safetensors, shirt_lora.safetensors, pants_lora.safetensors
```

## Troubleshooting

### No LoRAs Detected

- Check that LoRAs are in ComfyUI's `models/loras/` directory
- Ensure files are `.safetensors` format
- Set `reindex_on_run=True` to force re-scan

### API Key Errors

- Verify `.env` file is in the node's root directory
- Check that API keys are valid and not expired
- Ensure you have available quota/credits

### No LoRAs Selected

- Check that LoRAs match the selected base model family
- Verify `allowlist_loras` isn't too restrictive
- Try increasing `temperature` for more creative selection
- Check console for indexing errors

### LLM Timeout/Rate Limits

- Groq: Very generous rate limits, shouldn't be an issue
- Gemini: Has rate limits on free tier; wait and retry
- Consider using faster models for indexing

### LoRAs Not Applied

- Ensure MODEL and CLIP inputs are connected
- Check console for application errors
- Verify LoRAs are compatible with your base model

## Advanced Usage

### Custom Base Model Families

Edit `utils/base_model_mapping.py` to add custom model family mappings.

### Bypass LLM for Indexing

Set `reindex_on_run=False` after initial indexing to skip re-indexing on every run.

### Manual Catalog Editing

Edit `data/lora_index.json` directly to:
- Adjust default weights
- Fix incorrect base model classifications
- Add custom summaries
- Mark LoRAs as characters

### Integration with Other Nodes

- Connect output prompt to any text conditioning node
- Use selected_loras_json with custom logic nodes
- Chain multiple SmartPowerLoRALoader nodes with different allowlists

## File Structure

```
ComfyUI-SmartPowerLoRALoader/
├── __init__.py                 # Node registration
├── requirements.txt            # Dependencies
├── .env.example                # API key template
├── README.md                   # This file
├── nodes/
│   └── smart_power_lora_loader.py  # Main node
├── llm_providers/
│   ├── __init__.py             # Base provider interface
│   ├── groq_provider.py        # Groq implementation
│   └── gemini_provider.py      # Gemini implementation
├── utils/
│   ├── config_manager.py       # API key management
│   ├── base_model_mapping.py   # Base model normalization
│   ├── lora_catalog.py         # Catalog management
│   ├── civitai_utils.py        # Civitai API integration
│   ├── safetensors_utils.py    # Metadata extraction
│   ├── indexing_llm.py         # LLM indexing logic
│   ├── prompting_llm.py        # LLM prompting logic
│   ├── lora_selector.py        # Selection/filtering
│   ├── lora_applicator.py      # LoRA application
│   ├── prompt_builder.py       # Prompt construction
│   ├── show_info_generator.py  # RGThree compatibility
│   └── utils.py                # Helper functions
└── data/
    ├── lora_index.json         # LoRA catalog (auto-generated)
    └── civitai_cache/          # Cached Civitai responses
```

## Credits

- Inspired by [rgthree's Power LoRA Loader](https://github.com/rgthree/rgthree-comfy)
- Uses Civitai API for LoRA metadata
- LLM integration patterns from ComfyUI-mnemic-nodes and ComfyUI-OllamaGemini

## License

MIT License - feel free to use and modify!

## Support

For issues, feature requests, or questions, please open an issue on GitHub.

## Changelog

### v1.0.0 (Initial Release)
- Automatic LoRA indexing with Civitai integration
- LLM-powered LoRA selection (Groq & Gemini)
- Smart prompt generation with trigger words
- Base model family filtering
- Manual LoRA override support
- Vision model support for image analysis
- RGThree Show Info compatibility
