import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Name of our node type
const NODE_NAME = "SmartPowerLoRALoader";

// Store available LoRAs globally
let availableLoras = [];

// Fetch LoRAs from ComfyUI
async function getAvailableLoras() {
    if (availableLoras.length === 0) {
        try {
            // Use ComfyUI's folder_paths API to get LoRAs
            const response = await api.fetchApi('/folder_paths');
            if (response.ok) {
                const data = await response.json();
                if (data && data.loras) {
                    availableLoras = data.loras;
                    return availableLoras;
                }
            }
            
            // Fallback: Use object_info to get LoRA list
            const objectInfo = await api.getObjectInfo();
            for (const nodeType in objectInfo) {
                const nodeDef = objectInfo[nodeType];
                if (nodeDef.input && nodeDef.input.required) {
                    for (const inputName in nodeDef.input.required) {
                        const inputDef = nodeDef.input.required[inputName];
                        if (Array.isArray(inputDef) && inputDef[0] && Array.isArray(inputDef[0])) {
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

// Show LoRA chooser dialog (properly centered)
function showLoraChooser(callback, currentValue = null) {
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #202020;
        border: 2px solid #444;
        border-radius: 8px;
        padding: 20px;
        width: 500px;
        max-height: 80vh;
        overflow: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;

    const title = document.createElement('h3');
    title.textContent = 'Select LoRA';
    title.style.cssText = 'margin: 0 0 15px 0; color: #fff; font-size: 18px;';
    content.appendChild(title);

    const search = document.createElement('input');
    search.type = 'text';
    search.placeholder = 'Search LoRAs...';
    search.style.cssText = `
        width: 100%;
        padding: 10px;
        margin-bottom: 15px;
        background: #2a2a2a;
        border: 1px solid #444;
        color: #fff;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
    `;
    content.appendChild(search);

    const list = document.createElement('div');
    list.style.cssText = `
        max-height: 400px;
        overflow-y: auto;
        margin-bottom: 15px;
    `;

    function updateList(filter = '') {
        list.innerHTML = '';
        const filtered = availableLoras.filter(lora => 
            lora.toLowerCase().includes(filter.toLowerCase())
        );

        if (filtered.length === 0) {
            const noResults = document.createElement('div');
            noResults.textContent = 'No LoRAs found';
            noResults.style.cssText = 'padding: 20px; text-align: center; color: #888;';
            list.appendChild(noResults);
            return;
        }

        filtered.forEach(lora => {
            const item = document.createElement('div');
            item.textContent = lora;
            item.style.cssText = `
                padding: 10px;
                cursor: pointer;
                border-bottom: 1px solid #333;
                color: #fff;
                transition: background 0.2s;
                ${lora === currentValue ? 'background: #3a5a7a;' : ''}
            `;
            item.onmouseenter = () => item.style.background = '#3a5a7a';
            item.onmouseleave = () => item.style.background = lora === currentValue ? '#3a5a7a' : 'transparent';
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
    buttonContainer.style.cssText = 'display: flex; justify-content: flex-end; gap: 10px;';
    
    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.cssText = `
        padding: 10px 20px;
        background: #444;
        border: none;
        color: #fff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    `;
    cancelBtn.onmouseenter = () => cancelBtn.style.background = '#555';
    cancelBtn.onmouseleave = () => cancelBtn.style.background = '#444';
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

// Custom LoRA Widget (like rgthree's PowerLoraLoaderWidget)
class ManualLoraWidget {
    constructor(name, node) {
        this.name = name;
        this.type = "manual_lora";
        this.node = node;
        this.value = {
            lora: "None",
            strength: 1.0,
            on: true
        };
        this.y = 0;
        this.options = { serialize: true };
    }

    draw(ctx, node, widgetWidth, posY, widgetHeight) {
        const margin = 15;
        const midY = posY + widgetHeight / 2;
        
        ctx.save();
        ctx.fillStyle = "#222";
        ctx.fillRect(margin, posY, widgetWidth - margin * 2, widgetHeight);
        ctx.strokeStyle = "#444";
        ctx.strokeRect(margin, posY, widgetWidth - margin * 2, widgetHeight);
        
        // Toggle button
        const toggleSize = 16;
        const toggleX = margin + 10;
        ctx.fillStyle = this.value.on ? "#4a7" : "#666";
        ctx.beginPath();
        ctx.arc(toggleX + toggleSize/2, midY, toggleSize/2, 0, Math.PI * 2);
        ctx.fill();
        
        // LoRA name (clickable)
        const nameX = toggleX + toggleSize + 10;
        const nameWidth = widgetWidth - nameX - 120 - margin * 2;
        ctx.fillStyle = this.value.on ? "#fff" : "#888";
        ctx.font = "12px Arial";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        const displayName = this.value.lora || "None";
        const truncated = displayName.length > 30 ? displayName.substring(0, 27) + "..." : displayName;
        ctx.fillText(truncated, nameX, midY);
        
        // Strength controls
        const strengthX = widgetWidth - margin - 100;
        ctx.fillStyle = this.value.on ? "#fff" : "#888";
        ctx.textAlign = "center";
        
        // Decrease button
        ctx.fillStyle = "#444";
        ctx.fillRect(strengthX, posY + 8, 25, widgetHeight - 16);
        ctx.fillStyle = this.value.on ? "#fff" : "#888";
        ctx.fillText("-", strengthX + 12.5, midY);
        
        // Value display
        ctx.fillStyle = "#333";
        ctx.fillRect(strengthX + 28, posY + 8, 40, widgetHeight - 16);
        ctx.fillStyle = this.value.on ? "#fff" : "#888";
        ctx.fillText(this.value.strength.toFixed(2), strengthX + 48, midY);
        
        // Increase button
        ctx.fillStyle = "#444";
        ctx.fillRect(strengthX + 71, posY + 8, 25, widgetHeight - 16);
        ctx.fillStyle = this.value.on ? "#fff" : "#888";
        ctx.fillText("+", strengthX + 83.5, midY);
        
        ctx.restore();
        
        // Store hit areas for mouse events
        this.hitAreas = {
            toggle: [toggleX, posY, toggleSize + 20, widgetHeight],
            lora: [nameX, posY, nameWidth, widgetHeight],
            decrease: [strengthX, posY + 8, 25, widgetHeight - 16],
            value: [strengthX + 28, posY + 8, 40, widgetHeight - 16],
            increase: [strengthX + 71, posY + 8, 25, widgetHeight - 16]
        };
        
        this.last_y = posY;
    }

    mouse(event, pos, node) {
        if (!this.hitAreas) return false;
        
        const [x, y] = pos;
        const localY = y - this.last_y;
        
        // Check toggle
        const [tx, ty, tw, th] = this.hitAreas.toggle;
        if (x >= tx && x <= tx + tw && localY >= 0 && localY <= th) {
            if (event.type === "pointerdown") {
                this.value.on = !this.value.on;
                node.setDirtyCanvas(true, true);
                return true;
            }
        }
        
        // Check LoRA name (open chooser)
        const [lx, ly, lw, lh] = this.hitAreas.lora;
        if (x >= lx && x <= lx + lw && localY >= 0 && localY <= lh) {
            if (event.type === "pointerdown") {
                showLoraChooser((selectedLora) => {
                    this.value.lora = selectedLora;
                    node.setDirtyCanvas(true, true);
                }, this.value.lora);
                return true;
            }
        }
        
        // Check decrease button
        const [dx, dy, dw, dh] = this.hitAreas.decrease;
        if (x >= dx && x <= dx + dw && localY >= dy - this.last_y && localY <= dy - this.last_y + dh) {
            if (event.type === "pointerdown") {
                this.value.strength = Math.max(0, Math.round((this.value.strength - 0.05) * 100) / 100);
                node.setDirtyCanvas(true, true);
                return true;
            }
        }
        
        // Check value (open input)
        const [vx, vy, vw, vh] = this.hitAreas.value;
        if (x >= vx && x <= vx + vw && localY >= vy - this.last_y && localY <= vy - this.last_y + vh) {
            if (event.type === "pointerdown") {
                const newValue = prompt("Enter strength value:", this.value.strength);
                if (newValue !== null) {
                    const parsed = parseFloat(newValue);
                    if (!isNaN(parsed)) {
                        this.value.strength = Math.round(parsed * 100) / 100;
                        node.setDirtyCanvas(true, true);
                    }
                }
                return true;
            }
        }
        
        // Check increase button
        const [ix, iy, iw, ih] = this.hitAreas.increase;
        if (x >= ix && x <= ix + iw && localY >= iy - this.last_y && localY <= iy - this.last_y + ih) {
            if (event.type === "pointerdown") {
                this.value.strength = Math.round((this.value.strength + 0.05) * 100) / 100;
                node.setDirtyCanvas(true, true);
                return true;
            }
        }
        
        return false;
    }

    computeSize(width) {
        return [width, 35];
    }

    serializeValue() {
        return this.value;
    }
}

// Custom Button Widget (like rgthree's RgthreeBetterButtonWidget)
class CustomButtonWidget {
    constructor(name, label, callback) {
        this.name = name;
        this.type = "button";
        this.value = "";
        this.label = label;
        this.callback = callback;
        this.options = { serialize: false };
        this.y = 0;
        this.last_y = 0;
        this.isMouseDownedAndOver = false;
    }

    draw(ctx, node, widgetWidth, posY, widgetHeight) {
        const margin = 15;
        const buttonWidth = widgetWidth - margin * 2;
        const buttonHeight = widgetHeight - 4;
        
        ctx.save();
        
        // Button background
        const bgColor = this.isMouseDownedAndOver ? "#4a6a8a" : "#3a5a7a";
        ctx.fillStyle = bgColor;
        ctx.beginPath();
        ctx.roundRect(margin, posY + 2, buttonWidth, buttonHeight, 4);
        ctx.fill();
        
        // Button border
        ctx.strokeStyle = "#5a7a9a";
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Button text
        ctx.fillStyle = "#ffffff";
        ctx.font = "14px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(this.label, widgetWidth / 2, posY + widgetHeight / 2);
        
        ctx.restore();
        
        this.last_y = posY;
    }

    mouse(event, pos, node) {
        if (event.type === "pointerdown") {
            this.isMouseDownedAndOver = true;
            node.setDirtyCanvas(true, false);
            return true;
        }
        
        if (event.type === "pointerup") {
            if (this.isMouseDownedAndOver) {
                this.isMouseDownedAndOver = false;
                node.setDirtyCanvas(true, false);
                
                // Call the callback
                if (this.callback) {
                    this.callback(event, pos, node);
                }
                return true;
            }
        }
        
        return false;
    }

    computeSize(width) {
        return [width, 34];
    }

    serializeValue() {
        return "";
    }
}

// Spacer Widget for proper spacing
class SpacerWidget {
    constructor(height = 4) {
        this.name = "spacer_" + Math.random();
        this.type = "spacer";
        this.value = "";
        this.height = height;
        this.options = { serialize: false };
        this.y = 0;
    }

    draw(ctx, node, widgetWidth, posY, widgetHeight) {
        // Draw nothing, just take up space
        return;
    }

    mouse(event, pos, node) {
        return false;
    }

    computeSize(width) {
        return [width, this.height];
    }

    serializeValue() {
        return "";
    }
}

// Register the extension
app.registerExtension({
    name: "autopilot.smart.power.lora.loader",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === NODE_NAME) {
            // Load available LoRAs on startup
            await getAvailableLoras();
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Hide the manual_loras text widget
                const manualLorasWidget = this.widgets?.find(w => w.name === "manual_loras");
                if (manualLorasWidget) {
                    // Hide it by making it 0 height
                    manualLorasWidget.computeSize = () => [0, -4];
                    manualLorasWidget.type = "converted-widget";
                    manualLorasWidget.serializeValue = async () => {
                        // Collect manual LoRAs and convert to comma-separated string
                        const manualLoras = [];
                        for (const widget of this.widgets || []) {
                            if (widget.type === "manual_lora" && widget.value.lora !== "None" && widget.value.on) {
                                manualLoras.push(widget.value.lora);
                            }
                        }
                        return manualLoras.join(',');
                    };
                }
                
                // Store manual LoRA widgets
                this.manualLoraWidgets = [];
                this.manualLoraCounter = 0;
                
                // Add a spacer at the top
                this.widgets.push(new SpacerWidget(4));
                
                // Create and add "Add Manual LoRA" button using custom widget
                const addLoraBtn = new CustomButtonWidget(
                    "add_manual_lora_btn",
                    "➕ Add Manual LoRA",
                    (event, pos, node) => {
                        const widget = new ManualLoraWidget("manual_lora_" + node.manualLoraCounter++, node);
                        node.manualLoraWidgets.push(widget);
                        
                        // Find the button's index and insert before it
                        const buttonIndex = node.widgets.findIndex(w => w.name === "add_manual_lora_btn");
                        if (buttonIndex >= 0) {
                            node.widgets.splice(buttonIndex, 0, widget);
                        } else {
                            node.widgets.push(widget);
                        }
                        
                        const computed = node.computeSize();
                        node.size[1] = Math.max(node.size[1], computed[1]);
                        node.setDirtyCanvas(true, true);
                        return true;
                    }
                );
                this.widgets.push(addLoraBtn);
                
                // Add a small spacer
                this.widgets.push(new SpacerWidget(4));
                
                // Create and add "Show LoRA Catalog" button using custom widget
                const catalogBtn = new CustomButtonWidget(
                    "show_catalog_btn",
                    "ℹ️ Show LoRA Catalog",
                    async (event, pos, node) => {
                        await showLoraCatalogDialog(node);
                        return true;
                    }
                );
                this.widgets.push(catalogBtn);
                
                return r;
            };
            
            // Override serialize to convert manual LoRA widgets to string
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(o) {
                const result = onSerialize ? onSerialize.apply(this, arguments) : o;
                
                // Collect manual LoRAs and convert to comma-separated string
                const manualLoras = [];
                for (const widget of this.widgets || []) {
                    if (widget.type === "manual_lora" && widget.value.lora !== "None" && widget.value.on) {
                        manualLoras.push(widget.value.lora);
                    }
                }
                
                // Find and update the hidden manual_loras widget
                const manualLorasWidget = this.widgets?.find(w => w.name === "manual_loras");
                if (manualLorasWidget) {
                    manualLorasWidget.value = manualLoras.join(',');
                }
                
                return result;
            };
            
            // Add context menu option
            const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
            nodeType.prototype.getExtraMenuOptions = function(_, options) {
                if (getExtraMenuOptions) {
                    getExtraMenuOptions.apply(this, arguments);
                }
                
                // Count manual LoRAs
                const manualLoraCount = this.widgets?.filter(w => w.type === "manual_lora").length || 0;
                
                if (manualLoraCount > 0) {
                    options.push(
                        null, // Separator
                        {
                            content: "Toggle All Manual LoRAs",
                            callback: () => {
                                // Check if any are on
                                let anyOn = false;
                                for (const widget of this.widgets || []) {
                                    if (widget.type === "manual_lora" && widget.value.on) {
                                        anyOn = true;
                                        break;
                                    }
                                }
                                // Toggle all to opposite of current state
                                const newState = !anyOn;
                                for (const widget of this.widgets || []) {
                                    if (widget.type === "manual_lora") {
                                        widget.value.on = newState;
                                    }
                                }
                                this.setDirtyCanvas(true, true);
                            }
                        },
                        {
                            content: "Clear All Manual LoRAs",
                            callback: () => {
                                // Remove all manual LoRA widgets
                                this.widgets = this.widgets.filter(w => w.type !== "manual_lora");
                                this.manualLoraWidgets = [];
                                const computed = this.computeSize();
                                this.size[1] = Math.max(this.size[1], computed[1]);
                                this.setDirtyCanvas(true, true);
                            }
                        }
                    );
                }
                
                options.push(
                    null, // Separator
                    {
                        content: "ℹ️ Show LoRA Catalog",
                        callback: async () => {
                            await showLoraCatalogDialog(this);
                        }
                    }
                );
            };
        }
    }
});

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

// Show LoRA info dialog (properly centered with editing capability)
function showLoraInfoDialog(loraName, catalogInfo) {
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const content = document.createElement('div');
    content.style.cssText = `
        background: #202020;
        border: 2px solid #444;
        border-radius: 8px;
        padding: 20px;
        width: 600px;
        max-height: 80vh;
        overflow: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;

    const title = document.createElement('h2');
    title.textContent = catalogInfo?.display_name || loraName;
    title.style.cssText = 'margin: 0 0 15px 0; color: #fff; font-size: 20px;';
    content.appendChild(title);

    if (catalogInfo && catalogInfo.file_hash) {
        // Edit mode
        let isEditing = false;
        
        // Summary
        const summaryLabel = document.createElement('h3');
        summaryLabel.textContent = 'Summary';
        summaryLabel.style.cssText = 'color: #aaa; font-size: 14px; margin: 10px 0 5px 0;';
        content.appendChild(summaryLabel);

        const summaryText = document.createElement('p');
        summaryText.textContent = catalogInfo.summary || 'No summary available';
        summaryText.style.cssText = 'margin: 0 0 15px 0; color: #fff; line-height: 1.5; cursor: text; padding: 8px; border-radius: 4px;';
        content.appendChild(summaryText);
        
        const summaryInput = document.createElement('textarea');
        summaryInput.value = catalogInfo.summary || '';
        summaryInput.style.cssText = `
            width: 100%;
            margin: 0 0 15px 0;
            padding: 8px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            display: none;
            min-height: 80px;
            resize: vertical;
        `;
        content.appendChild(summaryInput);

        // Trigger Words
        const triggerLabel = document.createElement('h3');
        triggerLabel.textContent = 'Trigger Words (comma-separated)';
        triggerLabel.style.cssText = 'color: #aaa; font-size: 14px; margin: 15px 0 8px 0;';
        content.appendChild(triggerLabel);

        const triggersContainer = document.createElement('div');
        triggersContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px;';
        if (catalogInfo.trained_words && catalogInfo.trained_words.length > 0) {
            catalogInfo.trained_words.forEach(word => {
                const tag = document.createElement('span');
                tag.textContent = word;
                tag.style.cssText = `
                    background: #3a5a7a;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 13px;
                    color: #fff;
                `;
                triggersContainer.appendChild(tag);
            });
        } else {
            triggersContainer.textContent = 'No trigger words';
            triggersContainer.style.color = '#888';
        }
        content.appendChild(triggersContainer);

        const triggersInput = document.createElement('input');
        triggersInput.type = 'text';
        triggersInput.value = catalogInfo.trained_words ? catalogInfo.trained_words.join(', ') : '';
        triggersInput.placeholder = 'Enter trigger words separated by commas';
        triggersInput.style.cssText = `
            width: 100%;
            margin-bottom: 15px;
            padding: 8px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            display: none;
        `;
        content.appendChild(triggersInput);

        // Tags
        const tagsLabel = document.createElement('h3');
        tagsLabel.textContent = 'Tags (comma-separated)';
        tagsLabel.style.cssText = 'color: #aaa; font-size: 14px; margin: 15px 0 8px 0;';
        content.appendChild(tagsLabel);

        const tagsContainer = document.createElement('div');
        tagsContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px;';
        if (catalogInfo.tags && catalogInfo.tags.length > 0) {
            catalogInfo.tags.forEach(tag => {
                const tagEl = document.createElement('span');
                tagEl.textContent = tag;
                tagEl.style.cssText = `
                    background: #444;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 13px;
                    color: #ccc;
                `;
                tagsContainer.appendChild(tagEl);
            });
        } else {
            tagsContainer.textContent = 'No tags';
            tagsContainer.style.color = '#888';
        }
        content.appendChild(tagsContainer);

        const tagsInput = document.createElement('input');
        tagsInput.type = 'text';
        tagsInput.value = catalogInfo.tags ? catalogInfo.tags.join(', ') : '';
        tagsInput.placeholder = 'Enter tags separated by commas';
        tagsInput.style.cssText = `
            width: 100%;
            margin-bottom: 15px;
            padding: 8px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            display: none;
        `;
        content.appendChild(tagsInput);

        // Base Model
        const baseLabel = document.createElement('h3');
        baseLabel.textContent = 'Base Model';
        baseLabel.style.cssText = 'color: #aaa; font-size: 14px; margin: 15px 0 5px 0;';
        content.appendChild(baseLabel);

        const baseModel = document.createElement('p');
        baseModel.textContent = catalogInfo.base_compat ? catalogInfo.base_compat.join(', ') : 'Unknown';
        baseModel.style.cssText = 'margin: 0 0 15px 0; color: #fff;';
        content.appendChild(baseModel);

        // Weight
        const weightLabel = document.createElement('h3');
        weightLabel.textContent = 'Default Weight';
        weightLabel.style.cssText = 'color: #aaa; font-size: 14px; margin: 15px 0 5px 0;';
        content.appendChild(weightLabel);

        const weightText = document.createElement('p');
        weightText.textContent = catalogInfo.default_weight != null ? catalogInfo.default_weight.toFixed(2) : '1.00';
        weightText.style.cssText = 'margin: 0 0 15px 0; color: #fff;';
        content.appendChild(weightText);

        const weightInput = document.createElement('input');
        weightInput.type = 'number';
        weightInput.step = '0.05';
        weightInput.min = '0';
        weightInput.max = '2';
        weightInput.value = catalogInfo.default_weight != null ? catalogInfo.default_weight : 1.0;
        weightInput.style.cssText = `
            width: 100%;
            margin-bottom: 15px;
            padding: 8px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            display: none;
        `;
        content.appendChild(weightInput);

        // Civitai Link
        if (catalogInfo.civitai_model_id) {
            const link = document.createElement('a');
            link.href = `https://civitai.com/models/${catalogInfo.civitai_model_id}`;
            link.target = '_blank';
            link.textContent = '🔗 View on Civitai';
            link.style.cssText = `
                display: inline-block;
                margin-top: 10px;
                margin-bottom: 15px;
                padding: 10px 15px;
                background: #3a5a7a;
                color: #fff;
                text-decoration: none;
                border-radius: 4px;
            `;
            link.onmouseenter = () => link.style.background = '#4a6a8a';
            link.onmouseleave = () => link.style.background = '#3a5a7a';
            content.appendChild(link);
        }

        // Button container
        const buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = 'display: flex; gap: 10px; margin-top: 20px;';

        const editBtn = document.createElement('button');
        editBtn.textContent = 'Edit';
        editBtn.style.cssText = `
            flex: 1;
            padding: 10px 20px;
            background: #3a5a7a;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        editBtn.onmouseenter = () => editBtn.style.background = '#4a6a8a';
        editBtn.onmouseleave = () => editBtn.style.background = isEditing ? '#2a4a6a' : '#3a5a7a';
        editBtn.onclick = () => {
            if (!isEditing) {
                // Enter edit mode
                isEditing = true;
                editBtn.textContent = 'Save';
                editBtn.style.background = '#2a8a4a';
                editBtn.onmouseenter = () => editBtn.style.background = '#3a9a5a';
                editBtn.onmouseleave = () => editBtn.style.background = '#2a8a4a';
                
                summaryText.style.display = 'none';
                summaryInput.style.display = 'block';
                triggersContainer.style.display = 'none';
                triggersInput.style.display = 'block';
                tagsContainer.style.display = 'none';
                tagsInput.style.display = 'block';
                weightText.style.display = 'none';
                weightInput.style.display = 'block';
                closeBtn.textContent = 'Cancel';
            } else {
                // Save changes
                const updateData = {
                    file_hash: catalogInfo.file_hash,
                    summary: summaryInput.value,
                    trained_words: triggersInput.value.split(',').map(t => t.trim()).filter(t => t),
                    tags: tagsInput.value.split(',').map(t => t.trim()).filter(t => t),
                    default_weight: parseFloat(weightInput.value)
                };

                api.fetchApi('/autopilot_lora/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateData)
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        document.body.removeChild(dialog);
                        alert('LoRA information updated successfully!');
                    } else {
                        alert('Failed to update LoRA: ' + (result.error || 'Unknown error'));
                    }
                })
                .catch(error => {
                    alert('Failed to update LoRA: ' + error.message);
                });
            }
        };
        buttonContainer.appendChild(editBtn);

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.style.cssText = `
            flex: 1;
            padding: 10px 20px;
            background: #444;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        closeBtn.onmouseenter = () => closeBtn.style.background = '#555';
        closeBtn.onmouseleave = () => closeBtn.style.background = '#444';
        closeBtn.onclick = () => document.body.removeChild(dialog);
        buttonContainer.appendChild(closeBtn);

        content.appendChild(buttonContainer);
    } else {
        const noInfo = document.createElement('p');
        noInfo.textContent = 'No catalog information available. Run indexing first.';
        noInfo.style.cssText = 'color: #888; margin: 20px 0;';
        content.appendChild(noInfo);

        const closeBtn = document.createElement('button');
        closeBtn.textContent = 'Close';
        closeBtn.style.cssText = `
            margin-top: 20px;
            padding: 10px 20px;
            background: #444;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            font-size: 14px;
        `;
        closeBtn.onmouseenter = () => closeBtn.style.background = '#555';
        closeBtn.onmouseleave = () => closeBtn.style.background = '#444';
        closeBtn.onclick = () => document.body.removeChild(dialog);
        content.appendChild(closeBtn);
    }

    dialog.appendChild(content);
    dialog.onclick = (e) => {
        if (e.target === dialog) {
            document.body.removeChild(dialog);
        }
    };

    document.body.appendChild(dialog);
}

// Show full LoRA catalog dialog (properly centered)
async function showLoraCatalogDialog(node) {
    try {
        const response = await api.fetchApi('/autopilot_lora/catalog');
        const catalog = response.ok ? await response.json() : {};

        const dialog = document.createElement('div');
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: #202020;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 20px;
            width: 85%;
            max-width: 900px;
            height: 85vh;
            overflow: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;

        const title = document.createElement('h2');
        title.textContent = 'LoRA Catalog';
        title.style.cssText = 'margin: 0 0 15px 0; color: #fff; font-size: 22px;';
        content.appendChild(title);

        const search = document.createElement('input');
        search.type = 'text';
        search.placeholder = 'Search LoRAs...';
        search.style.cssText = `
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        `;
        content.appendChild(search);

        const catalogList = document.createElement('div');
        catalogList.style.cssText = 'display: flex; flex-direction: column; gap: 10px; margin-bottom: 15px;';

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
                noResults.style.cssText = 'color: #888; padding: 20px; text-align: center;';
                catalogList.appendChild(noResults);
                return;
            }

            filtered.forEach(entry => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 15px;
                    background: #2a2a2a;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.2s;
                    border: 1px solid #333;
                `;
                item.onmouseenter = () => item.style.background = '#353535';
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
            margin-top: 15px;
            padding: 10px 20px;
            background: #444;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            font-size: 14px;
        `;
        closeBtn.onmouseenter = () => closeBtn.style.background = '#555';
        closeBtn.onmouseleave = () => closeBtn.style.background = '#444';
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
