/**
 * Elevator Fleet Dashboard — Frontend Logic
 *
 * Connects to the FastAPI WebSocket, renders the building,
 * updates stats, decision log, and live charts in real-time.
 */

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════
let ws = null;
let state = null;
let heatmapEnabled = false;
let waitHistory = [];
let utilHistory = [];
const MAX_HISTORY = 200;

// ═══════════════════════════════════════════════════════════════
// DOM References
// ═══════════════════════════════════════════════════════════════
const $ = (sel) => document.querySelector(sel);
const buildingContainer = $("#building-container");

// ═══════════════════════════════════════════════════════════════
// WebSocket Connection
// ═══════════════════════════════════════════════════════════════
function connect() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => console.log("[WS] Connected");

    ws.onmessage = (event) => {
        state = JSON.parse(event.data);
        render(state);
    };

    ws.onclose = () => {
        console.log("[WS] Disconnected — reconnecting in 2s...");
        setTimeout(connect, 2000);
    };

    ws.onerror = (err) => {
        console.error("[WS] Error:", err);
        ws.close();
    };
}

// ═══════════════════════════════════════════════════════════════
// Building Renderer
// ═══════════════════════════════════════════════════════════════
let buildingRendered = false;

function renderBuilding(numFloors, numElevators) {
    if (buildingRendered) return;
    buildingRendered = true;

    buildingContainer.innerHTML = "";

    // Floor labels + queue area
    const floorCol = document.createElement("div");
    floorCol.className = "floor-column";
    floorCol.style.display = "flex";
    floorCol.style.flexDirection = "column-reverse";

    for (let f = 1; f <= numFloors; f++) {
        const row = document.createElement("div");
        row.className = "floor-row";
        row.id = `floor-${f}`;

        const label = document.createElement("div");
        label.className = "floor-label" + (f === 1 ? " ground" : "");
        label.textContent = f === 1 ? "G" : f;

        const queue = document.createElement("div");
        queue.className = "floor-queue";
        queue.id = `queue-${f}`;

        row.appendChild(label);
        row.appendChild(queue);
        floorCol.appendChild(row);
    }

    buildingContainer.appendChild(floorCol);

    // Shaft area
    const shaftArea = document.createElement("div");
    shaftArea.className = "shaft-area";

    for (let e = 0; e < numElevators; e++) {
        const shaft = document.createElement("div");
        shaft.className = "shaft";
        shaft.id = `shaft-${e}`;

        // Header
        const header = document.createElement("div");
        header.className = "shaft-header";
        header.textContent = `E${e}`;
        shaft.appendChild(header);

        // Shaft body (relative container for car)
        const body = document.createElement("div");
        body.style.position = "relative";
        body.style.height = `${numFloors * 48}px`;
        body.id = `shaft-body-${e}`;

        // Elevator car
        const car = document.createElement("div");
        car.className = `elevator-car elev-${e}`;
        car.id = `car-${e}`;

        const pax = document.createElement("div");
        pax.className = "car-pax";
        pax.id = `car-pax-${e}`;
        pax.textContent = "0";

        const dir = document.createElement("div");
        dir.className = "car-dir";
        dir.id = `car-dir-${e}`;
        dir.textContent = "IDLE";

        const loadBar = document.createElement("div");
        loadBar.className = "car-load-bar";
        const loadFill = document.createElement("div");
        loadFill.className = "car-load-fill low";
        loadFill.id = `car-load-${e}`;
        loadBar.appendChild(loadFill);

        car.appendChild(pax);
        car.appendChild(dir);
        car.appendChild(loadBar);
        body.appendChild(car);
        shaft.appendChild(body);
        shaftArea.appendChild(shaft);
    }

    buildingContainer.appendChild(shaftArea);
}

// ═══════════════════════════════════════════════════════════════
// Main Render Loop
// ═══════════════════════════════════════════════════════════════
function render(s) {
    if (!s) return;

    // Build the building DOM once
    renderBuilding(s.num_floors, s.elevators.length);

    // Update stats bar
    updateStats(s);

    // Update elevator positions
    updateElevators(s);

    // Update floor queues
    updateFloorQueues(s);

    // Update decision log
    updateDecisionLog(s);

    // Update charts
    updateCharts(s);

    // Update weights display
    updateWeights(s);

    // Update progress bar
    const pct = s.total_steps > 0 ? (s.step / s.total_steps) * 100 : 0;
    $("#progress-fill").style.width = `${pct}%`;
}

function updateStats(s) {
    const m = s.metrics;

    $("#val-strategy").textContent = s.strategy.toUpperCase();
    $("#val-scenario").textContent = s.scenario.replace("_", " ");
    $("#val-avg-wait").textContent = `${m.avg_wait}s`;
    $("#val-max-wait").textContent = `${m.max_wait}s`;
    $("#val-completed").textContent = m.completed;
    $("#val-calls").textContent = m.total_calls;
    $("#val-active").textContent = m.active_passengers;
    $("#val-step").textContent = `${s.step}/${s.total_steps}`;
    $("#val-time").textContent = s.sim_time;

    // SLA indicator
    const slaEl = $("#stat-sla");
    const slaVal = $("#val-sla");
    if (m.sla_met) {
        slaVal.textContent = "MET";
        slaEl.className = "stat highlight sla-met";
    } else {
        slaVal.textContent = "FAIL";
        slaEl.className = "stat highlight sla-fail";
    }
}

function updateElevators(s) {
    const floorH = 48; // matches CSS --floor-height

    s.elevators.forEach((e) => {
        const car = $(`#car-${e.id}`);
        if (!car) return;

        // Position (bottom-up, floor 1 = 0px)
        const bottomPx = (e.floor - 1) * floorH + 3;
        car.style.bottom = `${bottomPx}px`;

        // Passenger count
        $(`#car-pax-${e.id}`).textContent = e.passengers;

        // Direction arrow
        const dirMap = { UP: "\u25B2", DOWN: "\u25BC", IDLE: "\u25CF" };
        $(`#car-dir-${e.id}`).textContent = dirMap[e.direction] || "\u25CF";

        // Load bar
        const loadEl = $(`#car-load-${e.id}`);
        loadEl.style.width = `${e.load_pct}%`;
        loadEl.className = "car-load-fill " +
            (e.load_pct > 75 ? "high" : e.load_pct > 40 ? "medium" : "low");
    });
}

function updateFloorQueues(s) {
    for (let f = 1; f <= s.num_floors; f++) {
        const queueEl = $(`#queue-${f}`);
        if (!queueEl) continue;

        const floorData = s.floors[String(f)] || { up: 0, down: 0, express: 0 };
        const total = floorData.up + floorData.down + floorData.express;

        // Clear existing dots
        queueEl.innerHTML = "";

        // Add dots for waiting passengers
        for (let i = 0; i < Math.min(floorData.up, 6); i++) {
            const dot = document.createElement("div");
            dot.className = "queue-dot";
            dot.title = "UP call";
            queueEl.appendChild(dot);
        }
        for (let i = 0; i < Math.min(floorData.down, 6); i++) {
            const dot = document.createElement("div");
            dot.className = "queue-dot";
            dot.style.background = "var(--cyan)";
            dot.title = "DOWN call";
            queueEl.appendChild(dot);
        }
        for (let i = 0; i < Math.min(floorData.express, 3); i++) {
            const dot = document.createElement("div");
            dot.className = "queue-dot express";
            dot.title = "EXPRESS call";
            queueEl.appendChild(dot);
        }

        // Heatmap
        const row = $(`#floor-${f}`);
        if (row) {
            row.className = "floor-row";
            if (heatmapEnabled) {
                if (total >= 4) row.classList.add("heatmap-4");
                else if (total >= 3) row.classList.add("heatmap-3");
                else if (total >= 2) row.classList.add("heatmap-2");
                else if (total >= 1) row.classList.add("heatmap-1");
            }
        }
    }
}

function updateDecisionLog(s) {
    const logEl = $("#log-entries");
    if (!logEl || !s.decisions) return;

    logEl.innerHTML = "";

    // Show newest first
    const decisions = [...s.decisions].reverse();
    for (const d of decisions) {
        const entry = document.createElement("div");
        entry.className = "log-entry";

        const elevClass = `e${d.elevator % 4}`;
        entry.innerHTML = `
            <span class="log-info">F${d.floor}${d.direction === "UP" ? "\u2191" : "\u2193"}F${d.dest}</span>
            <span class="log-elev ${elevClass}">E${d.elevator}</span>
            <span class="log-score">${d.score}</span>
        `;
        logEl.appendChild(entry);
    }
}

function updateWeights(s) {
    const panel = $("#weights-bars");
    if (!panel) return;

    if (!s.weights || Object.keys(s.weights).length === 0) {
        panel.innerHTML = '<div style="color:var(--text-muted);font-size:11px;">N/A (non-GBFS strategy)</div>';
        return;
    }

    panel.innerHTML = "";
    for (const [key, val] of Object.entries(s.weights)) {
        const bar = document.createElement("div");
        bar.className = "weight-bar";

        const pct = Math.min(val * 200, 100); // scale to 0-100% (0.5 = 100%)
        bar.innerHTML = `
            <div class="weight-bar-label">
                <span>${key.replace("_", " ")}</span>
                <span>${(val * 100).toFixed(0)}%</span>
            </div>
            <div class="weight-bar-track">
                <div class="weight-bar-fill" style="width:${pct}%"></div>
            </div>
        `;
        panel.appendChild(bar);
    }
}

// ═══════════════════════════════════════════════════════════════
// Simple Canvas Charts
// ═══════════════════════════════════════════════════════════════
function updateCharts(s) {
    // Accumulate history
    if (s.step % 5 === 0) { // sample every 5 steps
        waitHistory.push(s.metrics.avg_wait);
        if (waitHistory.length > MAX_HISTORY) waitHistory.shift();

        const avgUtil = s.elevators.length > 0
            ? s.elevators.reduce((sum, e) => sum + e.load_pct, 0) / s.elevators.length
            : 0;
        utilHistory.push(avgUtil);
        if (utilHistory.length > MAX_HISTORY) utilHistory.shift();
    }

    drawLineChart("chart-wait", waitHistory, s.metrics.sla_target, "#6366f1", "#22c55e");
    drawBarChart("chart-util", s.elevators);
}

function drawLineChart(canvasId, data, threshold, lineColor, thresholdColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    if (data.length < 2) return;

    const maxVal = Math.max(threshold * 1.5, ...data, 1);
    const xStep = W / (MAX_HISTORY - 1);

    // Threshold line
    const thY = H - (threshold / maxVal) * (H - 10) - 5;
    ctx.beginPath();
    ctx.strokeStyle = thresholdColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.moveTo(0, thY);
    ctx.lineTo(W, thY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Label
    ctx.fillStyle = thresholdColor;
    ctx.font = "9px JetBrains Mono";
    ctx.fillText(`SLA ${threshold}s`, W - 55, thY - 4);

    // Data line
    ctx.beginPath();
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    const offset = MAX_HISTORY - data.length;
    for (let i = 0; i < data.length; i++) {
        const x = (i + offset) * xStep;
        const y = H - (data[i] / maxVal) * (H - 10) - 5;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Gradient fill under line
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, lineColor + "40");
    grad.addColorStop(1, lineColor + "05");
    ctx.lineTo((data.length - 1 + offset) * xStep, H);
    ctx.lineTo(offset * xStep, H);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
}

function drawBarChart(canvasId, elevators) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    if (!elevators || elevators.length === 0) return;

    const n = elevators.length;
    const barW = Math.min(40, (W - 20) / n - 10);
    const gap = (W - n * barW) / (n + 1);
    const colors = ["#6366f1", "#06b6d4", "#f59e0b", "#ef4444"];

    for (let i = 0; i < n; i++) {
        const e = elevators[i];
        const x = gap + i * (barW + gap);
        const barH = (e.load_pct / 100) * (H - 30);

        // Bar
        const grad = ctx.createLinearGradient(x, H - 15, x, H - 15 - barH);
        grad.addColorStop(0, colors[i % 4] + "cc");
        grad.addColorStop(1, colors[i % 4] + "44");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, H - 15 - barH, barW, barH, 3);
        ctx.fill();

        // Glow
        ctx.shadowColor = colors[i % 4];
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Label
        ctx.fillStyle = "#94a3b8";
        ctx.font = "10px JetBrains Mono";
        ctx.textAlign = "center";
        ctx.fillText(`E${i}`, x + barW / 2, H - 3);

        // Value
        ctx.fillStyle = "#f1f5f9";
        ctx.font = "9px JetBrains Mono";
        ctx.fillText(`${Math.round(e.load_pct)}%`, x + barW / 2, H - 18 - barH);
    }
}

// ═══════════════════════════════════════════════════════════════
// Controls
// ═══════════════════════════════════════════════════════════════
function setupControls() {
    // Start button
    $("#btn-start").addEventListener("click", () => {
        fetch("/api/start", { method: "POST" });
    });

    // Pause button
    $("#btn-pause").addEventListener("click", () => {
        fetch("/api/pause", { method: "POST" });
    });

    // Reset button
    $("#btn-reset").addEventListener("click", () => {
        buildingRendered = false;
        waitHistory = [];
        utilHistory = [];
        const body = {
            strategy: $("#sel-strategy").value,
            scenario: $("#sel-scenario").value,
            seed: parseInt($("#inp-seed").value) || 42,
            speed: parseFloat($("#rng-speed").value) || 1.0,
        };
        fetch("/api/configure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    });

    // Strategy change
    $("#sel-strategy").addEventListener("change", () => {
        applyConfig();
    });

    // Scenario change
    $("#sel-scenario").addEventListener("change", () => {
        applyConfig();
    });

    // Speed slider
    $("#rng-speed").addEventListener("input", (e) => {
        const speed = parseFloat(e.target.value);
        $("#speed-label").textContent = `${speed}x`;
        fetch(`/api/speed?speed=${speed}`, { method: "POST" });
    });

    // Heatmap toggle
    $("#chk-heatmap").addEventListener("change", (e) => {
        heatmapEnabled = e.target.checked;
    });
}

function applyConfig() {
    buildingRendered = false;
    waitHistory = [];
    utilHistory = [];
    const body = {
        strategy: $("#sel-strategy").value,
        scenario: $("#sel-scenario").value,
        seed: parseInt($("#inp-seed").value) || 42,
        speed: parseFloat($("#rng-speed").value) || 1.0,
    };
    fetch("/api/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

// ═══════════════════════════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    setupControls();
    connect();
});
