# Testing Guide - v1.2.0 Refactoring

This guide outlines the testing procedures for the major refactoring completed in v1.2.0.

## Prerequisites

1. **ComfyUI Environment:**
   - Working ComfyUI installation
   - Access to `models/loras/` directory with test LoRAs
   
2. **API Keys:**
   - At least one API key configured (Groq or Gemini)
   - Both keys recommended for full testing

3. **Test LoRAs:**
   - Mix of indexed and unindexed LoRAs
   - LoRAs for different base models (Flux, SDXL, SD1.x)
   - At least 10-20 LoRAs for meaningful testing

## Phase 1: Node Loading

### Test 1.1: Node Appears in ComfyUI
**Steps:**
1. Start ComfyUI
2. Check console for node loading messages
3. Search for "Smart Power LoRA Loader" in node menu
4. Search for "LoRA Manager" in node menu

**Expected Result:**
- Both nodes appear under category `loaders/Autopilot LoRA`
- Node names: "⚡ Smart Power LoRA Loader" and "⚙️ LoRA Manager"
- No error messages in console during load

**Console Messages to Check:**
```
[Autopilot LoRA] Initializing Smart Power LoRA Loader
[Autopilot LoRA] Node loaded successfully
```

### Test 1.2: Model Dropdowns Populate
**Steps:**
1. Add Smart Power LoRA Loader node to canvas
2. Check `indexing_model` dropdown
3. Check `prompting_model` dropdown

**Expected Result:**
- Both dropdowns show models from both providers
- Format: "groq: model-name" or "gemini: model-name"
- At least 5-10 models listed
- No duplicate entries

**Example Expected Models:**
```
groq: llama-3.1-8b-instant
groq: llama-3.3-70b-versatile
gemini: gemini-1.5-flash
gemini: gemini-1.5-pro
gemini: gemini-2.0-flash-exp
```

## Phase 2: Model Fetching

### Test 2.1: API Model Fetching (Groq Only)
**Setup:**
- Configure only `GROQ_API_KEY` in `.env`
- Leave `GEMINI_API_KEY` empty

**Steps:**
1. Restart ComfyUI
2. Add Smart Power LoRA Loader node
3. Check model dropdowns

**Expected Result:**
- Groq models populate from API
- Gemini models fallback to hardcoded list
- Console shows: `[ModelFetcher] Fetched X models from Groq API`
- Console shows: `[ModelFetcher] Using fallback for Gemini`

### Test 2.2: API Model Fetching (Gemini Only)
**Setup:**
- Configure only `GEMINI_API_KEY` in `.env`
- Leave `GROQ_API_KEY` empty

**Steps:**
1. Restart ComfyUI
2. Add Smart Power LoRA Loader node
3. Check model dropdowns

**Expected Result:**
- Gemini models populate from API
- Groq models fallback to hardcoded list
- Console shows: `[ModelFetcher] Fetched X models from Gemini API`
- Console shows: `[ModelFetcher] Using fallback for Groq`

### Test 2.3: API Model Fetching (Both Keys)
**Setup:**
- Configure both API keys in `.env`

**Steps:**
1. Restart ComfyUI
2. Add Smart Power LoRA Loader node
3. Check model dropdowns

**Expected Result:**
- Both providers fetch from APIs
- Console shows fetch success for both
- Dropdown includes latest models from both providers

### Test 2.4: Fallback Behavior (No API Keys)
**Setup:**
- Remove or comment out all API keys in `.env`

**Steps:**
1. Restart ComfyUI
2. Add Smart Power LoRA Loader node
3. Check model dropdowns

**Expected Result:**
- Dropdowns still populate with hardcoded defaults
- Console shows: `[ModelFetcher] Using fallback models`
- Node remains functional

## Phase 3: Parameter Naming

### Test 3.1: Prompt Parameter
**Steps:**
1. Add Smart Power LoRA Loader node
2. Check for `prompt` input field
3. Hover over parameter to see tooltip

**Expected Result:**
- Parameter named `prompt` (not `base_context`)
- Tooltip is detailed (3-5 sentences)
- Tooltip mentions: "Your creative idea or prompt for image/video generation"

### Test 3.2: Image Parameter
**Steps:**
1. Check for `image` input
2. Verify it accepts IMAGE type
3. Check tooltip

**Expected Result:**
- Parameter named `image` (not `init_image`)
- Type: IMAGE
- Tooltip mentions vision model usage

### Test 3.3: Removed Parameters
**Steps:**
1. Inspect all node parameters
2. Search for old parameter names

**Expected Result:**
- No `indexing_provider` parameter
- No `prompting_provider` parameter
- No `autoselect` parameter (always on)
- No `allowlist_loras` parameter

## Phase 4: New Features

### Test 4.1: enable_negative_prompt Toggle
**Steps:**
1. Add Smart Power LoRA Loader node
2. Find `enable_negative_prompt` parameter
3. Verify default value is False
4. Toggle to True
5. Run workflow

**Expected Result:**
- Parameter exists and defaults to False
- When False: negative_prompt output is minimal/empty
- When True: negative_prompt output contains AI-generated content
- Console shows: `[Prompting] Negative prompt generation: enabled/disabled`

### Test 4.2: max_index_count Limiting
**Steps:**
1. Add LoRA Manager node
2. Set `max_index_count` to 5
3. Run "Scan & Index New LoRAs" with 20+ unindexed LoRAs

**Expected Result:**
- Only 5 LoRAs indexed
- Console shows: `[Manager] Limiting to first 5 of 20 LoRAs`
- Progress stops at 5/5
- Remaining LoRAs stay unindexed

### Test 4.3: disable_lora Flag
**Steps:**
1. Add LoRA Manager node
2. Select a LoRA
3. Set `disable_lora` to True
4. Apply changes
5. Run Smart Power LoRA Loader with that LoRA's style

**Expected Result:**
- LoRA marked as disabled in catalog
- Smart Power LoRA Loader skips that LoRA during auto-selection
- Console shows: `[Selection] Excluding disabled LoRAs: X`
- LoRA can still be manually selected via `manual_loras`

## Phase 5: LoRA Manager Updates

### Test 5.1: Scan & Index (No Provider Selector)
**Steps:**
1. Add LoRA Manager node
2. Set action to "Scan & Index New LoRAs"
3. Select indexing model (note: single dropdown, not provider + model)
4. Set `max_index_count` to 10
5. Run

**Expected Result:**
- No error about missing `indexing_provider`
- Model string parsed correctly ("provider: model")
- Indexing proceeds using correct API
- Console shows: `[Manager] Using groq with model llama-3.1-8b-instant`

### Test 5.2: Re-index Selected LoRA
**Steps:**
1. Add LoRA Manager node
2. Set action to "Re-index Selected LoRA"
3. Select a LoRA
4. Select indexing model
5. Enable `force_reindex`
6. Run

**Expected Result:**
- LoRA re-indexed with selected model
- Model string parsed correctly
- No error about `indexing_provider`
- Console shows successful re-indexing

### Test 5.3: Manual Metadata Edit
**Steps:**
1. Add LoRA Manager node
2. Select a LoRA
3. Edit `edit_summary`, `edit_triggers`, `edit_tags`
4. Set `disable_lora` to True
5. Run

**Expected Result:**
- Metadata updates in catalog
- Disabled flag set correctly
- Console shows: `[Manager] Applying manual edits`
- Changes persist in catalog

## Phase 6: Integration Testing

### Test 6.1: Full Workflow (Groq)
**Steps:**
1. Add Smart Power LoRA Loader
2. Set `prompt` to "cyberpunk city at night"
3. Select `base_model` (e.g., "Flux-1")
4. Select Groq model for both indexing and prompting
5. Connect MODEL and CLIP
6. Set `reindex_on_run` to True (first run)
7. Run workflow

**Expected Result:**
- New LoRAs indexed
- LoRAs auto-selected based on prompt
- Detailed prompt generated with trigger words
- MODEL and CLIP outputs have LoRAs applied
- Console shows selection and application process

### Test 6.2: Full Workflow (Gemini)
**Steps:**
1. Same as 6.1 but select Gemini models
2. Use different prompt: "medieval castle in fantasy forest"

**Expected Result:**
- Works with Gemini API
- Different LoRAs selected (appropriate to prompt)
- Prompt generation style may differ from Groq

### Test 6.3: Vision Model with Image
**Steps:**
1. Add Smart Power LoRA Loader
2. Connect an `image` input
3. Set `prompt` to "match this style"
4. Select vision-capable model (e.g., "gemini: gemini-1.5-flash")
5. Run

**Expected Result:**
- Image analyzed by vision model
- Console shows: `[Prompting] Using vision model with reference image`
- LoRAs selected based on image content
- Prompt reflects image analysis

### Test 6.4: Manual LoRAs + Auto-Selection
**Steps:**
1. Add Smart Power LoRA Loader
2. Set `manual_loras` to "character_lora.safetensors"
3. Set `prompt` to "wearing cyberpunk outfit"
4. Run

**Expected Result:**
- Character LoRA applied first
- Additional LoRAs auto-selected for outfit
- Console shows: `[Application] Manual LoRAs: 1`
- Console shows: `[Application] Auto-selected LoRAs: X`
- No duplication if character LoRA also auto-selected

## Phase 7: Error Handling

### Test 7.1: Invalid Model String
**Steps:**
1. Manually edit catalog or test with invalid format
2. Try model string without prefix (e.g., "llama-3.1-8b")

**Expected Result:**
- Graceful fallback to first available provider
- Console warning: `[Warning] Invalid model format`
- Workflow continues

### Test 7.2: API Failure During Run
**Steps:**
1. Start workflow with valid API key
2. Revoke API key during execution (or use invalid key)

**Expected Result:**
- Clear error message
- Console shows: `[Error] API key invalid or expired`
- Node doesn't crash ComfyUI

### Test 7.3: No API Key for Selected Provider
**Steps:**
1. Select "groq: llama-3.1-8b-instant"
2. Remove GROQ_API_KEY from .env
3. Run

**Expected Result:**
- Clear error message
- Console shows: `[Error] No API key for groq`
- Suggests checking .env configuration

## Phase 8: Performance & Edge Cases

### Test 8.1: Large LoRA Collection (100+ LoRAs)
**Steps:**
1. Test with 100+ LoRAs in directory
2. Set `reindex_on_run` to False
3. Run workflow multiple times

**Expected Result:**
- Reasonable load time (<5 seconds for catalog read)
- Selection completes within 30 seconds
- No memory issues

### Test 8.2: Rapid Successive Runs
**Steps:**
1. Run workflow 5 times in quick succession
2. Different prompts each time

**Expected Result:**
- No rate limit errors (with Groq)
- Each run completes successfully
- Catalog saves don't conflict

### Test 8.3: Empty Prompt
**Steps:**
1. Leave `prompt` field empty
2. Run workflow

**Expected Result:**
- Graceful handling
- Console shows: `[Warning] Empty prompt, using default selection`
- Some LoRAs still selected (random or default)

### Test 8.4: Unsupported Base Model
**Steps:**
1. Select base model not in any LoRA catalog
2. Run workflow

**Expected Result:**
- Console shows: `[Warning] No LoRAs found for base model`
- Workflow continues without LoRAs
- Clear message in output

## Phase 9: Tooltip Verification

### Test 9.1: All Tooltips Present
**Steps:**
1. Add Smart Power LoRA Loader node
2. Hover over each parameter
3. Verify tooltip appears

**Expected Result:**
- Every parameter has a tooltip
- Tooltips are detailed (3-5 sentences)
- No placeholder text ("TODO" or "Description here")

### Test 9.2: Tooltip Accuracy
**Steps:**
1. Read each tooltip
2. Test the parameter as described

**Expected Result:**
- Tooltips accurately describe functionality
- Examples in tooltips work as stated
- Recommended values are sensible

## Phase 10: Documentation Verification

### Test 10.1: README Accuracy
**Steps:**
1. Follow README setup instructions
2. Compare parameter names in README vs actual node

**Expected Result:**
- All parameter names match
- No references to old names (`base_context`, `init_image`, etc.)
- Examples use current parameter names

### Test 10.2: REFACTORING_SUMMARY Completeness
**Steps:**
1. Review REFACTORING_SUMMARY.md
2. Test each listed change

**Expected Result:**
- All listed changes implemented
- No missing features
- Breaking changes section accurate

## Test Results Template

Create a test results document with this format:

```markdown
# Test Results - v1.2.0 Refactoring
Date: [DATE]
Tester: [NAME]
ComfyUI Version: [VERSION]

## Phase 1: Node Loading
- [ ] Test 1.1: PASS/FAIL - [Notes]
- [ ] Test 1.2: PASS/FAIL - [Notes]

## Phase 2: Model Fetching
- [ ] Test 2.1: PASS/FAIL - [Notes]
- [ ] Test 2.2: PASS/FAIL - [Notes]
- [ ] Test 2.3: PASS/FAIL - [Notes]
- [ ] Test 2.4: PASS/FAIL - [Notes]

[Continue for all phases...]

## Issues Found
1. [Issue description] - Severity: HIGH/MEDIUM/LOW
2. [Issue description] - Severity: HIGH/MEDIUM/LOW

## Overall Assessment
[Summary of testing results and recommendation]
```

## Critical Issues to Watch For

1. **Model Parsing Failures:**
   - Symptom: Error when selecting models
   - Check: Console for parsing errors
   - Fix: Verify model_fetcher.parse_model_string()

2. **API Key Access:**
   - Symptom: "No API key" errors despite .env configured
   - Check: ConfigManager property decorators
   - Fix: Verify config_manager.py properties

3. **Catalog Corruption:**
   - Symptom: LoRAs disappear or metadata lost
   - Check: data/lora_index.json integrity
   - Backup: Keep backup of catalog before testing

4. **Memory Leaks:**
   - Symptom: ComfyUI slows down after multiple runs
   - Check: Memory usage in Task Manager
   - Monitor: Long testing sessions (20+ runs)

## Performance Benchmarks

Target performance metrics:

- **Node Load Time:** <2 seconds
- **Model Dropdown Population:** <3 seconds
- **LoRA Indexing (per LoRA):** 2-5 seconds with LLM
- **LoRA Selection:** <15 seconds with LLM
- **Prompt Generation:** <10 seconds
- **Total Workflow:** <60 seconds (including LLM calls)

## Next Steps After Testing

1. **Document Issues:** Create GitHub issues for any failures
2. **Update Changelog:** Add test results to CHANGELOG.md
3. **Tag Release:** Tag v1.2.0 if all critical tests pass
4. **User Beta:** Consider beta release for real-world testing
5. **Monitor Feedback:** Watch for user-reported issues

## Contact for Testing Questions

- GitHub Issues: [Repository URL]
- Check console output for detailed error messages
- Include full console log when reporting issues
