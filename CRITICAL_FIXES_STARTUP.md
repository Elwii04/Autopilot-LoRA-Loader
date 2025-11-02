# Critical Fixes - Startup Performance & LLM Context

## Issues Fixed

### 1. **Removed Slow Hash Computation on Startup** ⚡
**Problem:** Startup was computing SHA256 hashes for ALL LoRAs (taking 4+ minutes for large collections), which was completely unnecessary.

**Solution:** 
- Removed all hash computation from `startup.py`
- Startup now just counts files and reports status (instant)
- Hashes are only computed when indexing (which is manual via button)

**Impact:** Startup time reduced from 4+ minutes to < 1 second

### 2. **Added Filename to LLM Indexing Context** 📝
**Problem:** The LLM didn't receive the LoRA filename when indexing, missing important contextual information.

**Solution:**
- Added `filename` parameter to `create_indexing_prompt()` and `index_with_llm()`
- Filename is now passed to the LLM: "LoRA Filename: example-lora.safetensors"
- LLM can use filename to better understand the LoRA's purpose

**Files Changed:**
- `utils/indexing_llm.py`: Added `filename` parameter to prompt functions
- `nodes/lora_manager.py`: Pass `file_path.name` when calling `index_with_llm()`
- `nodes/smart_power_lora_loader.py`: Pass `file_path.name` when calling `index_with_llm()`

### 3. **Clarified `is_character` Field Usage** 📋
**Note:** The `is_character` field is intentionally kept and is NOT the same as enabled/disabled:

- **`is_character`**: Used to filter character LoRAs from auto-selection (permanent classification)
- **`enabled`**: User toggle to temporarily disable LoRAs without deleting them

Both fields serve different purposes and are used throughout the codebase.

## Before & After

### Startup Behavior

**Before:**
```
[LoRACatalog] No existing catalog found, will create new one
[Computing hashes for all LoRAs... 4+ minutes]
⚡ Autopilot LoRA: Added 150 new LoRA(s) to catalog
```

**After:**
```
⚡ Autopilot LoRA: 150 LoRA(s) available (0 indexed)
[Instant startup]
```

### LLM Indexing Context

**Before:**
```
Extract structured metadata from this LoRA description:

[Civitai description text only]
```

**After:**
```
Extract structured metadata from this LoRA description:

[Civitai description text]

LoRA Filename: cyberpunk-neon-style-v2.safetensors
```

## Technical Details

### Why Hash Computation is Slow
- SHA256 hashing requires reading entire file (some LoRAs are 1-2GB)
- With 100+ LoRAs, this means reading 100+ GB of data
- Even on fast SSDs, this takes minutes
- **Solution:** Only compute hashes when actually indexing (manual button click)

### Catalog Population Strategy
- Catalog is built incrementally as you index LoRAs
- No pre-population on startup
- Fast startup, indexing on demand
- Catalog persists across sessions

### Filename Context for LLM
- Filenames often contain useful information: version numbers, style names, model type
- Example: `flux-realistic-portrait-v3.safetensors` tells the LLM it's for Flux, realistic portraits, version 3
- Helps LLM make better decisions about tags, summary, and trigger words

## User Impact

✅ **Instant Startup**: No more waiting 4+ minutes for ComfyUI to load
✅ **Better Indexing**: LLM gets filename context for more accurate metadata extraction
✅ **Same Functionality**: Everything else works exactly the same
✅ **Manual Control**: Indexing only happens when you click the button

## Testing

1. ✅ Restart ComfyUI - should be instant (< 1 second)
2. ✅ Check console - no hash computation messages
3. ✅ Open LoRA Catalog - all LoRAs visible (indexed and non-indexed)
4. ✅ Run indexing - filename appears in LLM prompt
5. ✅ Check metadata - should be more accurate with filename context
