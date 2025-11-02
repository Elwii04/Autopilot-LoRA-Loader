import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Name of our node type
const NODE_NAME = "SmartPowerLoRALoader";

// Store available LoRAs globally
let availableLoras = [];

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

// Show LoRA chooser (like rgthree's showLoraChooser using LiteGraph.ContextMenu)
async function showLoraChooser(callback, currentValue = null) {
    await getAvailableLoras();
    
    const loras = availableLoras.length > 0 ? availableLoras : ["None"];
    
    new LiteGraph.ContextMenu(loras, {
        event: window.event || { clientX: 100, clientY: 100 },
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
        showLoraChooser((value) => {
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
                this.widgets.push(new SpacerWidget(4));
                
                console.log("[Autopilot LoRA] Adding Manual LoRA Header...");
                // Add the header widget with Toggle All and Strength label
                const headerWidget = new ManualLoraHeaderWidget();
                this.widgets.push(headerWidget);
                
                console.log("[Autopilot LoRA] Adding Add Manual LoRA button...");
                // Create and add "Add Manual LoRA" button using custom widget
                const addLoraBtn = new CustomButtonWidget(
                    "add_manual_lora_btn",
                    "➕ Add Manual LoRA",
                    (event, pos, node) => {
                        console.log("[Autopilot LoRA] Add Manual LoRA button clicked!");
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
                console.log("[Autopilot LoRA] Add button added, total widgets now:", this.widgets.length);
                
                // Add a small spacer
                this.widgets.push(new SpacerWidget(4));
                
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
            indexBtn.disabled = true;
            indexBtn.textContent = '⏳ Indexing...';
            indexBtn.style.background = '#666';
            indexBtn.style.cursor = 'wait';

            try {
                const response = await api.fetchApi('/autopilot_lora/index', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ max_loras: maxLoras })
                });

                const result = await response.json();

                if (result.success) {
                    alert(`✅ Indexing complete!\n\nIndexed: ${result.indexed_count || 0}\nFailed: ${result.failed_count || 0}\nSkipped: ${result.skipped_count || 0}`);
                    
                    // Refresh the catalog display
                    const newCatalogResponse = await api.fetchApi('/autopilot_lora/catalog');
                    const newCatalog = newCatalogResponse.ok ? await newCatalogResponse.json() : {};
                    // Replace the catalog entries
                    Object.keys(catalog).forEach(key => delete catalog[key]);
                    Object.assign(catalog, newCatalog);
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
            }
        };
        indexingControls.appendChild(indexBtn);

        indexingSection.appendChild(indexingControls);
        content.appendChild(indexingSection);

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
