# Quick Setup Guide

## Installation Steps

1. **Clone to ComfyUI custom_nodes directory**:
   ```bash
   cd [YOUR_COMFYUI_PATH]/custom_nodes/
   git clone [REPOSITORY_URL] ComfyUI-SmartPowerLoRALoader
   cd ComfyUI-SmartPowerLoRALoader
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys**:
   - Copy `.env.example` to `.env`
   - Get Groq API key: https://console.groq.com/keys (recommended - free and fast)
   - Get Gemini API key: https://aistudio.google.com/apikey (alternative)
   - Edit `.env` and paste your keys

4. **Restart ComfyUI**

## First Use

1. Open ComfyUI
2. Add node: Right-click → Add Node → loaders → "Smart Power LoRA Loader"
3. Connect MODEL and CLIP inputs
4. In `base_context`, write your idea (e.g., "a cyberpunk street at night")
5. Select `base_model` matching your checkpoint (e.g., "Flux-1", "SDXL")
6. Configure LLM settings:
   - Indexing: "groq" + "llama-3.1-8b-instant" (fast, for initial LoRA processing)
   - Prompting: "gemini" + "gemini-1.5-flash" (good quality, supports vision)
7. First run will index your LoRAs (may take a few minutes)
8. Subsequent runs will be fast

## Recommended Settings

**For Speed**:
- Indexing: Groq + llama-3.1-8b-instant
- Prompting: Groq + llama-3.1-8b-instant
- Temperature: 0.7

**For Quality**:
- Indexing: Groq + llama-3.1-8b-instant (doesn't need to be fancy)
- Prompting: Gemini + gemini-1.5-pro
- Temperature: 0.85

**For Vision (with reference image)**:
- Prompting: Gemini + gemini-1.5-flash or Groq + llama-4-maverick
- Connect an IMAGE to `init_image` input

## Troubleshooting

**"No API key" error**:
- Check `.env` file exists in node folder
- Verify keys don't have quotes or extra spaces
- Restart ComfyUI after editing `.env`

**"No LoRAs detected"**:
- Check LoRAs are in `ComfyUI/models/loras/` directory
- Ensure they are `.safetensors` files
- Enable `reindex_on_run` in node settings

**Node doesn't appear**:
- Check console for import errors
- Verify all dependencies installed: `pip list | grep -E "dotenv|requests|groq|google-generativeai"`
- Restart ComfyUI completely

**Slow indexing**:
- Normal on first run (fetches from Civitai for each LoRA)
- Subsequent runs use cache and are fast
- Can disable `reindex_on_run` after first successful indexing

## File Locations

- **LoRA Catalog**: `ComfyUI-SmartPowerLoRALoader/data/lora_index.json`
- **Civitai Cache**: `ComfyUI-SmartPowerLoRALoader/data/civitai_cache/`
- **RGThree Info Files**: Next to each LoRA file (`.rgthree-info.json`)

## Getting Help

Check the full README.md for detailed documentation, advanced usage, and troubleshooting.
