# SmartPowerLoRALoader Enhancements

## Overview
This document describes the recent enhancements made to the SmartPowerLoRALoader project after the initial v1.0.0 implementation.

## Enhancement 1: Availability Tracking ✅ COMPLETED

### Problem
Previously, when LoRA files were removed from disk, they were completely removed from the catalog. This meant losing all the indexed metadata (LLM summaries, tags, trained words, etc.).

### Solution
Added an `available` field to track whether a LoRA file still exists on disk:

**Changes Made:**
- `utils/lora_catalog.py`:
  - Added `available: True` field to catalog entries (default True for new entries)
  - Modified `detect_new_loras()` to mark missing LoRAs as `available: False` instead of removing them
  - Updated `filter_by_base_model()` to add `include_unavailable` parameter (default False)
  - Updated `filter_by_names()` to add `include_unavailable` parameter (default False)
  - Automatically marks existing files as `available: True` when rescanned

**Benefits:**
- Preserves expensive LLM-indexed metadata even when files are temporarily unavailable
- Allows users to see what LoRAs were previously indexed
- Catalog entries automatically reactivate when files return
- Selection pipeline automatically excludes unavailable LoRAs

**Example Catalog Entry:**
```json
{
  "file": "awesome_style.safetensors",
  "sha256": "abc123...",
  "available": false,
  "summary": "Creates cinematic lighting effects...",
  "trained_words": ["cinematic", "dramatic"],
  ...
}
```

---

## Enhancement 2: System Prompt Input ✅ COMPLETED

### Problem
The prompting LLM used a hardcoded system prompt that couldn't be customized per workflow or use case.

### Solution
Added optional `system_prompt` input field to allow users to override the default system prompt:

**Changes Made:**
- `nodes/smart_power_lora_loader.py`:
  - Added `system_prompt` to optional INPUT_TYPES (multiline STRING)
  - Updated `process()` method signature to accept `system_prompt` parameter
  - Passed `system_prompt` to `_autoselect_loras()` and then to `prompt_with_llm()`

- `utils/prompting_llm.py`:
  - Added `DEFAULT_SYSTEM_PROMPT` constant for video generation workflows
  - Updated `prompt_with_llm()` to accept `system_prompt` parameter
  - Uses custom `system_prompt` if provided, otherwise uses default

**Usage:**
Leave empty to use default, or provide custom system prompt like:
```
You are a cinematic prompt expert specializing in sci-fi themes...
```

**Default System Prompt:**
```
You are a prompt crafting expert for video generation models. Your role is to 
transform brief user ideas into detailed, production-ready prompts for AI video 
generation systems.

Key responsibilities:
- Expand simple ideas into rich, detailed prompts
- Include specific visual details, atmosphere, lighting, and mood
- Use cinematic language appropriate for video generation
- Maintain coherent narrative flow across the prompt
- Optimize for the target model's capabilities
```

---

## Enhancement 3: Custom Instruction Input ✅ COMPLETED

### Problem
The LLM instruction (how to perform the task) was hardcoded and couldn't be customized for different styles or formats.

### Solution
Added `custom_instruction` input field to allow users to customize how the LLM generates prompts:

**Changes Made:**
- `nodes/smart_power_lora_loader.py`:
  - Added `custom_instruction` to optional INPUT_TYPES (multiline STRING)
  - Updated `process()` method signature to accept `custom_instruction` parameter
  - Passed `custom_instruction` to `_autoselect_loras()` and then to `prompt_with_llm()`

- `utils/prompting_llm.py`:
  - Added `DEFAULT_CUSTOM_INSTRUCTION` constant with detailed task instructions
  - Modified `prompt_with_llm()` to accept `custom_instruction` parameter
  - Priority order: custom_instruction > system_prompt > DEFAULT_CUSTOM_INSTRUCTION
  - Added logging to show which instruction source is being used

**Usage:**
Leave empty to use default, or provide custom instruction like:
```
Generate a 50-word cinematic prompt in the style of movie trailers.
Focus on action and drama. Always include lighting details.
```

**Default Custom Instruction:**
```
You are a prompting expert. Transform the user's brief idea into a detailed 
80-100 word prompt perfect for video generation.

INSTRUCTIONS:
1. Analyze the user's context and available LoRAs
2. Select up to 6 most relevant concept LoRAs (NEVER select character LoRAs)
3. Create a detailed, cinematic prompt that:
   - Expands the user's idea with specific visual details
   - Naturally incorporates trigger words from selected LoRAs
   - Uses vivid, descriptive language suitable for video generation
   - Maintains 80-100 word length
   - Includes atmosphere, lighting, movement, and mood
4. Output ONLY valid JSON format

OUTPUT FORMAT:
{
  "prompt": "Your detailed 80-100 word video generation prompt here",
  "negative_prompt": "Optional quality/style negative prompt",
  "selected_loras": [
    {
      "name": "exact_lora_filename.safetensors",
      "reason": "Brief explanation why this LoRA was selected",
      "used_triggers": ["trigger_word1", "trigger_word2"]
    }
  ]
}

RULES:
- Use EXACT filenames from the candidate list
- Use EXACT trigger words from LoRA metadata
- Maximum 6 LoRAs
- NEVER select is_character=true LoRAs
- Do NOT include LoRA weights
- Output valid JSON only
```

**Priority Logic:**
1. If `custom_instruction` provided → use it
2. Else if `system_prompt` provided → use it (legacy support)
3. Else → use `DEFAULT_CUSTOM_INSTRUCTION`

---

## Enhancement 4: Manual Catalog Editing UI (IN PROGRESS)

### Problem
Users cannot manually edit catalog entries (fix LLM mistakes, add missing metadata, toggle availability).

### Solution (Planned)
Implement a Show Info dialog similar to rgthree's Power LoRA Loader:

**Research Completed:**
- Analyzed rgthree's architecture:
  - Frontend: `RgthreeLoraInfoDialog` (TypeScript) displays editable fields
  - Service: `LORA_INFO_SERVICE` handles API calls via `savePartialInfo()`
  - Backend: `POST /rgthree/api/{type}/info` endpoint saves to `.rgthree-info.json` files
  - Storage: Info stored alongside LoRA files as `.rgthree-info.json`

**Planned Implementation:**

### Phase 1: Backend API (TODO)
Create `server/routes_catalog.py` with endpoints:
- `GET /smart-power-lora-loader/api/catalog` - List all catalog entries
- `GET /smart-power-lora-loader/api/catalog/{lora_file}` - Get single entry
- `POST /smart-power-lora-loader/api/catalog/{lora_file}` - Update single entry
- `DELETE /smart-power-lora-loader/api/catalog/{lora_file}` - Remove entry

**API Example:**
```python
@routes.post('/smart-power-lora-loader/api/catalog/{lora_file}')
async def save_catalog_entry(request):
    lora_file = request.match_info['lora_file']
    post = await request.post()
    updates = json.loads(post.get("json"))
    
    # Find entry by filename in catalog
    for hash_key, entry in lora_catalog.catalog.items():
        if entry['file'] == lora_file:
            # Update fields
            for key, value in updates.items():
                if key in ['summary', 'trained_words', 'tags', 'base_compat', 
                          'available', 'is_character', 'display_name']:
                    entry[key] = value
            
            lora_catalog.save_catalog()
            return web.json_response({'status': 200, 'data': entry})
    
    return web.json_response({'status': 404, 'error': 'LoRA not found'})
```

### Phase 2: Frontend Service (TODO)
Create `web/catalog_service.ts`:
```typescript
class SmartLoRACatalogService extends EventTarget {
  async getEntry(loraFile: string) {
    const response = await fetch(`/smart-power-lora-loader/api/catalog/${loraFile}`);
    return await response.json();
  }
  
  async saveEntry(loraFile: string, updates: Partial<CatalogEntry>) {
    const formData = new FormData();
    formData.append('json', JSON.stringify(updates));
    
    const response = await fetch(
      `/smart-power-lora-loader/api/catalog/${loraFile}`,
      { method: 'POST', body: formData }
    );
    return await response.json();
  }
}

export const CATALOG_SERVICE = new SmartLoRACatalogService();
```

### Phase 3: Frontend Dialog (TODO)
Create `web/catalog_dialog.ts` similar to `rgthree/dialog_info.ts`:
```typescript
export class SmartLoRACatalogDialog extends RgthreeDialog {
  constructor(loraFile: string) {
    // Load catalog entry
    // Display editable fields: summary, trained_words, tags, base_compat, available
    // Save button calls CATALOG_SERVICE.saveEntry()
  }
  
  private renderEditableFields() {
    // Summary: textarea
    // Trained Words: editable list
    // Tags: editable list  
    // Base Model: dropdown
    // Available: checkbox
    // Is Character: checkbox
  }
}
```

### Phase 4: Node Integration (TODO)
Add Show Info button to SmartPowerLoRALoader node:
- Display button in node UI when LoRAs are selected
- Click opens `SmartLoRACatalogDialog`
- Allow editing any LoRA in the catalog

---

## Summary

### Completed Enhancements (3/4)
1. ✅ **Availability Tracking** - Catalog preserves metadata for missing files
2. ✅ **System Prompt Input** - Customizable system prompt for LLM
3. ✅ **Custom Instruction Input** - Customizable task instruction for LLM

### In Progress (1/4)
4. 🚧 **Manual Catalog Editing UI** - Research complete, implementation planned

### Breaking Changes
None. All enhancements are backward compatible with v1.0.0.

### Migration Notes
- Existing catalog entries automatically get `available: True` on first scan
- Empty `system_prompt` and `custom_instruction` use sensible defaults
- No user action required for upgrade

---

## Next Steps

To complete Enhancement 4 (Manual Editing UI):
1. Implement backend API routes (`server/routes_catalog.py`)
2. Register routes in ComfyUI server startup
3. Create TypeScript service (`web/catalog_service.ts`)
4. Create dialog component (`web/catalog_dialog.ts`)
5. Add Show Info button to node UI
6. Test full edit flow (frontend → API → catalog → save)

Estimated implementation time: 4-6 hours
