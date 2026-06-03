const state = {
  design: window.__BPD_INITIAL__,
  currentStep: 0,
  playTimer: null,
};

const form = document.getElementById("design-form");
const routeTableBody = document.querySelector("#route-table tbody");
const summaryGrid = document.getElementById("summary-grid");
const warningBox = document.getElementById("warning-box");
const nodesPanel = document.getElementById("nodes-panel");
const stepList = document.getElementById("step-list");
const statusBadge = document.getElementById("status-badge");
const routeSchemeSelect = document.getElementById("route-scheme-select");

const topSvg = document.getElementById("top-view");
const frontSvg = document.getElementById("front-view");
const sideSvg = document.getElementById("side-view");
const explodedSvg = document.getElementById("exploded-view");
const canvas = document.getElementById("three-view");
const ctx = canvas.getContext("2d");

const viewBoxSize = { width: 760, height: 360 };

function render() {
  renderSummary();
  renderWarnings();
  renderRouteTable();
  renderNodeChips();
  renderSteps();
  renderTopView();
  renderFrontView();
  renderSideView();
  renderExplodedView();
  renderPseudo3D();
}

function renderSummary() {
  const metrics = state.design.metrics;
  const request = state.design.request;
  const selectedRoute = state.design.selected_route;
  const entries = [
    ["Model", state.design.cell_spec.model],
    ["Cells", `${metrics.used_cells}`],
    ["Topology", `${request.series_count}S${request.parallel_count}P`],
    ["Capacity", `${metrics.total_capacity_ah} Ah`],
    ["Voltage", `${metrics.total_voltage_v} V`],
    ["Energy", `${metrics.total_energy_wh} Wh`],
    ["Weight", `${metrics.total_weight_kg} kg`],
    ["Envelope", `${metrics.pack_width_mm} × ${metrics.pack_depth_mm} × ${metrics.pack_height_mm} mm`],
    ["Placement", `${request.placement_mode.toUpperCase()} / ${request.layers} layer(s)`],
    ["Route", selectedRoute.name],
    ["Difficulty", `${selectedRoute.difficulty} / 5`],
    ["Jump wires", `${state.design.jump_wires.length}`],
  ];
  summaryGrid.innerHTML = entries
    .map(
      ([label, value]) => `
        <div class="summary-item">
          <span class="subtle-copy">${label}</span>
          <strong>${value}</strong>
        </div>
      `
    )
    .join("");
}

function renderWarnings() {
  if (state.design.warnings.length) {
    warningBox.classList.remove("hidden");
    warningBox.innerHTML = state.design.warnings.map((warning) => `<div>${warning}</div>`).join("");
  } else {
    warningBox.classList.add("hidden");
    warningBox.innerHTML = "";
  }
}

function renderRouteTable() {
  const selectedKey = state.design.selected_route.key;
  routeTableBody.innerHTML = state.design.route_options
    .map((option) => {
      const selected = option.key === selectedKey ? "is-selected" : "";
      return `
        <tr class="${selected}" data-route-key="${option.key}">
          <td>${option.name}</td>
          <td>${option.difficulty}</td>
          <td>${option.jump_wire_count}</td>
          <td>${option.fold_count}</td>
          <td>${option.max_span_mm}</td>
          <td>${option.total_bus_length_mm}</td>
        </tr>
      `;
    })
    .join("");

  [...routeTableBody.querySelectorAll("tr")].forEach((row) => {
    row.addEventListener("click", () => {
      routeSchemeSelect.value = row.dataset.routeKey;
      submitForm();
    });
  });
}

function renderNodeChips() {
  const strips = state.design.tab_strips;
  const leads = state.design.balance_leads;
  const wires = state.design.jump_wires;

  const stripChips = strips.map(
    (strip) => `<span class="chip">${strip.node_label} / ${strip.side} / ${strip.cell_ids.length} cells</span>`
  );
  const leadChips = leads.map((lead) => `<span class="chip">${lead.label} lead @ (${lead.x_mm}, ${lead.y_mm})</span>`);
  const wireChips = wires.map((wire) => `<span class="chip">${wire.id} / ${wire.length_mm} mm</span>`);
  nodesPanel.innerHTML = [...stripChips, ...leadChips, ...wireChips].join("");
}

function renderSteps() {
  const activeIndex = state.currentStep;
  stepList.innerHTML = state.design.weld_steps
    .map(
      (step, index) => `
        <li class="${index === activeIndex ? "is-active" : ""}">
          <strong>${step.index}. ${step.title}</strong><br>
          <span class="subtle-copy">${step.description}</span>
        </li>
      `
    )
    .join("");
}

function getCellStyle(cell) {
  if (!cell.active) {
    return { fill: "rgba(99,120,134,0.12)", stroke: "rgba(99,120,134,0.35)" };
  }
  if (!cell.used) {
    return { fill: "rgba(99,120,134,0.18)", stroke: "rgba(99,120,134,0.45)" };
  }
  return {
    fill: cell.polarity_up ? "rgba(255,90,95,0.72)" : "rgba(63,125,255,0.74)",
    stroke: cell.polarity_up ? "#e14248" : "#2f67da",
  };
}

function computeBounds(cells) {
  const xs = cells.map((cell) => cell.x_mm);
  const ys = cells.map((cell) => cell.y_mm);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return { minX, maxX, minY, maxY };
}

function scalePoint(x, y, bounds, width, height, padding = 40) {
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const sx = padding + ((x - bounds.minX) / spanX) * usableWidth;
  const sy = padding + ((y - bounds.minY) / spanY) * usableHeight;
  return [sx, sy];
}

function currentHighlights() {
  const step = state.design.weld_steps[state.currentStep] ?? null;
  return {
    cells: new Set(step?.highlight_cell_ids ?? []),
    tabs: new Set(step?.highlight_tab_ids ?? []),
    wires: new Set(step?.highlight_wire_ids ?? []),
    leads: new Set(step?.highlight_balance_labels ?? []),
  };
}

function renderTopView() {
  const cells = state.design.cells.filter((cell) => cell.active || cell.used);
  const bounds = computeBounds(cells);
  const highlights = currentHighlights();
  const width = viewBoxSize.width;
  const height = viewBoxSize.height;
  const diameter = state.design.cell_spec.diameter_mm;
  topSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const cellMap = Object.fromEntries(cells.map((cell) => [cell.id, cell]));
  const strips = state.design.tab_strips.map((strip) => {
    const points = strip.cell_ids
      .map((cellId) => cellMap[cellId])
      .filter(Boolean)
      .map((cell) => scalePoint(cell.x_mm, cell.y_mm, bounds, width, height));
    if (!points.length) return "";
    const xs = points.map(([x]) => x);
    const ys = points.map(([, y]) => y);
    const pad = 18;
    const fill = highlights.tabs.has(strip.id) ? "rgba(255, 214, 133, 0.45)" : "rgba(13, 159, 139, 0.18)";
    return `<rect x="${Math.min(...xs) - pad}" y="${Math.min(...ys) - pad}" width="${Math.max(...xs) - Math.min(...xs) + pad * 2}" height="${Math.max(...ys) - Math.min(...ys) + pad * 2}" rx="18" fill="${fill}" stroke="rgba(13,159,139,0.32)" />`;
  });

  const wires = state.design.jump_wires.map((wire) => {
    const [x1, y1] = scalePoint(wire.from_x_mm, wire.from_y_mm, bounds, width, height);
    const [x2, y2] = scalePoint(wire.to_x_mm, wire.to_y_mm, bounds, width, height);
    const stroke = highlights.wires.has(wire.id) ? "#f59e0b" : "#9345d4";
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="4" stroke-dasharray="10 8" />`;
  });

  const leads = state.design.balance_leads.map((lead) => {
    const [x, y] = scalePoint(lead.x_mm, lead.y_mm, bounds, width, height);
    const radius = highlights.leads.has(lead.label) ? 10 : 7;
    return `<g><circle cx="${x}" cy="${y}" r="${radius}" fill="#32b66d" /><text x="${x + 10}" y="${y - 10}" font-size="12" fill="#266843">${lead.label}</text></g>`;
  });

  const cellR = Math.max(8, diameter);
  const scaleR = Math.min(28, Math.max(10, cellR / 1.1));
  const cellCircles = cells.map((cell) => {
    const [cx, cy] = scalePoint(cell.x_mm, cell.y_mm, bounds, width, height);
    const style = getCellStyle(cell);
    const strokeWidth = highlights.cells.has(cell.id) ? 5 : 2;
    return `<g>
      <circle cx="${cx}" cy="${cy}" r="${scaleR}" fill="${style.fill}" stroke="${style.stroke}" stroke-width="${strokeWidth}" />
      <text x="${cx}" y="${cy + 4}" text-anchor="middle" font-size="11" fill="#17323d">${cell.series_group ?? "-"}</text>
    </g>`;
  });

  topSvg.innerHTML = [...strips, ...wires, ...cellCircles, ...leads].join("");
}

function renderFrontView() {
  renderLinearProjection(frontSvg, "front");
}

function renderSideView() {
  renderLinearProjection(sideSvg, "side");
}

function renderExplodedView() {
  renderLinearProjection(explodedSvg, "exploded");
}

function renderLinearProjection(svg, mode) {
  const cells = state.design.cells.filter((cell) => cell.used);
  const highlights = currentHighlights();
  const width = viewBoxSize.width;
  const height = viewBoxSize.height;
  const spec = state.design.cell_spec;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const projected = cells.map((cell) => {
    const baseX = mode === "side" ? cell.y_mm : cell.x_mm;
    const layerOffset = mode === "exploded" ? (cell.layer - 1) * 34 : (cell.layer - 1) * 8;
    const x = baseX + layerOffset;
    const y = cell.z_mm;
    return { cell, x, y };
  });

  const bounds = {
    minX: Math.min(...projected.map((item) => item.x)),
    maxX: Math.max(...projected.map((item) => item.x)) + spec.diameter_mm,
    minY: 0,
    maxY: Math.max(...projected.map((item) => item.y)) + spec.height_mm,
  };

  const rects = projected.map(({ cell, x, y }) => {
    const [sx, sy] = scalePoint(x, y, bounds, width, height);
    const [sx2, sy2] = scalePoint(x + spec.diameter_mm, y + spec.height_mm, bounds, width, height);
    const style = getCellStyle(cell);
    const strokeWidth = highlights.cells.has(cell.id) ? 4 : 1.8;
    const positiveColor = cell.polarity_up ? "#ff5a5f" : "#3f7dff";
    const negativeColor = cell.polarity_up ? "#3f7dff" : "#ff5a5f";
    return `<g>
      <rect x="${sx}" y="${sy}" width="${sx2 - sx}" height="${sy2 - sy}" rx="14" fill="rgba(255,255,255,0.35)" stroke="${style.stroke}" stroke-width="${strokeWidth}" />
      <rect x="${sx}" y="${sy}" width="${sx2 - sx}" height="14" fill="${positiveColor}" opacity="0.85" />
      <rect x="${sx}" y="${sy2 - 14}" width="${sx2 - sx}" height="14" fill="${negativeColor}" opacity="0.82" />
      <text x="${sx + 8}" y="${sy + 26}" font-size="11" fill="#17323d">${cell.id}</text>
    </g>`;
  });

  svg.innerHTML = rects.join("");
}

function renderPseudo3D() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#f4f8fa";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const cells = state.design.cells.filter((cell) => cell.used);
  const spec = state.design.cell_spec;
  const highlights = currentHighlights();
  const iso = cells
    .map((cell) => ({
      cell,
      x: 130 + cell.x_mm * 3.2 - cell.y_mm * 1.1,
      y: 300 - cell.z_mm * 1.9 - cell.y_mm * 1.2,
    }))
    .sort((a, b) => a.cell.z_mm - b.cell.z_mm || a.cell.y_mm - b.cell.y_mm);

  for (const item of iso) {
    const { cell, x, y } = item;
    const height = Math.max(52, spec.height_mm * 0.82);
    const radius = Math.max(16, spec.diameter_mm * 0.95);
    const topColor = cell.polarity_up ? "rgba(255,90,95,0.82)" : "rgba(63,125,255,0.82)";
    const sideColor = cell.polarity_up ? "rgba(237,117,120,0.64)" : "rgba(95,143,255,0.64)";
    const activeGlow = highlights.cells.has(cell.id);

    ctx.save();
    if (activeGlow) {
      ctx.shadowColor = "rgba(245, 158, 11, 0.65)";
      ctx.shadowBlur = 18;
    }
    ctx.fillStyle = sideColor;
    ctx.beginPath();
    ctx.ellipse(x, y, radius, radius * 0.45, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillRect(x - radius, y - height, radius * 2, height);

    ctx.fillStyle = topColor;
    ctx.beginPath();
    ctx.ellipse(x, y - height, radius, radius * 0.45, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#17323d";
    ctx.font = "12px Segoe UI";
    ctx.fillText(cell.id, x - 14, y - height - 10);
    ctx.restore();
  }

  for (const wire of state.design.jump_wires) {
    const p1 = { x: 130 + wire.from_x_mm * 3.2 - wire.from_y_mm * 1.1, y: 300 - wire.from_z_mm * 1.9 - wire.from_y_mm * 1.2 - 90 };
    const p2 = { x: 130 + wire.to_x_mm * 3.2 - wire.to_y_mm * 1.1, y: 300 - wire.to_z_mm * 1.9 - wire.to_y_mm * 1.2 - 90 };
    ctx.save();
    ctx.strokeStyle = highlights.wires.has(wire.id) ? "#f59e0b" : "#9345d4";
    ctx.lineWidth = 4;
    ctx.setLineDash([10, 8]);
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
    ctx.restore();
  }
}

async function submitForm() {
  statusBadge.textContent = "Updating";
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  const response = await fetch("/api/design", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorText = await response.text();
    statusBadge.textContent = "Error";
    warningBox.classList.remove("hidden");
    warningBox.textContent = errorText;
    return;
  }
  state.design = await response.json();
  state.currentStep = 0;
  statusBadge.textContent = "Ready";
  render();
}

function moveStep(delta) {
  const total = state.design.weld_steps.length;
  state.currentStep = (state.currentStep + delta + total) % total;
  render();
}

function togglePlay() {
  const button = document.getElementById("play-step");
  if (state.playTimer) {
    clearInterval(state.playTimer);
    state.playTimer = null;
    button.textContent = "Play";
    return;
  }
  button.textContent = "Pause";
  state.playTimer = setInterval(() => moveStep(1), 1000);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm();
});

document.getElementById("prev-step").addEventListener("click", () => moveStep(-1));
document.getElementById("next-step").addEventListener("click", () => moveStep(1));
document.getElementById("play-step").addEventListener("click", () => togglePlay());

render();

