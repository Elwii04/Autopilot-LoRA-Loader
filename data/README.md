# Data Directory

This directory stores the persistent LoRA catalog (`lora_index.json`) which is automatically created on first run.

The catalog contains:
- LoRA file hashes
- Extracted metadata (trained words, tags, summaries)
- Base model compatibility information
- Default weights
- Civitai data cache

**Note:** `lora_index.json` is created automatically by the node on first execution. You don't need to create it manually.
