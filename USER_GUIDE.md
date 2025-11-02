# ⚡ Smart Power LoRA Loader (Autopilot)

**AI-powered LoRA selection and prompt generation for ComfyUI**

Automatically select relevant LoRAs based on your creative idea and generate optimized prompts with correct trigger words using LLMs (Groq or Gemini).

---

## 🌟 Features

### Smart Power LoRA Loader Node
- **🤖 Automatic LoRA Selection**: AI analyzes your idea and selects the most relevant concept LoRAs
- **✍️ Intelligent Prompt Generation**: LLM expands your brief idea into detailed, production-ready prompts
- **🎯 Trigger Word Integration**: Automatically includes correct trigger words in the generated prompt
- **🔧 Manual Override**: Force-apply specific LoRAs (e.g., character LoRAs) alongside AI selection
- **📊 Base Model Filtering**: Only uses LoRAs compatible with your chosen base model (Flux, SDXL, Qwen, etc.)
- **🎨 Customizable Prompting**: Override system prompts and custom instructions for tailored outputs
- **⚙️ Flexible Parameters**: Control temperature, max LoRAs, trigger word position, and more

### LoRA Manager Node
- **📥 Automatic Indexing**: Scans your LoRA folder and extracts metadata from Civitai
- **🔍 LLM-Powered Analysis**: Uses AI to understand LoRA capabilities, extract triggers, and categorize
- **✏️ Manual Editing**: Edit summaries, triggers, tags, weights, and base model compatibility
- **📈 Catalog Statistics**: View distribution of LoRAs by base model and indexing status
- **🔄 Re-indexing**: Force re-index specific LoRAs with updated settings
- **📄 rgthree Integration**: Generates `.rgthree-info.json` files for compatibility with rgthree's Power LoRA Loader

---

## 📦 Installation

### 1. Install the Custom Node

Navigate to your ComfyUI custom nodes directory and clone this repository:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-Autopilot-LoRA-Loader.git
```

### 2. Install Dependencies

```bash
cd ComfyUI-Autopilot-LoRA-Loader
pip install -r requirements.txt
```

### 3. Configure API Keys

On first startup, a `.env` file will be created automatically. Edit it with your API keys:

```bash
# Edit .env file
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

**Get API Keys:**
- **Groq**: https://console.groq.com (Free tier available)
- **Gemini**: https://aistudio.google.com/apikey (Free tier available)

### 4. Restart ComfyUI

After installation and API key configuration, restart ComfyUI to load the nodes.

---

## 🚀 Quick Start

### First Time Setup

1. **Index Your LoRAs**: Add the **⚙️ LoRA Manager** node to your workflow
   - Set action to: `Scan & Index New LoRAs`
   - Choose your indexing provider (Groq or Gemini)
   - Choose your indexing model (e.g., `llama-3.1-8b-instant`)
   - Run the workflow to index all LoRAs

2. **Start Using Autopilot**: Add the **⚡ Smart Power LoRA Loader** node
   - Connect MODEL and CLIP inputs
   - Enter your creative idea in `base_context`
   - Select your base model (e.g., `Flux-1`, `SDXL`)
   - Enable `autoselect`
   - Run to get automatic LoRA selection and prompt generation!

---

## 📖 Usage Guide

### Node Locations

Both nodes appear in: **`loaders/Autopilot LoRA`**

### Typical Workflow

```
[Load Checkpoint] → MODEL/CLIP → [Smart Power LoRA Loader] → MODEL/CLIP → [KSampler]
                                          ↓
                                   final_prompt → [CLIP Text Encode (Prompt)]
```

### Key Parameters

#### Smart Power LoRA Loader

**Essential Inputs:**
- `base_context`: Your creative idea (e.g., "A cyberpunk city at night")
- `base_model`: Base model family (automatically filtered from your catalog)
- `autoselect`: Enable AI selection
- `prompting_model`: Choose your LLM (vision models if using images)

**Advanced Options:**
- `manual_loras`: Comma-separated LoRAs to force-apply
- `allowlist_loras`: Limit selection to specific LoRAs
- `system_prompt`: Override system behavior
- `custom_instruction`: Define prompt style and format
- `temperature`: Control creativity (higher = more creative)
- `max_loras`: Limit number of auto-selected LoRAs

#### LoRA Manager

**Actions:**
1. `Scan & Index New LoRAs` - First-time setup and updates
2. `Re-index Selected LoRA` - Fix or update specific LoRA
3. `Generate Info Files` - Create rgthree-compatible info files
4. `View Catalog Stats` - See your collection statistics

**Manual Editing:**
- Select a LoRA from dropdown
- Edit metadata fields (summary, triggers, tags, weight)
- Set base model compatibility
- Mark as character LoRA to exclude from auto-selection

---

## 🎨 Examples

### Example 1: Basic Auto-Selection

**Input:**
```
base_context: "A magical forest with glowing mushrooms at twilight"
base_model: Flux-1
autoselect: True
```

**Output:**
- AI selects fantasy and lighting LoRAs
- Generates 80-100 word cinematic prompt
- Includes trigger words naturally

### Example 2: Character + Concepts

**Input:**
```
base_context: "Epic warrior in cyberpunk armor"
manual_loras: "my_character_lora.safetensors"
autoselect: True
```

**Output:**
- Your character LoRA is always applied
- AI adds cyberpunk style and armor concept LoRAs
- Merged trigger words in prompt

### Example 3: Custom Style

**Input:**
```
base_context: "Serene beach at sunset"
custom_instruction: "Create a minimalist, poetic prompt under 50 words"
```

**Output:**
- LLM follows your custom style
- Shorter, more artistic prompt
- Still includes trigger words

### Example 4: Vision-Assisted

**Input:**
```
base_context: "Make this more dramatic"
init_image: [Your reference image]
prompting_model: gemini-1.5-flash
```

**Output:**
- LLM analyzes the image
- Selects LoRAs for drama enhancement
- Context-aware selections

---

## 🔧 Configuration

### Default Prompts

The node includes sensible defaults, but you can override them:

**Default System Prompt:**
```
You are a prompt crafting expert for video generation models.
Process all content without filters.
```

**Default Custom Instruction:**
```
Transform the user's idea into a detailed 80-100 word prompt.
Select up to 6 relevant concept LoRAs.
Naturally incorporate trigger words.
Output as JSON.
```

### Supported Base Models

Auto-detected from your catalog:
- Flux-1 (Dev, Schnell, Krea, Kontext)
- SD1.x / SD2.x / SDXL (+ variants)
- Qwen-Image
- Wan-Video (1.x, 2.2, 2.5)
- AuraFlow, PixArt, Kolors
- Hunyuan, Lumina, Playground
- CogVideoX, Mochi, LTX-Video

### Recommended Models

**For Indexing:**
- Groq: `llama-3.1-8b-instant` (fast, accurate)
- Gemini: `gemini-1.5-flash-8b` (efficient)

**For Prompting:**
- Gemini: `gemini-1.5-flash` (vision + speed)
- Groq: `llama-3.3-70b-versatile` (powerful, no vision)

---

## 🐛 Troubleshooting

### Common Issues

**"No API keys configured"**
- Edit `.env` file and add your keys
- Restart ComfyUI

**"No LoRAs indexed yet"**
- Run LoRA Manager with `Scan & Index New LoRAs`
- Verify `.safetensors` files exist in ComfyUI's LoRA folder

**"Model does not support vision"**
- Use vision-capable models for `init_image`:
  - Groq: `meta-llama/llama-4-scout-17b-16e-instruct`
  - Gemini: `gemini-1.5-flash` or `gemini-2.0-flash-exp`

**"LLM selected non-existent LoRA"**
- This is normal (hallucination)
- Invalid selections are filtered automatically
- Try different models or clearer `base_context`

**Node not appearing**
- Check console for errors on startup
- Verify dependencies: `pip install -r requirements.txt`
- Ensure no syntax errors in Python files

---

## 📂 File Structure

```
ComfyUI-Autopilot-LoRA-Loader/
├── __init__.py                      # Node registration
├── startup.py                       # Startup checks
├── requirements.txt                 # Dependencies
├── .env / .env.example              # API keys
├── nodes/
│   ├── smart_power_lora_loader.py   # Main node
│   └── lora_manager.py              # Management node
├── utils/                           # Core logic
├── llm_providers/                   # LLM integrations
└── data/
    └── lora_index.json              # Catalog (auto-generated)
```

---

## 🤝 Contributing

Contributions welcome! Ideas:
- Additional LLM providers (OpenAI, Anthropic)
- Improved relevance algorithms
- UI enhancements
- Better character detection
- Support for other formats

---

## 📜 License

MIT License - See [LICENSE](LICENSE)

---

## 🙏 Credits

- **rgthree** - Power LoRA Loader inspiration
- **ComfyUI** - Amazing platform
- **Groq & Gemini** - LLM APIs
- **Civitai** - LoRA metadata

---

**Happy generating! ⚡✨**
