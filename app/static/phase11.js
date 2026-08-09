"use strict";

(() => {
  const ENGINE_ENDPOINTS = [
    ["Interface System", "/api/v2/interface/status", "Official white agri-tech design and interactive controls"],
    ["Weather Assimilation", "/api/v2/weather/status", "16-day live forecast and agricultural feature pipeline"],
    ["Production", "/api/v2/production/status", "Versioned ML baseline and named-variety adjustment"],
    ["Bayesian Simulation", "/api/v2/bayesian/status", "Particle-filter uncertainty and farm-state updating"],
    ["Pest Inference", "/api/v2/pests/status", "Pest-specific probability, spatial pressure, and loss"],
    ["Intercropping", "/api/v2/intercropping/status", "Cell-level light, crop compatibility, and economics"],
    ["Rehabilitation", "/api/v2/rehabilitation/status", "Budget-aware action and scenario optimization"],
    ["Decision Network", "/api/v2/decision-support/status", "Integrated traceable farm recommendations"],
    ["CoCO-PILOT", "/api/v2/coco-pilot/status", "Grounded explanation and formal report generation"],
    ["Data Foundation", "/api/v2/data-foundation/summary", "PCA references and privacy-isolated registry"],
    ["Model Registry", "/api/v2/models", "Versioned model artifacts and runtime compatibility"],
  ];

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`${response.status}`);
    return response.json();
  }

  function createCoconutMeshRenderer(element) {
    const canvas = element?.querySelector(".holo-coconut-mesh");
    if (!canvas) return { draw() {} };
    const context = canvas.getContext("2d", { alpha: true });
    if (!context) return { draw() {} };

    const makeModel = (name, scale) => ({ name, scale, segments: [], points: [] });
    const coconut = makeModel("coconut", .94);
    const tree = makeModel("tree", .82);
    const addPolyline = (model, points, family, weight = 1) => {
      for (let index = 1; index < points.length; index += 1) {
        model.segments.push({ a: points[index - 1], b: points[index], family, weight });
      }
    };
    const addPoint = (model, point, family, radius = 2.8) => model.points.push({ point, family, radius });

    const coconutPoint = (u, v) => {
      const vertical = Math.cos(u);
      const latitudeRadius = Math.sin(u);
      const lowerWeight = (1 - vertical) * .5;
      const shoulder = .955 + (.045 * lowerWeight);
      const ridge = 1 + (.030 * Math.cos(3 * v)) + (.010 * Math.cos(6 * v));
      const radius = latitudeRadius * shoulder * ridge;
      return {
        x: radius * Math.cos(v),
        y: (1.035 * vertical) - (.025 * lowerWeight) + (.014 * Math.cos(2 * v) * latitudeRadius),
        z: radius * Math.sin(v),
      };
    };

    const longitudeCount = 18;
    for (let longitude = 0; longitude < longitudeCount; longitude += 1) {
      const v = (longitude / longitudeCount) * Math.PI * 2;
      const points = [];
      for (let sample = 0; sample <= 30; sample += 1) points.push(coconutPoint((sample / 30) * Math.PI, v));
      addPolyline(coconut, points, "longitude", 1);
    }
    for (let latitude = 1; latitude < 12; latitude += 1) {
      const u = (latitude / 12) * Math.PI;
      const points = [];
      for (let sample = 0; sample <= 44; sample += 1) points.push(coconutPoint(u, (sample / 44) * Math.PI * 2));
      addPolyline(coconut, points, "latitude", .92);
    }
    for (let seam = 0; seam < 3; seam += 1) {
      const v = (seam / 3) * Math.PI * 2;
      const points = [];
      for (let sample = 0; sample <= 36; sample += 1) {
        const p = coconutPoint((sample / 36) * Math.PI, v);
        const push = .018 * Math.sin((sample / 36) * Math.PI);
        points.push({ x: p.x * (1 + push), y: p.y, z: p.z * (1 + push) });
      }
      addPolyline(coconut, points, "seam", 1.35);
    }
    const stem = [];
    for (let index = 0; index <= 18; index += 1) {
      const t = index / 18;
      stem.push({ x: .02 + (.055 * Math.sin(t * Math.PI)), y: 1.13 + (t * .28), z: .01 - (t * .035) });
    }
    addPolyline(coconut, stem, "stem", 1.7);
    [
      { x: -.12, y: 1.015, z: .205 },
      { x: .12, y: 1.015, z: .205 },
      { x: 0, y: .91, z: .29 },
    ].forEach((point) => addPoint(coconut, point, "eye", 3.1));

    const trunkCenter = (t) => ({
      x: -.06 + (.10 * Math.sin(t * 1.6)),
      y: -1.18 + (t * 1.62),
      z: .035 * Math.sin(t * 2.3),
    });
    for (let side = 0; side < 10; side += 1) {
      const angle = (side / 10) * Math.PI * 2;
      const points = [];
      for (let sample = 0; sample <= 22; sample += 1) {
        const t = sample / 22;
        const center = trunkCenter(t);
        const radius = .17 - (.075 * t) + (.012 * Math.sin(t * Math.PI * 5));
        points.push({ x: center.x + (Math.cos(angle) * radius), y: center.y, z: center.z + (Math.sin(angle) * radius) });
      }
      addPolyline(tree, points, "trunk-longitude", 1.35);
    }
    for (let ring = 0; ring <= 10; ring += 1) {
      const t = ring / 10;
      const center = trunkCenter(t);
      const radius = .17 - (.075 * t) + (.012 * Math.sin(t * Math.PI * 5));
      const points = [];
      for (let sample = 0; sample <= 28; sample += 1) {
        const angle = (sample / 28) * Math.PI * 2;
        points.push({ x: center.x + (Math.cos(angle) * radius), y: center.y, z: center.z + (Math.sin(angle) * radius) });
      }
      addPolyline(tree, points, "trunk-ring", 1.05);
    }

    const crown = trunkCenter(1);
    const frondCount = 14;
    for (let frond = 0; frond < frondCount; frond += 1) {
      const angle = (frond / frondCount) * Math.PI * 2;
      const length = 1.04 + (.16 * Math.sin(frond * 1.7));
      const lift = .18 + (.11 * ((frond % 3) / 2));
      const centerline = [];
      for (let sample = 0; sample <= 22; sample += 1) {
        const t = sample / 22;
        const radial = length * Math.sin(t * Math.PI * .5);
        const sway = .055 * Math.sin(t * Math.PI * 2 + frond);
        centerline.push({
          x: crown.x + (Math.cos(angle) * radial) + (Math.cos(angle + Math.PI / 2) * sway),
          y: crown.y + (lift * Math.sin(t * Math.PI)) - (.48 * t * t),
          z: crown.z + (Math.sin(angle) * radial) + (Math.sin(angle + Math.PI / 2) * sway),
        });
      }
      addPolyline(tree, centerline, "frond", 1.55);
      for (let sample = 4; sample <= 18; sample += 3) {
        const t = sample / 22;
        const center = centerline[sample];
        const leafletLength = .20 * (1 - (.55 * t));
        const sideX = Math.cos(angle + Math.PI / 2);
        const sideZ = Math.sin(angle + Math.PI / 2);
        addPolyline(tree, [
          center,
          { x: center.x + (sideX * leafletLength), y: center.y - (.035 + .04 * t), z: center.z + (sideZ * leafletLength) },
        ], "leaflet", .85);
        addPolyline(tree, [
          center,
          { x: center.x - (sideX * leafletLength), y: center.y - (.035 + .04 * t), z: center.z - (sideZ * leafletLength) },
        ], "leaflet", .85);
      }
    }

    const addWireSphere = (model, center, radius) => {
      for (let axis = 0; axis < 3; axis += 1) {
        const points = [];
        for (let sample = 0; sample <= 18; sample += 1) {
          const angle = (sample / 18) * Math.PI * 2;
          const c = Math.cos(angle) * radius;
          const d = Math.sin(angle) * radius;
          if (axis === 0) points.push({ x: center.x, y: center.y + c, z: center.z + d });
          if (axis === 1) points.push({ x: center.x + c, y: center.y, z: center.z + d });
          if (axis === 2) points.push({ x: center.x + c, y: center.y + d, z: center.z });
        }
        addPolyline(model, points, "tree-fruit", 1.2);
      }
    };
    [
      { x: crown.x - .16, y: crown.y - .03, z: crown.z + .10 },
      { x: crown.x + .12, y: crown.y - .08, z: crown.z + .14 },
      { x: crown.x + .03, y: crown.y - .15, z: crown.z - .13 },
      { x: crown.x - .12, y: crown.y - .12, z: crown.z - .08 },
    ].forEach((center) => addWireSphere(tree, center, .095));
    addPoint(tree, crown, "crown", 3.0);

    let cssWidth = 0;
    let cssHeight = 0;
    let deviceScale = 1;
    const startedAt = Date.now();
    const HOLD_MS = 5000;
    const TRANSITION_MS = 1250;
    const PHASE_MS = HOLD_MS + TRANSITION_MS;

    const syncCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const nextWidth = Math.max(1, Math.round(rect.width));
      const nextHeight = Math.max(1, Math.round(rect.height));
      const nextScale = Math.min(2, window.devicePixelRatio || 1);
      if (nextWidth === cssWidth && nextHeight === cssHeight && nextScale === deviceScale) return;
      cssWidth = nextWidth;
      cssHeight = nextHeight;
      deviceScale = nextScale;
      canvas.width = Math.round(cssWidth * deviceScale);
      canvas.height = Math.round(cssHeight * deviceScale);
      context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
    };

    const rotate = (point, pitch, yaw) => {
      const cosY = Math.cos(yaw);
      const sinY = Math.sin(yaw);
      const xYaw = (point.x * cosY) + (point.z * sinY);
      const zYaw = (-point.x * sinY) + (point.z * cosY);
      const cosX = Math.cos(pitch);
      const sinX = Math.sin(pitch);
      return {
        x: xYaw,
        y: (point.y * cosX) - (zYaw * sinX),
        z: (point.y * sinX) + (zYaw * cosX),
      };
    };

    const project = (point, pitch, yaw, modelScale = 1) => {
      const rotated = rotate(point, pitch, yaw);
      const camera = 5.0;
      const perspective = camera / (camera - rotated.z);
      const scale = Math.min(cssWidth, cssHeight) * .292 * modelScale;
      return {
        x: (cssWidth * .5) + (rotated.x * scale * perspective),
        y: (cssHeight * .505) - (rotated.y * scale * perspective),
        z: rotated.z,
        perspective,
      };
    };

    const lineWeight = (segment, front) => {
      const family = segment.family;
      if (family === "stem") return 3.2;
      if (family === "seam") return 2.55;
      if (family === "trunk-longitude") return 2.15 + (front * .8);
      if (family === "trunk-ring") return 1.45 + (front * .65);
      if (family === "frond") return 2.0 + (front * .8);
      if (family === "leaflet") return 1.05 + (front * .45);
      if (family === "tree-fruit") return 1.45 + (front * .5);
      return 1.28 + (front * 1.4);
    };

    const drawModel = (model, pitch, yaw, alpha, scaleFactor, blurAmount) => {
      if (alpha <= .005) return;
      const modelScale = model.scale * scaleFactor;
      const depthBuckets = Array.from({ length: 18 }, () => []);
      for (const segment of model.segments) {
        const a = project(segment.a, pitch, yaw, modelScale);
        const b = project(segment.b, pitch, yaw, modelScale);
        const depth = (a.z + b.z) * .5;
        const front = Math.max(0, Math.min(1, (depth + 1.45) / 2.9));
        const width = lineWeight(segment, front) * segment.weight;
        const widthClass = width >= 2.55 ? 2 : width >= 1.65 ? 1 : 0;
        const depthClass = Math.max(0, Math.min(5, Math.floor(front * 5.999)));
        depthBuckets[(depthClass * 3) + widthClass].push({ a, b });
      }

      context.save();
      context.globalAlpha = alpha;
      context.filter = blurAmount > .02 ? `blur(${blurAmount}px)` : "none";
      context.lineCap = "round";
      context.lineJoin = "round";
      for (let bucketIndex = 0; bucketIndex < depthBuckets.length; bucketIndex += 1) {
        const bucket = depthBuckets[bucketIndex];
        if (!bucket.length) continue;
        const depthClass = Math.floor(bucketIndex / 3);
        const widthClass = bucketIndex % 3;
        const front = depthClass / 5;
        const widths = [1.2, 1.9, 2.9];
        context.strokeStyle = `rgba(255,255,255,${.56 + (front * .44)})`;
        context.lineWidth = widths[widthClass] * (.92 + (front * .22));
        context.shadowColor = front > .35 ? "rgba(255,255,255,.92)" : "rgba(224,255,235,.48)";
        context.shadowBlur = front > .58 ? 9 : 4;
        context.beginPath();
        for (const line of bucket) {
          context.moveTo(line.a.x, line.a.y);
          context.lineTo(line.b.x, line.b.y);
        }
        context.stroke();
      }
      context.filter = "none";
      for (const item of model.points) {
        const projectedPoint = project(item.point, pitch, yaw, modelScale);
        if (projectedPoint.z < -.32) continue;
        context.fillStyle = "rgba(255,255,255,.98)";
        context.shadowColor = "rgba(255,255,255,.96)";
        context.shadowBlur = 14;
        context.beginPath();
        context.arc(projectedPoint.x, projectedPoint.y, item.radius + (projectedPoint.perspective * .8), 0, Math.PI * 2);
        context.fill();
      }
      context.restore();
    };

    const draw = (rotationX, rotationY, time = Date.now()) => {
      syncCanvas();
      if (cssWidth < 2 || cssHeight < 2) return;
      context.clearRect(0, 0, cssWidth, cssHeight);
      const pitch = rotationX * Math.PI / 180;
      const yaw = rotationY * Math.PI / 180;
      const forcedElapsed = Number(element.dataset.hologramElapsedMs);
      const startOffset = Number(element.dataset.hologramStartOffsetMs);
      const naturalElapsed = Math.max(0, time - startedAt) + (Number.isFinite(startOffset) ? Math.max(0, startOffset) : 0);
      const elapsed = Number.isFinite(forcedElapsed) ? Math.max(0, forcedElapsed) : naturalElapsed;
      const phaseIndex = Math.floor(elapsed / PHASE_MS);
      const localTime = elapsed % PHASE_MS;
      const current = phaseIndex % 2 === 0 ? coconut : tree;
      const next = current === coconut ? tree : coconut;
      const transitioning = localTime >= HOLD_MS;
      const linear = transitioning ? Math.min(1, (localTime - HOLD_MS) / TRANSITION_MS) : 0;
      const eased = linear * linear * (3 - (2 * linear));
      const pulse = Math.sin(eased * Math.PI);
      element.dataset.hologramForm = transitioning ? `${current.name}-to-${next.name}` : current.name;

      const glow = context.createRadialGradient(
        cssWidth * .5, cssHeight * .49, 5,
        cssWidth * .5, cssHeight * .49, Math.min(cssWidth, cssHeight) * .42,
      );
      glow.addColorStop(0, `rgba(255,255,255,${.25 + (.14 * pulse)})`);
      glow.addColorStop(.38, "rgba(223,255,232,.13)");
      glow.addColorStop(.76, "rgba(198,255,216,.045)");
      glow.addColorStop(1, "rgba(255,255,255,0)");
      context.fillStyle = glow;
      context.beginPath();
      context.arc(cssWidth * .5, cssHeight * .49, Math.min(cssWidth, cssHeight) * .43, 0, Math.PI * 2);
      context.fill();

      if (!transitioning) {
        drawModel(current, pitch, yaw, 1, 1, 0);
      } else {
        drawModel(current, pitch, yaw, 1 - eased, 1 + (.07 * eased), 1.8 * eased);
        drawModel(next, pitch, yaw, eased, .90 + (.10 * eased), 1.8 * (1 - eased));
        context.save();
        context.globalAlpha = .72 * pulse;
        context.strokeStyle = "#ffffff";
        context.lineWidth = 2.2;
        context.shadowColor = "rgba(255,255,255,.95)";
        context.shadowBlur = 16;
        context.beginPath();
        context.ellipse(cssWidth * .5, cssHeight * .5, Math.min(cssWidth, cssHeight) * (.18 + (.20 * eased)), Math.min(cssWidth, cssHeight) * (.05 + (.06 * eased)), 0, 0, Math.PI * 2);
        context.stroke();
        context.restore();
      }
    };

    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(() => draw(-7, 0, Date.now())) : null;
    observer?.observe(canvas);
    return { draw };
  }

  function initializeHologram(element) {
    if (!element || element.dataset.phase11Ready === "true") return;
    element.dataset.phase11Ready = "true";
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let rotationX = -7;
    let rotationY = Number(element.dataset.rotation || 0);
    let velocityX = 0;
    let velocityY = .03;
    let lastTime = performance.now();
    let lastRenderTime = 0;
    const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const meshRenderer = createCoconutMeshRenderer(element);

    const apply = (time = Date.now()) => {
      rotationX = Math.max(-35, Math.min(35, rotationX));
      element.style.setProperty("--holo-x", `${rotationX}deg`);
      element.style.setProperty("--holo-y", `${rotationY}deg`);
      element.dataset.rotation = String(rotationY);
      meshRenderer.draw(rotationX, rotationY, time);
    };

    element.addEventListener("pointerdown", (event) => {
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      velocityX = 0;
      velocityY = 0;
      element.setPointerCapture?.(event.pointerId);
    });
    element.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      rotationY += dx * .34;
      rotationX -= dy * .23;
      velocityY = dx * .026;
      velocityX = -dy * .018;
      lastX = event.clientX;
      lastY = event.clientY;
      apply();
    });
    const release = () => { dragging = false; };
    element.addEventListener("pointerup", release);
    element.addEventListener("pointercancel", release);
    element.addEventListener("keydown", (event) => {
      const step = event.shiftKey ? 12 : 5;
      if (event.key === "ArrowLeft") rotationY -= step;
      else if (event.key === "ArrowRight") rotationY += step;
      else if (event.key === "ArrowUp") rotationX -= step;
      else if (event.key === "ArrowDown") rotationX += step;
      else return;
      event.preventDefault();
      apply();
    });

    const animate = (time) => {
      const delta = Math.min(40, time - lastTime);
      lastTime = time;
      if (!dragging && !reducedMotion) {
        rotationY += (.01 * delta) + velocityY;
        rotationX += velocityX;
        velocityY *= .965;
        velocityX *= .94;
        rotationX += (-7 - rotationX) * .004 * delta;
        element.style.setProperty("--holo-depth-shift", `${Math.sin(rotationY / 36) * 10}px`);
      }
      if (dragging || time - lastRenderTime >= 55) {
        apply(Date.now());
        lastRenderTime = time;
      }
      requestAnimationFrame(animate);
    };
    apply();
    requestAnimationFrame(animate);
  }

  function chartFor(canvas) {
    return window.Chart?.getChart?.(canvas) || null;
  }

  function downloadChartPng(canvas) {
    const chart = chartFor(canvas);
    if (!chart) return;
    const link = document.createElement("a");
    link.download = `${canvas.id || "cocoaid-chart"}.png`;
    link.href = chart.toBase64Image("image/png", 1);
    link.click();
  }

  function exportChartCsv(canvas) {
    const chart = chartFor(canvas);
    if (!chart) return;
    const labels = chart.data.labels || [];
    const datasets = chart.data.datasets || [];
    const rows = [["Label", ...datasets.map((item) => item.label || "Series")]];
    labels.forEach((label, index) => {
      rows.push([label, ...datasets.map((item) => {
        const value = item.data?.[index];
        return typeof value === "object" && value !== null ? (value.y ?? value.x ?? "") : (value ?? "");
      })]);
    });
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.download = `${canvas.id || "cocoaid-chart"}.csv`;
    link.href = URL.createObjectURL(blob);
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function addChartToolbars() {
    document.querySelectorAll(".chart-panel canvas").forEach((canvas) => {
      const panel = canvas.closest(".chart-panel");
      const head = panel?.querySelector(".panel-head");
      if (!panel || !head || head.querySelector(".phase11-chart-tools")) return;
      const existingReset = head.querySelector(".chart-reset");
      if (existingReset) existingReset.hidden = true;
      const tools = document.createElement("div");
      tools.className = "phase11-chart-tools";
      tools.setAttribute("aria-label", "Chart controls");
      tools.innerHTML = `
        <button type="button" title="Zoom in" aria-label="Zoom chart in">+</button>
        <button type="button" title="Zoom out" aria-label="Zoom chart out">−</button>
        <button type="button" title="Reset view" aria-label="Reset chart view">↺</button>
        <button type="button" title="Download PNG" aria-label="Download chart as PNG">⇩</button>
        <button type="button" title="Export CSV" aria-label="Export chart data as CSV">CSV</button>
        <button type="button" title="Full screen" aria-label="Toggle chart full screen">⛶</button>`;
      const buttons = tools.querySelectorAll("button");
      buttons[0].addEventListener("click", () => chartFor(canvas)?.zoom?.(1.2));
      buttons[1].addEventListener("click", () => chartFor(canvas)?.zoom?.(.82));
      buttons[2].addEventListener("click", () => {
        const chart = chartFor(canvas);
        chart?.resetZoom?.();
        existingReset?.click();
      });
      buttons[3].addEventListener("click", () => downloadChartPng(canvas));
      buttons[4].addEventListener("click", () => exportChartCsv(canvas));
      buttons[5].addEventListener("click", () => {
        panel.classList.toggle("phase11-chart-fullscreen");
        document.body.style.overflow = panel.classList.contains("phase11-chart-fullscreen") ? "hidden" : "";
        setTimeout(() => chartFor(canvas)?.resize?.(), 80);
      });
      head.appendChild(tools);
    });
  }

  function normalizeStatus(payload) {
    const engine = payload.engine || payload;
    const available = engine.availability || payload.status || (payload.runtime?.compatible === false ? "warning" : "available");
    return {
      status: available,
      version: engine.version || engine.engine_version || payload.feature_adapter_version || payload.contract_api_version || payload.catalog_version || "versioned",
    };
  }

  async function refreshEngineGrid() {
    const grid = document.getElementById("phase11EngineGrid");
    if (!grid) return;
    grid.innerHTML = ENGINE_ENDPOINTS.map(([name, , description]) => `
      <article class="phase11-engine-card" data-engine-name="${escapeHtml(name)}">
        <header><span class="engine-code">V3 MODULE</span><i class="engine-status-dot"></i></header>
        <h3>${escapeHtml(name)}</h3><p>${escapeHtml(description)}</p>
      </article>`).join("");
    await Promise.all(ENGINE_ENDPOINTS.map(async ([name, endpoint]) => {
      const card = [...grid.children].find((node) => node.dataset.engineName === name);
      try {
        const payload = await fetchJson(endpoint);
        const result = normalizeStatus(payload);
        card?.querySelector(".engine-status-dot")?.classList.add("ok");
        const code = card?.querySelector(".engine-code");
        if (code) code.textContent = String(result.version).toUpperCase().slice(0, 25);
      } catch {
        card?.querySelector(".engine-status-dot")?.classList.add("warn");
        const code = card?.querySelector(".engine-code");
        if (code) code.textContent = "OFFLINE CHECK";
      }
    }));
  }

  function formatValue(value) {
    if (value === null || value === undefined || value === "") return "Not available";
    if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 3 });
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return String(value).replaceAll("_", " ");
  }

  async function refreshIntelligence() {
    const status = document.getElementById("intelligenceStatus");
    const recent = document.getElementById("intelligenceRecentRun");
    const reports = document.getElementById("intelligenceReports");
    if (!status) return;
    status.innerHTML = '<div class="phase11-data-row"><span>Loading integrated system status</span><strong>…</strong></div>';
    const requests = await Promise.allSettled([
      fetchJson("/api/v2/decision-support/status"),
      fetchJson("/api/v2/decision-support/runs?limit=1"),
      fetchJson("/api/v2/formal-reports?limit=5"),
      fetchJson("/api/v2/health"),
    ]);
    const decision = requests[0].status === "fulfilled" ? requests[0].value : {};
    const latest = requests[1].status === "fulfilled" ? (requests[1].value.runs || [])[0] : null;
    const reportList = requests[2].status === "fulfilled" ? requests[2].value.reports || [] : [];
    const health = requests[3].status === "fulfilled" ? requests[3].value : {};
    const engine = decision.engine || decision;
    status.innerHTML = [
      ["Decision network", engine.availability || "Unavailable"],
      ["Engine version", engine.version || "—"],
      ["Contract", health.contract_api_version || "—"],
      ["Model runtime", health.model_runtime?.compatible === false ? "Compatibility check required" : "Compatible"],
      ["Failure policy", (decision.failure_policies || ["continue_optional", "strict"]).join(" / ")],
    ].map(([label, value]) => `<div class="phase11-data-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(formatValue(value))}</strong></div>`).join("");

    if (recent) {
      recent.innerHTML = latest ? [
        ["Analysis run", latest.analysis_run_id || latest.id],
        ["Status", latest.status],
        ["Generated", latest.generated_at || latest.created_at],
        ["Completeness", latest.overview?.data_completeness != null ? `${Math.round(latest.overview.data_completeness * 100)}%` : "Not available"],
        ["Recommendations", latest.recommendations?.length ?? latest.recommendation_count ?? "Not available"],
      ].map(([label, value]) => `<div class="phase11-data-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(formatValue(value))}</strong></div>`).join("") : '<div class="phase11-data-row"><span>No integrated run has been saved yet.</span><strong>Run Phase 9 workflow</strong></div>';
    }
    if (reports) {
      reports.innerHTML = reportList.length ? reportList.map((item) => `<div class="phase11-data-row"><span>${escapeHtml(item.filename || item.report_format || "Report")}</span><strong>${escapeHtml(String(item.report_format || "").toUpperCase())}</strong></div>`).join("") : '<div class="phase11-data-row"><span>No formal report has been generated.</span><strong>Phase 10 ready</strong></div>';
    }
  }

  function applyChartDefaults() {
    if (!window.Chart) return;
    Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
    Chart.defaults.font.size = 11;
    Chart.defaults.color = "#627068";
    Chart.defaults.borderColor = "rgba(53, 83, 57, .13)";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 7;
  }

  function syncDedicatedWeatherFrame() {
    const primary = document.getElementById("weatherViewerFrame");
    const dedicated = document.getElementById("weatherDedicatedFrame");
    const forecast = document.getElementById("forecastWeatherViewerFrame");
    [dedicated, forecast].filter(Boolean).forEach((frame) => frame.addEventListener("load", () => {
      try {
        frame.contentWindow.postMessage({ type: "COCO_AID_THEME", theme: "light" }, location.origin);
      } catch {}
    }, { once: true }));
    if (!primary) return;
  }

  function enhanceAccessibility() {
    document.querySelectorAll("button:not([aria-label])").forEach((button) => {
      const text = button.textContent.trim();
      if (text) button.setAttribute("aria-label", text);
    });
    document.querySelectorAll("canvas").forEach((canvas) => {
      if (!canvas.getAttribute("role")) canvas.setAttribute("role", "img");
      if (!canvas.getAttribute("aria-label")) {
        const heading = canvas.closest(".panel")?.querySelector("h3, h2")?.textContent?.trim();
        canvas.setAttribute("aria-label", heading ? `${heading} interactive chart` : "Interactive COCOAID chart");
      }
    });
  }

  function observeNewCharts() {
    const observer = new MutationObserver(() => {
      addChartToolbars();
      enhanceAccessibility();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }


  function setupFarmerProfileGuide() {
    const farmPage = document.getElementById("farm-setup");
    if (!farmPage) return;
    const steps = ["identity", "trees", "soil", "symptoms"];
    const tabs = new Map([...farmPage.querySelectorAll(".subtab[data-form-tab]")].map((tab) => [tab.dataset.formTab, tab]));
    const panels = new Map([...farmPage.querySelectorAll(".form-tab[data-form-panel]")].map((panel) => [panel.dataset.formPanel, panel]));
    const guideTitle = document.getElementById("farmGuideTitle");
    const guideMessage = document.getElementById("farmGuideMessage");
    const progressBar = document.getElementById("farmGuideProgressBar");
    const completionHint = document.getElementById("farmCompletionHint");
    const polygonInfo = document.getElementById("polygonInfo");
    const farmMap = document.getElementById("farmMap");
    const boundarySuccess = document.getElementById("farmBoundarySuccess");
    const mapLiveGuide = document.getElementById("farmMapLiveGuide");
    const touchedIdentity = new Set();
    let activeStep = "identity";
    let identityAutoAdvanced = false;
    let boundaryAutoAdvanced = false;
    const formPanel = farmPage.querySelector(".farmer-guided-form");
    const mapPanel = farmPage.querySelector(".farmer-map-panel");
    const summaryText = document.getElementById("farmBoundarySummaryText");
    const startForecastButton = document.getElementById("startForecastButton");

    const value = (id) => document.getElementById(id)?.value?.trim() || "";
    const hasBoundary = () => Boolean(polygonInfo && !/^No polygon drawn/i.test(polygonInfo.textContent.trim()));
    const dispatchInput = (element) => {
      if (!element) return;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const stepCopy = {
      identity: ["Now add the basic farm details", "Only the farm name and location are needed here. When those are complete, the tree questions open automatically."],
      trees: ["Next, describe the coconut trees", "Count what you know. Use the Easy Tree Estimate if exact tree groups are difficult to count."],
      soil: ["Next, describe the soil and farm care", "Choose simple descriptions for slope, fertility, and drainage. Exact technical values remain optional."],
      symptoms: ["Last, tell us what you can see on the trees", "Tick only what you can actually see. It is completely fine to report no visible problems."],
    };

    const isCompleted = (step) => tabs.get(step)?.dataset.completed === "true";
    const positiveNumber = (id) => Number(document.getElementById(id)?.value) > 0;
    const nonNegativeNumber = (id) => Number(document.getElementById(id)?.value) >= 0;
    function announceStepProblem(title, message, focusId) {
      if (guideTitle) guideTitle.textContent = title;
      if (guideMessage) guideMessage.textContent = message;
      const target = document.getElementById(focusId);
      target?.focus?.({ preventScroll: true });
      target?.scrollIntoView?.({ behavior: "smooth", block: "center" });
      return false;
    }
    function identityReady() {
      if (!value("farmName")) return announceStepProblem("Give the farm a name", "Type a simple name so you can recognize this farm later.", "farmName");
      if (!value("municipality")) return announceStepProblem("Add the municipality or city", "This connects the farm to the correct local reference and weather context.", "municipality");
      if (!value("barangay")) return announceStepProblem("Add the barangay", "The barangay helps keep the farm location clear and easy to identify.", "barangay");
      return true;
    }
    function treesReady() {
      const total = ["youngTrees","productiveTrees","agingTrees","stressedTrees","infestedTrees","recoveringTrees","deadTrees"].reduce((sum,id) => sum + Math.max(0, Number(document.getElementById(id)?.value) || 0), 0);
      if (total <= 0) return announceStepProblem("Add at least one coconut palm", "Enter the tree counts you know, or use the Easy Tree Estimate above.", "farmerTreeCount");
      if (!positiveNumber("averageAge")) return announceStepProblem("Add the average tree age", "A rough age in years is enough for the model.", "averageAge");
      if (!nonNegativeNumber("annualProduction")) return announceStepProblem("Check annual production", "Enter the farm's usual annual production, or keep a reasonable non-negative estimate.", "annualProduction");
      if (!nonNegativeNumber("yieldPerHa")) return announceStepProblem("Check yield per hectare", "Enter a non-negative yield estimate before continuing.", "yieldPerHa");
      return true;
    }
    function soilReady() {
      if (!value("farmerSlopeChoice")) return announceStepProblem("Choose how steep the farm is", "Pick the plain-language option that looks closest to your farm.", "farmerSlopeChoice");
      if (!value("farmerDrainageChoice")) return announceStepProblem("Choose how water drains", "Think about what happens after heavy rain and pick the closest answer.", "farmerDrainageChoice");
      if (!value("farmerFertilityChoice")) return announceStepProblem("Choose the soil fertility", "A simple Poor, Fair, Good, or Very good estimate is enough when there is no soil test.", "farmerFertilityChoice");
      return true;
    }
    function updateForecastGate() {
      const ready = hasBoundary() && steps.every(isCompleted);
      if (startForecastButton) {
        startForecastButton.disabled = !ready;
        startForecastButton.setAttribute("aria-disabled", String(!ready));
        startForecastButton.textContent = ready ? "Start Forecast →" : "Complete Farm Setup First";
        startForecastButton.classList.toggle("is-ready", ready);
      }
      if (completionHint) completionHint.textContent = ready
        ? "Everything required is complete. You can now start the forecast."
        : "Complete the current guided step. The forecast unlocks only when the whole farm setup is finished.";
      return ready;
    }

    function setStep(step, { scroll = false, announce = true } = {}) {
      if (!tabs.has(step) || !panels.has(step)) return;
      activeStep = step;
      tabs.forEach((tab, name) => tab.classList.toggle("active", name === step));
      panels.forEach((panel, name) => panel.classList.toggle("active", name === step));
      const index = steps.indexOf(step);
      tabs.forEach((tab, name) => {
        const position = steps.indexOf(name);
        tab.classList.toggle("is-complete", position < index || tab.dataset.completed === "true");
        tab.setAttribute("aria-selected", String(name === step));
      });
      if (progressBar) progressBar.style.width = `${35 + (index * 20)}%`;
      if (guideTitle) guideTitle.textContent = stepCopy[step][0];
      if (guideMessage) guideMessage.textContent = stepCopy[step][1];
      if (announce) farmPage.dataset.guideStep = step;
      setTimeout(() => window.dispatchEvent(new Event("resize")), 80);
      if (scroll) farmPage.querySelector(".farm-guide-banner")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function showBoundaryStage({ scroll = false } = {}) {
      farmPage.dataset.workflowStage = "boundary";
      if (guideTitle) guideTitle.textContent = "First, mark the farm boundary";
      if (guideMessage) guideMessage.textContent = "Choose Polygon for most farms or Square for a rectangular farm. Finish the orange shape and the next questions will open automatically.";
      if (progressBar) progressBar.style.width = "18%";
      setTimeout(() => { window.dispatchEvent(new Event("resize")); window.state?.maps?.farm?.invalidateSize?.(); }, 80);
      if (scroll) farmPage.querySelector(".farm-guide-banner")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    function showDataStage(step = "identity", { scroll = true } = {}) {
      farmPage.dataset.workflowStage = "details";
      setStep(step, { scroll, announce: true });
      setTimeout(() => window.dispatchEvent(new Event("resize")), 80);
    }
    document.getElementById("returnToFarmMapButton")?.addEventListener("click", () => {
      boundaryAutoAdvanced = false;
      showBoundaryStage({ scroll: true });
    });

    // Future tabs remain hidden from the farmer; navigation is sequential through the guide buttons.
    tabs.forEach((tab) => { tab.tabIndex = -1; tab.setAttribute("aria-hidden", "true"); });
    farmPage.querySelectorAll("[data-farm-back]").forEach((button) => button.addEventListener("click", () => setStep(button.dataset.farmBack, { scroll: true })));
    document.getElementById("identityContinueButton")?.addEventListener("click", () => {
      if (!identityReady()) return;
      tabs.get("identity")?.setAttribute("data-completed", "true");
      updateForecastGate();
      setStep("trees", { scroll: true });
    });
    document.getElementById("treeContinueButton")?.addEventListener("click", () => {
      if (!treesReady()) return;
      tabs.get("trees")?.setAttribute("data-completed", "true");
      updateForecastGate();
      setStep("soil", { scroll: true });
    });
    document.getElementById("soilContinueButton")?.addEventListener("click", () => {
      if (!soilReady()) return;
      tabs.get("soil")?.setAttribute("data-completed", "true");
      updateForecastGate();
      setStep("symptoms", { scroll: true });
    });
    document.getElementById("healthContinueButton")?.addEventListener("click", () => {
      tabs.get("symptoms")?.setAttribute("data-completed", "true");
      if (hasBoundary()) {
        guideTitle.textContent = "Farm profile ready";
        guideMessage.textContent = "All required farm details are complete. The Start Forecast button is now unlocked.";
        if (progressBar) progressBar.style.width = "100%";
        updateForecastGate();
        startForecastButton?.scrollIntoView?.({ behavior: "smooth", block: "center" });
      } else {
        guideTitle.textContent = "One last thing: draw the farm boundary";
        guideMessage.textContent = "Use the large Polygon or Square button on the map. When the orange farm shape appears, your profile is ready.";
        updateForecastGate();
        showBoundaryStage({ scroll: true });
      }
    });

    // Auto-advance after the farmer has actually interacted with all key identity fields.
    ["farmName", "municipality", "barangay"].forEach((id) => {
      const input = document.getElementById(id);
      ["input", "change"].forEach((eventName) => input?.addEventListener(eventName, () => {
        touchedIdentity.add(id);
        const ready = ["farmName", "municipality", "barangay"].every((field) => value(field));
        if (!identityAutoAdvanced && activeStep === "identity" && ready && touchedIdentity.size === 3) {
          identityAutoAdvanced = true;
          if (!identityReady()) return;
          tabs.get("identity")?.setAttribute("data-completed", "true");
          updateForecastGate();
          if (guideTitle) guideTitle.textContent = "Basic details complete — moving to Tree Data";
          if (guideMessage) guideMessage.textContent = "Good. Next, tell us about the coconut palms. You can use the Easy Tree Estimate if you do not know every category.";
          setTimeout(() => setStep("trees", { scroll: true }), 700);
        }
      }));
    });

    // Easy tree estimate helper. It only fills the existing fields and remains editable.
    const treePresets = {
      productive: [0.08, 0.72, 0.08, 0.05, 0.025, 0.025, 0.02],
      mixed: [0.15, 0.52, 0.13, 0.07, 0.04, 0.05, 0.04],
      young: [0.40, 0.42, 0.05, 0.04, 0.02, 0.04, 0.03],
      aging: [0.05, 0.48, 0.27, 0.08, 0.04, 0.04, 0.04],
    };
    const treeFields = ["youngTrees", "productiveTrees", "agingTrees", "stressedTrees", "infestedTrees", "recoveringTrees", "deadTrees"];
    document.getElementById("applyTreeEstimateButton")?.addEventListener("click", () => {
      const totalInput = document.getElementById("farmerTreeCount");
      const total = Math.max(1, Math.round(Number(totalInput?.value || 0)));
      if (!Number.isFinite(total) || total < 1) {
        totalInput?.focus();
        if (guideTitle) guideTitle.textContent = "Enter the total number of coconut palms first";
        if (guideMessage) guideMessage.textContent = "A rough total is enough. Then COCOAID can create a starting tree breakdown for you.";
        return;
      }
      const preset = treePresets[document.getElementById("treeConditionPreset")?.value] || treePresets.mixed;
      let assigned = 0;
      treeFields.forEach((id, index) => {
        const count = index === treeFields.length - 1 ? total - assigned : Math.round(total * preset[index]);
        assigned += count;
        const input = document.getElementById(id);
        input.value = Math.max(0, count);
        dispatchInput(input);
      });
      if (guideTitle) guideTitle.textContent = "Easy tree estimate created";
      if (guideMessage) guideMessage.textContent = "Review the numbers and change anything you know is different on your farm.";
    });

    function syncTreeTotalDisplay() {
      const total = document.getElementById("totalTrees")?.value || "0";
      const display = document.getElementById("treeTotalDisplay");
      if (display) display.textContent = total;
    }
    treeFields.forEach((id) => document.getElementById(id)?.addEventListener("input", () => setTimeout(syncTreeTotalDisplay, 0)));
    syncTreeTotalDisplay();

    // Farmer-friendly soil choices feed the existing exact numeric inputs.
    document.getElementById("farmerSlopeChoice")?.addEventListener("change", (event) => {
      if (!event.target.value) return;
      const input = document.getElementById("slope"); input.value = event.target.value; dispatchInput(input);
    });
    document.getElementById("farmerDrainageChoice")?.addEventListener("change", (event) => {
      if (!event.target.value) return;
      const input = document.getElementById("drainage"); input.value = event.target.value; dispatchInput(input);
    });
    document.getElementById("farmerFertilityChoice")?.addEventListener("change", (event) => {
      if (!event.target.value) return;
      const base = Number(event.target.value);
      [["nitrogen", base], ["phosphorus", Math.max(0, base - 0.05)], ["potassium", Math.min(1, base + 0.04)]].forEach(([id, val]) => {
        const input = document.getElementById(id); input.value = Number(val).toFixed(2); dispatchInput(input);
      });
    });

    const saveMapEditButton = document.getElementById("mapSaveEditButton");
    let mapEditActive = false;

    function setMapEditMode(active) {
      mapEditActive = Boolean(active);
      if (saveMapEditButton) saveMapEditButton.hidden = !mapEditActive;
      farmMap?.classList.toggle("farm-boundary-editing", mapEditActive);
    }

    function startMapTool(selector, message, { editing = false } = {}) {
      const control = farmMap?.querySelector(selector);
      if (editing && !hasBoundary()) {
        setMapEditMode(false);
        if (mapLiveGuide) mapLiveGuide.innerHTML = '<span aria-hidden="true">!</span><strong>Draw and finish a farm boundary first. Then you can edit its corners.</strong>';
        return;
      }
      setMapEditMode(editing);
      farmMap?.classList.remove("farm-boundary-complete");
      farmMap?.classList.add("farm-boundary-drawing");
      if (mapLiveGuide) mapLiveGuide.innerHTML = `<span aria-hidden="true">➜</span><strong>${message}</strong>`;
      if (control) control.click();
      else setTimeout(() => farmMap?.querySelector(selector)?.click(), 120);
    }

    function findLeafletEditAction(label) {
      return [...(farmMap?.querySelectorAll(".leaflet-draw-actions a") || [])]
        .find((link) => link.textContent.trim().toLowerCase() === label.toLowerCase());
    }

    document.getElementById("mapPolygonGuideButton")?.addEventListener("click", () => startMapTool(".leaflet-draw-draw-polygon", "Click each corner of your farm. Click the first point again when you reach the end."));
    document.getElementById("mapRectangleGuideButton")?.addEventListener("click", () => startMapTool(".leaflet-draw-draw-rectangle", "Click one corner, hold and drag to the opposite corner, then release."));
    document.getElementById("mapEditGuideButton")?.addEventListener("click", () => startMapTool(".leaflet-draw-edit-edit", "Move the white corner handles until the orange farm boundary is correct, then press the large Save Farm Shape Changes button below.", { editing: true }));
    saveMapEditButton?.addEventListener("click", () => {
      const nativeSave = findLeafletEditAction("Save");
      if (!mapEditActive || !nativeSave) {
        if (mapLiveGuide) mapLiveGuide.innerHTML = '<span aria-hidden="true">!</span><strong>Choose Edit farm shape first, then move a corner before saving.</strong>';
        return;
      }
      nativeSave.click();
      setMapEditMode(false);
      if (mapLiveGuide) mapLiveGuide.innerHTML = '<span aria-hidden="true">✓</span><strong>Farm shape changes saved. The orange boundary is now the shape COCOAID will use.</strong>';
      setTimeout(syncBoundaryFocus, 80);
    });

    function syncBoundaryFocus() {
      const complete = hasBoundary();
      farmMap?.classList.toggle("farm-boundary-complete", complete);
      farmMap?.classList.remove("farm-boundary-drawing");
      if (!mapEditActive) farmMap?.classList.remove("farm-boundary-editing");
      if (boundarySuccess) boundarySuccess.hidden = !complete;
      if (mapLiveGuide) mapLiveGuide.innerHTML = complete
        ? '<span aria-hidden="true">✓</span><strong>Farm shape complete. The orange area is the farm COCOAID will use.</strong>'
        : '<span aria-hidden="true">➜</span><strong>Choose Polygon or Rectangle above to begin.</strong>';
      const helper = document.getElementById("farmAreaHelper");
      if (helper) helper.textContent = complete ? "Updated automatically from your orange farm shape." : "Draw your farm on the map and this will update automatically.";
      if (summaryText && complete) summaryText.textContent = polygonInfo?.textContent ? `${polygonInfo.textContent} · side lengths are labeled directly on the map.` : "The orange farm shape and side lengths are saved.";
      updateForecastGate();
      if (complete && farmPage.dataset.workflowStage === "boundary" && !boundaryAutoAdvanced && !mapEditActive) {
        boundaryAutoAdvanced = true;
        if (guideTitle) guideTitle.textContent = "Farm boundary confirmed";
        if (guideMessage) guideMessage.textContent = "Area and side lengths are calculated. Opening the basic farm details now.";
        if (progressBar) progressBar.style.width = "32%";
        setTimeout(() => showDataStage("identity", { scroll: true }), 900);
      }
    }
    if (polygonInfo) new MutationObserver(syncBoundaryFocus).observe(polygonInfo, { childList: true, characterData: true, subtree: true });
    document.getElementById("clearFarmPolygon")?.addEventListener("click", () => {
      boundaryAutoAdvanced = false;
      showBoundaryStage();
      setTimeout(syncBoundaryFocus, 0);
      updateForecastGate();
    });
    setTimeout(syncBoundaryFocus, 300);
    if (hasBoundary()) showDataStage("identity", { scroll: false });
    else showBoundaryStage();
    updateForecastGate();
  }

  function bootPhase11() {
    document.documentElement.dataset.theme = "light";
    document.body.classList.add("phase11-interface");
    applyChartDefaults();
    document.querySelectorAll(".coconut-hologram").forEach(initializeHologram);
    addChartToolbars();
    enhanceAccessibility();
    refreshEngineGrid();
    syncDedicatedWeatherFrame();
    observeNewCharts();
    setupFarmerProfileGuide();
    window.phase11RefreshIntelligence = refreshIntelligence;
    if (location.hash === "#intelligence") refreshIntelligence();
    document.querySelectorAll('[data-section="intelligence"]').forEach((button) => button.addEventListener("click", refreshIntelligence));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootPhase11);
  else bootPhase11();
})();
