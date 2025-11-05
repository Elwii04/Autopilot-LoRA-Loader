import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Name of our node type
const NODE_NAME = "SmartPowerLoRALoader";

// Store available LoRAs globally
let availableLoras = [];
let baseModelOptionsCache = null;

function getStaticBaseModelFallback() {
    return [
        'Aura Flow', 'Chroma', 'CogVideoX', 'Flux .1 S', 'Flux .1 D',
        'Flux .1 Krea', 'Flux .1 Kontext', 'HiDream', 'Hunyuan 1',
        'Hunyuan Video', 'Illustrious', 'Kolors', 'LTXV', 'Lumina',
        'Mochi', 'NoobAI', 'Other', 'PixArt α', 'PixArt Σ', 'Pony',
        'Pony V7', 'Qwen', 'Qwen-Image-Edit', 'SD 1.4', 'SD 1.5', 'SD 1.5 LCM',
        'SD 1.5 Hyper', 'SD 2.0', 'SD 2.1', 'SDXL 1.0', 'SDXL Lightning',
        'SDXL Hyper', 'Wan Video 1.3B t2v', 'Wan Video 1.4B t2v',
        'Wan Video 1.4B i2v 480p', 'Wan Video 1.4B i2v 720p',
        'Wan Video 2.2 T12V-5B', 'Wan Video 2.2 I2V-A14B',
        'Wan Video 2.2 T2V-A14B', 'Wan Video 2.5 T2V', 'Wan Video 2.5 I2V',
        'Unknown'
    ];
}

async function fetchBaseModelOptions() {
    if (Array.isArray(baseModelOptionsCache) && baseModelOptionsCache.length > 0) {
        return baseModelOptionsCache;
    }
    
    try {
        const response = await api.fetchApi('/autopilot_lora/base_models');
        if (response.ok) {
            const data = await response.json();
            if (Array.isArray(data.models) && data.models.length > 0) {
                baseModelOptionsCache = data.models;
                return baseModelOptionsCache;
            }
        }
    } catch (error) {
        console.warn('[Autopilot LoRA] Failed to fetch base model list, using fallback.', error);
    }
    
    baseModelOptionsCache = getStaticBaseModelFallback();
    return baseModelOptionsCache;
}

async function populateBaseModelSelect(selectElement, selectedModels = []) {
    const models = await fetchBaseModelOptions();
    const normalizedSelected = Array.isArray(selectedModels) ? selectedModels : [selectedModels];
    
    // Ensure any existing selections are available even if not in base list
    const augmentedModels = [...models];
    normalizedSelected.forEach(model => {
        if (model && !augmentedModels.includes(model)) {
            augmentedModels.push(model);
        }
    });
    
    selectElement.innerHTML = '';
    augmentedModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        if (normalizedSelected.includes(model)) {
            option.selected = true;
        }
        selectElement.appendChild(option);
    });
}

function createTokenEditor({
    initialValues = [],
    placeholder = '',
    emptyLabel = 'No items yet',
    chipBackground = '#3a5a7a',
    chipTextColor = '#fff'
} = {}) {
    const wrapper = document.createElement('div');
    const chipsContainer = document.createElement('div');
    chipsContainer.style.cssText = 'display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;';
    wrapper.appendChild(chipsContainer);

    let values = Array.isArray(initialValues)
        ? initialValues
            .map(item => typeof item === 'string' ? item.trim() : '')
            .filter(Boolean)
        : [];

    const inputRow = document.createElement('div');
    inputRow.style.cssText = 'display: flex; gap: 6px;';

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = placeholder;
    input.style.cssText = `
        flex: 1;
        padding: 8px;
        background: #2a2a2a;
        border: 1px solid #444;
        color: #fff;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
    `;
    inputRow.appendChild(input);

    const addBtn = document.createElement('button');
    addBtn.textContent = '+';
    addBtn.title = 'Add item';
    addBtn.style.cssText = `
        padding: 0 12px;
        background: #3a5a7a;
        border: none;
        color: #fff;
        border-radius: 4px;
        cursor: pointer;
        font-size: 18px;
        font-weight: bold;
        line-height: 1;
    `;
    addBtn.onmouseenter = () => addBtn.style.background = '#4a6a8a';
    addBtn.onmouseleave = () => addBtn.style.background = '#3a5a7a';
    inputRow.appendChild(addBtn);

    wrapper.appendChild(inputRow);

    const syncPlaceholder = () => {
        if (values.length === 0) {
            chipsContainer.textContent = emptyLabel;
            chipsContainer.style.color = '#888';
        } else {
            chipsContainer.textContent = '';
            chipsContainer.style.color = '';
        }
    };

    const renderChips = () => {
        chipsContainer.innerHTML = '';
        syncPlaceholder();

        values.forEach((item, index) => {
            const chip = document.createElement('span');
            chip.style.cssText = `
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: ${chipBackground};
                color: ${chipTextColor};
                padding: 5px 8px;
                border-radius: 4px;
                font-size: 13px;
            `;
            chip.textContent = item;

            const removeBtn = document.createElement('button');
            removeBtn.textContent = '×';
            removeBtn.title = `Remove "${item}"`;
            removeBtn.style.cssText = `
                background: transparent;
                border: none;
                color: inherit;
                cursor: pointer;
                font-size: 14px;
                line-height: 1;
                padding: 0;
            `;
            removeBtn.onclick = (event) => {
                event.stopPropagation();
                values = values.filter((_, idx) => idx !== index);
                renderChips();
            };
            chip.appendChild(removeBtn);

            chip.onclick = () => {
                values = values.filter((_, idx) => idx !== index);
                renderChips();
            };

            chipsContainer.appendChild(chip);
        });
    };

    const addFromInput = () => {
        const raw = input.value;
        if (!raw) {
            return;
        }

        const candidates = raw.split(',').map(item => item.trim()).filter(Boolean);
        let added = false;
        candidates.forEach(candidate => {
            const exists = values.some(value => value.toLowerCase() === candidate.toLowerCase());
            if (!exists) {
                values.push(candidate);
                added = true;
            }
        });

        if (added) {
            renderChips();
        }

        input.value = '';
    };

    addBtn.onclick = (event) => {
        event.preventDefault();
        addFromInput();
        input.focus();
    };

    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ',') {
            event.preventDefault();
            addFromInput();
        } else if (event.key === 'Backspace' && !input.value && values.length) {
            values.pop();
            renderChips();
        }
    });

    input.addEventListener('blur', () => {
        if (input.value.includes(',')) {
            addFromInput();
        }
    });

    renderChips();

    return {
        container: wrapper,
        getValues: () => [...values],
        setValues: (newValues) => {
            values = Array.isArray(newValues)
                ? newValues.map(item => typeof item === 'string' ? item.trim() : '').filter(Boolean)
                : [];
            renderChips();
        },
        focus: () => input.focus(),
        input
    };
}

// Fetch LoRAs from ComfyUI (gets ALL LoRAs from folder_paths, not just indexed ones)
async function getAvailableLoras() {
    try {
        console.log("[Autopilot LoRA] Fetching available LoRAs...");
        
        // First try to get from our API endpoint (fastest and most reliable)
        const response = await api.fetchApi('/autopilot_lora/available');
        if (response.ok) {
            const data = await response.json();
            availableLoras = ["None", ...(data.loras || [])];
            console.log("[Autopilot LoRA] Found", availableLoras.length - 1, "LoRAs from API");
            return availableLoras;
        }
        
        // Fallback: Try to get object_info which contains all available LoRAs
        const objectInfo = await api.getObjectInfo();
        
        // Find any node that has lora inputs to get the list
        for (const nodeType in objectInfo) {
            const nodeDef = objectInfo[nodeType];
            if (nodeDef.input && nodeDef.input.required) {
                for (const inputName in nodeDef.input.required) {
                    const inputDef = nodeDef.input.required[inputName];
                    // Check if this is a lora combo input
                    if (Array.isArray(inputDef) && inputDef[0] && Array.isArray(inputDef[0])) {
                        const options = inputDef[0];
                        // Check if it looks like a lora list (has .safetensors files)
                        if (options.length > 0 && options.some(item => 
                            typeof item === 'string' && item.includes('.safetensors'))) {
                            availableLoras = ["None", ...options];
                            console.log("[Autopilot LoRA] Found", availableLoras.length - 1, "LoRAs from ComfyUI");
                            return availableLoras;
                        }
                    }
                }
            }
        }
        
        console.warn("[Autopilot LoRA] No LoRA inputs found in node definitions");
        availableLoras = ["None"];
        return availableLoras;
        
    } catch (error) {
        console.error("[Autopilot LoRA] Failed to fetch LoRAs:", error);
        availableLoras = ["None"];
        return availableLoras;
    }
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

function getIndexingModelFromNode(node) {
    if (!node) {
        return null;
    }

    const resolveWidgetValue = (widget) => {
        if (!widget) {
            return null;
        }

        const value = widget.value;
        if (typeof value === "string" && value.trim()) {
            return value.trim();
        }

        if (typeof value === "number" && Array.isArray(widget.options?.values)) {
            const candidate = widget.options.values[value];
            if (typeof candidate === "string" && candidate.trim()) {
                return candidate.trim();
            }
        }

        if (Array.isArray(widget.options?.values)) {
            const maybeIndex = widget.options.values.indexOf(value);
            if (maybeIndex >= 0) {
                const candidate = widget.options.values[maybeIndex];
                if (typeof candidate === "string" && candidate.trim()) {
                    return candidate.trim();
                }
            }
            const first = widget.options.values[0];
            if (typeof first === "string" && first.trim()) {
                return first.trim();
            }
        }

        if (typeof widget.options?.default === "string" && widget.options.default.trim()) {
            return widget.options.default.trim();
        }

        return null;
    };

    if (typeof node.autopilotIndexingModel === "string" && node.autopilotIndexingModel.trim()) {
        return node.autopilotIndexingModel.trim();
    }

    if (Array.isArray(node.widgets)) {
        const widget = node.widgets.find((w) => w && w.name === "indexing_model");
        const resolved = resolveWidgetValue(widget);
        if (resolved) {
            node.autopilotIndexingModel = resolved;
            return resolved;
        }
    }

    const propValue = node?.properties?.indexing_model;
    if (typeof propValue === "string" && propValue.trim()) {
        const trimmed = propValue.trim();
        node.autopilotIndexingModel = trimmed;
        return trimmed;
    }

    return null;
}

// Show LoRA chooser (like rgthree's showLoraChooser using LiteGraph.ContextMenu)
async function showLoraChooser(event, callback, currentValue = null) {
    await getAvailableLoras();
    
    const loras = availableLoras.length > 0 ? availableLoras : ["None"];
    
    new LiteGraph.ContextMenu(loras, {
        event: event,
        title: "Choose a LoRA",
        scale: Math.max(1, app.canvas.ds?.scale ?? 1),
        className: "dark",
        callback: callback
    });
}

// Manual LoRA Widget (matching rgthree's PowerLoraLoaderWidget exactly)
class ManualLoraWidget {
    constructor(name, node) {
        this.name = name;
        this.type = "manual_lora";
        this.node = node;
        this.value = {
            lora: null,
            strength: 1.0,
            on: true
        };
        this.y = 0;
        this.last_y = 0;
        this.options = { serialize: true };
        this.hitAreas = {
            toggle: { bounds: [0, 0], onDown: this.onToggleDown.bind(this) },
            lora: { bounds: [0, 0], onClick: this.onLoraClick.bind(this) },
            strengthDec: { bounds: [0, 0], onClick: this.onStrengthDecDown.bind(this) },
            strengthVal: { bounds: [0, 0], onClick: this.onStrengthValUp.bind(this) },
            strengthInc: { bounds: [0, 0], onClick: this.onStrengthIncDown.bind(this) },
            strengthAny: { bounds: [0, 0], onMove: this.onStrengthAnyMove.bind(this) }
        };
        this.mouseDowned = null;
        this.isMouseDownedAndOver = false;
        this.downedHitAreasForMove = [];
        this.downedHitAreasForClick = [];
        this.haveMouseMovedStrength = false;
    }

    draw(ctx, node, widgetWidth, posY, widgetHeight) {
        const margin = 10;
        const innerMargin = margin * 0.33;
        const midY = posY + widgetHeight * 0.5;
        let posX = margin;

        ctx.save();

        // Draw rounded rectangle background
        ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
        ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
        ctx.beginPath();
        ctx.roundRect(margin, posY, widgetWidth - margin * 2, widgetHeight, [widgetHeight * 0.5]);
        ctx.fill();
        ctx.stroke();

        // Draw toggle
        const toggleRadius = widgetHeight * 0.36;
        const toggleBgWidth = widgetHeight * 1.5;
        
        // Toggle background
        ctx.beginPath();
        ctx.roundRect(posX + 4, posY + 4, toggleBgWidth - 8, widgetHeight - 8, [widgetHeight * 0.5]);
        ctx.globalAlpha = app.canvas.editor_alpha * 0.25;
        ctx.fillStyle = "rgba(255,255,255,0.45)";
        ctx.fill();
        ctx.globalAlpha = app.canvas.editor_alpha;

        // Toggle circle
        ctx.fillStyle = this.value.on === true ? "#89B" : "#888";
        const toggleX = this.value.on === false ? posX + widgetHeight * 0.5 : posX + widgetHeight;
        ctx.beginPath();
        ctx.arc(toggleX, posY + widgetHeight * 0.5, toggleRadius, 0, Math.PI * 2);
        ctx.fill();

        this.hitAreas.toggle.bounds = [posX, toggleBgWidth];
        posX += toggleBgWidth + innerMargin;

        if (!this.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }

        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;

        // Draw strength controls on the right
        let rposX = widgetWidth - margin - innerMargin - innerMargin;
        
        // Strength arrows and value
        const arrowWidth = 9;
        const arrowHeight = 10;
        const numberWidth = 32;
        const strengthInnerMargin = 3;

        rposX = rposX - arrowWidth - strengthInnerMargin - numberWidth - strengthInnerMargin - arrowWidth;

        // Left arrow (decrease)
        ctx.fill(new Path2D(`M ${rposX} ${midY} l ${arrowWidth} ${arrowHeight / 2} l 0 -${arrowHeight} L ${rposX} ${midY} z`));
        this.hitAreas.strengthDec.bounds = [rposX, arrowWidth];
        rposX += arrowWidth + strengthInnerMargin;

        // Strength value
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(this.value.strength.toFixed(2), rposX + numberWidth / 2, midY);
        this.hitAreas.strengthVal.bounds = [rposX, numberWidth];
        rposX += numberWidth + strengthInnerMargin;

        // Right arrow (increase)
        ctx.fill(new Path2D(`M ${rposX} ${midY - arrowHeight / 2} l ${arrowWidth} ${arrowHeight / 2} l -${arrowWidth} ${arrowHeight / 2} v -${arrowHeight} z`));
        this.hitAreas.strengthInc.bounds = [rposX, arrowWidth];

        // Strength "any" area for mouse drag
        const strengthStartX = rposX - numberWidth - strengthInnerMargin - arrowWidth;
        this.hitAreas.strengthAny.bounds = [strengthStartX, arrowWidth + strengthInnerMargin + numberWidth + strengthInnerMargin + arrowWidth];

        rposX = strengthStartX - innerMargin;

        // Draw LoRA name
        const loraWidth = rposX - posX;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        const loraLabel = String(this.value.lora || "None");
        ctx.fillText(this.fitString(ctx, loraLabel, loraWidth), posX, midY);
        this.hitAreas.lora.bounds = [posX, loraWidth];

        ctx.globalAlpha = app.canvas.editor_alpha;
        ctx.restore();

        this.last_y = posY;
    }

    fitString(ctx, str, maxWidth) {
        let width = ctx.measureText(str).width;
        if (width <= maxWidth) return str;
        
        const ellipsis = "…";
        const ellipsisWidth = ctx.measureText(ellipsis).width;
        if (width <= ellipsisWidth) return str;
        
        let len = str.length;
        while (len > 0 && ctx.measureText(str.substring(0, len)).width + ellipsisWidth > maxWidth) {
            len--;
        }
        return str.substring(0, len) + ellipsis;
    }

    clickWasWithinBounds(pos, bounds) {
        let xStart = bounds[0];
        let xEnd = xStart + (bounds.length > 2 ? bounds[2] : bounds[1]);
        const clickedX = pos[0] >= xStart && pos[0] <= xEnd;
        if (bounds.length === 2) {
            return clickedX;
        }
        return clickedX && pos[1] >= bounds[1] && pos[1] <= bounds[1] + bounds[3];
    }

    mouse(event, pos, node) {
        if (event.type == "pointerdown") {
            this.mouseDowned = [...pos];
            this.isMouseDownedAndOver = true;
            this.downedHitAreasForMove = [];
            this.downedHitAreasForClick = [];
            
            let anyHandled = false;
            for (const [key, part] of Object.entries(this.hitAreas)) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    if (part.onMove) {
                        this.downedHitAreasForMove.push(part);
                    }
                    if (part.onClick) {
                        this.downedHitAreasForClick.push(part);
                    }
                    if (part.onDown) {
                        const thisHandled = part.onDown(event, pos, node, part);
                        anyHandled = anyHandled || thisHandled == true;
                    }
                }
            }
            return anyHandled || true;
        }

        if (event.type == "pointerup") {
            if (!this.mouseDowned) return true;
            
            this.downedHitAreasForMove = [];
            const wasMouseDownedAndOver = this.isMouseDownedAndOver;
            this.mouseDowned = null;
            this.isMouseDownedAndOver = false;
            this.haveMouseMovedStrength = false;
            
            let anyHandled = false;
            for (const part of this.downedHitAreasForClick) {
                if (this.clickWasWithinBounds(pos, part.bounds)) {
                    const thisHandled = part.onClick(event, pos, node, part);
                    anyHandled = anyHandled || thisHandled == true;
                }
            }
            this.downedHitAreasForClick = [];
            
            return anyHandled || true;
        }

        if (event.type == "pointermove") {
            this.isMouseDownedAndOver = !!this.mouseDowned;
            if (this.mouseDowned && 
                (pos[0] < 15 || pos[0] > node.size[0] - 15 || 
                 pos[1] < this.last_y || pos[1] > this.last_y + LiteGraph.NODE_WIDGET_HEIGHT)) {
                this.isMouseDownedAndOver = false;
            }
            
            for (const part of this.downedHitAreasForMove) {
                if (part.onMove) {
                    part.onMove(event, pos, node, part);
                }
            }
            
            return true;
        }

        return false;
    }

    onToggleDown(event, pos, node) {
        this.value.on = !this.value.on;
        this.mouseDowned = null;
        this.isMouseDownedAndOver = false;
        node.setDirtyCanvas(true, true);
        return true;
    }

    onLoraClick(event, pos, node) {
        showLoraChooser(event, (value) => {
            if (typeof value === "string") {
                this.value.lora = value;
            }
            node.setDirtyCanvas(true, true);
        }, this.value.lora);
        this.mouseDowned = null;
        this.isMouseDownedAndOver = false;
        return true;
    }

    onStrengthDecDown(event, pos, node) {
        this.stepStrength(-1);
        node.setDirtyCanvas(true, true);
        return true;
    }

    onStrengthIncDown(event, pos, node) {
        this.stepStrength(1);
        node.setDirtyCanvas(true, true);
        return true;
    }

    onStrengthValUp(event, pos, node) {
        if (this.haveMouseMovedStrength) return;
        const canvas = app.canvas;
        canvas.prompt("Value", this.value.strength, (v) => {
            this.value.strength = Number(v);
            node.setDirtyCanvas(true, true);
        }, event);
        return true;
    }

    onStrengthAnyMove(event, pos, node) {
        if (event.deltaX) {
            this.haveMouseMovedStrength = true;
            this.value.strength = (this.value.strength ?? 1) + event.deltaX * 0.05;
            this.value.strength = Math.round(this.value.strength * 100) / 100;
            node.setDirtyCanvas(true, true);
        }
    }

    stepStrength(direction) {
        const step = 0.05;
        this.value.strength = (this.value.strength ?? 1) + step * direction;
        this.value.strength = Math.round(this.value.strength * 100) / 100;
    }

    computeSize(width) {
        return [width, LiteGraph.NODE_WIDGET_HEIGHT];
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

// Header Widget with Toggle All and Strength label
class ManualLoraHeaderWidget {
    constructor() {
        this.name = "manual_lora_header";
        this.type = "manual_lora_header";
        this.value = "";
        this.options = { serialize: false };
        this.y = 0;
        this.last_y = 0;
        this.isMouseDownedAndOver = false;
        this.toggleBounds = null;
    }

    draw(ctx, node, widgetWidth, posY, widgetHeight) {
        // Only show if there are manual LoRAs
        const hasManualLoras = node.widgets?.some(w => w.type === "manual_lora");
        if (!hasManualLoras) return;

        // Move slightly up so it sits clear of the first manual LoRA widget
        posY = Math.max(posY - widgetHeight * 0.35, 0);
        
        const margin = 10;
        const innerMargin = margin * 0.33;
        const midY = posY + widgetHeight * 0.5;
        let posX = margin + 4; // Add some extra left margin

        ctx.save();
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.globalAlpha = app.canvas.editor_alpha * 0.55;

        // Draw toggle all button
        const toggleRadius = widgetHeight * 0.36;
        const toggleBgWidth = widgetHeight * 1.5;
        
        // Determine toggle state
        let allOn = true;
        let allOff = true;
        for (const widget of node.widgets || []) {
            if (widget.type === "manual_lora") {
                const on = widget.value?.on;
                allOn = allOn && on === true;
                allOff = allOff && on === false;
                if (!allOn && !allOff) break;
            }
        }
        const toggleState = allOn ? true : (allOff ? false : null);

        // Toggle background
        ctx.beginPath();
        ctx.roundRect(posX, posY + 4, toggleBgWidth - 8, widgetHeight - 8, [widgetHeight * 0.5]);
        ctx.globalAlpha = app.canvas.editor_alpha * 0.25;
        ctx.fillStyle = "rgba(255,255,255,0.45)";
        ctx.fill();
        ctx.globalAlpha = app.canvas.editor_alpha * 0.55;

        // Toggle circle
        ctx.fillStyle = toggleState === true ? "#89B" : (toggleState === false ? "#888" : "#AA8");
        const toggleX = toggleState === false ? posX + widgetHeight * 0.5 : posX + widgetHeight;
        ctx.beginPath();
        ctx.arc(toggleX, posY + widgetHeight * 0.5, toggleRadius, 0, Math.PI * 2);
        ctx.fill();

        this.toggleBounds = [posX, posY, toggleBgWidth, widgetHeight];
        posX += toggleBgWidth + innerMargin;

        // Draw "Toggle All" text
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText("Toggle All", posX, midY);

        // Draw "Strength" label on the right
        const strengthLabelX = widgetWidth - margin - 60; // Position for "Strength" label
        ctx.textAlign = "center";
        ctx.fillText("Strength", strengthLabelX, midY);

        ctx.restore();
        this.last_y = posY;
    }

    mouse(event, pos, node) {
        if (event.type === "pointerdown" && this.toggleBounds) {
            const [x, y, w, h] = this.toggleBounds;
            if (pos[0] >= x && pos[0] <= x + w && pos[1] >= y && pos[1] <= y + h) {
                this.isMouseDownedAndOver = true;
                return true;
            }
        }
        
        if (event.type === "pointerup" && this.isMouseDownedAndOver && this.toggleBounds) {
            const [x, y, w, h] = this.toggleBounds;
            if (pos[0] >= x && pos[0] <= x + w && pos[1] >= y && pos[1] <= y + h) {
                // Toggle all manual LoRAs
                let allOn = true;
                for (const widget of node.widgets || []) {
                    if (widget.type === "manual_lora" && !widget.value?.on) {
                        allOn = false;
                        break;
                    }
                }
                const newState = !allOn;
                for (const widget of node.widgets || []) {
                    if (widget.type === "manual_lora") {
                        widget.value.on = newState;
                    }
                }
                node.setDirtyCanvas(true, true);
            }
            this.isMouseDownedAndOver = false;
            return true;
        }
        
        return false;
    }

    computeSize(width) {
        // Only show if there are manual LoRAs
        const node = this.node || (this.options && this.options.node);
        const hasManualLoras = node?.widgets?.some(w => w.type === "manual_lora");
        return hasManualLoras ? [width, LiteGraph.NODE_WIDGET_HEIGHT] : [width, 0];
    }

    serializeValue() {
        return "";
    }
}

// Register the extension
app.registerExtension({
    name: "autopilot.smart.power.lora.loader",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        console.log("[Autopilot LoRA] beforeRegisterNodeDef called for:", nodeData.name);
        
        if (nodeData.name === NODE_NAME) {
            console.log("[Autopilot LoRA] Matched NODE_NAME! Setting up node...");
            
            // Load available LoRAs on startup
            await getAvailableLoras();
            console.log("[Autopilot LoRA] Loaded", availableLoras.length, "LoRAs");
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                console.log("[Autopilot LoRA] onNodeCreated called!");
                console.log("[Autopilot LoRA] Initial widgets:", this.widgets ? this.widgets.length : 0);
                
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Hide the manual_loras text widget
                const manualLorasWidget = this.widgets?.find(w => w.name === "manual_loras");
                if (manualLorasWidget) {
                    console.log("[Autopilot LoRA] Found manual_loras widget, hiding it");
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
                
                console.log("[Autopilot LoRA] Adding spacer...");
                // Add a spacer at the top
                this.widgets.push(new SpacerWidget(8));
                
                console.log("[Autopilot LoRA] Adding Manual LoRA Header...");
                // Add the header widget with Toggle All and Strength label
                const headerWidget = new ManualLoraHeaderWidget();
                this.widgets.push(headerWidget);
                
                console.log("[Autopilot LoRA] Adding small spacer after header...");
                // Add a small spacer after header
                this.widgets.push(new SpacerWidget(6));
                
                console.log("[Autopilot LoRA] Adding Add Manual LoRA button...");
                // Create and add "Add Manual LoRA" button using custom widget
                const addLoraBtn = new CustomButtonWidget(
                    "add_manual_lora_btn",
                    "➕ Add Manual LoRA",
                    (event, pos, node) => {
                        console.log("[Autopilot LoRA] Add Manual LoRA button clicked!");
                        const widget = new ManualLoraWidget("manual_lora_" + node.manualLoraCounter++, node);
                        node.manualLoraWidgets.push(widget);
                        
                        // Find the last manual LoRA position
                        let lastLoraIndex = -1;
                        for (let i = node.widgets.length - 1; i >= 0; i--) {
                            if (node.widgets[i].type === "manual_lora") {
                                lastLoraIndex = i;
                                break;
                            }
                        }
                        
                        if (lastLoraIndex >= 0) {
                            // Insert after the last manual LoRA
                            node.widgets.splice(lastLoraIndex + 1, 0, widget);
                        } else {
                            // No manual LoRAs yet, insert after header and its spacer
                            const headerIndex = node.widgets.findIndex(w => w.type === "manual_lora_header");
                            if (headerIndex >= 0) {
                                node.widgets.splice(headerIndex + 2, 0, widget);
                            } else {
                                node.widgets.push(widget);
                            }
                        }
                        
                        const computed = node.computeSize();
                        node.size[1] = Math.max(node.size[1], computed[1]);
                        node.setDirtyCanvas(true, true);
                        return true;
                    }
                );
                this.widgets.push(addLoraBtn);
                console.log("[Autopilot LoRA] Add button added, total widgets now:", this.widgets.length);
                
                // Add a smaller spacer between buttons
                this.widgets.push(new SpacerWidget(2));
                
                console.log("[Autopilot LoRA] Adding Show LoRA Catalog button...");
                // Create and add "Show LoRA Catalog" button using custom widget
                const catalogBtn = new CustomButtonWidget(
                    "show_catalog_btn",
                    "ℹ️ Show LoRA Catalog",
                    async (event, pos, node) => {
                        console.log("[Autopilot LoRA] Show LoRA Catalog button clicked!");
                        await showLoraCatalogDialog(node);
                        return true;
                    }
                );
                this.widgets.push(catalogBtn);
                console.log("[Autopilot LoRA] Catalog button added, total widgets now:", this.widgets.length);
                
                console.log("[Autopilot LoRA] Final widget list:");
                this.widgets.forEach((w, i) => {
                    console.log(`  [${i}] ${w.name || 'unnamed'} (type: ${w.type})`);
                });
                
                return r;
            };
            
            // Override serialize to convert manual LoRA widgets to string
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(o) {
                if (onSerialize) {
                    onSerialize.apply(this, arguments);
                }
                
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
                
                // Don't return anything - modify the passed object instead
            };
            
            // Override getSlotInPosition to detect widget clicks for context menu
            const origGetSlotInPosition = nodeType.prototype.getSlotInPosition;
            nodeType.prototype.getSlotInPosition = function(canvasX, canvasY) {
                const slot = origGetSlotInPosition ? origGetSlotInPosition.apply(this, arguments) : null;
                
                // If no slot found, check if we clicked a manual LoRA widget
                if (!slot) {
                    let lastWidget = null;
                    for (const widget of this.widgets || []) {
                        if (!widget.last_y) return;
                        if (canvasY > this.pos[1] + widget.last_y) {
                            lastWidget = widget;
                            continue;
                        }
                        break;
                    }
                    
                    // If we clicked a manual LoRA widget, return fake slot data
                    if (lastWidget?.type === "manual_lora") {
                        return { widget: lastWidget, output: { type: "MANUAL_LORA_WIDGET" } };
                    }
                }
                return slot;
            };
            
            // Override getSlotMenuOptions to show context menu for manual LoRA widgets
            const origGetSlotMenuOptions = nodeType.prototype.getSlotMenuOptions;
            nodeType.prototype.getSlotMenuOptions = function(slot) {
                // Check if this is a manual LoRA widget
                if (slot?.widget?.type === "manual_lora") {
                    const widget = slot.widget;
                    const index = this.widgets.indexOf(widget);
                    const canMoveUp = index > 0 && this.widgets[index - 1]?.type === "manual_lora";
                    const canMoveDown = index < this.widgets.length - 1 && this.widgets[index + 1]?.type === "manual_lora";
                    
                    const menuItems = [
                        {
                            content: `${widget.value.on ? "⚫" : "🟢"} Toggle ${widget.value.on ? "Off" : "On"}`,
                            callback: () => {
                                widget.value.on = !widget.value.on;
                                this.setDirtyCanvas(true, true);
                            }
                        },
                        null, // Divider
                        {
                            content: `⬆️ Move Up`,
                            disabled: !canMoveUp,
                            callback: () => {
                                if (canMoveUp) {
                                    // Swap with previous manual LoRA
                                    const temp = this.widgets[index];
                                    this.widgets[index] = this.widgets[index - 1];
                                    this.widgets[index - 1] = temp;
                                    this.setDirtyCanvas(true, true);
                                }
                            }
                        },
                        {
                            content: `⬇️ Move Down`,
                            disabled: !canMoveDown,
                            callback: () => {
                                if (canMoveDown) {
                                    // Swap with next manual LoRA
                                    const temp = this.widgets[index];
                                    this.widgets[index] = this.widgets[index + 1];
                                    this.widgets[index + 1] = temp;
                                    this.setDirtyCanvas(true, true);
                                }
                            }
                        },
                        {
                            content: `🗑️ Remove`,
                            callback: () => {
                                this.widgets = this.widgets.filter(w => w !== widget);
                                this.manualLoraWidgets = this.manualLoraWidgets?.filter(w => w !== widget) || [];
                                const computed = this.computeSize();
                                this.size[1] = Math.max(this.size[1], computed[1]);
                                this.setDirtyCanvas(true, true);
                            }
                        }
                    ];
                    
                    new LiteGraph.ContextMenu(menuItems, {
                        title: "MANUAL LORA",
                        event: app.canvas.last_mouse_event || window.event
                    });
                    
                    return undefined;
                }
                
                // Default behavior
                return origGetSlotMenuOptions ? origGetSlotMenuOptions.apply(this, arguments) : undefined;
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

// Show LoRA info dialog (properly centered with editing capability)
async function showLoraInfoDialog(loraName, catalogInfo = {}, onUpdate) {
    const info = catalogInfo ? { ...catalogInfo } : {};
    info.file = info.file || loraName;
    const defaultWeight = Number.isFinite(parseFloat(info.default_weight))
        ? parseFloat(info.default_weight)
        : 1.0;

    const dialog = document.createElement("div");
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

    const content = document.createElement("div");
    content.style.cssText = `
        background: #202020;
        border: 2px solid #444;
        border-radius: 8px;
        padding: 20px;
        width: 620px;
        max-height: 82vh;
        overflow: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    `;

    const title = document.createElement("h2");
    title.textContent = info.display_name || loraName;
    title.style.cssText = "margin: 0 0 10px 0; color: #fff; font-size: 20px;";
    content.appendChild(title);

    const statusLine = document.createElement("div");
    const indexedByLLM = info.indexed_by_llm;
    const manuallyIndexed = info.manually_indexed || info.indexed_manually;
    let statusText = "Status: not indexed";
    if (indexedByLLM) {
        statusText = "Status: indexed automatically";
    } else if (manuallyIndexed) {
        statusText = "Status: manually indexed";
    }
    statusLine.textContent = statusText;
    statusLine.style.cssText = "color: #888; font-size: 12px; margin-bottom: 12px;";
    content.appendChild(statusLine);

    const summaryLabel = document.createElement("h3");
    summaryLabel.textContent = "Summary";
    summaryLabel.style.cssText = "color: #aaa; font-size: 14px; margin: 0 0 6px 0;";
    content.appendChild(summaryLabel);

    const summaryInput = document.createElement("textarea");
    summaryInput.value = info.summary || "";
    summaryInput.placeholder = "Write a short description so this LoRA shows as ready.";
    summaryInput.style.cssText = `
        width: 100%;
        margin: 0 0 6px 0;
        padding: 8px;
        background: #2a2a2a;
        border: 1px solid #444;
        color: #fff;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
        min-height: 90px;
        resize: vertical;
    `;
    content.appendChild(summaryInput);

    const summaryHint = document.createElement("div");
    summaryHint.textContent = "Tip: leaving this blank keeps the LoRA marked as not indexed.";
    summaryHint.style.cssText = "color: #666; font-size: 12px; margin-bottom: 15px;";
    content.appendChild(summaryHint);

    const triggerLabel = document.createElement("h3");
    triggerLabel.textContent = "Trigger Words";
    triggerLabel.style.cssText = "color: #aaa; font-size: 14px; margin: 0 0 6px 0;";
    content.appendChild(triggerLabel);

    const triggerEditor = createTokenEditor({
        initialValues: info.trained_words || [],
        placeholder: "Add a trigger word and press Enter",
        emptyLabel: "No trigger words yet",
        chipBackground: "#3a5a7a",
        chipTextColor: "#fff"
    });
    content.appendChild(triggerEditor.container);

    const tagsLabel = document.createElement("h3");
    tagsLabel.textContent = "Tags";
    tagsLabel.style.cssText = "color: #aaa; font-size: 14px; margin: 15px 0 6px 0;";
    content.appendChild(tagsLabel);

    const tagsEditor = createTokenEditor({
        initialValues: info.tags || [],
        placeholder: "Add a tag and press Enter",
        emptyLabel: "No tags yet",
        chipBackground: "#444",
        chipTextColor: "#ddd"
    });
    content.appendChild(tagsEditor.container);

    const baseLabel = document.createElement("h3");
    baseLabel.textContent = "Base Models (select all that apply)";
    baseLabel.style.cssText = "color: #aaa; font-size: 14px; margin: 15px 0 6px 0;";
    content.appendChild(baseLabel);

    const baseModelSelect = document.createElement("select");
    baseModelSelect.multiple = true;
    baseModelSelect.size = 8;
    baseModelSelect.style.cssText = `
        width: 100%;
        margin-bottom: 15px;
        padding: 8px;
        background: #2a2a2a;
        border: 1px solid #444;
        color: #fff;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
    `;
    await populateBaseModelSelect(baseModelSelect, info.base_compat || ["Unknown"]);
    content.appendChild(baseModelSelect);

    const weightLabel = document.createElement("h3");
    weightLabel.textContent = "Default Weight";
    weightLabel.style.cssText = "color: #aaa; font-size: 14px; margin: 15px 0 6px 0;";
    content.appendChild(weightLabel);

    const weightInput = document.createElement("input");
    weightInput.type = "number";
    weightInput.step = "0.05";
    weightInput.min = "0";
    weightInput.max = "2";
    weightInput.value = defaultWeight;
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
    `;
    content.appendChild(weightInput);

    if (info.civitai_model_id) {
        const link = document.createElement("a");
        link.href = `https://civitai.com/models/${info.civitai_model_id}`;
        link.target = "_blank";
        link.textContent = "View on Civitai";
        link.style.cssText = `
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 15px;
            background: #3a5a7a;
            color: #fff;
            text-decoration: none;
            border-radius: 4px;
        `;
        link.onmouseenter = () => link.style.background = "#4a6a8a";
        link.onmouseleave = () => link.style.background = "#3a5a7a";
        content.appendChild(link);
    }

    const buttonRow = document.createElement("div");
    buttonRow.style.cssText = "display: flex; gap: 10px; margin-top: 20px;";

    const saveBtn = document.createElement("button");
    saveBtn.textContent = "Save Changes";
    saveBtn.style.cssText = "flex: 1; padding: 10px 20px; background: #2a8a4a; border: none; color: #fff; border-radius: 4px; cursor: pointer; font-size: 14px;";
    saveBtn.onmouseenter = () => saveBtn.style.background = "#39a35a";
    saveBtn.onmouseleave = () => saveBtn.style.background = "#2a8a4a";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.cssText = "flex: 1; padding: 10px 20px; background: #444; border: none; color: #fff; border-radius: 4px; cursor: pointer; font-size: 14px;";
    cancelBtn.onmouseenter = () => cancelBtn.style.background = "#555";
    cancelBtn.onmouseleave = () => cancelBtn.style.background = "#444";

    buttonRow.appendChild(saveBtn);
    buttonRow.appendChild(cancelBtn);
    content.appendChild(buttonRow);

    const cleanup = () => {
        if (dialog.parentElement) {
            dialog.parentElement.removeChild(dialog);
        }
        document.removeEventListener("keydown", escHandler);
    };

    const escHandler = (event) => {
        if (event.key === "Escape") {
            cleanup();
        }
    };
    document.addEventListener("keydown", escHandler);

    cancelBtn.onclick = (event) => {
        event.preventDefault();
        cleanup();
    };

    saveBtn.onclick = async (event) => {
        event.preventDefault();
        const selectedModels = Array.from(baseModelSelect.selectedOptions).map(opt => opt.value);
        const parsedWeight = parseFloat(weightInput.value);
        const payload = {
            summary: summaryInput.value.trim(),
            trained_words: triggerEditor.getValues(),
            tags: tagsEditor.getValues(),
            base_compat: selectedModels.length ? selectedModels : ["Unknown"],
            default_weight: Number.isFinite(parsedWeight) ? parsedWeight : 1.0
        };

        if (info.file_hash) {
            payload.file_hash = info.file_hash;
        } else if (info.file) {
            payload.file_name = info.file;
        } else {
            payload.file_name = loraName;
        }

        saveBtn.disabled = true;
        cancelBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        try {
            const response = await api.fetchApi('/autopilot_lora/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.success) {
                alert('LoRA information updated successfully!');
                if (typeof onUpdate === 'function') {
                    const updatedEntry = result.entry || { ...info, ...payload, file: info.file || loraName };
                    onUpdate(updatedEntry);
                }
                cleanup();
            } else {
                alert('Failed to update LoRA: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Failed to update LoRA: ' + error.message);
        } finally {
            if (dialog.parentElement) {
                saveBtn.disabled = false;
                cancelBtn.disabled = false;
                saveBtn.textContent = "Save Changes";
            }
        }
    };

    dialog.appendChild(content);
    dialog.onclick = (event) => {
        if (event.target === dialog) {
            cleanup();
        }
    };

    document.body.appendChild(dialog);
    setTimeout(() => summaryInput.focus(), 50);
}

// Show full LoRA catalog dialog (properly centered)
async function showLoraCatalogDialog(node) {
    try {
        // Fetch both catalog and all available LoRAs
        const [catalogResponse, availableResponse] = await Promise.all([
            api.fetchApi('/autopilot_lora/catalog'),
            api.fetchApi('/autopilot_lora/available')
        ]);
        
        let catalog = catalogResponse.ok ? await catalogResponse.json() : {};
        if (!catalog || typeof catalog !== "object") {
            catalog = {};
        }
        const availableData = availableResponse.ok ? await availableResponse.json() : { loras: [] };
        let allLoraFiles = Array.isArray(availableData.loras) ? availableData.loras : [];
        
        const loraMap = new Map();
        const fileToHash = new Map();

        const normalizeStringList = (values) => Array.isArray(values)
            ? values.map(value => typeof value === "string" ? value.trim() : "").filter(Boolean)
            : [];

        const isTruthyFlag = (value) => value === true || value === "true" || value === 1 || value === "1";

        const computeIndexedState = (entry) => {
            if (!entry) {
                return false;
            }
            if (isTruthyFlag(entry.indexed)) {
                return true;
            }
            if (isTruthyFlag(entry.indexed_by_llm) || isTruthyFlag(entry.indexedByLlm)) {
                return true;
            }
            if (isTruthyFlag(entry.manually_indexed) || isTruthyFlag(entry.indexed_manually)) {
                return true;
            }
            if (entry.indexing_source === "manual") {
                return true;
            }
            if (entry.source && entry.source.kind === "manual") {
                return true;
            }
            return false;
        };

        const rebuildState = () => {
            loraMap.clear();
            fileToHash.clear();

            const mergedEntries = new Map();

            allLoraFiles.forEach(file => {
                mergedEntries.set(file, {
                    file,
                    display_name: file,
                    indexed: false,
                    enabled: true,
                    source_kind: "unknown",
                    trained_words: [],
                    tags: [],
                    base_compat: ["Unknown"]
                });
            });

            Object.entries(catalog || {}).forEach(([hash, entry]) => {
                if (!entry || !entry.file) {
                    return;
                }
                const file = entry.file;
                fileToHash.set(file, hash);
                const baseEntry = mergedEntries.get(file) || {
                    file,
                    display_name: entry.display_name || file,
                    enabled: true,
                    source_kind: entry.source_kind || (entry.source && entry.source.kind) || "unknown",
                    trained_words: [],
                    tags: [],
                    base_compat: ["Unknown"]
                };
                const merged = { ...baseEntry, ...entry };
                merged.file = file;
                if (!merged.display_name) {
                    merged.display_name = file;
                }
                merged.enabled = merged.enabled !== false;
                merged.indexed = computeIndexedState(merged);
                mergedEntries.set(file, merged);
            });

            Object.values(catalog || {}).forEach(entry => {
                if (!entry || !entry.file || mergedEntries.has(entry.file)) {
                    return;
                }
                const copy = { ...entry };
                copy.file = entry.file;
                copy.display_name = copy.display_name || entry.file;
                copy.enabled = copy.enabled !== false;
                copy.indexed = computeIndexedState(copy);
                mergedEntries.set(entry.file, copy);
            });

            mergedEntries.forEach((value, file) => {
                const normalized = { ...value };
                normalized.indexed = computeIndexedState(value);
                normalized.enabled = normalized.enabled !== false;
                loraMap.set(file, normalized);
            });
        };

        const applyUpdatedEntry = (updated) => {
            if (!updated) {
                return;
            }
            const file = updated.file || updated.file_name || null;
            if (!file) {
                return;
            }
            if (!allLoraFiles.includes(file)) {
                allLoraFiles.push(file);
            }

            const hash = updated.file_hash || fileToHash.get(file) || null;
            if (hash) {
                const existing = catalog[hash] || {};
                catalog[hash] = { ...existing, ...updated, file };
                fileToHash.set(file, hash);
            } else {
                const tempKey = `temp_${file}`;
                const existing = catalog[tempKey] || {};
                catalog[tempKey] = { ...existing, ...updated, file };
                fileToHash.set(file, tempKey);
            }

            rebuildState();
        };

        const refreshStateFromServer = async () => {
            const [newCatalogResponse, newAvailableResponse] = await Promise.all([
                api.fetchApi('/autopilot_lora/catalog'),
                api.fetchApi('/autopilot_lora/available')
            ]);
            catalog = newCatalogResponse.ok ? await newCatalogResponse.json() : {};
            if (!catalog || typeof catalog !== "object") {
                catalog = {};
            }
            const available = newAvailableResponse.ok ? await newAvailableResponse.json() : { loras: [] };
            allLoraFiles = Array.isArray(available.loras) ? available.loras : [];
            rebuildState();
        };

        rebuildState();

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
            max-width: 1000px;
            height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;

        const title = document.createElement('h2');
        title.textContent = 'LoRA Catalog';
        title.style.cssText = 'margin: 0 0 15px 0; color: #fff; font-size: 22px;';
        content.appendChild(title);

        // Search and filter controls
        const controlsRow = document.createElement('div');
        controlsRow.style.cssText = 'display: flex; gap: 10px; margin-bottom: 15px; align-items: center;';
        
        const search = document.createElement('input');
        search.type = 'text';
        search.placeholder = 'Search LoRAs...';
        search.style.cssText = `
            flex: 1;
            padding: 10px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
        `;
        controlsRow.appendChild(search);
        
        // Filter toggle buttons
        const filterBtns = document.createElement('div');
        filterBtns.style.cssText = 'display: flex; gap: 5px;';
        
        let currentFilter = 'all'; // 'all', 'indexed', 'unindexed', 'enabled', 'disabled'
        
        const createFilterBtn = (label, filterType) => {
            const btn = document.createElement('button');
            btn.textContent = label;
            btn.style.cssText = `
                padding: 8px 12px;
                background: ${filterType === 'all' ? '#3a5a7a' : '#2a2a2a'};
                border: 1px solid #444;
                color: #fff;
                border-radius: 4px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            `;
            btn.onclick = () => {
                currentFilter = filterType;
                // Update button states
                filterBtns.querySelectorAll('button').forEach(b => {
                    b.style.background = '#2a2a2a';
                    b.style.borderColor = '#444';
                });
                btn.style.background = '#3a5a7a';
                btn.style.borderColor = '#5a7a9a';
                displayCatalog(search.value);
            };
            btn.onmouseenter = () => {
                if (currentFilter !== filterType) btn.style.background = '#353535';
            };
            btn.onmouseleave = () => {
                if (currentFilter !== filterType) btn.style.background = '#2a2a2a';
            };
            return btn;
        };
        
        filterBtns.appendChild(createFilterBtn('All', 'all'));
        filterBtns.appendChild(createFilterBtn('Indexed', 'indexed'));
        filterBtns.appendChild(createFilterBtn('Unindexed', 'unindexed'));
        filterBtns.appendChild(createFilterBtn('Enabled', 'enabled'));
        filterBtns.appendChild(createFilterBtn('Disabled', 'disabled'));
        
        controlsRow.appendChild(filterBtns);
        content.appendChild(controlsRow);

        const catalogList = document.createElement('div');
        catalogList.style.cssText = 'flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; padding-right: 5px;';

        function displayCatalog(filterText = '') {
            catalogList.innerHTML = '';
            
            let entries = Array.from(loraMap.values());
            
            // Apply filter
            entries = entries.filter(entry => {
                if (currentFilter === 'indexed' && !entry.indexed) return false;
                if (currentFilter === 'unindexed' && entry.indexed) return false;
                if (currentFilter === 'enabled' && !entry.enabled) return false;
                if (currentFilter === 'disabled' && entry.enabled) return false;
                
                if (filterText) {
                    const searchLower = filterText.toLowerCase();
                    return (entry.display_name?.toLowerCase().includes(searchLower) ||
                           entry.file?.toLowerCase().includes(searchLower) ||
                           entry.summary?.toLowerCase().includes(searchLower));
                }
                return true;
            });
            
            // Sort: indexed first, then alphabetically
            entries.sort((a, b) => {
                if (a.indexed !== b.indexed) return b.indexed ? 1 : -1;
                return (a.display_name || a.file).localeCompare(b.display_name || b.file);
            });

            if (entries.length === 0) {
                const noResults = document.createElement('p');
                noResults.textContent = 'No matching LoRAs found';
                noResults.style.cssText = 'color: #888; padding: 20px; text-align: center;';
                catalogList.appendChild(noResults);
                return;
            }

            entries.forEach(entry => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 12px;
                    background: ${entry.indexed ? '#2a3a2a' : '#2a2a2a'};
                    border-radius: 6px;
                    transition: background 0.2s;
                    border: 1px solid ${entry.enabled ? '#3a4a3a' : '#4a3a3a'};
                    display: flex;
                    gap: 12px;
                    align-items: start;
                    opacity: ${entry.enabled ? '1' : '0.6'};
                `;
                
                // Enable/Disable toggle
                const toggleBtn = document.createElement('button');
                toggleBtn.textContent = entry.enabled ? '✓' : '✗';
                toggleBtn.title = entry.enabled ? 'Click to disable' : 'Click to enable';
                toggleBtn.style.cssText = `
                    width: 32px;
                    height: 32px;
                    background: ${entry.enabled ? '#2a8a4a' : '#8a2a2a'};
                    border: none;
                    color: #fff;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                    flex-shrink: 0;
                    transition: all 0.2s;
                `;
                toggleBtn.onmouseenter = () => toggleBtn.style.transform = 'scale(1.1)';
                toggleBtn.onmouseleave = () => toggleBtn.style.transform = 'scale(1)';
                toggleBtn.onclick = async (e) => {
                    e.stopPropagation();
                    const originalEnabled = entry.enabled;
                    entry.enabled = !entry.enabled;
                    
                    try {
                        const response = await api.fetchApi('/autopilot_lora/update', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                file_name: entry.file,
                                enabled: entry.enabled
                            })
                        });
                        
                        const result = await response.json();
                        if (!result.success) {
                            console.error('Failed to update LoRA enabled state:', result.error);
                            entry.enabled = originalEnabled;
                        } else {
                            const updatedEntry = result.entry || { ...entry, enabled: entry.enabled };
                            applyUpdatedEntry(updatedEntry);
                        }
                    } catch (err) {
                        console.error('Failed to update LoRA enabled state:', err);
                        entry.enabled = originalEnabled;
                    }
                    
                    displayCatalog(search.value);
                };
                item.appendChild(toggleBtn);
                
                // Info section
                const infoSection = document.createElement('div');
                infoSection.style.cssText = 'flex: 1; cursor: pointer;';
                infoSection.onclick = () => {
                    showLoraInfoDialog(entry.file, entry, (updatedEntry) => {
                        applyUpdatedEntry(updatedEntry);
                        displayCatalog(search.value);
                    });
                };
                
                const nameRow = document.createElement('div');
                nameRow.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-bottom: 5px;';
                
                const name = document.createElement('div');
                name.textContent = entry.display_name || entry.file;
                name.style.cssText = 'font-weight: bold; color: #fff; font-size: 14px;';
                nameRow.appendChild(name);
                
                // Status badges
                if (!entry.indexed) {
                    const badge = document.createElement('span');
                    badge.textContent = 'Not Indexed';
                    badge.style.cssText = 'padding: 2px 6px; background: #5a4a2a; border-radius: 3px; font-size: 11px; color: #ffb;';
                    nameRow.appendChild(badge);
                }
                
                if (entry.is_character) {
                    const badge = document.createElement('span');
                    badge.textContent = 'Character';
                    badge.style.cssText = 'padding: 2px 6px; background: #4a2a5a; border-radius: 3px; font-size: 11px; color: #faf;';
                    nameRow.appendChild(badge);
                }
                
                infoSection.appendChild(nameRow);

                if (entry.indexed && entry.summary) {
                    const summary = document.createElement('div');
                    summary.textContent = entry.summary.substring(0, 120) + (entry.summary.length > 120 ? '...' : '');
                    summary.style.cssText = 'font-size: 0.9em; color: #aaa; margin-bottom: 6px;';
                    infoSection.appendChild(summary);
                }

                if (entry.indexed) {
                    const meta = document.createElement('div');
                    meta.style.cssText = 'font-size: 0.85em; color: #888; display: flex; gap: 12px; flex-wrap: wrap;';
                    
                    if (entry.base_compat && entry.base_compat.length > 0 && entry.base_compat[0] !== 'Unknown') {
                        const base = document.createElement('span');
                        base.textContent = `📦 ${entry.base_compat.join(', ')}`;
                        meta.appendChild(base);
                    }

                    if (entry.trained_words && entry.trained_words.length > 0) {
                        const triggers = document.createElement('span');
                        triggers.textContent = `🏷️ ${entry.trained_words.length} triggers`;
                        meta.appendChild(triggers);
                    }
                    
                    if (entry.default_weight) {
                        const weight = document.createElement('span');
                        weight.textContent = `⚖️ ${entry.default_weight}`;
                        meta.appendChild(weight);
                    }

                    infoSection.appendChild(meta);
                } else {
                    const notIndexedMsg = document.createElement('div');
                    notIndexedMsg.textContent = 'Click "Start Indexing" below to fetch metadata from Civitai';
                    notIndexedMsg.style.cssText = 'font-size: 0.85em; color: #888; font-style: italic;';
                    infoSection.appendChild(notIndexedMsg);
                }
                
                item.appendChild(infoSection);
                
                item.onmouseenter = () => {
                    if (infoSection.style.background !== '#353535') {
                        item.style.background = entry.indexed ? '#2f4a2f' : '#353535';
                    }
                };
                item.onmouseleave = () => {
                    item.style.background = entry.indexed ? '#2a3a2a' : '#2a2a2a';
                };
                
                catalogList.appendChild(item);
            });
        }

        search.oninput = (e) => displayCatalog(e.target.value);
        content.appendChild(catalogList);
        displayCatalog();

        // Indexing section
        const indexingSection = document.createElement('div');
        indexingSection.style.cssText = 'margin-top: 15px; padding-top: 15px; border-top: 1px solid #444;';

        const indexingTitle = document.createElement('h3');
        indexingTitle.textContent = 'Index New LoRAs';
        indexingTitle.style.cssText = 'margin: 0 0 10px 0; color: #fff; font-size: 16px;';
        indexingSection.appendChild(indexingTitle);

        const indexingDesc = document.createElement('p');
        indexingDesc.textContent = 'Fetch metadata from Civitai and index unindexed LoRAs';
        indexingDesc.style.cssText = 'margin: 0 0 10px 0; color: #aaa; font-size: 13px;';
        indexingSection.appendChild(indexingDesc);

        const indexingControls = document.createElement('div');
        indexingControls.style.cssText = 'display: flex; gap: 10px; align-items: center;';

        const maxLorasInput = document.createElement('input');
        maxLorasInput.type = 'number';
        maxLorasInput.value = '10';
        maxLorasInput.min = '1';
        maxLorasInput.max = '100';
        maxLorasInput.style.cssText = `
            width: 80px;
            padding: 8px;
            background: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 14px;
        `;
        indexingControls.appendChild(maxLorasInput);

        const maxLabel = document.createElement('span');
        maxLabel.textContent = 'max LoRAs';
        maxLabel.style.cssText = 'color: #aaa; font-size: 13px;';
        indexingControls.appendChild(maxLabel);

        const modelHint = document.createElement('div');
        modelHint.style.cssText = 'margin-top: 8px; color: #888; font-size: 12px;';
        const refreshModelHint = () => {
            const currentModel = getIndexingModelFromNode(node);
            if (currentModel) {
                modelHint.textContent = `Using LLM: ${currentModel}`;
            } else {
                modelHint.textContent = 'Using LLM: default (groq: llama-3.1-8b-instant)';
            }
        };
        refreshModelHint();

        const indexBtn = document.createElement('button');
        indexBtn.textContent = '🔄 Start Indexing';
        indexBtn.style.cssText = `
            flex: 1;
            padding: 10px 20px;
            background: #3a7a5a;
            border: none;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        indexBtn.onmouseenter = () => indexBtn.style.background = '#4a8a6a';
        indexBtn.onmouseleave = () => indexBtn.style.background = '#3a7a5a';
        indexBtn.onclick = async () => {
            const maxLoras = parseInt(maxLorasInput.value) || 10;
            const indexingModel = getIndexingModelFromNode(node);
            if (indexingModel) {
                node.autopilotIndexingModel = indexingModel;
            }
            refreshModelHint();
            indexBtn.disabled = true;
            indexBtn.textContent = '⏳ Indexing...';
            indexBtn.style.background = '#666';
            indexBtn.style.cursor = 'wait';

            try {
                const payload = { max_loras: maxLoras };
                if (indexingModel) {
                    payload.indexing_model = indexingModel;
                }

                const response = await api.fetchApi('/autopilot_lora/index', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.success) {
                    alert(`✅ Indexing complete!\n\nIndexed: ${result.indexed_count || 0}\nFailed: ${result.failed_count || 0}\nSkipped: ${result.skipped_count || 0}`);
                    
                    await refreshStateFromServer();
                    displayCatalog(search.value);
                } else {
                    alert('❌ Indexing failed: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('[Autopilot LoRA] Indexing error:', error);
                alert('❌ Indexing failed: ' + error.message);
            } finally {
                indexBtn.disabled = false;
                indexBtn.textContent = '🔄 Start Indexing';
                indexBtn.style.background = '#3a7a5a';
                indexBtn.style.cursor = 'pointer';
                refreshModelHint();
            }
        };
        indexingControls.appendChild(indexBtn);

        indexingSection.appendChild(indexingControls);
        indexingSection.appendChild(modelHint);
        content.appendChild(indexingSection);
        dialog.addEventListener('pointerover', refreshModelHint);

        // Close button
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
