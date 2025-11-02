# UI Features Guide

This guide explains the advanced UI features of the Smart Power LoRA Loader, inspired by rgthree's Power LoRA Loader design patterns.

## Overview

The Smart Power LoRA Loader now includes a rich JavaScript-based UI that provides:

1. **Manual LoRA Selection with Dropdowns** - No more typing filenames
2. **LoRA Catalog Browser** - Browse and search all indexed LoRAs
3. **LoRA Info Dialogs** - View detailed metadata for any LoRA
4. **Interactive Management** - Add, remove, and organize manual LoRAs

## Features

### 1. Manual LoRA Selection

**Old System:** Text input where you type comma-separated filenames
```
manual_loras: "character_lora.safetensors, style_lora.safetensors"
```

**New System:** Interactive dropdown selection with dedicated buttons

#### How to Use:

1. **Add Manual LoRA Button** (`➕ Add Manual LoRA`)
   - Click this button to open the LoRA chooser dialog
   - Search for LoRAs by name using the search box
   - Click on any LoRA to add it to your manual selection
   - LoRAs are automatically deduplicated

2. **Manage Manual LoRAs Button** (`📋 Manage Manual LoRAs`)
   - Opens a dialog showing all currently selected manual LoRAs
   - Each LoRA has action buttons:
     - `ℹ️` - Show info about this LoRA
     - `🗑️` - Remove from manual selection
   - Changes are immediately applied to the node

### 2. LoRA Catalog Browser

**Button:** `ℹ️ Show LoRA Catalog`

This button opens a comprehensive catalog browser that shows ALL indexed LoRAs in your collection.

#### Features:

- **Search Functionality**: Type to filter LoRAs by name, summary, or tags
- **Visual Cards**: Each LoRA displayed with:
  - Display name or filename
  - Summary (first 150 characters)
  - Base model compatibility (📦 icon)
  - Number of trigger words (🏷️ icon)
- **Click to View**: Click any LoRA card to open its detailed info dialog

#### When to Use:

- Browse your entire LoRA collection
- Find LoRAs by keywords or themes
- Discover what LoRAs you have indexed
- Check which LoRAs are compatible with your base model

### 3. LoRA Info Dialog

Displays comprehensive metadata for a specific LoRA. Opens when you:
- Click on a LoRA in the catalog browser
- Click the `ℹ️` button in the manual LoRAs manager
- Right-click a LoRA in various contexts

#### Information Displayed:

**Header**
- LoRA display name or filename

**Summary** (if available)
- AI-generated description of what the LoRA does
- Extracted during indexing from Civitai metadata

**Trigger Words** (if available)
- Blue tags showing exact words to use in prompts
- These activate the LoRA's trained features
- Example: `cyberpunk_style`, `neon_lights`, `futuristic`

**Tags** (if available)
- Gray tags showing categories and themes
- Example: `style`, `clothing`, `character`, `concept art`

**Base Model Compatibility**
- Shows which base models this LoRA works with
- Example: `Flux-1`, `SDXL`, `SD1.x`

**Default Weight**
- Recommended strength value for this LoRA
- Usually between 0.5 and 1.5

**Civitai Link** (if available)
- Direct link to the LoRA's page on Civitai
- Opens in new tab for more info, examples, versions

#### When to Use:

- Check trigger words before using a LoRA
- Verify base model compatibility
- Get ideas from the summary
- Find the Civitai page for more examples

### 4. Node Context Menu

Right-click on the node to access:
- **Show LoRA Catalog** - Quick access to catalog browser
- Other standard ComfyUI node options

## Usage Workflows

### Workflow 1: Quick Manual LoRA Addition

```
1. Click "➕ Add Manual LoRA"
2. Search for your character LoRA
3. Click to select it
4. Repeat for additional LoRAs
5. Run your workflow
```

### Workflow 2: Browse and Discover

```
1. Click "ℹ️ Show LoRA Catalog"
2. Search for a theme (e.g., "cyberpunk")
3. Click on interesting LoRAs to view details
4. Note trigger words for your prompt
5. Close and add LoRA via "Add Manual LoRA" if needed
```

### Workflow 3: Review Manual Selection

```
1. Click "📋 Manage Manual LoRAs"
2. Review your current selection
3. Click ℹ️ on any LoRA to review its info
4. Remove unwanted LoRAs with 🗑️
5. Close when done
```

### Workflow 4: Check LoRA Compatibility

```
1. Open "ℹ️ Show LoRA Catalog"
2. Search for LoRAs
3. Click to view details
4. Check "Base Model" field
5. Ensure it matches your checkpoint (e.g., Flux-1)
```

## Technical Details

### Manual LoRAs Format

**Internal Storage:**
- JavaScript stores as array: `[{ name: "lora1.safetensors", weight: 1.0 }, ...]`
- Converted to comma-separated string for Python: `"lora1.safetensors,lora2.safetensors"`

**Python Processing:**
- Receives comma-separated string
- Splits and processes as before
- Fully backward compatible with old text input

### API Endpoints

The UI connects to these endpoints:

1. **`GET /autopilot_lora/catalog`**
   - Returns complete catalog as JSON
   - Used by catalog browser

2. **`GET /autopilot_lora/info?file=<filename>`**
   - Returns metadata for specific LoRA
   - Used by info dialogs

### Catalog Data Structure

Each LoRA entry contains:

```json
{
  "file": "lora_name.safetensors",
  "display_name": "LoRA Name",
  "summary": "AI-generated description",
  "trained_words": ["trigger1", "trigger2"],
  "tags": ["style", "character"],
  "base_compat": ["Flux-1"],
  "default_weight": 1.0,
  "civitai_model_id": 12345,
  "indexed_by_llm": true,
  "disabled": false
}
```

## Comparison with rgthree Power LoRA Loader

### Similarities

- **Dropdown Selection**: Both use searchable dropdown dialogs
- **Info Dialogs**: Both show detailed LoRA metadata
- **Visual Design**: Similar dark theme and button styles
- **Search Functionality**: Filter LoRAs by name

### Differences

| Feature | rgthree | Autopilot LoRA |
|---------|---------|----------------|
| **LoRA Selection** | AI-powered auto-selection | ✅ AI-powered auto-selection |
| **Manual Addition** | Manual only | ✅ Manual + Auto hybrid |
| **Catalog Browser** | ❌ No catalog view | ✅ Full catalog browser |
| **Prompt Generation** | ❌ Manual prompts | ✅ AI-generated prompts |
| **Base Model Filter** | ❌ No filtering | ✅ Auto-filters by base model |
| **Indexing** | External tool | ✅ Built-in with LLM |
| **Strength per LoRA** | ✅ Individual sliders | ⚠️ Global weight (for now) |

## Tips & Best Practices

### Managing Your Collection

1. **Index First**: Use LoRA Manager to index new LoRAs before using the catalog
2. **Search Smart**: Use tags like "style", "character", "clothing" to narrow results
3. **Check Compatibility**: Always verify base model matches your checkpoint
4. **Bookmark Triggers**: Note down trigger words for your favorite LoRAs

### Performance

- **Large Collections**: Catalog browser handles 100+ LoRAs smoothly
- **Search Responsiveness**: Search is client-side for instant results
- **API Calls**: Info dialogs cache data to minimize API requests

### Troubleshooting

**Catalog is Empty**
- Run "Scan & Index New LoRAs" in LoRA Manager node
- Check that LoRAs are in `ComfyUI/models/loras/`
- Verify catalog file exists at `data/lora_index.json`

**LoRA Info Shows "Not Found"**
- LoRA may not be indexed yet
- Run indexing through LoRA Manager
- Check that API endpoints are accessible

**Buttons Don't Appear**
- Ensure ComfyUI loaded the JavaScript extension
- Check browser console for errors
- Verify `web/` directory exists with `.js` file
- Restart ComfyUI

**Dropdown is Empty**
- ComfyUI needs LoRAs in models/loras/ directory
- Restart ComfyUI to refresh LoRA list
- Check permissions on loras folder

## Future Enhancements

Planned improvements:

1. **Per-LoRA Strength Sliders** - Like rgthree's individual strength controls
2. **Drag to Reorder** - Reorder manual LoRAs by dragging
3. **Inline Info Icons** - Quick info preview on hover
4. **Favorites System** - Mark and filter favorite LoRAs
5. **Batch Operations** - Enable/disable multiple LoRAs at once
6. **Custom Tags** - Add your own organizational tags

## Keyboard Shortcuts

When dialogs are open:

- **`Esc`** - Close dialog
- **`Enter`** - Confirm selection (in chooser)
- **`/`** or **`Ctrl+F`** - Focus search box
- **Click outside** - Close dialog

## Accessibility

- All buttons have descriptive text and emojis
- Hover tooltips on action buttons
- Keyboard navigation in dialogs
- Screen reader compatible labels

## Credits

UI design inspired by **rgthree's Power LoRA Loader**, which pioneered this pattern in ComfyUI.

Key differences:
- Built on custom catalog system
- Integrated with AI-powered selection
- Enhanced with full catalog browser
- Optimized for large collections

## Support

If you encounter issues:

1. Check browser console for JavaScript errors
2. Verify API endpoints in terminal output
3. Test with a small LoRA collection first
4. Report issues on GitHub with:
   - Console errors
   - Steps to reproduce
   - Browser and ComfyUI version

---

**Next:** See [README.md](README.md) for overall usage guide and [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing procedures.
