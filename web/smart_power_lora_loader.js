import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { api } from "../../scripts/api.js";

// Name of our node type
const NODE_NAME = "⚡ Smart Power LoRA Loader";

// Store available LoRAs globally
let availableLoras = [];

// Fetch LoRAs from ComfyUI
async function getAvailableLoras() {
    if (availableLoras.length === 0) {
        try {
            // Use ComfyUI's object_info to get LoRA list
            const objectInfo = await api.getObjectInfo();
            // Look for any LoRA loader node to get the lora list
            for (const nodeType in objectInfo) {
                const nodeDef = objectInfo[nodeType];
                if (nodeDef.input && nodeDef.input.required) {
                    for (const inputName in nodeDef.input.required) {
                        const inputDef = nodeDef.input.required[inputName];
                        if (Array.isArray(inputDef) && inputDef[0] && Array.isArray(inputDef[0])) {
                            // Check if this looks like a LoRA list (contains .safetensors files)
                            const firstItem = inputDef[0][0] || "";
                            if (typeof firstItem === 'string' && firstItem.includes('.safetensors')) {
                                availableLoras = inputDef[0];
                                return availableLoras;
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error("[Autopilot LoRA] Failed to fetch LoRAs:", error);
        }
    }
    return availableLoras;
}

// Fetch LoRA catalog info
async function getLoraInfo(loraName) {
    try {
        const response = await api.fetchApi('/autopilot_lora/info?file=' + encodeURIComponent(loraName));
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.warn("[Autopilot LoRA] Could not fetch info for:", loraName, error);
    }
    return null;
}

// Show LoRA chooser dialog
function showLoraChooser(callback, currentValue = null) {
    const dialog = document.createElement('div');
    dialog.className = 'comfy-modal';
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #1e1e1e;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 20px;
        max-width: 500px;
        max-height: 600px;
        overflow: auto;
        color: #fff;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Select LoRA';
    title.style.marginTop = '0';
    content.appendChild(title);

    const search = document.createElement('input');
    search.type = 'text';
    search.placeholder = 'Search LoRAs...';
    search.style.cssText = `
        width: 100%;
        padding: 8px;
        margin-bottom: 10px;
        background: #2a2a2a;
        border: 1px solid #444;
        color: #fff;
        border-radius: 3px;
    `;
    content.appendChild(search);

    const list = document.createElement('div');
    list.style.cssText = `
        max-height: 400px;
        overflow-y: auto;
    `;

    function updateList(filter = '') {
        list.innerHTML = '';
        const filtered = availableLoras.filter(lora => 
            lora.toLowerCase().includes(filter.toLowerCase())
        );

        filtered.forEach(lora => {
            const item = document.createElement('div');
            item.textContent = lora;
            item.style.cssText = `
                padding: 8px;
                cursor: pointer;
                border-bottom: 1px solid #333;
                ${lora === currentValue ? 'background: #444;' : ''}
            `;
            item.onmouseenter = () => item.style.background = '#444';
            item.onmouseleave = () => item.style.background = lora === currentValue ? '#444' : 'transparent';
            item.onclick = () => {
                callback(lora);
                document.body.removeChild(dialog);
            };
            list.appendChild(item);
        });
    }

    search.oninput = (e) => updateList(e.target.value);
    content.appendChild(list);

    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'margin-top: 10px; text-align: right;';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = `
        padding: 8px 16px;
        background: #444;
        border: none;
        color: #fff;
        border-radius: 3px;
        cursor: pointer;
    `;
    cancelBtn.onclick = () => document.body.removeChild(dialog);
    buttonContainer.appendChild(cancelBtn);

    content.appendChild(buttonContainer);
    dialog.appendChild(content);

    dialog.onclick = (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    };

    document.body.appendChild(dialog);
    updateList();
    search.focus();
}

// Show LoRA info dialog
function showLoraInfoDialog(loraName, catalogInfo) {
    const dialog = document.createElement('div');
    dialog.className = 'comfy-modal';
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #1e1e1e;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 20px;
        max-width: 600px;
        max-height: 700px;
        overflow: auto;
        color: #fff;
    `;

    const title = document.createElement('h2');
    title.textContent = catalogInfo?.display_name || loraName;
    title.style.marginTop = '0';
    content.appendChild(title);

    if (catalogInfo) {
        // Summary
        if (catalogInfo.summary) {
            const summaryLabel = document.createElement('h3');
            summaryLabel.textContent = 'Summary';
            summaryLabel.style.color = '#888';
            summaryLabel.style.fontSize = '0.9em';
            content.appendChild(summaryLabel);

            const summary = document.createElement('p');
            summary.textContent = catalogInfo.summary;
            summary.style.marginTop = '5px';
            content.appendChild(summary);
        }

        // Trigger Words
        if (catalogInfo.trained_words && catalogInfo.trained_words.length > 0) {
            const triggerLabel = document.createElement('h3');
            triggerLabel.textContent = 'Trigger Words';
            triggerLabel.style.color = '#888';
            triggerLabel.style.fontSize = '0.9em';
            triggerLabel.style.marginTop = '15px';
            content.appendChild(triggerLabel);

            const triggers = document.createElement('div');
            triggers.style.cssText = 'display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;';
            catalogInfo.trained_words.forEach(word => {
                const tag = document.createElement('span');
                tag.textContent = word;
                tag.style.cssText = `
                    background: #2a5a8a;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 0.9em;
                `;
                triggers.appendChild(tag);
            });
            content.appendChild(triggers);
        }

        // Tags
        if (catalogInfo.tags && catalogInfo.tags.length > 0) {
            const tagsLabel = document.createElement('h3');
            tagsLabel.textContent = 'Tags';
            tagsLabel.style.color = '#888';
            tagsLabel.style.fontSize = '0.9em';
            tagsLabel.style.marginTop = '15px';
            content.appendChild(tagsLabel);

            const tags = document.createElement('div');
            tags.style.cssText = 'display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;';
            catalogInfo.tags.forEach(tag => {
                const tagEl = document.createElement('span');
                tagEl.textContent = tag;
                tagEl.style.cssText = `
                    background: #444;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 0.9em;
                `;
                tags.appendChild(tagEl);
            });
            content.appendChild(tags);
        }

        // Base Model Compatibility
        if (catalogInfo.base_compat && catalogInfo.base_compat.length > 0) {
            const baseLabel = document.createElement('h3');
            baseLabel.textContent = 'Base Model';
            baseLabel.style.color = '#888';
            baseLabel.style.fontSize = '0.9em';
            baseLabel.style.marginTop = '15px';
            content.appendChild(baseLabel);

            const baseModel = document.createElement('p');
            baseModel.textContent = catalogInfo.base_compat.join(', ');
            baseModel.style.marginTop = '5px';
            content.appendChild(baseModel);
        }

        // Weight
        if (catalogInfo.default_weight != null) {
            const weightLabel = document.createElement('h3');
            weightLabel.textContent = 'Default Weight';
            weightLabel.style.color = '#888';
            weightLabel.style.fontSize = '0.9em';
            weightLabel.style.marginTop = '15px';
            content.appendChild(weightLabel);

            const weight = document.createElement('p');
            weight.textContent = catalogInfo.default_weight.toFixed(2);
            weight.style.marginTop = '5px';
            content.appendChild(weight);
        }

        // Civitai Link
        if (catalogInfo.civitai_model_id) {
            const link = document.createElement('a');
            link.href = `https://civitai.com/models/${catalogInfo.civitai_model_id}`;
            link.target = '_blank';
            link.textContent = '🔗 View on Civitai';
            link.style.cssText = `
                display: inline-block;
                margin-top: 15px;
                padding: 8px 12px;
                background: #2a5a8a;
                color: #fff;
                text-decoration: none;
                border-radius: 3px;
            `;
            content.appendChild(link);
        }
    } else {
        const noInfo = document.createElement('p');
        noInfo.textContent = 'No catalog information available for this LoRA. Run indexing to fetch metadata.';
        noInfo.style.color = '#888';
        content.appendChild(noInfo);
    }

    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText = `
        margin-top: 20px;
        padding: 8px 16px;
        background: #444;
        border: none;
        color: #fff;
        border-radius: 3px;
        cursor: pointer;
        width: 100%;
    `;
    closeBtn.onclick = () => document.body.removeChild(dialog);
    content.appendChild(closeBtn);

    dialog.appendChild(content);
    dialog.onclick = (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    };

    document.body.appendChild(dialog);
}

// Custom widget for manual LoRA selection
function ManualLoraWidget(node, inputName, inputData, app) {
    const widget = {
        type: "manual_loras_selector",
        name: inputName,
        value: [],
        draw: function(ctx, node, width, posY, height) {
            // Draw a summary of selected LoRAs
            ctx.save();
            ctx.fillStyle = "#666";
            ctx.font = "12px Arial";
            ctx.textAlign = "left";
            
            const text = this.value.length > 0 
                ? `${this.value.length} manual LoRA(s) selected`
                : "Click 'Add Manual LoRA' button below";
            
            ctx.fillText(text, 15, posY + height / 2);
            ctx.restore();
        },
        computeSize: function(width) {
            return [width, 25];
        },
        serializeValue: function() {
            // Convert array to comma-separated string for Python
            return this.value.map(lora => lora.name).join(',');
        }
    };
    
    widget.value = [];
    return widget;
}

// Register the extension
app.registerExtension({
    name: "autopilot.lora.loader",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "SmartPowerLoRALoader") {
            // Store original onNodeCreated
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = async function() {
                const result = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Load available LoRAs
                await getAvailableLoras();
                
                // Find the manual_loras widget
                const manualLorasWidget = this.widgets?.find(w => w.name === "manual_loras");
                if (manualLorasWidget) {
                    // Store original type
                    manualLorasWidget.originalType = manualLorasWidget.type;
                    
                    // Initialize array if string
                    if (typeof manualLorasWidget.value === 'string') {
                        const loraNames = manualLorasWidget.value.split(',').map(s => s.trim()).filter(s => s);
                        manualLorasWidget.value = loraNames.map(name => ({ name, weight: 1.0 }));
                    } else if (!Array.isArray(manualLorasWidget.value)) {
                        manualLorasWidget.value = [];
                    }
                    
                    // Override serializeValue to convert back to string
                    const originalSerialize = manualLorasWidget.serializeValue;
                    manualLorasWidget.serializeValue = function() {
                        if (Array.isArray(this.value)) {
                            return this.value.map(lora => lora.name).join(',');
                        }
                        return this.value;
                    };
                }
                
                // Add "Add Manual LoRA" button
                const addLoraBtn = this.addWidget("button", "➕ Add Manual LoRA", null, () => {
                    showLoraChooser((selectedLora) => {
                        if (manualLorasWidget) {
                            if (!Array.isArray(manualLorasWidget.value)) {
                                manualLorasWidget.value = [];
                            }
                            // Check if not already added
                            if (!manualLorasWidget.value.find(l => l.name === selectedLora)) {
                                manualLorasWidget.value.push({ name: selectedLora, weight: 1.0 });
                                this.setDirtyCanvas(true, true);
                            }
                        }
                    });
                });
                
                // Add button to manage manual LoRAs
                const manageBtn = this.addWidget("button", "📋 Manage Manual LoRAs", null, () => {
                    showManualLorasManager(this, manualLorasWidget);
                });
                
                // Add "Show LoRA Catalog" button at the end
                const showInfoBtn = this.addWidget("button", "ℹ️ Show LoRA Catalog", null, async () => {
                    await showLoraCatalogDialog(this);
                });
                
                return result;
            };
            
            // Add context menu for node
            const origGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function(_, options) {
                if (origGetExtraMenuOptions) {
                    origGetExtraMenuOptions.apply(this, arguments);
                }
                
                options.push({
                    content: "ℹ️ Show LoRA Catalog",
                    callback: async () => {
                        await showLoraCatalogDialog(this);
                    }
                });
            };
        }
    }
});

// Show manager for manual LoRAs
function showManualLorasManager(node, widget) {
    if (!widget || !Array.isArray(widget.value)) {
        alert("No manual LoRAs to manage");
        return;
    }

    const dialog = document.createElement('div');
    dialog.className = 'comfy-modal';
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #1e1e1e;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 20px;
        max-width: 600px;
        max-height: 600px;
        overflow: auto;
        color: #fff;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Manage Manual LoRAs';
    title.style.marginTop = '0';
    content.appendChild(title);

    const list = document.createElement('div');
    list.style.cssText = 'margin: 15px 0;';

    function refreshList() {
        list.innerHTML = '';
        
        if (widget.value.length === 0) {
            const empty = document.createElement('p');
            empty.textContent = 'No manual LoRAs selected';
            empty.style.color = '#888';
            list.appendChild(empty);
            return;
        }

        widget.value.forEach((lora, index) => {
            const item = document.createElement('div');
            item.style.cssText = `
                padding: 10px;
                background: #2a2a2a;
                margin-bottom: 8px;
                border-radius: 3px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;

            const nameSpan = document.createElement('span');
            nameSpan.textContent = lora.name;
            nameSpan.style.flex = '1';
            item.appendChild(nameSpan);

            const btnContainer = document.createElement('div');
            btnContainer.style.cssText = 'display: flex; gap: 5px;';

            const infoBtn = document.createElement('button');
            infoBtn.textContent = 'ℹ️';
            infoBtn.title = 'Show Info';
            infoBtn.style.cssText = `
                padding: 4px 8px;
                background: #2a5a8a;
                border: none;
                color: #fff;
                border-radius: 3px;
                cursor: pointer;
            `;
            infoBtn.onclick = async () => {
                const info = await getLoraInfo(lora.name);
                showLoraInfoDialog(lora.name, info);
            };
            btnContainer.appendChild(infoBtn);

            const removeBtn = document.createElement('button');
            removeBtn.textContent = '🗑️';
            removeBtn.title = 'Remove';
            removeBtn.style.cssText = `
                padding: 4px 8px;
                background: #8a2a2a;
                border: none;
                color: #fff;
                border-radius: 3px;
                cursor: pointer;
            `;
            removeBtn.onclick = () => {
                widget.value.splice(index, 1);
                refreshList();
                node.setDirtyCanvas(true, true);
            };
            btnContainer.appendChild(removeBtn);

            item.appendChild(btnContainer);
            list.appendChild(item);
        });
    }

    refreshList();
    content.appendChild(list);

    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText = `
        padding: 8px 16px;
        background: #444;
        border: none;
        color: #fff;
        border-radius: 3px;
        cursor: pointer;
        width: 100%;
    `;
    closeBtn.onclick = () => document.body.removeChild(dialog);
    content.appendChild(closeBtn);

    dialog.appendChild(content);
    dialog.onclick = (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    };

    document.body.appendChild(dialog);
}

// Show full LoRA catalog dialog
async function showLoraCatalogDialog(node) {
    try {
        const response = await api.fetchApi('/autopilot_lora/catalog');
        const catalog = response.ok ? await response.json() : {};

        const dialog = document.createElement('div');
        dialog.className = 'comfy-modal';
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: #1e1e1e;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 20px;
            width: 80%;
            max-width: 900px;
            height: 80%;
            overflow: auto;
            color: #fff;
        `;

        const title = document.createElement('h2');
        title.textContent = 'LoRA Catalog';
        title.style.marginTop = '0';
        content.appendChild(title);

        const search = document.createElement('input');
        search.type = 'text';
        search.placeholder = 'Search LoRAs...';
        search.style.cssText = `
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 3px;
        `;
        content.appendChild(search);

        const catalogList = document.createElement('div');
        catalogList.style.cssText = 'display: flex; flex-direction: column; gap: 10px;';

        function displayCatalog(filter = '') {
            catalogList.innerHTML = '';
            
            const entries = Object.values(catalog);
            const filtered = entries.filter(entry => 
                entry.display_name?.toLowerCase().includes(filter.toLowerCase()) ||
                entry.file?.toLowerCase().includes(filter.toLowerCase()) ||
                entry.summary?.toLowerCase().includes(filter.toLowerCase())
            );

            if (filtered.length === 0) {
                const noResults = document.createElement('p');
                noResults.textContent = filter ? 'No matching LoRAs found' : 'No LoRAs in catalog. Run indexing first.';
                noResults.style.color = '#888';
                catalogList.appendChild(noResults);
                return;
            }

            filtered.forEach(entry => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 15px;
                    background: #2a2a2a;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: background 0.2s;
                `;
                item.onmouseenter = () => item.style.background = '#333';
                item.onmouseleave = () => item.style.background = '#2a2a2a';
                item.onclick = () => showLoraInfoDialog(entry.file, entry);

                const name = document.createElement('div');
                name.textContent = entry.display_name || entry.file;
                name.style.cssText = 'font-weight: bold; margin-bottom: 5px;';
                item.appendChild(name);

                if (entry.summary) {
                    const summary = document.createElement('div');
                    summary.textContent = entry.summary.substring(0, 150) + (entry.summary.length > 150 ? '...' : '');
                    summary.style.cssText = 'font-size: 0.9em; color: #aaa; margin-bottom: 8px;';
                    item.appendChild(summary);
                }

                const meta = document.createElement('div');
                meta.style.cssText = 'font-size: 0.85em; color: #888; display: flex; gap: 15px;';
                
                if (entry.base_compat && entry.base_compat.length > 0) {
                    const base = document.createElement('span');
                    base.textContent = `📦 ${entry.base_compat.join(', ')}`;
                    meta.appendChild(base);
                }

                if (entry.trained_words && entry.trained_words.length > 0) {
                    const triggers = document.createElement('span');
                    triggers.textContent = `🏷️ ${entry.trained_words.length} triggers`;
                    meta.appendChild(triggers);
                }

                item.appendChild(meta);
                catalogList.appendChild(item);
            });
        }

        search.oninput = (e) => displayCatalog(e.target.value);
        content.appendChild(catalogList);
        displayCatalog();

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.style.cssText = `
            margin-top: 20px;
            padding: 8px 16px;
            background: #444;
            border: none;
            color: #fff;
            border-radius: 3px;
            cursor: pointer;
            width: 100%;
        `;
        closeBtn.onclick = () => document.body.removeChild(dialog);
        content.appendChild(closeBtn);

        dialog.appendChild(content);
        dialog.onclick = (e) => {
            if (e.target === dialog) {
                document.body.removeChild(dialog);
            }
        };

        document.body.appendChild(dialog);
    } catch (error) {
        console.error("[Autopilot LoRA] Failed to show catalog:", error);
        alert("Failed to load LoRA catalog. Make sure the API endpoint is available.");
    }
}
