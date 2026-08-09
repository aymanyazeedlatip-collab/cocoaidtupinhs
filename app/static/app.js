"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  section: "landing",
  farms: [],
  selectedFarmId: null,
  polygon: [],
  landingPolygon: [],
  maps: {},
  layers: {},
  renderers: {},
  charts: {},
  latestForecast: null,
  visualFrames: [],
  productionChartMode: "index",
  latestAnalysis: null,
  latestAnalysisId: null,
  health: null,
  rehabPlanIndex: 0,
  hazardIndex: 0,
  forecastMapFitKey: null,
  rehabAiByPlan: {},
  forecastIndex: 0,
  forecastTimer: null,
  forecastFreshnessTimer: null,
  forecastRequestInFlight: false,
  forecastMapLayers: { rain: true, wind: true, satellite: false, farm: true },
  forecastProviderCube: null,
  forecastProviderDetailError: null,
  forecastWindFrame: null,
  forecastWindAnimation: null,
  forecastWindParticles: [],
  forecastWindLastFrame: 0,
  forecastCalendarViewDate: null,
  hazardCalendarViewDate: null,
  rehabCalendarViewDate: null,
  rehabCalendarSelectedPhase: null,
  loadingProgressTimer: null,
  loadingProgressStep: 0,
  autoWorkflowTimer: null,
  autoWorkflowStatus: null,
  pilotSphereState: "waiting",
  rehabClipPolygon: null,
  intercropCandidates: [],
  intercropAssessments: [],
  intercropSelectedId: "cacao",
  intercropLight: 36,
  intercropCamera: { yaw: -0.55, pitch: -0.28, zoom: 1 },
  intercropSceneAnimation: null,
  intercropSceneDrag: null,
  intercropSceneLastTime: 0,
  intercropSceneLastRender: 0,
  intercropSceneLayoutCache: null,
  intercropSceneDepthOrder: null,
  intercropSceneDepthOrderAt: 0,
  intercropPhotoCache: {},
  intercropPhotoFetchStarted: false,
  aboutHologramAnimation: null,
  aboutHologramLastRender: 0,
  aboutHologramDrag: null,
  aboutHologramYaw: -0.35,
  aboutHologramPitch: -0.12,
  aboutModule: "foundation",
  forecastOpenPanel: null,
  weatherModalOpen: false,
  latestReportId: null,
  pilotHistory: [],
  pilotDocumentIds: [],
  pilotContextAttached: true,
  officialProfile: null,
  previewEntered: false,
  activeVoiceToken: 0,
  settings: {
    theme: "light",
    orbits: true,
    scenario: "ssp245",
    intervention: "combined_rehabilitation",
    runs: 1000,
    rainOpacity: 72,
    timelineSpeed: 500,
    bgmEnabled: true,
    voiceEnabled: true,
    bgmVolume: 10,
    voiceVolume: 88,
    sidebarCollapsed: false,
  },
};
const ALLOWED_SIMULATION_RUNS = [100, 500, 1000, 2000, 5000];
const VALID_SCENARIOS = new Set(["ssp126", "ssp245", "ssp370", "ssp585"]);
const VALID_INTERVENTIONS = new Set([
  "no_intervention",
  "monitoring",
  "pest_management",
  "soil_rehabilitation",
  "partial_replanting",
  "combined_rehabilitation",
]);

function normalizeRunCount(value) {
  const numeric = Number(value);
  if (ALLOWED_SIMULATION_RUNS.includes(numeric)) return numeric;
  if (!Number.isFinite(numeric) || numeric <= 0) return 1000;
  return ALLOWED_SIMULATION_RUNS.reduce((best, candidate) =>
    Math.abs(candidate - numeric) < Math.abs(best - numeric) ? candidate : best,
  ALLOWED_SIMULATION_RUNS[0]);
}

function normalizeSettingsValues(settings) {
  return {
    ...settings,
    theme: "light",
    orbits: settings.orbits !== false,
    scenario: VALID_SCENARIOS.has(settings.scenario) ? settings.scenario : "ssp245",
    intervention: VALID_INTERVENTIONS.has(settings.intervention)
      ? settings.intervention
      : "combined_rehabilitation",
    runs: normalizeRunCount(settings.runs),
    rainOpacity: Math.max(25, Math.min(95, Number(settings.rainOpacity) || 72)),
    timelineSpeed: 500,
    bgmEnabled: settings.bgmEnabled !== false,
    voiceEnabled: settings.voiceEnabled !== false,
    bgmVolume: 10,
    voiceVolume: Math.max(10, Math.min(100, Number(settings.voiceVolume) || 88)),
    sidebarCollapsed: settings.sidebarCollapsed === true,
  };
}

function formatApiErrorDetail(body, fallback) {
  if (!body) return fallback;
  if (typeof body.detail === "string") return body.detail;
  const errors = Array.isArray(body.errors)
    ? body.errors
    : Array.isArray(body.detail)
      ? body.detail.map((item) => ({
          field: Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "request",
          message: item.msg || "Invalid value",
        }))
      : [];
  if (errors.length) {
    return `Invalid forecast input: ${errors
      .slice(0, 6)
      .map((item) => `${item.field || "request"}: ${item.message || "Invalid value"}`)
      .join("; ")}`;
  }
  return fallback;
}

const sectionMeta = {
  landing: ["", ""],
  "farm-setup": ["Farm profile", "Define the boundary, palm cohorts, production, soil, and observations"],
  "weather-gis-page": ["Live atmospheric intelligence", "Interactive radar and genuine 16-day forecast workspace"],
  outlook: [
    "Weekly farm outlook",
    "Weather and three-product production through 2050",
  ],
  "extreme-weather": [
    "Hazard intelligence",
    "Estimated extreme-weather periods and farm effects",
  ],
  health: [
    "Farm health",
    "Spatial rehabilitation, suitability, and biological condition",
  ],
  "pest-risk": [
    "Pest-specific risk",
    "Ranked outbreak inference and pest-by-pest evidence",
  ],
  intercropping: [
    "Intercropping potential",
    "Canopy-responsive crop ranking and 3D farm simulation",
  ],
  intelligence: [
    "Integrated decision support",
    "Traceable analytical records and evidence-linked recommendations",
  ],
  reports: [
    "Reports",
    "Export and preserve the complete decision-support result",
  ],
  database: ["Local database", "Saved farms, forecasts, analyses and reports"],
  about: ["About COCO-AID", "Research platform, methodology, evidence, and system scope"],
};

const LOADING_TIPS = [
  "Tip: Draw the farm boundary as accurately as possible for better area-based estimates.",
  "Field note: Record visible damage immediately after a major weather event, then repeat the inspection after recovery begins.",
  "COCO-AID separates short-term numerical weather forecasts from long-term climate-conditioned projections.",
  "Bayesian pest risk becomes more useful when farm observations are updated consistently over time.",
  "Rehabilitation priorities should be confirmed through field inspection before trees are treated or replaced.",
  "Saved farms, forecasts, analyses, and reports remain available in the local COCO-AID database.",
];
let loadingTipTimer = null;
let loadingTipIndex = 0;

const VOICE_LINE_PATHS = Object.freeze({
  landing: "/static/assets/audio/home.mp3",
  "farm-setup": "/static/assets/audio/farm-setup.mp3",
  outlook: "/static/assets/audio/farm-site-forecast.mp3",
  "extreme-weather": "/static/assets/audio/extreme-weather.mp3",
  intercropping: "/static/assets/audio/intercropping.mp3",
  health: "/static/assets/audio/farm-health.mp3",
  "pest-risk": "/static/assets/audio/pest-risk.mp3",
  intelligence: "/static/assets/audio/decision-support.mp3",
  database: "/static/assets/audio/database.mp3",
  reports: "/static/assets/audio/reports.mp3",
  about: "/static/assets/audio/about.mp3",
  "weather-gis": "/static/assets/audio/weather-gis.mp3",
  "weather-gis-page": "/static/assets/audio/weather-gis.mp3",
  "forecast-complete": "/static/assets/audio/forecast-complete.mp3",
});

function backgroundMusic() { return $("backgroundMusic"); }
function voiceNarration() { return $("voiceNarration"); }
function effectiveBgmVolume() {
  return 0.10;
}
function applyAudioLevels() {
  const bgm = backgroundMusic();
  const voice = voiceNarration();
  if (bgm) bgm.volume = effectiveBgmVolume();
  if (voice) voice.volume = state.settings.voiceVolume / 100;
}
async function startBackgroundMusic() {
  const bgm = backgroundMusic();
  if (!bgm || !state.settings.bgmEnabled) return false;
  applyAudioLevels();
  try {
    await bgm.play();
    return true;
  } catch {
    return false;
  }
}
function stopBackgroundMusic() {
  const bgm = backgroundMusic();
  if (bgm) bgm.pause();
}
function restoreBgmAfterVoice(token) {
  if (token !== state.activeVoiceToken) return;
  applyAudioLevels();
  if (state.settings.bgmEnabled) startBackgroundMusic();
}
function stopVoiceLine() {
  state.activeVoiceToken += 1;
  const voice = voiceNarration();
  if (voice) { voice.pause(); voice.removeAttribute("src"); voice.load(); }
  applyAudioLevels();
}
async function playVoiceLine(key, { force = false } = {}) {
  const path = VOICE_LINE_PATHS[key];
  if (!path || !state.settings.voiceEnabled || (!state.previewEntered && !force)) return false;
  const voice = voiceNarration();
  if (!voice) return false;
  const token = ++state.activeVoiceToken;
  voice.pause();
  voice.src = path;
  voice.currentTime = 0;
  voice.volume = state.settings.voiceVolume / 100;
  applyAudioLevels();
  voice.onended = () => restoreBgmAfterVoice(token);
  voice.onerror = () => restoreBgmAfterVoice(token);
  try {
    await voice.play();
    return true;
  } catch {
    restoreBgmAfterVoice(token);
    return false;
  }
}
function enterWebsite() {
  if (state.previewEntered) return;
  state.previewEntered = true;
  document.body.classList.remove("preview-active");
  const preview = $("experiencePreview");
  preview?.classList.add("leaving");
  $("appShell")?.removeAttribute("aria-hidden");
  if ($("appShell")) $("appShell").inert = false;
  setTimeout(() => preview?.setAttribute("hidden", ""), 650);
  startBackgroundMusic();
  playVoiceLine(state.section || "landing");
  setTimeout(() => Object.values(state.maps).forEach((map) => map?.invalidateSize?.()), 180);
}

function startLoadingTips() {
  const tip = $("loadingTip");
  if (!tip) return;
  clearInterval(loadingTipTimer);
  tip.textContent = LOADING_TIPS[loadingTipIndex % LOADING_TIPS.length];
  loadingTipTimer = setInterval(() => {
    loadingTipIndex = (loadingTipIndex + 1) % LOADING_TIPS.length;
    tip.style.opacity = "0";
    setTimeout(() => {
      tip.textContent = LOADING_TIPS[loadingTipIndex];
      tip.style.opacity = "1";
    }, 180);
  }, 2600);
}
function stopLoadingTips() {
  clearInterval(loadingTipTimer);
  loadingTipTimer = null;
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>'"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        c
      ],
  );
}
function optionalNumber(id) {
  const value = $(id).value.trim();
  if (value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}
function safeNumber(id, fallback, min = -Infinity, max = Infinity) {
  const numeric = Number($(id)?.value);
  const value = Number.isFinite(numeric) ? numeric : fallback;
  return Math.max(min, Math.min(max, value));
}
function number(value, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString(undefined, {
        maximumFractionDigits: digits,
        minimumFractionDigits: 0,
      })
    : "—";
}
function percent(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? `${(n * 100).toFixed(digits)}%` : "—";
}
function title(value) {
  return String(value ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
function isoToday() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function toast(message, error = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.className = "toast"), 3400);
}
function updateLoadingSegments(step) {
  const bar = $("loadingSegmentBar");
  if (!bar) return;
  const segments = Array.from(bar.querySelectorAll("i"));
  const bounded = Math.max(0, Math.min(segments.length, Number(step) || 0));
  segments.forEach((segment, index) => segment.classList.toggle("active", index < bounded));
  bar.setAttribute("aria-valuenow", String(Math.round((bounded / Math.max(1, segments.length)) * 100)));
}
function loading(show, text = "Working…") {
  const overlay = $("loadingOverlay");
  if (!overlay) return;
  $("loadingText").textContent = text;
  overlay.classList.toggle("show", show);
  overlay.setAttribute("aria-hidden", show ? "false" : "true");
  if (state.loadingProgressTimer) { clearInterval(state.loadingProgressTimer); state.loadingProgressTimer = null; }
  if (show) {
    startLoadingTips();
    state.loadingProgressStep = 1;
    updateLoadingSegments(state.loadingProgressStep);
    state.loadingProgressTimer = setInterval(() => {
      if (state.loadingProgressStep < 11) state.loadingProgressStep += 1;
      updateLoadingSegments(state.loadingProgressStep);
    }, 340);
  } else {
    stopLoadingTips();
    state.loadingProgressStep = 12;
    updateLoadingSegments(12);
    setTimeout(() => updateLoadingSegments(0), 260);
  }
}
async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = formatApiErrorDetail(body, detail);
    } catch {}
    throw new Error(String(detail));
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response;
}

function refreshLongTermForecastIfStale() {
  if (state.section !== "outlook" || !state.latestForecast || state.forecastRequestInFlight) return;
  const generatedAt = Date.parse(state.latestForecast.generated_at || "");
  if (!Number.isFinite(generatedAt)) return;
  if (Date.now() - generatedAt >= 30 * 60 * 1000) runForecast();
}

function startForecastFreshnessWatcher() {
  if (state.forecastFreshnessTimer) clearInterval(state.forecastFreshnessTimer);
  // Open-Meteo is request-based rather than push-based. While the farmer keeps
  // Productivity open, periodically re-run a stale forecast so the provider
  // window is refreshed and the downstream modeled path is regenerated.
  state.forecastFreshnessTimer = setInterval(refreshLongTermForecastIfStale, 5 * 60 * 1000);
}

function getNavigationGroupForSection(sectionId) {
  const item = document.querySelector(`.nav-subitem[data-section="${sectionId}"]`);
  return item?.closest('.nav-group') || null;
}

function setNavGroupOpen(group, open) {
  if (!group) return;
  const toggle = group.querySelector('[data-nav-group-toggle]');
  const sublist = group.querySelector('.nav-sublist');
  group.classList.toggle('open', open);
  if (toggle) {
    toggle.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  }
  if (sublist) sublist.classList.toggle('open', open);
}

function updateNavigationState(activeSection) {
  document.querySelectorAll('.nav-item[data-section]').forEach((el) => el.classList.toggle('active', el.dataset.section === activeSection));
  const activeGroup = getNavigationGroupForSection(activeSection);
  document.querySelectorAll('.nav-group').forEach((group) => {
    const hasActive = group === activeGroup;
    const toggle = group.querySelector('[data-nav-group-toggle]');
    group.classList.toggle('active', hasActive);
    toggle?.classList.toggle('active', hasActive);
    setNavGroupOpen(group, hasActive);
  });
}

function toggleNavGroup(groupName) {
  const group = document.querySelector(`.nav-group[data-nav-group="${groupName}"]`);
  if (!group) return;
  const isOpen = group.classList.contains('open');
  document.querySelectorAll('.nav-group').forEach((item) => setNavGroupOpen(item, false));
  setNavGroupOpen(group, !isOpen);
}

function showSection(id, { skipVoice = false } = {}) {
  const previousSection = state.section;
  state.section = id;
  document.body.dataset.activeSection = id;
  if (id !== "outlook") stopForecastWind();
  document
    .querySelectorAll(".page")
    .forEach((el) => el.classList.toggle("active", el.id === id));
  updateNavigationState(id);
  const [eyebrow, titleText] = sectionMeta[id] || ["COCO-AID", "Workspace"];
  $("pageEyebrow").textContent = eyebrow;
  $("pageTitle").textContent = titleText;
  document.querySelector(".page-heading")?.classList.toggle("is-empty", !eyebrow && !titleText);
  history.replaceState(null, "", `#${id}`);
  setNavigationOpen(false);
  if (previousSection !== id) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  setTimeout(() => {
    Object.values(state.maps).forEach((map) => map?.invalidateSize?.());
    if (id === "outlook") {
      if (state.latestForecast) {
        updateForecastFrame(state.forecastIndex);
        fitForecastMapToFarm(true);
        const generatedAt = Date.parse(state.latestForecast.generated_at || "");
        const stale = Number.isFinite(generatedAt) && (Date.now() - generatedAt > 30 * 60 * 1000);
        if (stale && !state.forecastRequestInFlight) setTimeout(() => runForecast(), 250);
      }
      setTimeout(syncFarmToWeatherViewer, 160);
      setTimeout(() => { resizeForecastWindCanvas(); startForecastWind(); }, 260);
    }
  }, 140);
  if (id === "database") { refreshDatabase(); refreshAutoWorkflowStatus(true); }
  if (["intelligence","reports","database","about"].includes(id)) refreshAutoWorkflowStatus(true);
  if (id === "extreme-weather") setTimeout(() => {
    state.maps.hazardSnapshot?.invalidateSize?.({ pan:false });
    const event = state.latestForecast?.extreme_events?.[state.hazardIndex] || state.latestForecast?.extreme_events?.[0];
    if (event) renderHazardForecastSnapshot(event);
  }, 180);
  if (id === "landing") setTimeout(() => { syncFarmToWeatherViewer(); state.maps.landing?.invalidateSize?.(); }, 120);
  if (id === "weather-gis-page") setTimeout(syncFarmToWeatherViewer, 120);
  if (id === "health") setTimeout(() => {
    state.maps.rehab?.invalidateSize?.();
    if (state.health) renderRehabMap(selectedRehabPlan(), state.health.rehab);
    [state.charts.healthOverview,state.charts.tree,state.charts.healthPestDonut,state.charts.healthSuitabilityDonut,state.charts.healthConditionDonut].forEach((chart) => chart?.resize?.());
  }, 140);
  if (id === "pest-risk" && state.health?.specific) setTimeout(() => { renderPestCards(state.health.specific); state.charts.pestRanking?.resize?.(); state.charts.pestDrivers?.resize?.(); }, 80);
  if (id === "intercropping") setTimeout(() => { setupIntercropSceneControls(); loadIntercroppingWorkspace(); startIntercropScene(); }, 90);
  if (id !== "intercropping" && state.intercropSceneAnimation) { cancelAnimationFrame(state.intercropSceneAnimation); state.intercropSceneAnimation=null; }
  if (id === "about") setTimeout(setupAboutExperience, 90);
  if (id !== "about" && state.aboutHologramAnimation) { cancelAnimationFrame(state.aboutHologramAnimation); state.aboutHologramAnimation=null; }
  if (id === "intelligence") window.phase11RefreshIntelligence?.();
  if (!skipVoice && state.previewEntered && previousSection !== id) playVoiceLine(id);
}

function navigationWidth(collapsed = state.settings.sidebarCollapsed === true) {
  if (collapsed) return 78;
  return Math.max(240, Math.min(316, window.innerWidth - 48));
}

function syncGlobalNavigationControl() {
  const sidebar = $("sidebar");
  const button = $("globalNavButton");
  if (!sidebar || !button) return;
  const open = sidebar.classList.contains("open");
  const collapsed = state.settings.sidebarCollapsed === true;
  const icon = button.querySelector(".global-menu-icon");
  const label = button.querySelector("b");
  const action = !open ? "Open navigation" : collapsed ? "Expand navigation" : "Minimize navigation";
  const restingLeft = window.innerWidth <= 620 ? 16 : 24;
  button.style.setProperty("left", `${open ? navigationWidth(collapsed) : restingLeft}px`, "important");
  button.style.setProperty("right", "auto", "important");
  button.classList.toggle("is-connected", open);
  button.setAttribute("aria-expanded", String(open));
  button.setAttribute("aria-label", action);
  button.title = action;
  if (icon) icon.textContent = !open ? "☰" : collapsed ? "›" : "‹";
  if (label) label.textContent = !open ? "Menu" : collapsed ? "Expand" : "Minimize";
}

function setNavigationOpen(open, { forceExpanded = false } = {}) {
  const sidebar = $("sidebar");
  if (!sidebar) return;
  if (open && forceExpanded && state.settings.sidebarCollapsed) {
    state.settings.sidebarCollapsed = false;
    localStorage.setItem("cocoAidSettings", JSON.stringify(normalizeSettingsValues(state.settings)));
  }
  sidebar.classList.toggle("open", open);
  document.body.classList.toggle("navigation-open", open);
  applySidebarState();
}

function toggleGlobalNavigation() {
  const sidebar = $("sidebar");
  if (!sidebar) return;
  const open = sidebar.classList.contains("open");
  if (!open) {
    state.settings.sidebarCollapsed = false;
    saveSettings();
    setNavigationOpen(true);
    return;
  }
  state.settings.sidebarCollapsed = !state.settings.sidebarCollapsed;
  saveSettings();
  sidebar.classList.add("open");
  document.body.classList.add("navigation-open");
  applySidebarState();
}

function applySidebarState() {
  const collapsed = state.settings.sidebarCollapsed === true;
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  const sidebar = $("sidebar");
  if (sidebar) sidebar.style.setProperty("width", `${navigationWidth(collapsed)}px`, "important");
  const button = $("sidebarCollapseButton");
  if (button) {
    button.setAttribute("aria-expanded", String(!collapsed));
    button.setAttribute("aria-label", collapsed ? "Expand navigation" : "Minimize navigation");
    button.title = collapsed ? "Expand navigation" : "Minimize navigation";
    const label = button.querySelector(".sidebar-collapse-label");
    if (label) label.textContent = collapsed ? "Expand" : "Minimize";
  }
  document.querySelectorAll(".nav-item[data-section]").forEach((item) => {
    const navLabel = item.querySelector(".nav-label")?.textContent?.trim() || "";
    item.title = collapsed ? navLabel : "";
  });
  syncGlobalNavigationControl();
}

function loadSettings() {
  try {
    state.settings = normalizeSettingsValues({
      ...state.settings,
      ...JSON.parse(localStorage.getItem("cocoAidSettings") || "{}"),
    });
  } catch {
    state.settings = normalizeSettingsValues(state.settings);
  }
  applySettings();
}
function saveSettings() {
  state.settings = normalizeSettingsValues(state.settings);
  localStorage.setItem("cocoAidSettings", JSON.stringify(state.settings));
  applySettings();
}
function applySettings() {
  state.settings = normalizeSettingsValues(state.settings);
  document.documentElement.dataset.theme = state.settings.theme;
  document.body.classList.toggle("no-orbits", !state.settings.orbits);
  $("themeButton").textContent = state.settings.theme === "dark" ? "☀" : "☾";
  $("darkThemeSetting").checked = state.settings.theme === "dark";
  $("orbitSetting").checked = state.settings.orbits;
  $("defaultScenarioSetting").value = state.settings.scenario;
  $("defaultInterventionSetting").value = state.settings.intervention;
  $("defaultRunsSetting").value = String(state.settings.runs);
  $("rainOpacitySetting").value = state.settings.rainOpacity;
  $("rainOpacityOutput").textContent = `${state.settings.rainOpacity}%`;
  state.settings.timelineSpeed = 500;
  if ($("timelineSpeedSetting")) $("timelineSpeedSetting").value = "500";
  document.documentElement.style.setProperty(
    "--rain-opacity",
    state.settings.rainOpacity / 100,
  );
  if ($("bgmEnabledSetting")) $("bgmEnabledSetting").checked = state.settings.bgmEnabled;
  if ($("voiceEnabledSetting")) $("voiceEnabledSetting").checked = state.settings.voiceEnabled;
  if ($("voiceVolumeSetting")) $("voiceVolumeSetting").value = String(state.settings.voiceVolume);
  if ($("bgmVolumeOutput")) $("bgmVolumeOutput").textContent = "10%";
  if ($("voiceVolumeOutput")) $("voiceVolumeOutput").textContent = `${state.settings.voiceVolume}%`;
  applyAudioLevels();
  if (!state.settings.bgmEnabled) stopBackgroundMusic();
  else startBackgroundMusic();
  if (!state.settings.voiceEnabled) stopVoiceLine();
  applySidebarState();
  if (window.Chart) {
    Chart.defaults.color = getComputedStyle(document.documentElement)
      .getPropertyValue("--muted")
      .trim();
    Object.values(state.charts).forEach((chart) => chart?.update?.("none"));
  }
  postWeatherTheme();
}
function openSettings(open = true) {
  $("settingsDrawer").classList.toggle("open", open);
  $("drawerBackdrop").classList.toggle("open", open);
  $("settingsDrawer").setAttribute("aria-hidden", String(!open));
}
function postWeatherTheme() {
  [$("weatherViewerFrame"), $("weatherDedicatedFrame")].forEach((frame) => {
    if (frame?.contentWindow)
      frame.contentWindow.postMessage(
        { type: "COCO_AID_THEME", theme: "light" },
        location.origin,
      );
  });
}

function addBase(map) {
  return L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);
}
function polygonAreaHa(points) {
  if (!points?.length || !L.GeometryUtil) return 0;
  return (
    L.GeometryUtil.geodesicArea(points.map((p) => L.latLng(p[0], p[1]))) / 10000
  );
}
function polygonCenter(points) {
  if (!points?.length)
    return [Number($("latitude").value), Number($("longitude").value)];
  const sum = points.reduce(
    (a, p) => [a[0] + Number(p[0]), a[1] + Number(p[1])],
    [0, 0],
  );
  return [sum[0] / points.length, sum[1] / points.length];
}
function fitDrawMapToFarm(source = "farm") {
  const map = state.maps[source];
  if (!map || !Array.isArray(state.polygon) || state.polygon.length < 3) return;
  const bounds = L.latLngBounds(state.polygon.map((point) => L.latLng(Number(point[0]), Number(point[1]))));
  if (!bounds.isValid()) return;
  map.invalidateSize();
  map.fitBounds(bounds, { padding: source === "farm" ? [76, 76] : [54, 54], maxZoom: 18, animate: true, duration: .35 });
}

function setPolygon(points, source = "farm") {
  state.polygon = (points || []).map((p) => [Number(p[0]), Number(p[1])]);
  state.landingPolygon = [...state.polygon];
  const area = polygonAreaHa(state.polygon);
  if (area > 0) $("area").value = area.toFixed(3);
  const center = polygonCenter(state.polygon);
  $("latitude").value = center[0].toFixed(6);
  $("longitude").value = center[1].toFixed(6);
  renderFarmPolygons();
  updatePolygonText();
  if (state.polygon.length >= 3) setTimeout(() => fitDrawMapToFarm(source), 80);
  if (source === "landing") {
    $("landingContinue").disabled = state.polygon.length < 3;
    $("landingMapStatus").textContent =
      state.polygon.length >= 3
        ? "Farm boundary ready"
        : "Draw a polygon to begin";
  }
}
function updatePolygonText() {
  const area = polygonAreaHa(state.polygon);
  $("polygonInfo").textContent =
    state.polygon.length >= 3
      ? `${state.polygon.length} vertices · ${number(area, 3)} ha`
      : "No polygon drawn";
  $("landingArea").textContent =
    state.polygon.length >= 3
      ? `${number(area, 3)} hectares selected`
      : "No farm area selected";
}
function formatFarmSideKm(meters) {
  const km = Math.max(0, Number(meters || 0)) / 1000;
  return `${km < 1 ? km.toFixed(3) : km < 10 ? km.toFixed(2) : km.toFixed(1)} km`;
}
function renderFarmSideDimensions() {
  const map = state.maps.farm;
  const group = state.layers.farmDimensions;
  if (!map || !group) return;
  group.clearLayers();
  if (!Array.isArray(state.polygon) || state.polygon.length < 3) return;
  state.polygon.forEach((point, index) => {
    const next = state.polygon[(index + 1) % state.polygon.length];
    const a = L.latLng(Number(point[0]), Number(point[1]));
    const b = L.latLng(Number(next[0]), Number(next[1]));
    const meters = map.distance(a, b);
    const midpoint = L.latLng((a.lat + b.lat) / 2, (a.lng + b.lng) / 2);
    L.marker(midpoint, {
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: "farm-side-distance-marker",
        html: `<span>Side ${index + 1} · ${formatFarmSideKm(meters)}</span>`,
        iconSize: null,
      }),
    }).addTo(group);
  });
}

function renderFarmPolygons() {
  ["landing", "farm"].forEach((key) => {
    const group = state.layers[`${key}Drawn`];
    if (!group) return;
    group.clearLayers();
    if (state.polygon.length >= 3) {
      const farmFocus = key === "farm";
      L.polygon(state.polygon, {
        color: farmFocus ? "#ff9f1a" : "#246b32",
        weight: farmFocus ? 5 : 3,
        fillColor: farmFocus ? "#ef8500" : "#6fae22",
        fillOpacity: farmFocus ? 0.42 : 0.24,
        className: farmFocus ? "farm-focus-boundary" : "",
      }).addTo(group);
    }
  });
  renderFarmSideDimensions();
}
function initDrawMap(container, key, center = [6.334, 124.952], zoom = 7) {
  const map = L.map(container, { preferCanvas: true }).setView(center, zoom);
  addBase(map);
  const drawn = L.featureGroup().addTo(map);
  state.maps[key] = map;
  state.layers[`${key}Drawn`] = drawn;
  if (key === "farm") state.layers.farmDimensions = L.featureGroup().addTo(map);
  const controls = new L.Control.Draw({
    draw: {
      polyline: false,
      rectangle: true,
      circle: false,
      circlemarker: false,
      marker: false,
      polygon: { allowIntersection: false, showArea: true },
    },
    edit: { featureGroup: drawn, remove: true },
  });
  map.addControl(controls);
  map.on(L.Draw.Event.CREATED, (e) => {
    drawn.clearLayers();
    e.layer.addTo(drawn);
    const pts = e.layer.getLatLngs()[0].map((p) => [p.lat, p.lng]);
    setPolygon(pts, key);
    if (key === "landing") completeDrawTutorial();
  });
  map.on(L.Draw.Event.EDITED, (e) => {
    e.layers.eachLayer((layer) =>
      setPolygon(
        layer.getLatLngs()[0].map((p) => [p.lat, p.lng]),
        key,
      ),
    );
  });
  map.on(L.Draw.Event.DELETED, () => setPolygon([], key));
  return map;
}
function initMaps() {
  initDrawMap("landingMap", "landing");
  initDrawMap("farmMap", "farm");
  state.maps.forecast = L.map("forecastMap", {
    preferCanvas: true,
    zoomControl: true,
  }).setView([6.334, 124.952], 8);
  state.layers.forecastBase = addBase(state.maps.forecast);
  state.layers.forecastFarm = L.featureGroup().addTo(state.maps.forecast);
  state.layers.forecastWind = L.featureGroup().addTo(state.maps.forecast);
  state.maps.forecast.on("moveend zoomend resize", () => {
    resizeForecastWindCanvas();
    if (state.forecastMapLayers.wind !== false) startForecastWind();
  });
  state.maps.rehab = L.map("rehabMap", { preferCanvas: false }).setView(
    [6.334, 124.952],
    15,
  );
  addBase(state.maps.rehab);
  const rehabGridPane = state.maps.rehab.createPane("rehabGridPane");
  rehabGridPane.style.zIndex = "430";
  const rehabOutlinePane = state.maps.rehab.createPane("rehabOutlinePane");
  rehabOutlinePane.style.zIndex = "455";
  state.renderers.rehabGrid = L.svg({ pane:"rehabGridPane", padding:.35 }).addTo(state.maps.rehab);
  state.layers.rehab = L.featureGroup().addTo(state.maps.rehab);
  if ($("hazardSnapshotMap")) {
    state.maps.hazardSnapshot = L.map("hazardSnapshotMap", { preferCanvas:true, zoomControl:false, attributionControl:false, scrollWheelZoom:false, doubleClickZoom:false }).setView([6.334,124.952],8);
    state.layers.hazardSnapshotBase = addBase(state.maps.hazardSnapshot);
    state.layers.hazardSnapshot = L.featureGroup().addTo(state.maps.hazardSnapshot);
  }
}

function treeTotal() {
  return [
    "youngTrees",
    "productiveTrees",
    "agingTrees",
    "stressedTrees",
    "infestedTrees",
    "recoveringTrees",
    "deadTrees",
  ].reduce((sum, id) => sum + Math.max(0, Number($(id).value) || 0), 0);
}
function validateFarm() {
  const total = treeTotal();
  $("totalTrees").value = total;
  const valid = total > 0 && Number($("area").value) > 0;
  $("farmValidation").textContent = valid
    ? `${total} tree positions · ready to forecast`
    : "Enter a valid area and tree population";
  $("farmValidation").style.color = valid ? "var(--green)" : "var(--red)";
  return valid;
}
function getFarm() {
  validateFarm();
  return {
    name: $("farmName").value.trim() || "Unnamed Farm",
    location: {
      region: $("region").value.trim(),
      province: $("province").value,
      municipality: $("municipality").value.trim(),
      barangay: $("barangay").value.trim(),
      latitude: safeNumber("latitude", 6.334, -90, 90),
      longitude: safeNumber("longitude", 124.952, -180, 180),
      polygon: (state.polygon || []).filter((point) => Array.isArray(point) && point.length === 2 && point.every((value) => Number.isFinite(Number(value)))).map((point) => [Number(point[0]), Number(point[1])]),
    },
    area_hectares: safeNumber("area", 5, 0.001, 10000),
    trees: {
      total_trees: Math.max(1, Math.round(safeNumber("totalTrees", treeTotal(), 1, 100000))),
      young: Math.max(0, Math.round(safeNumber("youngTrees", 0, 0, 100000))),
      productive: Math.max(0, Math.round(safeNumber("productiveTrees", 0, 0, 100000))),
      aging: Math.max(0, Math.round(safeNumber("agingTrees", 0, 0, 100000))),
      stressed: Math.max(0, Math.round(safeNumber("stressedTrees", 0, 0, 100000))),
      infested: Math.max(0, Math.round(safeNumber("infestedTrees", 0, 0, 100000))),
      recovering: Math.max(0, Math.round(safeNumber("recoveringTrees", 0, 0, 100000))),
      dead: Math.max(0, Math.round(safeNumber("deadTrees", 0, 0, 100000))),
      average_age_years: safeNumber("averageAge", 34, 0, 120),
      variety: $("variety").value,
    },
    production: {
      annual_production_tons: safeNumber("annualProduction", 16, 0, 100000),
      yield_tons_per_hectare: safeNumber("yieldPerHa", 3.2, 0, 50),
      copra_weight_kg: optionalNumber("copraWeight"),
      nut_count: optionalNumber("nutCount"),
      oil_content_percent: optionalNumber("oilContent"),
    },
    soil_terrain: {
      elevation_m: safeNumber("elevation", 150, -100, 5000),
      slope_degrees: safeNumber("slope", 4.5, 0, 90),
      soil_ph: safeNumber("soilPh", 6.0, 2.5, 10),
      nitrogen_index: safeNumber("nitrogen", 0.62, 0, 1),
      phosphorus_index: safeNumber("phosphorus", 0.55, 0, 1),
      potassium_index: safeNumber("potassium", 0.66, 0, 1),
      drainage_index: safeNumber("drainage", 0.72, 0, 1),
    },
    symptoms: {
      yellowing: $("symptomYellowing").checked,
      crown_decline: $("symptomCrownDecline").checked,
      frond_cuts: $("symptomFrondCuts").checked,
      visible_scale_insects: $("symptomScale").checked,
      rhinoceros_beetle_damage: $("symptomBeetle").checked,
      premature_nut_fall: $("symptomNutFall").checked,
      nearby_reports: $("symptomNearby").checked,
      severity: Math.round(safeNumber("symptomSeverity", 0, 0, 3)),
    },
    management: {
      fertilizer_activity: $("fertilizerActivity").checked,
      soil_rehabilitation: $("soilRehabilitation").checked,
      pest_control: $("pestControl").checked,
      replanting_percent: 0,
      monitoring_activity: $("monitoringActivity").checked,
      intervention_burden_score: safeNumber("interventionBurden", 0, 0, 10),
    },
    events: [],
    provenance: {
      farm_area_hectares: "farmer_reported",
      tree_counts: "farmer_reported",
      soil_terrain: "estimated",
      production: "farmer_reported",
      provincial_production_reference: "government_record",
    },
  };
}
function setFarm(farm) {
  $("farmName").value = farm.name;
  $("region").value = farm.location.region;
  $("province").value = farm.location.province;
  $("municipality").value = farm.location.municipality;
  $("barangay").value = farm.location.barangay;
  $("area").value = farm.area_hectares;
  $("latitude").value = farm.location.latitude;
  $("longitude").value = farm.location.longitude;
  state.polygon = farm.location.polygon || [];
  for (const [id, key] of [
    ["youngTrees", "young"],
    ["productiveTrees", "productive"],
    ["agingTrees", "aging"],
    ["stressedTrees", "stressed"],
    ["infestedTrees", "infested"],
    ["recoveringTrees", "recovering"],
    ["deadTrees", "dead"],
  ])
    $(id).value = farm.trees[key];
  $("averageAge").value = farm.trees.average_age_years;
  $("variety").value = farm.trees.variety;
  $("annualProduction").value = farm.production.annual_production_tons;
  $("yieldPerHa").value = farm.production.yield_tons_per_hectare;
  $("copraWeight").value = farm.production.copra_weight_kg ?? "";
  $("nutCount").value = farm.production.nut_count ?? "";
  $("oilContent").value = farm.production.oil_content_percent ?? "";
  for (const [id, key] of [
    ["elevation", "elevation_m"],
    ["slope", "slope_degrees"],
    ["soilPh", "soil_ph"],
    ["nitrogen", "nitrogen_index"],
    ["phosphorus", "phosphorus_index"],
    ["potassium", "potassium_index"],
    ["drainage", "drainage_index"],
  ])
    $(id).value = farm.soil_terrain[key];
  $("fertilizerActivity").checked = farm.management.fertilizer_activity;
  $("soilRehabilitation").checked = farm.management.soil_rehabilitation;
  $("pestControl").checked = farm.management.pest_control;
  $("monitoringActivity").checked = farm.management.monitoring_activity;
  $("interventionBurden").value = farm.management.intervention_burden_score;
  for (const [id, key] of [
    ["symptomYellowing", "yellowing"],
    ["symptomCrownDecline", "crown_decline"],
    ["symptomFrondCuts", "frond_cuts"],
    ["symptomScale", "visible_scale_insects"],
    ["symptomBeetle", "rhinoceros_beetle_damage"],
    ["symptomNutFall", "premature_nut_fall"],
    ["symptomNearby", "nearby_reports"],
  ])
    $(id).checked = !!farm.symptoms?.[key];
  $("symptomSeverity").value = String(farm.symptoms?.severity ?? 0);
  validateFarm();
  renderFarmPolygons();
  updatePolygonText();
  const center = polygonCenter(state.polygon);
  state.maps.farm.setView(center, state.polygon.length ? 16 : 9);
  if (state.polygon.length) setTimeout(() => fitDrawMapToFarm("farm"), 80);
  loadOfficialProfile();
  syncFarmToWeatherViewer();
}

async function refreshFarms() {
  try {
    const data = await api("/api/farms");
    state.farms = data.farms || [];
    $("savedFarmSelect").innerHTML =
      '<option value="">Load saved farm</option>' +
      state.farms
        .map(
          (f) =>
            `<option value="${escapeHtml(f.id)}">${escapeHtml(f.name)}</option>`,
        )
        .join("");
    renderFarmDatabase();
  } catch (e) {
    toast(e.message, true);
  }
}
async function saveFarm() {
  if (!validateFarm()) return toast("Complete the farm inputs first.", true);
  try {
    loading(true, "Saving farm…");
    const farm = getFarm();
    let record;
    if (state.selectedFarmId)
      record = await api(`/api/farms/${state.selectedFarmId}`, {
        method: "PUT",
        body: JSON.stringify(farm),
      });
    else
      record = await api("/api/farms", {
        method: "POST",
        body: JSON.stringify(farm),
      });
    state.selectedFarmId = record.id;
    await refreshFarms();
    $("savedFarmSelect").value = record.id;
    if ($("saveFarmButton")) $("saveFarmButton").textContent = "Save Farm Changes";
    toast("Farm saved to the local database.");
  } catch (e) {
    toast(e.message, true);
  } finally {
    loading(false);
  }
}
async function loadSelectedFarm(id = $("savedFarmSelect").value) {
  if (!id) return toast("Select a saved farm.", true);
  try {
    const farm = await api(`/api/farms/${id}`);
    state.selectedFarmId = id;
    setFarm(farm);
    if ($("saveFarmButton")) $("saveFarmButton").textContent = "Save Farm Changes";
    showSection("farm-setup");
    toast("Farm loaded. Edit any details, then press Save Farm Changes.");
  } catch (e) {
    toast(e.message, true);
  }
}

async function loadOfficialProfile() {
  const province = $("province").value;
  try {
    const data = await api(
      `/api/official-data/profile?province=${encodeURIComponent(province)}&region=${encodeURIComponent($("region").value)}`,
    );
    state.officialProfile = data;
    const h = data.products.coconut_w_husk.latest_official_2025_tons;
    $("officialProvinceReference").textContent =
      `${data.province}: ${number(h, 0)} metric tons in 2025`;
    renderOfficialChart(data);
    $("officialChartSubtitle").textContent =
      `PSA ${data.province}: official annual totals through 2025; 2026 is estimated from available quarters`;
  } catch (e) {
    $("officialProvinceReference").textContent =
      "Official provincial profile unavailable";
  }
}

const timelineMarker = {
  id: "timelineMarker",
  afterDatasetsDraw(chart) {
    const idx = chart.$markerIndex;
    if (idx === undefined || idx === null || !chart.scales.x) return;
    const x = chart.scales.x.getPixelForValue(idx);
    if (!Number.isFinite(x)) return;
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.strokeStyle =
      getComputedStyle(document.documentElement)
        .getPropertyValue("--green")
        .trim() || "#246b32";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.arc(x, chartArea.top + 7, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  },
};
if (window.Chart) {
  Chart.register(timelineMarker);
  Chart.defaults.font.family = "Inter, Segoe UI, system-ui, sans-serif";
  Chart.defaults.color = getComputedStyle(document.documentElement)
    .getPropertyValue("--muted")
    .trim();
}
function chartOptions(yTitle, extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    animation: { duration: 350 },
    plugins: {
      legend: {
        position: "bottom",
        labels: { usePointStyle: true, boxWidth: 8 },
      },
      tooltip: { callbacks: {} },
      zoom: {
        pan: { enabled: true, mode: "x" },
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          drag: { enabled: true, backgroundColor: "rgba(31,122,79,.12)" },
          mode: "x",
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
      },
      y: {
        title: { display: !!yTitle, text: yTitle },
        grid: { color: "rgba(120,145,132,.12)" },
      },
    },
    ...extra,
  };
}
function replaceChart(key, canvas, config) {
  state.charts[key]?.destroy();
  state.charts[key] = new Chart($(canvas), config);
  return state.charts[key];
}
function renderOfficialChart(profile) {
  if (!profile?.products) return;
  const products = ["coconut_w_husk", "coconut_mature", "coconut_young"];
  const labels = profile.products.coconut_w_husk.history.map((x) =>
    String(x.year),
  );
  const colors = ["#246b32", "#ef8500", "#724413"];
  replaceChart("official", "officialHistoryChart", {
    type: "line",
    data: {
      labels,
      datasets: products.map((p, i) => {
        const history = profile.products[p].history;
        return {
          label: profile.products[p].label,
          data: history.map((x) => x.annual_tons),
          borderColor: colors[i],
          backgroundColor: "transparent",
          pointRadius: history.map((x) =>
            x.status === "official_psa" ? 2 : 5,
          ),
          pointStyle: history.map((x) =>
            x.status === "official_psa" ? "circle" : "rectRot",
          ),
          pointBackgroundColor: history.map((x) =>
            x.status === "official_psa" ? colors[i] : "#ffffff",
          ),
          pointBorderColor: colors[i],
          pointBorderWidth: 2,
          tension: 0.22,
          segment: {
            borderDash: (ctx) =>
              history[ctx.p1DataIndex]?.status === "official_psa"
                ? undefined
                : [7, 5],
          },
        };
      }),
    },
    options: {
      ...chartOptions("Metric tons"),
      plugins: {
        ...chartOptions("Metric tons").plugins,
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const row =
                profile.products[products[ctx.datasetIndex]].history[
                  ctx.dataIndex
                ];
              return row.status === "official_psa"
                ? "PSA official annual total"
                : "Estimated from available PSA quarters and historical seasonality";
            },
          },
        },
      },
    },
  });
}

const AUTO_FORECAST_SCENARIO = "ssp245";
const AUTO_FORECAST_INTERVENTION = "combined_rehabilitation";
const AUTO_FORECAST_RUNS = 1000;

function runPayload() {
  const currentYear = new Date().getFullYear();
  const runs = AUTO_FORECAST_RUNS;
  const farm = getFarm();
  const requiredNumbers = [
    ["Farm area", farm.area_hectares],
    ["Latitude", farm.location.latitude],
    ["Longitude", farm.location.longitude],
    ["Annual production", farm.production.annual_production_tons],
    ["Yield per hectare", farm.production.yield_tons_per_hectare],
  ];
  const invalid = requiredNumbers.find(([, value]) => !Number.isFinite(Number(value)));
  if (invalid) throw new Error(`${invalid[0]} must be a valid number.`);
  if (farm.trees.total_trees <= 0) throw new Error("Enter at least one tree before running the forecast.");
  const startYear = Math.min(2049, Math.max(2020, currentYear));
  const startDate = currentYear === startYear ? isoToday() : `${startYear}-01-01`;
  return {
    farm,
    start_year: startYear,
    end_year: 2050,
    start_date: startDate,
    scenario: AUTO_FORECAST_SCENARIO,
    intervention: AUTO_FORECAST_INTERVENTION,
    runs,
    seed: 42,
    include_live_short_term: true,
  };
}

function averageFinite(values) {
  const finiteValues = values.map(Number).filter(Number.isFinite);
  return finiteValues.length ? finiteValues.reduce((sum, value) => sum + value, 0) / finiteValues.length : null;
}
function lerpNumber(a, b, t) {
  const av = Number(a), bv = Number(b);
  if (!Number.isFinite(av) && !Number.isFinite(bv)) return null;
  if (!Number.isFinite(av)) return bv;
  if (!Number.isFinite(bv)) return av;
  return av + (bv - av) * t;
}
function interpolateDirection(a, b, t) {
  const ar = Number(a) * Math.PI / 180, br = Number(b) * Math.PI / 180;
  if (!Number.isFinite(ar) && !Number.isFinite(br)) return 0;
  if (!Number.isFinite(ar)) return Number(b) || 0;
  if (!Number.isFinite(br)) return Number(a) || 0;
  const x = Math.cos(ar) * (1 - t) + Math.cos(br) * t;
  const y = Math.sin(ar) * (1 - t) + Math.sin(br) * t;
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}
function providerMatrixAt(cube, variable, position) {
  const seriesByPoint = cube?.values?.[variable];
  if (!Array.isArray(seriesByPoint) || !seriesByPoint.length) return null;
  const h0 = Math.max(0, Math.min((cube.times?.length || 1) - 1, Math.floor(position)));
  const h1 = Math.min((cube.times?.length || 1) - 1, h0 + 1);
  const t = Math.max(0, Math.min(1, position - h0));
  const flat = seriesByPoint.map((series) => variable === "wind_direction_10m"
    ? interpolateDirection(series?.[h0], series?.[h1], t)
    : lerpNumber(series?.[h0], series?.[h1], t));
  return Array.from({ length: cube.rows }, (_, row) => flat.slice(row * cube.cols, (row + 1) * cube.cols));
}
function providerAverageAt(cube, variable, position) {
  const matrix = providerMatrixAt(cube, variable, position);
  return matrix ? averageFinite(matrix.flat()) : null;
}
function providerAverageDirectionAt(cube, position) {
  const matrix = providerMatrixAt(cube, "wind_direction_10m", position);
  if (!matrix) return null;
  const directions = matrix.flat().map(Number).filter(Number.isFinite);
  if (!directions.length) return null;
  const x = directions.reduce((sum, d) => sum + Math.cos(d * Math.PI / 180), 0) / directions.length;
  const y = directions.reduce((sum, d) => sum + Math.sin(d * Math.PI / 180), 0) / directions.length;
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}
function dailyFrameForTimestamp(data, timestamp) {
  const date = new Date(timestamp).toISOString().slice(0, 10);
  return (data.daily_frames || []).find((frame) => frame.date === date) || data.daily_frames?.[0] || data.frames?.[0] || {};
}
function buildHourlyProviderFrames(data, cube) {
  if (!cube?.times?.length) return [];
  return cube.times.map((timestamp, position) => {
    const daily = dailyFrameForTimestamp(data, timestamp);
    const rainGrid = providerMatrixAt(cube, "precipitation", position);
    const windSpeedGrid = providerMatrixAt(cube, "wind_speed_10m", position);
    const windDirectionGrid = providerMatrixAt(cube, "wind_direction_10m", position);
    return {
      ...daily,
      timestamp,
      date: timestamp.slice(0, 10),
      data_mode: "deterministic_short_term_forecast",
      visual_resolution: "hourly_provider",
      provider_position: position,
      rainfall_mm: providerAverageAt(cube, "precipitation", position),
      temperature_c: providerAverageAt(cube, "temperature_2m", position),
      humidity_percent: providerAverageAt(cube, "relative_humidity_2m", position),
      cloud_cover_percent: providerAverageAt(cube, "cloud_cover", position),
      pressure_hpa: providerAverageAt(cube, "pressure_msl", position),
      wind_speed_kmh: providerAverageAt(cube, "wind_speed_10m", position),
      wind_direction_deg: providerAverageDirectionAt(cube, position),
      spatial_grid: rainGrid,
      wind_speed_grid: windSpeedGrid,
      wind_direction_grid: windDirectionGrid,
      elevation_grid: cube.elevation_m,
      grid_bounds: { west: cube.west, south: cube.south, east: cube.east, north: cube.north },
    };
  });
}
function providerCubeBounds(data) {
  const bounds = data?.map_bounds;
  if (bounds) return bounds;
  const farm = data?.farm || {};
  const lat = Number(farm.latitude), lon = Number(farm.longitude);
  return { west: lon - .08, south: lat - .08, east: lon + .08, north: lat + .08 };
}
async function loadForecastProviderDetail(data) {
  state.forecastProviderCube = null;
  state.forecastProviderDetailError = null;
  const bounds = providerCubeBounds(data);
  try {
    state.forecastProviderCube = await api("/api/weather/cube", {
      method: "POST",
      body: JSON.stringify({
        west: Number(bounds.west), south: Number(bounds.south), east: Number(bounds.east), north: Number(bounds.north),
        rows: 6, cols: 6, forecast_hours: 384, model: "auto",
      }),
    });
  } catch (error) {
    state.forecastProviderDetailError = error?.message || "Provider weather grid unavailable";
    console.warn("High-frequency forecast weather could not be loaded; daily frames remain available.", error);
  }
}
function buildForecastVisualFrames(data) {
  const providerFrames = buildHourlyProviderFrames(data, state.forecastProviderCube);
  if (providerFrames.length) {
    const providerEndDate = providerFrames.at(-1)?.date;
    const modeledDaily = (data.daily_frames || []).filter((frame) =>
      frame.data_mode !== "deterministic_short_term_forecast" && (!providerEndDate || String(frame.date || frame.week_start || "") > providerEndDate)
    );
    return [...providerFrames, ...modeledDaily];
  }
  return data.daily_frames?.length ? data.daily_frames : (data.frames || []);
}

function triggerAutomaticPhaseWorkflows(farm) {
  if (!farm) return;
  renderAutoWorkflowStatus({state:"checking",phase9:"Preparing",phase10:"Waiting",message:"Preparing Phase 9 automatically from the farm forecast…"});
  api('/api/v2/workflows/auto-phase9-10/bootstrap', { method:'POST', body:JSON.stringify(farm) })
    .then(async (result)=>{
      renderAutoWorkflowStatus(result?.workflow || result || {});
      try { await api('/api/v2/workflows/auto-phase9-10/kick', { method:'POST' }); } catch (error) { console.warn('Automatic Phase 9/10 kick request failed.', error); }
      [800, 2200, 5200, 9000].forEach((delay) => setTimeout(() => refreshAutoWorkflowStatus(delay < 2000), delay));
    })
    .catch((error)=>{
      console.warn('Automatic Phase 9/10 bootstrap failed.',error);
      renderAutoWorkflowStatus({state:'error',phase9:'Retry available',phase10:'Waiting',message:`Automatic workflow could not start: ${error.message}`});
    });
}

async function runForecast() {
  if (state.forecastRequestInFlight) {
    toast("A forecast is already running. Please wait for it to finish.");
    return;
  }
  const button = $("runForecastButton");
  state.forecastRequestInFlight = true;
  button.disabled = true;
  button.dataset.originalText ||= button.textContent;
  button.textContent = "Running forecast…";
  try {
    const payload = runPayload();
    loading(
      true,
      "Generating daily visual frames and weather-driven production through 2050…",
    );
    const data = await api("/api/farm-site/forecast", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.latestForecast = data;
    state.forecastIndex = 0;
    triggerAutomaticPhaseWorkflows(payload.farm);
    state.forecastMapFitKey = null;
    await loadForecastProviderDetail(data);
    renderForecast(data);
    showSection("outlook", { skipVoice: true });
    await runHealth({ silent: true, keepOverlay: true });
    playVoiceLine("forecast-complete");
    toast(
      `Daily outlook generated: ${(data.daily_frame_count || data.daily_frames?.length || 0).toLocaleString()} dates linked to ${data.frames.length.toLocaleString()} weekly model control points.`,
    );
  } catch (e) {
    console.error("COCO-AID forecast request failed", e);
    toast(e?.message || "The forecast could not be generated.", true);
  } finally {
    state.forecastRequestInFlight = false;
    button.disabled = false;
    button.textContent = button.dataset.originalText || "Run daily outlook";
    loading(false);
  }
}
function renderForecast(data) {
  const weekly = data.weekly || data.frames || [];
  const visual = buildForecastVisualFrames(data);
  if (!weekly.length || !visual.length)
    throw new Error("Forecast returned no usable timeline frames");
  state.visualFrames = visual;
  state.forecastIndex = 0;
  $("forecastSlider").max = visual.length - 1;
  $("forecastSlider").step = 1;
  $("forecastSlider").value = 0;
  const providerFrameCount = visual.findIndex((frame) => frame.data_mode !== "deterministic_short_term_forecast");
  const providerRatio = Math.max(1.5, Math.min(98, ((providerFrameCount < 0 ? visual.length : providerFrameCount) / Math.max(1, visual.length - 1)) * 100));
  $("forecastSlider").style.setProperty("--provider-ratio", `${providerRatio}%`);
  $("timelineStart").textContent = visual[0].date || weekly[0].week_start;
  $("timelineEnd").textContent = visual.at(-1).date || weekly.at(-1).week_end;
  const summary = data.posterior_summary || {};
  $("forecast2050").textContent = `${number(summary.final_median_tons)} t/year`;
  $("forecastRange").textContent =
    `${number(summary.final_p05_tons)}–${number(summary.final_p95_tons)} t (5th–95th)`;
  $("forecastRecovery").textContent = percent(summary.rehabilitation_probability);
  $("forecastLoss").textContent = percent(summary.severe_loss_probability);
  const liveMerge = data.short_term_live_merge || {};
  const liveWindow = $("forecastLiveWindowLabel");
  const syncStatus = $("forecastWeatherSyncStatus");
  if (liveWindow) {
    liveWindow.textContent = liveMerge.available
      ? `${liveMerge.first_merged_date} to ${liveMerge.last_merged_date} · ${state.forecastProviderCube?.times?.length ? "384 hourly Open-Meteo numerical-model frames" : `${liveMerge.dates_merged} provider-backed days`} .`
      : (liveMerge.warning || "Provider weather is unavailable for this run; the long-term model remains explicitly labeled as modeled weather.");
  }
  if (syncStatus) syncStatus.textContent = liveMerge.available ? "Open-Meteo weather merged into the current production run" : "Weather GIS synced; provider merge unavailable for this run";
  const hazard = data.extreme_events?.[0];
  $("forecastNextHazard").textContent = hazard
    ? `${hazard.label} · ${hazard.start_date}`
    : "No major event flagged";
  renderForecastCharts(data);
  renderHazards(data.extreme_events || []);
  updateForecastFrame(0);
  renderHealthTreeChart();
  syncFarmToWeatherViewer();
}
function normalizedSeries(values) {
  const base = values.find((value) => Number(value) > 0) || 1;
  return values.map((value) => (Number(value || 0) / base) * 100);
}

function focusedOptions(yTitle, radius = 26, extra = {}) {
  const base = chartOptions(yTitle, extra);
  base.$focusRadius = radius;
  return base;
}

function renderProductionChart(frames) {
  const labels = frames.map((f) => f.week_start);
  const raw = {
    husk: frames.map((f) => Number(f.production_coconut_w_husk_tons || 0)),
    mature: frames.map((f) => Number(f.production_coconut_mature_tons || 0)),
    young: frames.map((f) => Number(f.production_coconut_young_tons || 0)),
  };
  const indexMode = state.productionChartMode !== "tons";
  const display = indexMode
    ? { husk: normalizedSeries(raw.husk), mature: normalizedSeries(raw.mature), young: normalizedSeries(raw.young) }
    : raw;
  const chart = replaceChart("production", "productionChart", {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Coconut w/ husk", data: display.husk, borderColor: "#246b32", backgroundColor: "rgba(0,183,90,.10)", tension: .24, pointRadius: 0, borderWidth: 2.4, rawValues: raw.husk },
        { label: "Coconut Mature", data: display.mature, borderColor: "#ef8500", tension: .24, pointRadius: 0, borderWidth: 2.1, rawValues: raw.mature },
        { label: "Coconut Young", data: display.young, borderColor: "#724413", tension: .24, pointRadius: 0, borderWidth: 2.1, rawValues: raw.young },
      ],
    },
    options: focusedOptions(indexMode ? "Trend index (first forecast week = 100)" : "Weekly production (t)", 52, {
      plugins: {
        ...chartOptions("").plugins,
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const rawValue = ctx.dataset.rawValues?.[ctx.dataIndex] ?? ctx.raw;
              return indexMode
                ? `${ctx.dataset.label}: ${number(ctx.raw, 1)} index · ${number(rawValue, 4)} t`
                : `${ctx.dataset.label}: ${number(rawValue, 4)} t`;
            },
          },
        },
      },
    }),
  });
  chart.$focusRadius = 52;
  $("productionIndexMode")?.classList.toggle("active", indexMode);
  $("productionTonsMode")?.classList.toggle("active", !indexMode);
}

function singleFactorChart(key, canvas, labels, label, values, color, unit, bounds = {}) {
  const chart = replaceChart(key, canvas, {
    type: "line",
    data: { labels, datasets: [{ label, data: values, borderColor: color, backgroundColor: `${color}18`, fill: true, pointRadius: 0, tension: .25, borderWidth: 2 }] },
    options: focusedOptions(unit, 26, {
      scales: {
        x: { grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 9, maxRotation: 0 } },
        y: { ...bounds, title: { display: true, text: unit }, grid: { color: "rgba(120,145,132,.12)" } },
      },
    }),
  });
  chart.$focusRadius = 26;
}

function renderForecastCharts(data) {
  const frames = data.weekly || data.frames || [];
  const labels = frames.map((f) => f.week_start);
  renderProductionChart(frames);
  const weather = replaceChart("weather", "weatherChart", {
    data: { labels, datasets: [
      { type: "bar", label: "Rainfall (mm)", data: frames.map((f) => f.rainfall_mm), backgroundColor: "rgba(22,140,255,.32)", borderColor: "#724413", yAxisID: "y" },
      { type: "line", label: "Mean temperature (°C)", data: frames.map((f) => f.temperature_c), borderColor: "#ef8500", pointRadius: 0, tension: .22, yAxisID: "y1" },
      { type: "line", label: "Maximum temperature (°C)", data: frames.map((f) => f.temperature_max_c), borderColor: "#b7463c", borderDash: [6,4], pointRadius: 0, tension: .22, yAxisID: "y1" },
    ] },
    options: focusedOptions("Rainfall (mm)", 26, { scales: {
      x: { grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 9, maxRotation: 0 } },
      y: { position: "left", title: { display: true, text: "Rainfall (mm)" } },
      y1: { position: "right", title: { display: true, text: "Temperature (°C)" }, grid: { drawOnChartArea: false } },
    } }),
  });
  weather.$focusRadius = 26;
  singleFactorChart("humidity", "humidityChart", labels, "Relative humidity", frames.map((f) => f.humidity_percent), "#246b32", "Percent", { min: 0, max: 100 });
  singleFactorChart("cloud", "cloudChart", labels, "Cloud cover", frames.map((f) => f.cloud_cover_percent), "#724413", "Percent", { min: 0, max: 100 });
  singleFactorChart("wind", "windChart", labels, "Wind speed", frames.map((f) => f.wind_speed_kmh), "#6fae22", "km/h", { min: 0 });
  singleFactorChart("pressure", "pressureChart", labels, "Mean sea-level pressure", frames.map((f) => f.pressure_hpa), "#724413", "hPa", {});
  const condition = replaceChart("condition", "conditionChart", {
    type: "line",
    data: { labels, datasets: [
      { label: "Farm condition", data: frames.map((f) => f.farm_condition_score * 100), borderColor: "#246b32", pointRadius: 0, fill: true, backgroundColor: "rgba(0,183,90,.10)" },
      { label: "Pest probability", data: frames.map((f) => f.pest_probability * 100), borderColor: "#b7463c", pointRadius: 0 },
    ] },
    options: focusedOptions("Percent", 26, { scales: {
      x: { grid: { display: false }, ticks: { autoSkip: true, maxTicksLimit: 9 } },
      y: { min: 0, max: 100, title: { display: true, text: "Percent" } },
    } }),
  });
  condition.$focusRadius = 26;
  updateChartMarkers(0);
}
function focusChartWindow(chart, index, radius = null) {
  if (!chart?.data?.labels?.length || !chart.scales?.x) return;
  const count = chart.data.labels.length;
  const windowRadius = radius ?? chart.$focusRadius;
  if (!windowRadius || count <= windowRadius * 2 + 1) return;
  const min = Math.max(0, Math.min(count - 1, index - windowRadius));
  const max = Math.min(count - 1, Math.max(0, index + windowRadius));
  chart.options.scales.x.min = min;
  chart.options.scales.x.max = max;
}

function updateChartMarkers(index) {
  const keys = ["production", "weather", "humidity", "cloud", "wind", "pressure", "condition"];
  for (const key of keys) {
    const chart = state.charts[key];
    if (chart) {
      chart.$markerIndex = index;
      focusChartWindow(chart, index);
      chart.update("none");
    }
  }
  if (state.charts.official && state.latestForecast) {
    const visual = state.visualFrames[state.forecastIndex] || {};
    const sourceDate = visual.date || state.latestForecast.frames[index]?.week_start || "";
    const year = Number(String(sourceDate).slice(0, 4));
    const labels = state.charts.official.data.labels;
    state.charts.official.$markerIndex = Math.max(0, labels.indexOf(String(Math.min(2026, year))));
    state.charts.official.draw();
  }
}
function colorForRain(value) {
  if (!Number.isFinite(value) || value < 0.03) return [0, 0, 0, 0];
  const stops = [
    { v: 0.03, c: [95, 218, 255, 45] },
    { v: 0.6, c: [48, 172, 255, 125] },
    { v: 2.0, c: [20, 102, 232, 190] },
    { v: 5.0, c: [10, 47, 175, 225] },
    { v: 10.0, c: [255, 225, 48, 235] },
    { v: 18.0, c: [255, 137, 38, 242] },
    { v: 30.0, c: [224, 37, 42, 250] },
  ];
  const valueClamped = Math.min(30, Math.max(stops[0].v, value));
  let upper = 1;
  while (upper < stops.length && valueClamped > stops[upper].v) upper += 1;
  upper = Math.min(stops.length - 1, upper);
  const lower = Math.max(0, upper - 1);
  const span = Math.max(1e-9, stops[upper].v - stops[lower].v);
  const t = (valueClamped - stops[lower].v) / span;
  return stops[lower].c.map((v, i) =>
    Math.round(v + (stops[upper].c[i] - v) * t),
  );
}

function generatedGrid(frame, size = 44) {
  if (frame.spatial_grid?.length) return frame.spatial_grid;
  const [cx = 0.5, cy = 0.5, spread = 0.15, peak = 0, seed = 1] =
    frame.spatial || [];
  let x = Number(seed) || 1;
  const rnd = () => {
    x = (x * 1664525 + 1013904223) % 4294967296;
    return x / 4294967296;
  };
  const blobs = [{ x: cx, y: cy, s: spread, p: peak }];
  for (let b = 0; b < 5; b += 1) {
    blobs.push({
      x: (cx + (rnd() - 0.5) * spread * 2.5 + 1) % 1,
      y: (cy + (rnd() - 0.5) * spread * 2.5 + 1) % 1,
      s: spread * (0.45 + rnd() * 0.9),
      p: peak * (0.18 + rnd() * 0.52),
    });
  }
  return Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => {
      const px = c / (size - 1);
      const py = r / (size - 1);
      let value = 0;
      for (const blob of blobs) {
        const dx = px - blob.x;
        const dy = py - blob.y;
        value +=
          blob.p * Math.exp(-(dx * dx + dy * dy) / (2 * blob.s * blob.s));
      }
      return value;
    }),
  );
}

function bilinearGridValue(grid, x, y) {
  const rows = grid.length;
  const cols = grid[0]?.length || 0;
  if (!rows || !cols) return 0;
  const gx = Math.max(0, Math.min(cols - 1, x * (cols - 1)));
  const gy = Math.max(0, Math.min(rows - 1, y * (rows - 1)));
  const x0 = Math.floor(gx);
  const y0 = Math.floor(gy);
  const x1 = Math.min(cols - 1, x0 + 1);
  const y1 = Math.min(rows - 1, y0 + 1);
  const tx0 = gx - x0;
  const ty0 = gy - y0;
  // Smoothstep softens the transitions between model cells without inventing
  // additional observations.
  const tx = tx0 * tx0 * (3 - 2 * tx0);
  const ty = ty0 * ty0 * (3 - 2 * ty0);
  const top =
    Number(grid[y0][x0] || 0) * (1 - tx) + Number(grid[y0][x1] || 0) * tx;
  const bottom =
    Number(grid[y1][x0] || 0) * (1 - tx) + Number(grid[y1][x1] || 0) * tx;
  return top * (1 - ty) + bottom * ty;
}

function drawRainDataUrl(frame) {
  const grid = generatedGrid(frame);
  const width = 320;
  const height = 240;
  const source = document.createElement("canvas");
  source.width = width;
  source.height = height;
  const sourceCtx = source.getContext("2d", { willReadFrequently: false });
  const image = sourceCtx.createImageData(width, height);
  const opacity = state.settings.rainOpacity / 100;
  for (let py = 0; py < height; py += 1) {
    const y = py / (height - 1);
    for (let px = 0; px < width; px += 1) {
      const x = px / (width - 1);
      const value = bilinearGridValue(grid, x, y);
      const [r, g, b, a] = colorForRain(value);
      const i = (py * width + px) * 4;
      image.data[i] = r;
      image.data[i + 1] = g;
      image.data[i + 2] = b;
      image.data[i + 3] = Math.round(a * opacity);
    }
  }
  sourceCtx.putImageData(image, 0, 0);

  // A small blur removes any remaining cell boundaries and produces a continuous
  // weather-report heat field. The underlying values remain the same interpolated
  // model grid; this is a visualization treatment only.
  const output = document.createElement("canvas");
  output.width = width;
  output.height = height;
  const outCtx = output.getContext("2d");
  outCtx.clearRect(0, 0, width, height);
  outCtx.filter = "blur(3.5px) saturate(1.12)";
  outCtx.drawImage(source, -3, -3, width + 6, height + 6);
  outCtx.filter = "none";
  return output.toDataURL("image/png");
}

function farmForecastBounds() {
  const farm = state.latestForecast?.farm;
  if (Array.isArray(farm?.polygon) && farm.polygon.length >= 3) {
    return L.latLngBounds(farm.polygon.map((point) => L.latLng(Number(point[0]), Number(point[1]))));
  }
  if (Number.isFinite(Number(farm?.latitude)) && Number.isFinite(Number(farm?.longitude))) {
    const lat = Number(farm.latitude);
    const lon = Number(farm.longitude);
    return L.latLngBounds([[lat - 0.0035, lon - 0.0035], [lat + 0.0035, lon + 0.0035]]);
  }
  return null;
}

function fitForecastMapToFarm(force = false) {
  const map = state.maps.forecast;
  const farm = state.latestForecast?.farm;
  if (!map || !farm) return;
  const polygonSignature = Array.isArray(farm.polygon)
    ? farm.polygon.map((point) => `${Number(point[0]).toFixed(6)},${Number(point[1]).toFixed(6)}`).join("|")
    : `${Number(farm.latitude).toFixed(6)},${Number(farm.longitude).toFixed(6)}`;
  if (!force && state.forecastMapFitKey === polygonSignature) return;
  const bounds = farmForecastBounds();
  if (!bounds?.isValid?.()) return;
  map.invalidateSize();
  map.fitBounds(bounds, { padding: [92, 92], maxZoom: 16, animate: false });
  setTimeout(() => {
    map.invalidateSize();
    map.fitBounds(bounds, { padding: [92, 92], maxZoom: 16, animate: false });
  }, 180);
  state.forecastMapFitKey = polygonSignature;
}

function forecastBounds() {
  const b = state.latestForecast?.map_bounds;
  return b
    ? [
        [b.south, b.west],
        [b.north, b.east],
      ]
    : [
        [5.6, 124.1],
        [7.1, 125.8],
      ];
}
function forecastWindGridFromFrame(frame) {
  const speeds = frame?.wind_speed_grid;
  const directions = frame?.wind_direction_grid;
  const bounds = frame?.grid_bounds;
  if (!Array.isArray(speeds) || !speeds.length || !Array.isArray(directions) || !directions.length || !bounds) return null;
  return {
    west: Number(bounds.west), south: Number(bounds.south), east: Number(bounds.east), north: Number(bounds.north),
    rows: speeds.length, cols: speeds[0]?.length || 0,
    values: { wind_speed_10m: speeds, wind_direction_10m: directions },
    elevation_m: frame.elevation_grid,
  };
}
function forecastGridFraction(grid, lat, lng) {
  if (!grid || lat < grid.south || lat > grid.north || lng < grid.west || lng > grid.east) return null;
  const row = ((grid.north - lat) / Math.max(1e-9, grid.north - grid.south)) * (grid.rows - 1);
  const col = ((lng - grid.west) / Math.max(1e-9, grid.east - grid.west)) * (grid.cols - 1);
  return { row, col };
}
function forecastBilinearValue(matrix, row, col) {
  if (!Array.isArray(matrix) || !matrix.length || !Array.isArray(matrix[0])) return null;
  const rows = matrix.length, cols = matrix[0].length;
  const r0 = Math.max(0, Math.min(rows - 1, Math.floor(row)));
  const r1 = Math.max(0, Math.min(rows - 1, Math.ceil(row)));
  const c0 = Math.max(0, Math.min(cols - 1, Math.floor(col)));
  const c1 = Math.max(0, Math.min(cols - 1, Math.ceil(col)));
  const fy = row - r0, fx = col - c0;
  const q00 = Number(matrix[r0]?.[c0]), q01 = Number(matrix[r0]?.[c1]);
  const q10 = Number(matrix[r1]?.[c0]), q11 = Number(matrix[r1]?.[c1]);
  if (![q00, q01, q10, q11].every(Number.isFinite)) return null;
  return q00 * (1 - fx) * (1 - fy) + q01 * fx * (1 - fy) + q10 * (1 - fx) * fy + q11 * fx * fy;
}
function forecastVectorMatrixAt(grid, row, col) {
  const speeds = grid.values.wind_speed_10m;
  const directions = grid.values.wind_direction_10m;
  if (!speeds || !directions) return null;
  const rows = grid.rows, cols = grid.cols;
  const r0 = Math.max(0, Math.min(rows - 1, Math.floor(row)));
  const r1 = Math.max(0, Math.min(rows - 1, Math.ceil(row)));
  const c0 = Math.max(0, Math.min(cols - 1, Math.floor(col)));
  const c1 = Math.max(0, Math.min(cols - 1, Math.ceil(col)));
  const fy = row - r0, fx = col - c0;
  const weights = [[r0,c0,(1-fx)*(1-fy)],[r0,c1,fx*(1-fy)],[r1,c0,(1-fx)*fy],[r1,c1,fx*fy]];
  let u = 0, v = 0, total = 0;
  for (const [r,c,weight] of weights) {
    const speed = Number(speeds[r]?.[c]);
    const direction = Number(directions[r]?.[c]);
    if (!Number.isFinite(speed) || !Number.isFinite(direction)) continue;
    const radians = (direction * Math.PI) / 180;
    u += -speed * Math.sin(radians) * weight;
    v += -speed * Math.cos(radians) * weight;
    total += weight;
  }
  return total > 0 ? { u: u / total, v: v / total } : null;
}
function forecastTerrainAt(grid, row, col) {
  const elevation = grid.elevation_m;
  if (!Array.isArray(elevation) || !Array.isArray(elevation[0])) return null;
  const sample = (r,c) => forecastBilinearValue(elevation, Math.max(0,Math.min(grid.rows-1,r)), Math.max(0,Math.min(grid.cols-1,c)));
  const center = sample(row,col);
  const eastGradient = (sample(row,col+.65) - sample(row,col-.65)) / 1.3;
  const northGradient = -(sample(row+.65,col) - sample(row-.65,col)) / 1.3;
  if (![center,eastGradient,northGradient].every(Number.isFinite)) return null;
  return { elevation:center, gx:eastGradient, gy:northGradient };
}
function forecastApplyTerrainDeflection(vector, terrain) {
  if (!terrain) return vector;
  const gradientMagnitude = Math.hypot(terrain.gx, terrain.gy);
  if (gradientMagnitude < 2) return vector;
  const gx = terrain.gx / gradientMagnitude, gy = terrain.gy / gradientMagnitude;
  const alongGradient = vector.u * gx + vector.v * gy;
  const terrainStrength = Math.max(0, Math.min(.72, gradientMagnitude / 420 + Math.max(0, terrain.elevation - 250) / 3500));
  let u = vector.u, v = vector.v;
  if (alongGradient > 0) {
    u -= gx * alongGradient * terrainStrength; v -= gy * alongGradient * terrainStrength;
    const tangentX = -gy, tangentY = gx;
    const turnSign = vector.u * tangentY - vector.v * tangentX >= 0 ? 1 : -1;
    const turn = alongGradient * terrainStrength * .58 * turnSign;
    u += tangentX * turn; v += tangentY * turn;
  }
  const slowdown = 1 - terrainStrength * .24;
  return { u: u * slowdown, v: v * slowdown };
}
function forecastUniformWindVector(frame) {
  const speed = Number(frame?.wind_speed_kmh || 0);
  const direction = Number(frame?.wind_direction_deg || 0);
  const radians = (direction * Math.PI) / 180;
  return { u: -speed * Math.sin(radians), v: -speed * Math.cos(radians) };
}
function forecastApplyFarmTerrainProxy(vector, lat, lng) {
  const farm = state.latestForecast?.farm || {};
  const terrain = farm.soil_terrain || {};
  const farmLat = Number(farm.latitude), farmLng = Number(farm.longitude);
  if (![farmLat, farmLng].every(Number.isFinite)) return vector;
  const slope = Math.max(0, Number(terrain.slope_degrees || 0));
  const elevation = Math.max(0, Number(terrain.elevation_m || 0));
  if (slope < 2 && elevation < 250) return vector;
  const dy = (lat - farmLat) * 111;
  const dx = (lng - farmLng) * 111 * Math.cos((lat * Math.PI) / 180);
  const distance = Math.hypot(dx, dy);
  const radius = Math.max(4, Math.min(28, 5 + slope * .7 + elevation / 180));
  if (distance >= radius || distance < .05) return vector;
  const rx = dx / distance, ry = dy / distance;
  const influence = Math.pow(1 - distance / radius, 2) * Math.min(.55, slope / 35 + elevation / 4500);
  const inward = -(vector.u * rx + vector.v * ry);
  if (inward <= 0) return vector;
  const tangentX = -ry, tangentY = rx;
  const sign = vector.u * tangentX + vector.v * tangentY >= 0 ? 1 : -1;
  return {
    u: vector.u + rx * inward * influence + tangentX * inward * influence * .75 * sign,
    v: vector.v + ry * inward * influence + tangentY * inward * influence * .75 * sign,
  };
}
function forecastWindAt(lat, lng) {
  const frame = state.forecastWindFrame;
  if (!frame) return null;
  const fallback = forecastUniformWindVector(frame);
  const grid = forecastWindGridFromFrame(frame);
  if (!grid) return forecastApplyFarmTerrainProxy(fallback, lat, lng);
  const position = forecastGridFraction(grid, lat, lng);
  if (!position) return forecastApplyFarmTerrainProxy(fallback, lat, lng);
  const base = forecastVectorMatrixAt(grid, position.row, position.col) || fallback;
  const terrainAdjusted = forecastApplyTerrainDeflection(base, forecastTerrainAt(grid, position.row, position.col));
  return forecastApplyFarmTerrainProxy(terrainAdjusted, lat, lng);
}
function resizeForecastWindCanvas() {
  const canvas = $("forecastWindCanvas"), map = state.maps.forecast;
  if (!canvas || !map) return;
  const size = map.getSize();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(size.x * dpr); canvas.height = Math.round(size.y * dpr);
  canvas.style.width = `${size.x}px`; canvas.style.height = `${size.y}px`; canvas.dataset.pixelRatio = String(dpr);
  const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const count = Math.max(95, Math.min(340, Math.floor((size.x * size.y) / 4200)));
  state.forecastWindParticles = Array.from({ length: count }, () => ({ x:Math.random()*size.x, y:Math.random()*size.y, age:Math.random()*90 }));
}
function drawForecastWindArrow(ctx, x, y, vector, alpha) {
  const magnitude = Math.max(.001, Math.hypot(vector.u, vector.v));
  const ux = vector.u / magnitude, uyScreen = -vector.v / magnitude;
  const shaft = Math.max(7, Math.min(18, 7 + magnitude * .32));
  const x2 = x + ux * shaft, y2 = y + uyScreen * shaft;
  const head = Math.max(3.2, Math.min(5.8, shaft * .34));
  const angle = Math.atan2(y2-y, x2-x);
  ctx.globalAlpha = alpha; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x2,y2);
  ctx.moveTo(x2,y2); ctx.lineTo(x2-head*Math.cos(angle-Math.PI/6), y2-head*Math.sin(angle-Math.PI/6));
  ctx.moveTo(x2,y2); ctx.lineTo(x2-head*Math.cos(angle+Math.PI/6), y2-head*Math.sin(angle+Math.PI/6)); ctx.stroke();
}
function animateForecastWind(timestamp) {
  const canvas = $("forecastWindCanvas"), map = state.maps.forecast;
  if (!canvas || !map || state.forecastMapLayers.wind === false || !state.forecastWindFrame || state.section !== "outlook") { stopForecastWind(); return; }
  const ctx = canvas.getContext("2d"), size = map.getSize(), ratio = Number(canvas.dataset.pixelRatio || 1);
  ctx.setTransform(ratio,0,0,ratio,0,0);
  const dt = Math.min(2, Math.max(.35, (timestamp - (state.forecastWindLastFrame || timestamp)) / 16.67));
  state.forecastWindLastFrame = timestamp; ctx.clearRect(0,0,size.x,size.y);
  ctx.strokeStyle = "rgba(247,255,250,.96)"; ctx.shadowColor = "rgba(18,83,52,.45)"; ctx.shadowBlur = 2.2; ctx.lineWidth = 1.35; ctx.lineCap = "round"; ctx.lineJoin = "round";
  for (const particle of state.forecastWindParticles) {
    const latlng = map.containerPointToLatLng([particle.x,particle.y]);
    const vector = forecastWindAt(latlng.lat, latlng.lng);
    if (!vector || particle.age > 120 || particle.x < -24 || particle.y < -24 || particle.x > size.x + 24 || particle.y > size.y + 24) {
      particle.x=Math.random()*size.x; particle.y=Math.random()*size.y; particle.age=0; continue;
    }
    const magnitude = Math.max(.1, Math.hypot(vector.u,vector.v));
    const movement = Math.max(.55, Math.min(3.8, magnitude * .055)) * dt;
    drawForecastWindArrow(ctx, particle.x, particle.y, vector, Math.max(.28, 1 - particle.age / 150));
    particle.x += (vector.u/magnitude)*movement; particle.y -= (vector.v/magnitude)*movement; particle.age += 1;
  }
  ctx.globalAlpha=1; ctx.shadowBlur=0; state.forecastWindAnimation=requestAnimationFrame(animateForecastWind);
}
function startForecastWind() {
  if (state.forecastMapLayers.wind === false || !state.forecastWindFrame || state.section !== "outlook") return;
  const canvas = $("forecastWindCanvas");
  if (canvas) { canvas.hidden = false; canvas.style.display = "block"; canvas.style.opacity = "1"; }
  resizeForecastWindCanvas();
  if (!state.forecastWindParticles.length) resizeForecastWindCanvas();
  if (!state.forecastWindAnimation) { state.forecastWindLastFrame=0; state.forecastWindAnimation=requestAnimationFrame(animateForecastWind); }
}
function stopForecastWind() {
  if (state.forecastWindAnimation) cancelAnimationFrame(state.forecastWindAnimation);
  state.forecastWindAnimation=null;
  const canvas=$("forecastWindCanvas");
  if (canvas) { const ctx=canvas.getContext("2d"), ratio=Number(canvas.dataset.pixelRatio||1); ctx.setTransform(ratio,0,0,ratio,0,0); ctx.clearRect(0,0,canvas.clientWidth,canvas.clientHeight); }
}

function renderForecastWind(frame) {
  state.forecastWindFrame = frame;
  if (state.forecastMapLayers.wind === false) stopForecastWind(); else startForecastWind();
}
function updateForecastSatelliteLayer() {
  const map = state.maps.forecast;
  if (!map) return;
  const base = state.layers.forecastBase;
  if (state.forecastMapLayers.satellite === false) {
    if (state.layers.forecastSatellite && map.hasLayer(state.layers.forecastSatellite)) map.removeLayer(state.layers.forecastSatellite);
    state.layers.forecastSatellite = null;
    base?.setOpacity?.(1);
    return;
  }
  base?.setOpacity?.(0.12);
  if (!map.getPane("forecastSatellitePane")) {
    const pane = map.createPane("forecastSatellitePane");
    pane.style.zIndex = "235";
    pane.style.pointerEvents = "none";
  }
  if (state.layers.forecastSatellite && map.hasLayer(state.layers.forecastSatellite)) return;
  const url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
  state.layers.forecastSatellite = L.tileLayer(url, {
    pane: "forecastSatellitePane",
    opacity: .96,
    minZoom: 1,
    maxZoom: 19,
    tileSize: 256,
    crossOrigin: true,
    attribution: "Satellite imagery Esri World Imagery",
  }).on("tileerror", () => {
    if (!state.layers.forecastSatellite || state.layers.forecastSatellite._fallbackLoaded) return;
    state.layers.forecastSatellite._fallbackLoaded = true;
    try { map.removeLayer(state.layers.forecastSatellite); } catch (error) {}
    const date = new Date(Date.now() - 48 * 3600 * 1000).toISOString().slice(0, 10);
    state.layers.forecastSatellite = L.tileLayer(`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`, {
      pane: "forecastSatellitePane",
      opacity: .94,
      minZoom: 1,
      maxNativeZoom: 9,
      maxZoom: 19,
      tileSize: 256,
      crossOrigin: true,
      attribution: "Satellite imagery NASA EOSDIS GIBS",
    }).addTo(map);
  }).addTo(map);
}
function renderForecastMap(frame) {
  const map = state.maps.forecast;
  const bounds = frame.grid_bounds
    ? [[frame.grid_bounds.south, frame.grid_bounds.west], [frame.grid_bounds.north, frame.grid_bounds.east]]
    : forecastBounds();
  const previous = state.layers.forecastRain;
  if (state.forecastMapLayers.rain !== false) {
    const nextLayer = L.imageOverlay(drawRainDataUrl(frame), bounds, { opacity: 0, interactive: false, zIndex: 300 }).addTo(map);
    state.layers.forecastRain = nextLayer;
    requestAnimationFrame(() => nextLayer.setOpacity(1));
    if (previous) setTimeout(() => { if (map.hasLayer(previous)) map.removeLayer(previous); }, 190);
  } else {
    if (previous && map.hasLayer(previous)) map.removeLayer(previous);
    state.layers.forecastRain = null;
  }
  state.layers.forecastFarm.clearLayers();
  const farm = state.latestForecast.farm;
  const color = frame.farm_condition_score >= .75 ? "#246b32" : frame.farm_condition_score >= .55 ? "#e89008" : frame.farm_condition_score >= .35 ? "#ef8500" : "#b7463c";
  if (state.forecastMapLayers.farm !== false) {
    if (farm.polygon?.length) L.polygon(farm.polygon, { color: "#fff", weight: 3, dashArray: "7 5", fillColor: color, fillOpacity: .34 })
      .bindTooltip(`${escapeHtml(farm.name)} · ${escapeHtml(frame.condition_class)}`).addTo(state.layers.forecastFarm);
    L.circleMarker([farm.latitude, farm.longitude], { radius: 8, color: "#fff", weight: 2, fillColor: color, fillOpacity: 1 })
      .bindTooltip(farm.name).addTo(state.layers.forecastFarm);
  }
  renderForecastWind(frame);
  updateForecastSatelliteLayer();
  const legend = $("forecastLegend");
  if (legend) legend.hidden = state.forecastMapLayers.rain === false;
  fitForecastMapToFarm();
}
function updateForecastFrame(index) {
  const frames = state.visualFrames?.length
    ? state.visualFrames
    : state.latestForecast?.daily_frames?.length
      ? state.latestForecast.daily_frames
      : state.latestForecast?.frames;
  if (!frames?.length) return;
  state.forecastIndex = Math.max(0, Math.min(frames.length - 1, Number(index)));
  const f = frames[state.forecastIndex];
  const dateValue = f.date || f.week_start;
  const weekIndex = Number.isFinite(Number(f.week_index)) ? Number(f.week_index) : state.forecastIndex;
  const week = state.latestForecast?.frames?.[weekIndex] || f;
  $("forecastSlider").value = state.forecastIndex;
  const providerFrame = f.data_mode === "deterministic_short_term_forecast";
  const displayDate = f.timestamp ? new Date(f.timestamp) : new Date(`${dateValue}T00:00:00`);
  $("forecastDate").textContent = displayDate.toLocaleString(undefined, providerFrame
    ? { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }
    : { year: "numeric", month: "long", day: "numeric" });
  const sourceLabel = providerFrame ? "Open-Meteo numerical controls" : "climate-conditioned modeled weather";
  $("forecastWeekLabel").textContent = `${providerFrame ? "Hourly provider frame" : "Daily modeled snapshot"} · ${sourceLabel} · model week ${weekIndex + 1} · ${title(f.event || week.event)} · ${f.condition_class || week.condition_class}`;
  $("timelineSelected").textContent = providerFrame ? displayDate.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : dateValue;
  $("forecastModeBadge").textContent = providerFrame
    ? "OPEN-METEO · HOURLY FORECAST"
    : "LONG-TERM · DAILY MODELLED WEATHER";
  if ($("forecastResolutionLabel")) $("forecastResolutionLabel").textContent = providerFrame ? "Hourly forecast steps" : "Daily modeled snapshots";
  if ($("forecastResolutionNote")) $("forecastResolutionNote").textContent = providerFrame
    ? "Original hourly Open-Meteo numerical-model frames, aligned with Weather GIS forecast controls"
    : "Climate-conditioned projection shown daily to avoid unsupported sub-daily precision";
  $("mapRain").textContent = `${number(f.rainfall_mm, 1)} mm`;
  $("mapTemp").textContent = `${number(f.temperature_c, 1)} °C`;
  $("mapCondition").textContent = `${number(Number(f.farm_condition_score || 0) * 100, 0)}% · ${f.condition_class || week.condition_class || "—"}`;
  const dailyHusk = f.production_equivalent_kg != null ? Number(f.production_equivalent_kg) / 1000 : Number(f.production_coconut_w_husk_tons || 0);
  $("mapProduction").textContent = `${number(dailyHusk, 4)} t/day`;
  const miniSource = $("forecastMiniSource");
  if (miniSource) miniSource.textContent = providerFrame ? "Open-Meteo · provider" : "COCOAID · modeled";
  if ($("forecastMiniRain")) $("forecastMiniRain").textContent = `${number(f.rainfall_mm, 1)} mm`;
  if ($("forecastMiniTemp")) $("forecastMiniTemp").textContent = `${number(f.temperature_c, 1)} °C`;
  if ($("forecastMiniHumidity")) $("forecastMiniHumidity").textContent = f.humidity_percent == null ? "—" : `${number(f.humidity_percent, 0)}%`;
  if ($("forecastMiniCloud")) $("forecastMiniCloud").textContent = f.cloud_cover_percent == null ? "—" : `${number(f.cloud_cover_percent, 0)}%`;
  if ($("forecastMiniWind")) $("forecastMiniWind").textContent = `${number(f.wind_speed_kmh, 0)} km/h · ${number(f.wind_direction_deg, 0)}°`;
  const timelineStrip = $("forecastTimelineStrip");
  if (timelineStrip) timelineStrip.dataset.sourceMode = providerFrame ? "provider" : "model";
  state.forecastCalendarViewDate = new Date(Date.UTC(displayDate.getUTCFullYear(), displayDate.getUTCMonth(), 1));
  renderForecastCalendar();
  renderForecastMap(f);
  updateChartMarkers(weekIndex);
  if (state.health) renderHealthDonuts();
}
function forecastFrameDateKey(frame) {
  if (frame?.timestamp) {
    const date = new Date(frame.timestamp);
    if (!Number.isNaN(date.getTime())) {
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    }
  }
  return String(frame?.date || frame?.week_start || "").slice(0, 10);
}
function forecastFrameHour(frame) {
  if (!frame?.timestamp) return null;
  const date = new Date(frame.timestamp);
  return Number.isNaN(date.getTime()) ? null : date.getHours();
}
function forecastCalendarMonthDate(value) {
  const key = String(value || "").slice(0, 10);
  const parsed = new Date(`${key || isoToday()}T00:00:00Z`);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}
function renderForecastCalendar({ preserveView = false } = {}) {
  const frames = state.visualFrames || [];
  const grid = $("forecastCalendarGrid");
  const monthLabel = $("forecastCalendarMonth");
  const hourPicker = $("forecastHourPicker");
  const hourScroll = $("forecastHourScroll");
  const hourLabel = $("forecastHourLabel");
  if (!frames.length || !grid || !monthLabel || !hourPicker || !hourScroll) return;
  const selected = frames[state.forecastIndex] || frames[0];
  const selectedKey = forecastFrameDateKey(selected);
  if (!preserveView || !state.forecastCalendarViewDate) {
    const selectedDate = forecastCalendarMonthDate(selectedKey);
    state.forecastCalendarViewDate = new Date(Date.UTC(selectedDate.getUTCFullYear(), selectedDate.getUTCMonth(), 1));
  }
  const view = new Date(state.forecastCalendarViewDate);
  const year = view.getUTCFullYear();
  const month = view.getUTCMonth();
  monthLabel.textContent = view.toLocaleDateString(undefined, { month: "long", year: "numeric", timeZone: "UTC" });
  const byDate = new Map();
  frames.forEach((frame, index) => {
    const key = forecastFrameDateKey(frame);
    if (!key) return;
    if (!byDate.has(key)) byDate.set(key, []);
    byDate.get(key).push(index);
  });
  const firstWeekday = new Date(Date.UTC(year, month, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  const cells = [];
  for (let i = 0; i < firstWeekday; i += 1) cells.push('<span class="calendar-empty" aria-hidden="true"></span>');
  for (let day = 1; day <= daysInMonth; day += 1) {
    const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const indices = byDate.get(key) || [];
    const hasProvider = indices.some((index) => frames[index]?.data_mode === "deterministic_short_term_forecast");
    const hasModel = indices.some((index) => frames[index]?.data_mode !== "deterministic_short_term_forecast");
    const classes = ["forecast-calendar-day"];
    if (!indices.length) classes.push("unavailable");
    else classes.push(hasProvider ? "provider-day" : hasModel ? "model-day" : "available");
    if (key === selectedKey) classes.push("selected");
    cells.push(`<button class="${classes.join(" ")}" data-forecast-date="${key}" ${indices.length ? "" : "disabled"} type="button"><span>${day}</span><i aria-hidden="true"></i></button>`);
  }
  grid.innerHTML = cells.join("");
  grid.querySelectorAll("[data-forecast-date]").forEach((button) => button.addEventListener("click", () => {
    const indices = byDate.get(button.dataset.forecastDate) || [];
    if (!indices.length) return;
    const currentHour = forecastFrameHour(selected);
    let target = indices[0];
    if (currentHour != null) {
      const matching = indices.find((index) => forecastFrameHour(frames[index]) === currentHour);
      if (matching != null) target = matching;
    }
    updateForecastFrame(target);
  }));
  const selectedIndices = byDate.get(selectedKey) || [];
  const providerIndices = selectedIndices.filter((index) => frames[index]?.data_mode === "deterministic_short_term_forecast");
  const providerSelected = selected?.data_mode === "deterministic_short_term_forecast" && providerIndices.length;
  hourPicker.hidden = !providerSelected;
  hourScroll.innerHTML = "";
  if (providerSelected) {
    const selectedHour = forecastFrameHour(selected);
    if (hourLabel) hourLabel.textContent = `${selectedKey} · hourly Open-Meteo frames · local time`;
    hourScroll.innerHTML = providerIndices.map((index) => {
      const frame = frames[index];
      const date = frame?.timestamp ? new Date(frame.timestamp) : null;
      const label = date && !Number.isNaN(date.getTime())
        ? date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
        : "—";
      return `<button class="forecast-hour-button${index === state.forecastIndex ? " selected" : ""}" data-forecast-index="${index}" type="button">${label}</button>`;
    }).join("");
    hourScroll.querySelectorAll("[data-forecast-index]").forEach((button) => button.addEventListener("click", () => updateForecastFrame(Number(button.dataset.forecastIndex))));
  } else if (hourLabel) {
    hourLabel.textContent = "Daily modeled snapshot";
  }
  const minDate = forecastCalendarMonthDate(forecastFrameDateKey(frames[0]));
  const maxDate = forecastCalendarMonthDate(forecastFrameDateKey(frames.at(-1)));
  const prev = $("forecastCalendarPrev"), next = $("forecastCalendarNext");
  if (prev) prev.disabled = year < minDate.getUTCFullYear() || (year === minDate.getUTCFullYear() && month <= minDate.getUTCMonth());
  if (next) next.disabled = year > maxDate.getUTCFullYear() || (year === maxDate.getUTCFullYear() && month >= maxDate.getUTCMonth());
}
function shiftForecastCalendarMonth(delta) {
  const current = state.forecastCalendarViewDate || forecastCalendarMonthDate(forecastFrameDateKey(state.visualFrames?.[state.forecastIndex]));
  state.forecastCalendarViewDate = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + Number(delta || 0), 1));
  renderForecastCalendar({ preserveView: true });
}

function setForecastMapLayer(name, visible) {
  if (!(name in state.forecastMapLayers)) return;
  state.forecastMapLayers[name] = Boolean(visible);
  document.querySelectorAll(`[data-forecast-map-layer="${name}"]`).forEach((button) => {
    button.classList.toggle("active", Boolean(visible));
    button.setAttribute("aria-pressed", String(Boolean(visible)));
    const status = button.querySelector(".forecast-layer-status") || button.querySelector(":scope > b");
    if (status) status.textContent = visible ? "ON" : "OFF";
  });
  if (name === "satellite") updateForecastSatelliteLayer();
  if (name === "wind" && !visible) stopForecastWind();
  const frame = state.visualFrames?.[state.forecastIndex] || state.latestForecast?.daily_frames?.[state.forecastIndex] || state.latestForecast?.frames?.[state.forecastIndex];
  if (frame && state.latestForecast) renderForecastMap(frame);
}


function setForecastPanel(name, forceOpen = null) {
  const bodies = Array.from(document.querySelectorAll("[data-forecast-panel-body]"));
  const timeline = $("forecastTimelineDock");
  if (name === "timeline") {
    if (!timeline) return;
    const shouldOpen = forceOpen == null ? !timeline.classList.contains("calendar-open") : Boolean(forceOpen);
    if (shouldOpen) {
      bodies.filter((body) => body !== timeline).forEach((body) => body.classList.remove("open"));
      renderForecastCalendar();
    }
    timeline.classList.toggle("calendar-open", shouldOpen);
    const toggle = $("forecastTimelineCollapse");
    toggle?.setAttribute("aria-expanded", String(shouldOpen));
    toggle?.setAttribute("aria-label", shouldOpen ? "Close forecast calendar" : "Open forecast calendar");
  } else {
    const target = bodies.find((body) => body.dataset.forecastPanelBody === name);
    if (!target) return;
    const shouldOpen = forceOpen == null ? !target.classList.contains("open") : Boolean(forceOpen);
    if (shouldOpen) {
      bodies.filter((body) => body !== target && body !== timeline).forEach((body) => body.classList.remove("open"));
      timeline?.classList.remove("calendar-open");
      $("forecastTimelineCollapse")?.setAttribute("aria-expanded", "false");
    }
    target.classList.toggle("open", shouldOpen);
    if (name === "graphs" && shouldOpen) setTimeout(() => Object.values(state.charts).forEach((chart) => chart?.resize?.()), 180);
  }
  document.querySelectorAll("[data-forecast-panel]").forEach((button) => {
    const panelName = button.dataset.forecastPanel;
    const active = panelName === "timeline"
      ? Boolean(timeline?.classList.contains("calendar-open"))
      : Boolean(document.querySelector(`[data-forecast-panel-body="${panelName}"]`)?.classList.contains("open"));
    button.classList.toggle("active", active);
    button.setAttribute("aria-expanded", String(active));
  });
  setTimeout(() => { state.maps.forecast?.invalidateSize?.(); resizeForecastWindCanvas(); startForecastWind(); }, 180);
}

function toggleForecastPlay() {
  if (state.forecastTimer) {
    clearInterval(state.forecastTimer);
    state.forecastTimer = null;
    $("forecastPlay").textContent = "▶";
    return;
  }
  $("forecastPlay").textContent = "Ⅱ";
  const intervalMs = 500;
  state.forecastTimer = setInterval(() => {
    const frames = state.visualFrames || [];
    if (!frames.length) return;
    updateForecastFrame((state.forecastIndex + 1) % frames.length);
  }, intervalMs);
}
function hazardDateKey(value) { return String(value || "").slice(0, 10); }
function hazardCalendarDate(value) {
  const parsed = new Date(`${hazardDateKey(value) || isoToday()}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}
function hazardEventsForDay(events, key) {
  const day = new Date(`${key}T12:00:00`).getTime();
  return events.map((event, index) => ({ event, index })).filter(({ event }) => {
    const start = new Date(`${hazardDateKey(event.start_date)}T00:00:00`).getTime();
    const end = new Date(`${hazardDateKey(event.end_date || event.start_date)}T23:59:59`).getTime();
    return day >= start && day <= end;
  });
}
function hazardDotClass(event) {
  const severity = Number(event.severity_percent ?? event.peak_severity * 100) || 0;
  if (severity >= 70) return "severe";
  return event.data_mode === "deterministic_short_term_forecast" ? "provider" : "modeled";
}
function renderHazardCalendar(events = state.latestForecast?.extreme_events || [], { preserveView = false } = {}) {
  const root = $("hazardDateRail");
  if (!root) return;
  if (!events.length) { root.innerHTML = '<div class="empty-state">No hazard dates to display.</div>'; return; }
  const selected = events[Math.max(0, Math.min(events.length - 1, state.hazardIndex || 0))] || events[0];
  if (!preserveView || !state.hazardCalendarViewDate) {
    const base = hazardCalendarDate(selected.start_date);
    state.hazardCalendarViewDate = new Date(base.getFullYear(), base.getMonth(), 1);
  }
  const view = new Date(state.hazardCalendarViewDate);
  const year = view.getFullYear(), month = view.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < firstWeekday; i += 1) cells.push('<span class="hazard-calendar-empty"></span>');
  for (let day = 1; day <= days; day += 1) {
    const date = new Date(year, month, day);
    const key = `${year}-${String(month + 1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
    const hits = hazardEventsForDay(events, key);
    const eventIndex = hits[0]?.index;
    const selectedDay = hits.some(({ index }) => index === state.hazardIndex);
    const dots = hits.slice(0,3).map(({ event }) => `<i class="${hazardDotClass(event)}"></i>`).join("");
    cells.push(`<button type="button" class="hazard-calendar-day${hits.length ? " has-event" : ""}${selectedDay ? " selected" : ""}" ${hits.length ? `data-hazard-index="${eventIndex}"` : "disabled"} aria-label="${key}${hits.length ? ` · ${hits.map(({event}) => escapeHtml(event.label)).join(", ")}` : " · no flagged event"}"><span>${day}</span><em>${dots}</em></button>`);
  }
  root.innerHTML = `<div class="hazard-calendar-head"><button type="button" id="hazardCalendarPrev" aria-label="Previous month">‹</button><div><span>EVENT CALENDAR</span><strong>${view.toLocaleString(undefined,{month:"long",year:"numeric"})}</strong></div><button type="button" id="hazardCalendarNext" aria-label="Next month">›</button></div><div class="hazard-calendar-weekdays" aria-hidden="true"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div><div class="hazard-calendar-grid">${cells.join("")}</div>`;
  root.querySelector("#hazardCalendarPrev")?.addEventListener("click", () => shiftHazardCalendarMonth(-1));
  root.querySelector("#hazardCalendarNext")?.addEventListener("click", () => shiftHazardCalendarMonth(1));
  root.querySelectorAll("[data-hazard-index]").forEach((button) => button.addEventListener("click", () => highlightHazard(Number(button.dataset.hazardIndex), { scroll:false })));
}
function shiftHazardCalendarMonth(delta) {
  const current = state.hazardCalendarViewDate || new Date();
  state.hazardCalendarViewDate = new Date(current.getFullYear(), current.getMonth() + Number(delta || 0), 1);
  renderHazardCalendar(state.latestForecast?.extreme_events || [], { preserveView:true });
}

function renderHazards(events) {
  state.hazardIndex = events.length
    ? Math.max(0, Math.min(events.length - 1, Number(state.hazardIndex) || 0))
    : 0;
  const previousButton = $("hazardPrevEvent");
  const nextButton = $("hazardNextEvent");
  if (previousButton) previousButton.disabled = events.length <= 1;
  if (nextButton) nextButton.disabled = events.length <= 1;
  $("hazardCount").textContent = events.length;
  $("hazardPeak").textContent = events.length
    ? `${number(Math.max(...events.map((e) => e.severity_percent ?? e.peak_severity * 100)), 1)}/100`
    : "0/100";
  $("hazardLoss").textContent = `${number(
    events.reduce(
      (sum, event) => sum + Number(event.estimated_production_loss_tons || 0),
      0,
    ),
    2,
  )} t`;
  const maximumTrees = events.length ? Math.max(...events.map((e) => e.estimated_trees_affected || 0)) : 0;
  $("hazardTrees").textContent = events.length ? number(maximumTrees, 0) : "0";
  const peakSeverity = events.length ? Math.max(...events.map((e) => Number(e.severity_percent ?? e.peak_severity * 100) || 0)) : 0;
  const summedLossPercent = events.reduce((sum, event) => sum + Math.max(0, Number(event.loss_percent_of_event_baseline || 0)), 0);
  setHazardGauge("hazardCountGauge", Math.min(100, events.length * 10));
  setHazardGauge("hazardPeakGauge", peakSeverity);
  setHazardGauge("hazardLossGauge", Math.min(100, summedLossPercent));
  setHazardGauge("hazardTreesGauge", treeTotal() > 0 ? Math.min(100, maximumTrees / treeTotal() * 100) : 0);

  renderHazardCalendar(events);

  $("hazardTimeline").innerHTML = events.length
    ? events
        .map((event, index) => {
          const severity = Number(
            event.severity_percent ?? event.peak_severity * 100,
          );
          const lossPercent = Number(event.loss_percent_of_event_baseline || 0);
          const source = event.data_mode === "deterministic_short_term_forecast" ? "Provider" : "Modeled";
          return `<button type="button" class="hazard-item ${escapeHtml(event.event_type)}" data-hazard-index="${index}">
            <div class="hazard-list-date"><time>${escapeHtml(event.start_date)}</time><small>${escapeHtml(event.end_date)}</small></div>
            <div class="hazard-item-body"><div class="hazard-item-title"><strong>${escapeHtml(event.label)}</strong><span>${number(severity, 0)}/100</span></div>
            <div class="hazard-item-meta"><span>${escapeHtml(source)}</span><span>${escapeHtml(hazardEventWeatherChip(event))}</span><span>${number(event.estimated_production_loss_tons || 0, 2)} t loss</span><span>${number(event.estimated_trees_affected || 0, 0)} trees</span></div></div>
          </button>`;
        })
        .join("")
    : '<div class="empty-state">No major event periods were flagged.</div>';

  replaceChart("hazard", "hazardChart", {
    type: "bar",
    data: {
      labels: events.map((event) => event.start_date),
      datasets: [
        {
          label: "Severity score",
          data: events.map(
            (event) => event.severity_percent ?? event.peak_severity * 100,
          ),
          backgroundColor: "rgba(255,122,40,.74)",
          borderColor: "#ef8500",
          yAxisID: "y",
        },
        {
          label: "Estimated loss (t)",
          data: events.map((event) => event.estimated_production_loss_tons),
          backgroundColor: "rgba(191,58,47,.72)",
          borderColor: "#b83f35",
          yAxisID: "y1",
        },
      ],
    },
    options: {
      ...chartOptions("Severity score", {
        scales: {
          x: {
            grid: { display: false },
            ticks: { autoSkip: true, maxTicksLimit: 10 },
          },
          y: {
            position: "left",
            min: 0,
            max: 100,
            title: { display: true, text: "Severity (0-100)" },
          },
          y1: {
            position: "right",
            beginAtZero: true,
            title: { display: true, text: "Estimated loss (t)" },
            grid: { drawOnChartArea: false },
          },
        },
      }),
      onClick: (_, elements) => {
        if (!elements.length) return;
        highlightHazard(elements[0].index);
      },
    },
  });
  document
    .querySelectorAll("[data-hazard-index]")
    .forEach((element) =>
      element.addEventListener("click", () =>
        highlightHazard(Number(element.dataset.hazardIndex)),
      ),
    );
  if (events.length) highlightHazard(state.hazardIndex, { scroll: false });
}

function nearestForecastFrameForDate(dateValue) {
  const target = new Date(`${String(dateValue || "").slice(0,10)}T12:00:00`);
  if (Number.isNaN(target.getTime())) return state.visualFrames?.[state.forecastIndex] || null;
  let best = null, bestDistance = Infinity;
  for (const frame of state.visualFrames || []) {
    const raw = frame?.timestamp || frame?.date || frame?.week_start;
    if (!raw) continue;
    const when = new Date(String(raw).length <= 10 ? `${raw}T12:00:00` : raw);
    const distance = Math.abs(when.getTime() - target.getTime());
    if (distance < bestDistance) { best = frame; bestDistance = distance; }
  }
  return best || state.visualFrames?.[state.forecastIndex] || null;
}
function hazardIconMarkup(kind) {
  const icons = {
    typhoon:'<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M48 13c-12 0-23 8-27 19 5-5 12-8 19-7-3 3-5 7-5 12 0 8 6 14 14 14-6 2-13 1-19-3-10-7-14-20-9-31 5-10 15-17 27-18z"/><circle cx="39" cy="35" r="5"/></svg>',
    drought:'<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="25" r="11"/><path d="M32 4v8M32 38v8M11 25h8M45 25h8M17 10l6 6M41 34l6 6M47 10l-6 6M23 34l-6 6M12 54h40M20 46l6 8 6-8 6 8 6-8"/></svg>',
    extreme_rain:'<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M18 34h29a10 10 0 0 0 0-20 15 15 0 0 0-28-2A11 11 0 0 0 18 34z"/><path d="M23 40l-4 10M34 40l-4 10M45 40l-4 10"/></svg>',
    heavy_rain_forecast:'<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M18 34h29a10 10 0 0 0 0-20 15 15 0 0 0-28-2A11 11 0 0 0 18 34z"/><path d="M23 40l-4 10M34 40l-4 10M45 40l-4 10"/></svg>',
    rain_forecast:'<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M18 34h29a10 10 0 0 0 0-20 15 15 0 0 0-28-2A11 11 0 0 0 18 34z"/><path d="M28 41l-3 8M41 41l-3 8"/></svg>',
    heat_stress:'<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="41" cy="18" r="8"/><path d="M41 4v5M41 27v5M27 18h5M50 18h5M17 9v29a11 11 0 1 0 12 0V9a6 6 0 0 0-12 0zM23 19v25"/></svg>'
  };
  return icons[kind] || '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M12 38h39a11 11 0 0 0 0-22 16 16 0 0 0-30-2A12 12 0 0 0 12 38z"/><path d="M18 47h30"/></svg>';
}
function hazardWeatherPalette(kind) {
  if (kind === "drought" || kind === "heat_stress") return ["#ffcc3d","#ff7a22","#c8372f"];
  if (kind === "typhoon") return ["#5ed0ff","#7b5cff","#ef4fa2"];
  return ["#56d9ff","#3479f6","#8b43d2"];
}
function drawHazardWeatherDataUrl(event) {
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 560;
  const ctx = canvas.getContext("2d");
  const severity = Math.max(.18, Math.min(1, Number(event?.severity_percent ?? event?.peak_severity * 100) / 100 || .35));
  const colors = hazardWeatherPalette(String(event?.event_type || ""));
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#11161a");
  gradient.addColorStop(.55, "#20262b");
  gradient.addColorStop(1, "#0f1519");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // Greyscale satellite texture
  for (let i = 0; i < 130; i += 1) {
    const x = Math.random() * canvas.width;
    const y = Math.random() * canvas.height;
    const radius = 22 + Math.random() * 160;
    const alpha = .015 + Math.random() * .055;
    const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
    g.addColorStop(0, `rgba(255,255,255,${alpha})`);
    g.addColorStop(.6, `rgba(180,190,196,${alpha * .7})`);
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }
  // Stylized storm masses similar to TV weather maps.
  const cells = [
    [.18, .42, .22 * severity + .16, 1.0],
    [.34, .46, .18 * severity + .11, .82],
    [.54, .51, .17 * severity + .13, .72],
    [.75, .32, .11 * severity + .08, .58],
    [.84, .69, .14 * severity + .09, .66],
  ];
  cells.forEach(([x, y, r, w], idx) => {
    const cx = canvas.width * x;
    const cy = canvas.height * y;
    const radius = canvas.width * r;
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    g.addColorStop(0, idx === 0 ? "rgba(255,32,18,.98)" : "rgba(255,80,28,.92)");
    g.addColorStop(.2, "rgba(255,115,28,.94)");
    g.addColorStop(.38, "rgba(255,208,25,.90)");
    g.addColorStop(.58, "rgba(70,177,255,.86)");
    g.addColorStop(.78, "rgba(27,78,255,.72)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = w;
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(cx, cy, radius * 1.08, radius * (.66 + idx * .03), -0.55 + idx * .18, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;
  // green coast / grid hints
  ctx.strokeStyle = "rgba(61, 198, 93, .62)";
  ctx.lineWidth = 1.2;
  for (let x = 68; x < canvas.width; x += 128) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 48; y < canvas.height; y += 110) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  // stylized regional outlines.
  [[.08,.25],[.13,.16],[.2,.11],[.27,.18],[.23,.28],[.15,.31],[.1,.28]].forEach((_,i,a)=>{
    const [sx,sy]=a[i], [px,py]=a[(i-1+a.length)%a.length];
    if(i===0){ctx.beginPath(); ctx.moveTo(canvas.width*sx, canvas.height*sy);} else ctx.lineTo(canvas.width*sx, canvas.height*sy);
  });
  ctx.stroke();
  [[.42,.54],[.45,.48],[.49,.46],[.52,.51],[.51,.58],[.47,.61],[.43,.58]].forEach((_,i,a)=>{
    const [sx,sy]=a[i];
    if(i===0){ctx.beginPath(); ctx.moveTo(canvas.width*sx, canvas.height*sy);} else ctx.lineTo(canvas.width*sx, canvas.height*sy);
  });
  ctx.stroke();
  // red tracking boxes similar to forecast-news framing.
  ctx.strokeStyle = "rgba(248, 58, 46, .92)";
  ctx.lineWidth = 4;
  ctx.strokeRect(canvas.width * .23, canvas.height * .06, canvas.width * .5, canvas.height * .72);
  ctx.strokeStyle = "rgba(243, 63, 51, .78)";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(canvas.width * .39, canvas.height * .03);
  ctx.lineTo(canvas.width * .27, canvas.height * .26);
  ctx.lineTo(canvas.width * .21, canvas.height * .42);
  ctx.stroke();
  // light scan lines.
  ctx.globalCompositeOperation = "screen";
  for (let y = 0; y < canvas.height; y += 8) {
    ctx.fillStyle = `rgba(255,255,255,${(y % 24 === 0 ? .045 : .018) * severity})`;
    ctx.fillRect(0, y, canvas.width, 1);
  }
  ctx.globalCompositeOperation = "source-over";
  return canvas.toDataURL("image/png");
}
function renderHazardWeatherMap(event) {
  const map = state.maps.hazard; const group = state.layers.hazard; if (!map || !group || !event) return;
  group.clearLayers();
  const bounds = farmForecastBounds() || L.latLngBounds(forecastBounds());
  const expanded = bounds.pad(1.05);
  L.imageOverlay(drawHazardWeatherDataUrl(event), expanded, { opacity:.82, interactive:false }).addTo(group);
  const farm = state.latestForecast?.farm;
  if (Array.isArray(farm?.polygon) && farm.polygon.length >= 3) {
    L.polygon(farm.polygon, { color:"#42d969", weight:2.2, opacity:.95, fillColor:"#ff9b28", fillOpacity:.08 }).addTo(group);
  }
  const trackingBounds = bounds.pad(.25);
  L.rectangle(trackingBounds, { color:"#ff4338", weight:2.3, fill:false, opacity:.95, interactive:false }).addTo(group);
  const center = bounds.getCenter();
  L.marker(center, { interactive:false, icon:L.divIcon({ className:"hazard-map-event-marker", html:`<div><span>${Math.round(Number(event.severity_percent ?? event.peak_severity * 100) || 0)}</span><small>${escapeHtml(String(event.label || "Weather"))}</small></div>`, iconSize:null }) }).addTo(group);
  requestAnimationFrame(() => { map.invalidateSize({ pan:false }); map.fitBounds(expanded, { padding:[18,18], maxZoom:11, animate:false }); });
}
function eventFramesForWindow(event) {
  const startKey = String(event?.start_date || "").slice(0, 10);
  const endKey = String(event?.end_date || event?.start_date || "").slice(0, 10);
  if (!startKey) return [];
  const source = state.visualFrames?.length ? state.visualFrames : (state.latestForecast?.daily_frames || []);
  return source.filter((frame) => {
    const key = String(frame?.date || frame?.timestamp || frame?.week_start || "").slice(0, 10);
    return key && key >= startKey && key <= endKey;
  });
}
function hazardEventWeatherSummary(event) {
  const kind = String(event?.event_type || "").toLowerCase();
  const frames = eventFramesForWindow(event);
  const rainValues = frames.map((frame) => Math.max(0, Number(frame?.rainfall_mm || 0))).filter(Number.isFinite);
  const tempValues = frames.map((frame) => Number(frame?.temperature_max_c ?? frame?.temperature_c)).filter(Number.isFinite);
  const meanTempValues = frames.map((frame) => Number(frame?.temperature_c)).filter(Number.isFinite);
  const windValues = frames.map((frame) => ({ speed: Math.max(0, Number(frame?.wind_speed_kmh || 0)), direction: Number(frame?.wind_direction_deg || 0) })).filter((item) => Number.isFinite(item.speed));
  const humidities = frames.map((frame) => Number(frame?.humidity_percent)).filter(Number.isFinite);
  const peakWind = windValues.reduce((best, item) => item.speed >= best.speed ? item : best, { speed: 0, direction: 0 });
  const frameRainTotal = rainValues.reduce((sum, value) => sum + value, 0);
  const frameRainPeak = rainValues.length ? Math.max(0, ...rainValues) : 0;
  const frameTempPeak = tempValues.length ? Math.max(0, ...tempValues) : 0;
  let rainTotal = Number.isFinite(Number(event?.event_rainfall_total_mm)) ? Number(event.event_rainfall_total_mm) : frameRainTotal;
  let rainPeak = Number.isFinite(Number(event?.event_peak_week_rainfall_mm)) ? Number(event.event_peak_week_rainfall_mm) : frameRainPeak;
  let tempPeak = Number.isFinite(Number(event?.event_peak_temperature_c)) && Number(event.event_peak_temperature_c) > 0 ? Number(event.event_peak_temperature_c) : frameTempPeak;
  if (kind.includes("rain") && rainTotal <= 0 && frameRainTotal > 0) rainTotal = frameRainTotal;
  if (kind.includes("rain") && rainPeak <= 0 && frameRainPeak > 0) rainPeak = frameRainPeak;
  if (kind === "heat_stress" && tempPeak < 32 && frameTempPeak >= 32) tempPeak = frameTempPeak;
  if (kind === "heat_stress" && rainTotal > 0 && frameRainTotal <= 0) rainTotal = 0;
  return {
    rainTotal,
    rainPeak,
    tempPeak,
    tempMean: meanTempValues.length ? meanTempValues.reduce((sum, value) => sum + value, 0) / meanTempValues.length : 0,
    windPeak: Number.isFinite(Number(event?.event_peak_wind_kmh)) ? Number(event.event_peak_wind_kmh) : peakWind.speed,
    windDirection: Number.isFinite(Number(event?.event_peak_wind_direction_deg)) ? Number(event.event_peak_wind_direction_deg) : peakWind.direction,
    humidityMean: Number.isFinite(Number(event?.event_mean_humidity_percent)) ? Number(event.event_mean_humidity_percent) : (humidities.length ? humidities.reduce((sum, value) => sum + value, 0) / humidities.length : 0),
  };
}
function hazardEventWeatherChip(event) {
  const kind = String(event?.event_type || "").toLowerCase();
  const summary = hazardEventWeatherSummary(event);
  if (kind === "heat_stress") return `${number(summary.tempPeak, 1)} °C peak`;
  if (kind === "drought") return `${number(summary.rainTotal, 1)} mm event rain`;
  if (kind === "typhoon") return `${number(summary.windPeak, 0)} km/h peak wind`;
  if (kind.includes("rain")) return `${number(summary.rainTotal, 1)} mm event rain`;
  return `${number(summary.tempPeak || summary.tempMean, 1)} °C`;
}
function hazardEventBriefText(event, summary) {
  const kind = String(event?.event_type || "").toLowerCase();
  if (kind === "heat_stress") return `Heat stress is supported by a ${number(summary.tempPeak,1)} °C event-period peak temperature.`;
  if (kind === "drought") return `Drought pressure spans the flagged period with only ${number(summary.rainTotal,1)} mm of accumulated rain.`;
  if (kind === "typhoon") return `Typhoon exposure peaks near ${number(summary.windPeak,0)} km/h with ${number(summary.rainTotal,1)} mm of event-period rain.`;
  if (kind.includes("rain")) return `${event?.label || "Rain event"} accumulates ${number(summary.rainTotal,1)} mm across the flagged period; the wettest modeled week contributes ${number(summary.rainPeak,1)} mm.`;
  return `This event is summarized from all available weather frames inside the flagged period.`;
}
function setHazardGauge(id, value) {
  const element = $(id); if (!element) return;
  element.style.setProperty("--value", `${Math.max(0, Math.min(100, Number(value) || 0))}%`);
}

function updateHazardVisual(event) {
  const kind = String(event?.event_type || "");
  const icon = $("hazardEventIcon");
  if (icon) { icon.className = `hazard-event-icon ${kind}`; icon.innerHTML = hazardIconMarkup(kind); }
  const summary = hazardEventWeatherSummary(event);
  if ($("hazardWeatherRain")) $("hazardWeatherRain").textContent = `${number(summary.rainTotal, 1)} mm total`;
  if ($("hazardWeatherTemp")) $("hazardWeatherTemp").textContent = `${number(summary.tempPeak, 1)} °C peak`;
  if ($("hazardWeatherWind")) $("hazardWeatherWind").textContent = `${number(summary.windPeak, 1)} km/h · ${number(summary.windDirection, 0)}°`;
  if ($("hazardWeatherHumidity")) $("hazardWeatherHumidity").textContent = `${number(summary.humidityMean, 0)}% mean`;
  if ($("hazardEventBrief")) $("hazardEventBrief").textContent = hazardEventBriefText(event, summary);
  renderHazardForecastSnapshot(event);
}

function hazardRepresentativeForecastFrame(event) {
  const frames = eventFramesForWindow(event);
  if (!frames.length) return nearestForecastFrameForDate(event?.start_date);
  const kind = String(event?.event_type || "").toLowerCase();
  const metric = (frame) => {
    if (kind === "heat_stress") return Number(frame?.temperature_max_c ?? frame?.temperature_c ?? -Infinity);
    if (kind === "typhoon") return Number(frame?.wind_speed_kmh ?? -Infinity);
    if (kind === "drought") return -Number(frame?.rainfall_mm ?? 0);
    if (kind.includes("rain")) return Number(frame?.rainfall_mm ?? -Infinity);
    return Number(frame?.rainfall_mm ?? 0) + Number(frame?.wind_speed_kmh ?? 0) / 10;
  };
  return frames.reduce((best, frame) => metric(frame) > metric(best) ? frame : best, frames[0]);
}
function renderHazardForecastSnapshot(event) {
  const map = state.maps.hazardSnapshot;
  const group = state.layers.hazardSnapshot;
  if (!map || !group || !event || !state.latestForecast) return;
  const frame = hazardRepresentativeForecastFrame(event);
  if (!frame) return;
  group.clearLayers();
  const bounds = frame.grid_bounds
    ? L.latLngBounds([[frame.grid_bounds.south,frame.grid_bounds.west],[frame.grid_bounds.north,frame.grid_bounds.east]])
    : (farmForecastBounds()?.pad(.8) || L.latLngBounds(forecastBounds()));
  L.imageOverlay(drawRainDataUrl(frame), bounds, { opacity:.92, interactive:false }).addTo(group);
  const farm = state.latestForecast.farm;
  if (farm?.polygon?.length) L.polygon(farm.polygon, { color:"#ffffff", weight:3, dashArray:"6 4", fillColor:"#f28b23", fillOpacity:.08, interactive:false }).addTo(group);
  if (Number.isFinite(Number(farm?.latitude)) && Number.isFinite(Number(farm?.longitude))) {
    L.circleMarker([Number(farm.latitude),Number(farm.longitude)], { radius:6, color:"#fff", weight:2, fillColor:"#f28b23", fillOpacity:1, interactive:false }).addTo(group);
  }
  const label = frame.timestamp ? new Date(frame.timestamp).toLocaleString([], {year:"numeric",month:"short",day:"numeric",hour:"numeric"}) : String(frame.date || frame.week_start || event.start_date || "");
  if ($("hazardSnapshotDate")) $("hazardSnapshotDate").textContent = label;
  if ($("hazardSnapshotTitle")) $("hazardSnapshotTitle").textContent = `${event.label || title(event.event_type || "Weather event")} · ${number(frame.rainfall_mm || 0,1)} mm rain · ${number(frame.temperature_max_c ?? frame.temperature_c,1)} °C`;
  if ($("hazardSnapshotSource")) $("hazardSnapshotSource").textContent = frame.data_mode === "deterministic_short_term_forecast" ? "Exact Open-Meteo hourly frame used by Model Forecast" : "Exact COCOAID long-term modeled frame used by Model Forecast";
  state.hazardSnapshotFrame = frame;
  requestAnimationFrame(() => { map.invalidateSize({pan:false}); map.fitBounds(bounds, {padding:[16,16],maxZoom:13,animate:false}); });
}
function openSelectedHazardInForecast() {
  const frame = state.hazardSnapshotFrame;
  if (!frame) return toast("Select a hazard with an available forecast frame first.", true);
  const frames = state.visualFrames || [];
  const targetKey = String(frame.timestamp || frame.date || frame.week_start || "");
  let index = frames.findIndex((item) => String(item.timestamp || item.date || item.week_start || "") === targetKey);
  if (index < 0) index = frames.findIndex((item) => String(item.date || item.week_start || "").slice(0,10) === targetKey.slice(0,10));
  showSection("outlook");
  if (index >= 0) setTimeout(() => updateForecastFrame(index), 180);
}

function changeHazardEvent(delta) {
  const events = state.latestForecast?.extreme_events || [];
  if (!events.length) return;
  state.hazardIndex = (state.hazardIndex + Number(delta) + events.length) % events.length;
  highlightHazard(state.hazardIndex, { scroll: false });
}

function hazardFirstAction(event) {
  const kind = String(event?.event_type || "").toLowerCase();
  if (kind === "typhoon") return "Secure loose farm materials, avoid unsafe field work, and plan a post-storm tree and drainage inspection.";
  if (kind === "drought") return "Check soil moisture and palm stress first; prioritize water conservation and moisture-retention practices where available.";
  if (kind === "extreme_rain" || kind === "heavy_rain_forecast" || kind === "rain_forecast") return "Inspect drainage paths and low areas before the event, then check roots and standing water after rainfall.";
  if (kind === "heat_stress") return "Inspect palms for heat and moisture stress and prioritize soil-moisture monitoring during the flagged period.";
  return "Inspect the farm area most exposed to this event and use the detailed impact estimate to prioritize field checks.";
}

function highlightHazard(index, options = {}) {
  const events = state.latestForecast?.extreme_events || [];
  if (!events.length) return;
  const boundedIndex = Math.max(0, Math.min(events.length - 1, Number(index) || 0));
  state.hazardIndex = boundedIndex;
  const selectedEvent = events[boundedIndex];
  const selectedSeverity = Number(selectedEvent.severity_percent ?? selectedEvent.peak_severity * 100) || 0;
  const selectedLossPercent = Number(selectedEvent.loss_percent_of_event_baseline || 0);
  if ($("hazardFocusType")) $("hazardFocusType").textContent = selectedEvent.label || title(selectedEvent.event_type || "weather event");
  if ($("hazardFocusWindow")) $("hazardFocusWindow").textContent = `${selectedEvent.start_date} to ${selectedEvent.end_date}`;
  if ($("hazardFocusPosition")) $("hazardFocusPosition").textContent = `${boundedIndex + 1} / ${events.length}`;
  if ($("hazardFocusSeverity")) $("hazardFocusSeverity").textContent = `${number(selectedSeverity, 1)}/100`;
  if ($("hazardFocusSeverityBar")) $("hazardFocusSeverityBar").style.width = `${Math.min(100, Math.max(0, selectedSeverity))}%`;
  if ($("hazardFocusLoss")) $("hazardFocusLoss").textContent = `${number(selectedEvent.estimated_production_loss_tons || 0, 2)} t · ${number(selectedLossPercent, 1)}%`;
  if ($("hazardFocusLossBar")) $("hazardFocusLossBar").style.width = `${Math.min(100, Math.max(0, selectedLossPercent))}%`;
  if ($("hazardFocusSummary")) $("hazardFocusSummary").textContent = selectedEvent.impact_summary || "No additional impact summary was returned.";
  if ($("hazardFocusTrees")) $("hazardFocusTrees").textContent = number(selectedEvent.estimated_trees_affected || 0, 0);
  if ($("hazardFocusConfidence")) $("hazardFocusConfidence").textContent = selectedEvent.confidence || "Not specified";
  if ($("hazardFocusSource")) $("hazardFocusSource").textContent = selectedEvent.data_mode === "deterministic_short_term_forecast" ? "Open-Meteo provider window" : "COCOAID modeled scenario";
  if ($("hazardFocusAction")) $("hazardFocusAction").textContent = hazardFirstAction(selectedEvent);
  updateHazardVisual(selectedEvent);
  document
    .querySelectorAll("[data-hazard-index]")
    .forEach((element) =>
      element.classList.toggle(
        "active",
        Number(element.dataset.hazardIndex) === boundedIndex,
      ),
    );
  if (options.scroll !== false) {
    document
      .querySelector(`.hazard-item[data-hazard-index="${boundedIndex}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const selectedMonth = hazardCalendarDate(selectedEvent.start_date);
  if (!state.hazardCalendarViewDate || state.hazardCalendarViewDate.getFullYear() !== selectedMonth.getFullYear() || state.hazardCalendarViewDate.getMonth() !== selectedMonth.getMonth()) {
    state.hazardCalendarViewDate = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth(), 1);
  }
  renderHazardCalendar(events, { preserveView:true });
  const chart = state.charts.hazard;
  if (chart) {
    chart.setActiveElements([
      { datasetIndex: 0, index: boundedIndex },
      { datasetIndex: 1, index: boundedIndex },
    ]);
    chart.tooltip?.setActiveElements(
      [
        { datasetIndex: 0, index: boundedIndex },
        { datasetIndex: 1, index: boundedIndex },
      ],
      { x: 0, y: 0 },
    );
    chart.update("none");
  }
}

async function runHealth(options = {}) {
  const { silent = false, keepOverlay = false } = options;
  try {
    if (!keepOverlay)
      loading(
        true,
        "Calculating Bayesian risk, suitability, pest-specific outbreaks, and event-linked rehabilitation priorities…",
      );
    const farm = getFarm();
    const frame = state.visualFrames?.[state.forecastIndex] || state.latestForecast?.frames?.[0];
    const annualRainfall = state.latestForecast
      ? state.latestForecast.monthly
          .slice(0, 12)
          .reduce((sum, row) => sum + row.rainfall_mm, 0)
      : 2200;
    const hazards = (state.latestForecast?.extreme_events || []).slice(0, 40).map((event) => ({
      event_type: event.event_type || "other",
      label: event.label || title(event.event_type || "weather event"),
      start_date: event.start_date,
      end_date: event.end_date,
      peak_severity: Math.max(0, Math.min(1, Number(event.peak_severity) || 0)),
      estimated_production_loss_tons: Math.max(0, Number(event.estimated_production_loss_tons) || 0),
      loss_percent_of_event_baseline: Math.max(0, Math.min(100, Number(event.loss_percent_of_event_baseline) || 0)),
      estimated_trees_affected: Math.max(0, Math.round(Number(event.estimated_trees_affected) || 0)),
      data_mode: event.data_mode || null,
      confidence: event.confidence || null,
    }));
    const [pest, suit, assessment, rehab] = await Promise.all([
      api("/api/pest-risk/evaluate", {
        method: "POST",
        body: JSON.stringify({
          prior_probability: 0.15,
          symptoms: farm.symptoms,
          humidity_percent: frame?.humidity_percent || 78,
          rainfall_mm_month: (frame?.rainfall_mm || 35) * 4.33,
          average_tree_age: farm.trees.average_age_years,
        }),
      }),
      api("/api/suitability/evaluate", {
        method: "POST",
        body: JSON.stringify({
          soil_terrain: farm.soil_terrain,
          annual_rainfall_mm: annualRainfall,
          mean_temperature_c: frame?.temperature_c || 27,
          humidity_percent: frame?.humidity_percent || 78,
          drought_exposure: 0.18,
          climate_stress: 0.15,
        }),
      }),
      api("/api/farm-assessment", {
        method: "POST",
        body: JSON.stringify(farm),
      }),
      api("/api/rehabilitation-plan", {
        method: "POST",
        body: JSON.stringify({
          farm,
          hazards,
          rows: 14,
          cols: 14,
          assessment_delay_days: 3,
          rehabilitation_delay_days: 7,
        }),
      }),
    ]);
    let specific = { pests: [], highest_outbreak_score: 0, top_risk_pest: "Unavailable" };
    try {
      specific = await api("/api/pest-risk/specific", {
        method: "POST",
        body: JSON.stringify({
          farm,
          temperature_c: frame?.temperature_c || 27,
          humidity_percent: frame?.humidity_percent || 78,
          rainfall_mm_week: frame?.rainfall_mm || 35,
          wind_speed_kmh: frame?.wind_speed_kmh || 12,
          farm_condition_score: frame?.farm_condition_score || 0.65,
        }),
      });
    } catch (specificError) {
      console.warn("Pest-specific risk could not be refreshed; core Farm Health remains available.", specificError);
    }
    state.rehabPlanIndex = Math.min(state.rehabPlanIndex, Math.max(0, (rehab.plans || []).length - 1));
    state.health = { pest, suit, assessment, rehab, specific };
    renderHealth();
    refreshHealthIndicatorsForPlan(selectedRehabPlan());
    if (!silent) toast("Farm health and event-linked rehabilitation assessment complete.");
  } catch (e) {
    toast(e.message, true);
    if (!silent) throw e;
  } finally {
    if (!keepOverlay) loading(false);
  }
}

function donutChart(key, canvasId, value, color) {
  const bounded = Math.max(0, Math.min(100, Number(value) || 0));
  replaceChart(key, canvasId, {
    type: "doughnut",
    data: {
      labels: ["Score", "Remaining"],
      datasets: [
        {
          data: [bounded, 100 - bounded],
          backgroundColor: [color, "rgba(126,145,134,.14)"],
          borderWidth: 0,
          hoverOffset: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "74%",
      animation: { duration: 450 },
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

function pestScoreRingMarkup(score, label = "RISK") {
  const bounded = Math.max(0, Math.min(100, Number(score) || 0));
  const color = bounded >= 70 ? "#b7463c" : bounded >= 40 ? "#e89008" : "#246b32";
  return `<span class="pest-score-donut" style="--score:${bounded}; --score-color:${color};"><span><b>${number(bounded, 0)}%</b><small>${escapeHtml(label)}</small></span></span>`;
}

function rehabStepIcon(key) {
  return ({ event: "☁", inspection: "⌕", rehabilitation: "✚", followup30: "↻", followup90: "✓" })[key] || "•";
}

function renderHealthDonuts() {
  if (!state.health) return;
  const pestValue = Number(state.health.pest.event_conditioned_probability ?? state.health.pest.posterior_probability ?? 0) * 100;
  const suitValue = Number(state.health.suit.percentage || 0);
  const conditionFrame = state.health?.eventFrame || state.visualFrames[state.forecastIndex] || {};
  const conditionValue = state.latestForecast
    ? Number(conditionFrame.farm_condition_score || state.health.assessment?.condition_score || 0) * 100
    : Number(state.health.assessment?.condition_score || 0) * 100;
  $("healthPest").textContent = `${number(pestValue, 0)}%`;
  $("healthSuitability").textContent = `${number(suitValue, 0)}%`;
  $("healthCondition").textContent = `${number(conditionValue, 0)}%`;
  donutChart(
    "healthPestDonut",
    "healthPestDonut",
    pestValue,
    pestValue >= 60 ? "#b7463c" : pestValue >= 35 ? "#e89008" : "#246b32",
  );
  donutChart(
    "healthSuitabilityDonut",
    "healthSuitabilityDonut",
    suitValue,
    suitValue >= 70 ? "#246b32" : suitValue >= 45 ? "#e89008" : "#b7463c",
  );
  donutChart(
    "healthConditionDonut",
    "healthConditionDonut",
    conditionValue,
    conditionValue >= 70
      ? "#246b32"
      : conditionValue >= 45
        ? "#e89008"
        : "#b7463c",
  );
}

function renderHealthOverviewChart() {
  if (!state.health || !$("healthOverviewChart")) return;
  const pest = Number(state.health.pest.event_conditioned_probability ?? state.health.pest.posterior_probability ?? 0) * 100;
  const suitability = Number(state.health.suit.percentage || 0);
  const conditionFrame = state.health?.eventFrame || state.visualFrames[state.forecastIndex] || {};
  const condition = state.latestForecast ? Number(conditionFrame.farm_condition_score || state.health.assessment?.condition_score || 0) * 100 : Number(state.health.assessment?.condition_score || 0) * 100;
  const priority = Number(selectedRehabPlan()?.counts?.["Needs Rehabilitation"] || 0);
  const totalCells = Math.max(1, Number(state.health.rehab?.rows || 14) * Number(state.health.rehab?.cols || 14));
  const rehabHealthy = Math.max(0, 100 - (priority / totalCells) * 100);
  replaceChart("healthOverview", "healthOverviewChart", {
    type:"bar",
    data:{ labels:["Farm condition","Land suitability","Low pest pressure","Low rehab burden"], datasets:[{ label:"Score", data:[condition,suitability,Math.max(0,100-pest),rehabHealthy], backgroundColor:["rgba(45,121,61,.72)","rgba(105,166,66,.72)","rgba(239,133,0,.72)","rgba(56,117,82,.62)"] }] },
    options:{ ...chartOptions("Score (0-100)"), indexAxis:"y", scales:{ x:{ min:0,max:100,grid:{color:"rgba(80,110,88,.08)"}}, y:{grid:{display:false}} }, plugins:{ legend:{display:false} } }
  });
}

function intercropCanopyFit(candidate, lightPercent = state.intercropLight) {
  const light=Math.max(0.01,Math.min(1,Number(lightPercent||0)/100));
  const min=Math.max(0,Number(candidate?.min_light_fraction||0));
  const max=Math.min(1,Number(candidate?.max_light_fraction||1));
  const mid=(min+max)/2;
  if(light>=min&&light<=max){
    const half=Math.max(.03,(max-min)/2);
    return Math.max(90,100-10*Math.abs(light-mid)/half);
  }
  if(light<min){const scale=Math.max(.10,min); return Math.max(0,90-90*(min-light)/scale);}
  const scale=Math.max(.12,1-max); return Math.max(0,90-90*(light-max)/scale);
}
function intercropFitLabel(score){ return score>=90?"Excellent fit":score>=72?"Good fit":score>=48?"Moderate fit":score>=25?"Limited fit":"Poor fit"; }
function intercropRingColor(score){ return score>=72?"#3a964d":score>=48?"#e9a02e":"#c95a43"; }
function intercropAssessmentMap(){ const map=new Map(); for(const row of state.intercropAssessments||[]) map.set(String(row.candidate_id),row); return map; }
function intercropCandidateById(id){ return state.intercropCandidates.find((item)=>String(item.id)===String(id))||state.intercropCandidates[0]||null; }
function intercropGuidance(candidate,fit){
  const light=Number(state.intercropLight||36)/100, min=Number(candidate?.min_light_fraction||0), max=Number(candidate?.max_light_fraction||1);
  const name=String(candidate?.common_name||"This crop");
  if(light<min) return `${name} currently receives less light than its reference band. Start only in the brightest understory lanes and reassess canopy opening before expanding.`;
  if(light>max) return `${name} is more exposed than its reference band. Retain useful coconut shade or place the crop in more sheltered rows before scaling up.`;
  if(fit>=90) return `${name} is strongly matched to the selected canopy light. Begin with a monitored pilot block, preserve coconut access lanes, and track soil moisture, coconut production, and pest observations before expansion.`;
  return `${name} is workable at this canopy level. Use a small trial area first and verify drainage, soil condition, management capacity, and pest pressure before expanding.`;
}
function intercropCropKind(id){
  const key=String(id||"");
  if(["banana","papaya","mangosteen","citrus"].includes(key)) return "small-tree";
  if(["cacao","coffee","cloves","cinnamon"].includes(key)) return "shrub";
  if(["black-pepper","vanilla","grapes"].includes(key)) return "vine";
  if(["pineapple","ginger","coleus","begonia","ferns","philodendron","african-violets","saintpaulia-violets","violets","dendrobium","orchid","snap-leaf-vandas"].includes(key)) return "ground";
  if(["corn","sugarcane","rice","wheat","tobacco"].includes(key)) return "stalk";
  return "bush";
}
const INTERCROP_WIKI_TITLES = {
  "black-pepper":"Black_pepper",
  cacao:"Theobroma_cacao",
  cloves:"Clove",
  vanilla:"Vanilla",
  coleus:"Coleus",
  cinnamon:"Cinnamon",
  ginger:"Ginger",
  violets:"Viola_(plant)",
  "snap-leaf-vandas":"Vanda",
  begonia:"Begonia",
  dendrobium:"Dendrobium",
  "saintpaulia-violets":"Saintpaulia",
  "african-violets":"Saintpaulia",
  ferns:"Fern",
  philodendron:"Philodendron",
  banana:"Banana",
  pineapple:"Pineapple",
  papaya:"Papaya",
  coffee:"Coffea",
  citrus:"Citrus",
  mangosteen:"Mangosteen",
  corn:"Maize",
  rice:"Rice",
  cotton:"Cotton",
  tobacco:"Tobacco",
  coconut:"Coconut",
  "winged-bean":"Psophocarpus_tetragonolobus",
  "lima-bean":"Lima_bean",
  orchid:"Orchid",
  muskmelon:"Muskmelon",
  grapes:"Grape",
  peanut:"Peanut",
  "pigeon-pea":"Pigeon_pea",
  sugarcane:"Sugarcane",
  wheat:"Wheat",
};
function intercropFallbackImage(candidate){
  const label = String(candidate?.common_name || candidate?.id || "Crop").slice(0, 24);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420" viewBox="0 0 720 420" role="img" aria-label="${label}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#edf4ea"/><stop offset="100%" stop-color="#d9ead3"/></linearGradient></defs><rect width="720" height="420" rx="28" fill="url(#g)"/><g fill="none" stroke="#4f8b56" stroke-linecap="round" stroke-width="14"><path d="M360 322V162"/><path d="M360 214c-54-27-91-68-114-123"/><path d="M360 226c66-16 117-52 147-104"/><path d="M360 246c-81 11-142 42-181 92"/><path d="M360 264c87 2 149 27 192 74"/></g><circle cx="360" cy="160" r="26" fill="#f1b24d" opacity=".84"/><text x="50%" y="368" font-size="34" text-anchor="middle" font-family="Arial, sans-serif" fill="#33533c">${label}</text><text x="50%" y="396" font-size="18" text-anchor="middle" font-family="Arial, sans-serif" fill="#5d7263">Awaiting reference photo</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
function getIntercropPhotoMeta(candidate){
  const id = String(candidate?.id || "");
  if (state.intercropPhotoCache[id]) return state.intercropPhotoCache[id];
  try {
    const saved = localStorage.getItem(`cocoaid-intercrop-photo:${id}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed?.image) {
        state.intercropPhotoCache[id] = { ...parsed, loaded: true };
        return state.intercropPhotoCache[id];
      }
    }
  } catch {}
  return { image: intercropFallbackImage(candidate), href: "", credit: "Reference photo loading…", pending: true };
}
function persistIntercropPhotoMeta(id, meta){
  try { localStorage.setItem(`cocoaid-intercrop-photo:${id}`, JSON.stringify({ image:meta.image, href:meta.href||"", credit:meta.credit||"Wikipedia" })); } catch {}
}
function installIntercropImageFallbacks(scope=document){
  scope.querySelectorAll?.('img[data-intercrop-photo]').forEach((img)=>{
    if (img.dataset.fallbackBound === '1') return;
    img.dataset.fallbackBound = '1';
    img.addEventListener('error', ()=>{
      const candidate = intercropCandidateById(img.dataset.intercropPhoto);
      if (!candidate || img.dataset.fallbackApplied === '1') return;
      const failedSource = img.currentSrc || img.src || '';
      img.dataset.fallbackApplied = '1';
      img.src = intercropFallbackImage(candidate);
      const caption = img.closest('.intercrop-card-media')?.querySelector('.intercrop-card-media-caption');
      if (caption) caption.innerHTML = '<span>Crop reference</span><small>Local fallback image</small>';
      if (/^https?:/i.test(failedSource) && img.dataset.retryAttempted !== '1') {
        img.dataset.retryAttempted = '1';
        try { localStorage.removeItem(`cocoaid-intercrop-photo:${candidate.id}`); } catch {}
        delete state.intercropPhotoCache[String(candidate.id)];
        setTimeout(()=>loadIntercropPhotoMeta(candidate), 900);
      }
    });
  });
}
function updateIntercropPhotoCard(candidate, meta){
  if (!candidate || !meta) return;
  document.querySelectorAll(`img[data-intercrop-photo="${CSS.escape(String(candidate.id))}"]`).forEach((img)=>{
    if (meta.image && img.src !== meta.image) { img.dataset.fallbackApplied = '0'; img.src = meta.image; }
    const caption = img.closest('.intercrop-card-media')?.querySelector('.intercrop-card-media-caption');
    if (caption) caption.innerHTML = meta.href
      ? `<span>Real crop reference</span><a href="${escapeHtml(meta.href)}" target="_blank" rel="noreferrer">${escapeHtml(meta.credit||"Wikipedia")}</a>`
      : `<span>Crop reference</span><small>${escapeHtml(meta.credit||"Local fallback image")}</small>`;
  });
  installIntercropImageFallbacks(document);
}
async function loadIntercropPhotoMeta(candidate){
  const id = String(candidate?.id || "");
  if (!id || state.intercropPhotoCache[id]?.loaded) return state.intercropPhotoCache[id];
  const title = INTERCROP_WIKI_TITLES[id] || String(candidate?.scientific_name || candidate?.common_name || id).trim().replace(/\s+/g, "_");
  try {
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), 7000);
    const response = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`, { headers: { accept: "application/json" }, signal:controller.signal });
    clearTimeout(timeout);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const image = payload?.thumbnail?.source || payload?.originalimage?.source || "";
    if (!image) throw new Error("No thumbnail available");
    const meta = { image, href: payload?.content_urls?.desktop?.page || `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`, credit: payload?.title || candidate?.common_name || "Wikipedia", loaded: true };
    state.intercropPhotoCache[id] = meta;
    persistIntercropPhotoMeta(id, meta);
    updateIntercropPhotoCard(candidate, meta);
    return meta;
  } catch (_error) {
    const existing = state.intercropPhotoCache[id];
    const meta = existing?.image && !String(existing.image).startsWith('data:image/svg+xml')
      ? { ...existing, loaded:true }
      : { image:intercropFallbackImage(candidate), href:"", credit:"Local fallback image", loaded:true };
    state.intercropPhotoCache[id] = meta;
    updateIntercropPhotoCard(candidate, meta);
    return meta;
  }
}
async function prefetchIntercropPhotos(candidates){
  if (state.intercropPhotoFetchStarted) return;
  state.intercropPhotoFetchStarted = true;
  const queue = [...(candidates || [])];
  const worker = async () => {
    while (queue.length) {
      const candidate = queue.shift();
      await loadIntercropPhotoMeta(candidate);
      await new Promise((resolve)=>setTimeout(resolve,55));
    }
  };
  await Promise.all(Array.from({length:Math.min(4,queue.length||1)},worker));
}

function renderIntercropCanopyChart(candidate){
  if(!candidate||!$("intercropCanopyChart")) return;
  const levels=[]; for(let value=5;value<=100;value+=5) levels.push(value);
  replaceChart("intercropCanopy","intercropCanopyChart",{type:"line",data:{labels:levels.map(v=>`${v}%`),datasets:[{label:"Canopy fit",data:levels.map(v=>intercropCanopyFit(candidate,v)),borderColor:"#df7e22",backgroundColor:"rgba(223,126,34,.11)",fill:true,tension:.28,pointRadius:1.8,pointHoverRadius:4}]},options:{...chartOptions("Canopy fit (0-100)"),scales:{y:{min:0,max:100},x:{grid:{display:false},ticks:{maxTicksLimit:8}}},plugins:{legend:{display:false}}}});
}
function renderIntercroppingWorkspace(){
  const candidates=state.intercropCandidates||[]; if(!candidates.length) return;
  const assessments=intercropAssessmentMap();
  if(!candidates.some(c=>String(c.id)===String(state.intercropSelectedId))) state.intercropSelectedId=candidates[0].id;
  const selected=intercropCandidateById(state.intercropSelectedId); const fit=intercropCanopyFit(selected);
  const assessment=assessments.get(String(selected?.id));
  if($("intercropLightValue")) $("intercropLightValue").textContent=`${Math.round(state.intercropLight)}%`;
  if($("intercropSceneCropName")) $("intercropSceneCropName").textContent=selected?.common_name||"—";
  if($("intercropSceneCropClass")) $("intercropSceneCropClass").textContent=`Group ${selected?.light_group||"—"} · ${intercropFitLabel(fit)}`;
  if($("intercropSceneFit")) $("intercropSceneFit").textContent=`${number(fit,0)}/100`;
  if($("intercropSceneIntegrated")) $("intercropSceneIntegrated").textContent=assessment?`Integrated Phase 9: ${number(assessment.suitability_score,0)}/100`:`Integrated Phase 9: waiting`;
  if($("intercropCurrentFit")) $("intercropCurrentFit").textContent=`${number(fit,0)}/100`;
  if($("intercropCurrentClass")) $("intercropCurrentClass").textContent=intercropFitLabel(fit);
  if($("intercropPreferredLight")) $("intercropPreferredLight").textContent=`${number(Number(selected?.min_light_fraction||0)*100,0)}–${number(Number(selected?.max_light_fraction||0)*100,0)}%`;
  if($("intercropIntegratedScore")) $("intercropIntegratedScore").textContent=assessment?`${number(assessment.suitability_score,0)}/100`:`Waiting`;
  if($("intercropCompetition")) $("intercropCompetition").textContent=assessment?`${number(Number(assessment.coconut_competition_risk||0)*100,0)}%`:`Waiting`;
  if($("intercropChartTitle")) $("intercropChartTitle").textContent=`${selected?.common_name||"Crop"} canopy suitability across light levels`;
  const ranked=[...candidates].map(candidate=>({candidate,fit:intercropCanopyFit(candidate),assessment:assessments.get(String(candidate.id))})).sort((a,b)=>b.fit-a.fit||Number(b.assessment?.suitability_score||0)-Number(a.assessment?.suitability_score||0)||String(a.candidate.common_name).localeCompare(String(b.candidate.common_name)));
  const ranking=$("intercropRanking"); if(ranking) ranking.innerHTML=ranked.slice(0,12).map((row,index)=>`<button type="button" class="intercrop-rank-item${String(row.candidate.id)===String(state.intercropSelectedId)?" active":""}" data-intercrop-select="${escapeHtml(row.candidate.id)}"><span class="intercrop-rank-number">${index+1}</span><span class="intercrop-rank-name"><strong>${escapeHtml(row.candidate.common_name)}</strong><small>${number(Number(row.candidate.min_light_fraction||0)*100,0)}–${number(Number(row.candidate.max_light_fraction||0)*100,0)}% preferred light${row.assessment?` · Phase 9 ${number(row.assessment.suitability_score,0)}/100`:""}</small></span><span class="intercrop-rank-score"><strong>${number(row.fit,0)}</strong><small>CANOPY FIT</small></span><span class="intercrop-rank-bar"><i style="width:${Math.max(0,Math.min(100,row.fit))}%"></i></span></button>`).join("");
  const deck=$("intercropCardDeck"); if(deck) deck.innerHTML=ranked.map(row=>{const c=row.candidate,a=row.assessment,ring=intercropRingColor(row.fit),marker=Math.max(0,Math.min(100,state.intercropLight));const photo=getIntercropPhotoMeta(c);return `<article class="intercrop-card${String(c.id)===String(state.intercropSelectedId)?" active":""}" data-intercrop-select="${escapeHtml(c.id)}"><div class="intercrop-card-top"><div class="intercrop-card-title"><strong>${escapeHtml(c.common_name)}</strong><small>Light Group ${escapeHtml(c.light_group||"—")} · ${escapeHtml(intercropFitLabel(row.fit))}</small></div><span class="intercrop-score-ring" style="--score:${row.fit};--ring:${ring}"><span><b>${number(row.fit,0)}%</b><small>FIT</small></span></span></div><div class="intercrop-card-media"><img src="${escapeHtml(photo.image)}" data-intercrop-photo="${escapeHtml(c.id)}" alt="${escapeHtml(c.common_name)} crop photo" loading="lazy" decoding="async" referrerpolicy="no-referrer"/><div class="intercrop-card-media-caption"><span>Real crop reference</span>${photo.href?`<a href="${escapeHtml(photo.href)}" target="_blank" rel="noreferrer">${escapeHtml(photo.credit||"Wikipedia")}</a>`:`<small>${escapeHtml(photo.credit||"Reference photo")}</small>`}</div></div><div class="intercrop-light-band"><div><span>Preferred canopy light</span><strong>${number(Number(c.min_light_fraction||0)*100,0)}–${number(Number(c.max_light_fraction||0)*100,0)}%</strong></div><span class="intercrop-light-track"><i style="left:calc(${marker}% - 1px)"></i></span></div><div class="intercrop-card-guidance">${escapeHtml(intercropGuidance(c,row.fit))}</div><div class="intercrop-card-footer"><span>${a?`Integrated suitability ${number(a.suitability_score,0)}/100 · ${escapeHtml(a.suitability_class||"")}`:"Awaiting full Phase 9 assessment"}</span><strong>Show in 3D →</strong></div></article>`}).join("");
  document.querySelectorAll('[data-intercrop-select]').forEach(btn=>btn.addEventListener('click',()=>selectIntercropCandidate(btn.dataset.intercropSelect)));
  installIntercropImageFallbacks(deck || document);
  renderIntercropCanopyChart(selected); startIntercropScene();
}
async function loadIntercroppingWorkspace(force=false){
  try{
    if($("intercropEngineStatus")) $("intercropEngineStatus").textContent="Loading PCA candidate catalog…";
    const [candidateData,assessmentData]=await Promise.all([api('/api/v2/intercropping/candidates'),api('/api/v2/intercropping/assessments?limit=1000')]);
    state.intercropCandidates=candidateData.candidates||[];
    const all=assessmentData.assessments||[]; const latestRun=all[0]?.run_id; state.intercropAssessments=latestRun?all.filter(row=>String(row.run_id)===String(latestRun)):[];
    if($("intercropEngineStatus")) $("intercropEngineStatus").textContent=`${state.intercropCandidates.length} candidates ready`;
    if($("intercropRunStatus")) $("intercropRunStatus").textContent=latestRun?`${state.intercropAssessments.length} crops assessed in the latest Phase 9 run.`:"Phase 9 has not produced an integrated intercrop run yet; canopy-light ranking remains available.";
    const select=$("intercropCropSelect"); if(select){select.innerHTML=state.intercropCandidates.map(c=>`<option value="${escapeHtml(c.id)}">${escapeHtml(c.common_name)}</option>`).join(""); if(state.intercropCandidates.some(c=>c.id===state.intercropSelectedId)) select.value=state.intercropSelectedId; else {state.intercropSelectedId=state.intercropCandidates[0]?.id||"";select.value=state.intercropSelectedId;}}
    renderIntercroppingWorkspace();
    prefetchIntercropPhotos(state.intercropCandidates);
  }catch(error){if($("intercropEngineStatus")) $("intercropEngineStatus").textContent="Intercropping data unavailable";if($("intercropRunStatus")) $("intercropRunStatus").textContent=error.message;}
}
function selectIntercropCandidate(id){ state.intercropSelectedId=String(id||state.intercropSelectedId); if($("intercropCropSelect")) $("intercropCropSelect").value=state.intercropSelectedId; renderIntercroppingWorkspace(); }
function sceneTransform(point){
  const camera=state.intercropCamera||{yaw:-.55,pitch:-.28,zoom:1}; const cy=Math.cos(camera.yaw),sy=Math.sin(camera.yaw),cp=Math.cos(camera.pitch),sp=Math.sin(camera.pitch);
  const px=Number(point?.x||0),py=Number(point?.y||0),pz=Number(point?.z||0); const x=cy*px-sy*pz, z0=sy*px+cy*pz; const y=cp*py-sp*z0, z=sp*py+cp*z0; return {x,y,z};
}
function sceneProject(point,w,h){ const p=sceneTransform(point); const camera=state.intercropCamera||{zoom:1}; const distance=40/Math.max(.26,Math.min(3.6,camera.zoom||1)); const depth=Math.max(4,p.z+distance); const scale=Math.min(w,h)*.82/depth; return {x:w/2+p.x*scale,y:h*.66-p.y*scale,depth,scale}; }
function scenePolygon(ctx,points,w,h,fill,stroke=null,lineWidth=1){ const projected=points.map(p=>sceneProject(p,w,h)); ctx.beginPath();projected.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke();} return projected; }
function sceneOpenPath(ctx,points,w,h){ const projected=points.map(p=>sceneProject(p,w,h)); ctx.beginPath(); projected.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y)); return projected; }
function getIntercropFootprint(){
  const farm = getFarm?.() || {};
  const polygon = (Array.isArray(state.polygon) && state.polygon.length >= 3 ? state.polygon : farm.polygon) || [];
  if (!Array.isArray(polygon) || polygon.length < 3) return [{x:-8,y:0,z:-6.4},{x:8,y:0,z:-6.4},{x:8,y:0,z:6.4},{x:-8,y:0,z:6.4}];
  const pts = polygon.map((point) => ({ lat:Number(point[0]), lng:Number(point[1]) })).filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng));
  if (pts.length < 3) return [{x:-8,y:0,z:-6.4},{x:8,y:0,z:-6.4},{x:8,y:0,z:6.4},{x:-8,y:0,z:6.4}];
  const meanLat = pts.reduce((sum,p)=>sum+p.lat,0)/pts.length * Math.PI/180;
  const cx = pts.reduce((sum,p)=>sum+p.lng,0)/pts.length;
  const cz = pts.reduce((sum,p)=>sum+p.lat,0)/pts.length;
  const normalized = pts.map((p)=>({ x:(p.lng-cx)*Math.cos(meanLat), z:(cz-p.lat) }));
  const minX=Math.min(...normalized.map(p=>p.x)), maxX=Math.max(...normalized.map(p=>p.x)), minZ=Math.min(...normalized.map(p=>p.z)), maxZ=Math.max(...normalized.map(p=>p.z));
  const spanX=Math.max(.00001,maxX-minX), spanZ=Math.max(.00001,maxZ-minZ);
  const scale=Math.min(14.8/spanX,10.8/spanZ);
  return normalized.map((p)=>({x:p.x*scale,y:0,z:p.z*scale}));
}
function pointInScenePolygon(x,z,polygon){
  let inside = false;
  for (let i=0,j=polygon.length-1; i<polygon.length; j=i++) {
    const xi=Number(polygon[i].x), zi=Number(polygon[i].z), xj=Number(polygon[j].x), zj=Number(polygon[j].z);
    const intersect = ((zi>z)!==(zj>z)) && (x < (xj-xi)*(z-zi)/((zj-zi)||1e-9)+xi);
    if (intersect) inside = !inside;
  }
  return inside;
}
function buildIntercropSceneLayout(){
  const footprint = getIntercropFootprint();
  const cacheKey = footprint.map((p)=>`${p.x.toFixed(3)},${p.z.toFixed(3)}`).join('|');
  if (state.intercropSceneLayoutCache?.key === cacheKey) return state.intercropSceneLayoutCache.scene;
  const xs = footprint.map((p)=>p.x), zs = footprint.map((p)=>p.z);
  const minX=Math.min(...xs), maxX=Math.max(...xs), minZ=Math.min(...zs), maxZ=Math.max(...zs);
  const trees=[]; const treeSpacing=1.38; const rowSpacing=1.22;
  let row=0;
  for(let z=minZ+.42; z<=maxZ-.32; z+=rowSpacing, row++){
    const offset = row % 2 ? treeSpacing*.5 : 0;
    for(let x=minX+.42; x<=maxX-.32; x+=treeSpacing){ const px=x+offset; if(pointInScenePolygon(px,z,footprint))trees.push({x:px,z,y:0,variant:(row+Math.round((px-minX)*10))%5}); }
  }
  if(trees.length<12){for(const x of[-5.6,-3.2,-.8,1.6,4,6.4])for(const z of[-4.8,-2.4,0,2.4,4.8])if(pointInScenePolygon(x,z,footprint))trees.push({x,z,y:0,variant:Math.abs(Math.round((x+z)*3))%5});}
  const plants=[]; const cropSpacing=1.20; row=0;
  for(let z=minZ+.26;z<=maxZ-.22;z+=cropSpacing,row++){const offset=row%2?cropSpacing*.5:0;for(let x=minX+.26;x<=maxX-.22;x+=cropSpacing){const px=x+offset;if(!pointInScenePolygon(px,z,footprint))continue;const nearTree=trees.some((tree)=>((tree.x-px)**2+(tree.z-z)**2)<.46);if(!nearTree)plants.push({x:px,z,y:0});}}
  const maxPlants=125; const stride=Math.max(1,Math.ceil(plants.length/maxPlants)); const thinnedPlants=plants.filter((_,index)=>index%stride===0).slice(0,maxPlants);
  const scene={footprint,trees,plants:thinnedPlants,bounds:{minX,maxX,minZ,maxZ}};
  state.intercropSceneLayoutCache={key:cacheKey,scene}; state.intercropSceneDepthOrder=null; return scene;
}
function quadPoint(a,b,c,t){ const mt=1-t; return { x:mt*mt*a.x + 2*mt*t*b.x + t*t*c.x, y:mt*mt*a.y + 2*mt*t*b.y + t*t*c.y, z:mt*mt*a.z + 2*mt*t*b.z + t*t*c.z }; }
function drawPalmFrond3D(ctx,start,mid,end,w,h,color){
  const samples=[]; for(let step=0;step<=9;step++)samples.push(sceneProject(quadPoint(start,mid,end,step/9),w,h)); if(!samples.length)return;
  const widthBase=Math.max(3.6,samples[0]?.scale*.020||4),left=[],right=[];
  for(let i=0;i<samples.length;i++){const prev=samples[Math.max(0,i-1)],next=samples[Math.min(samples.length-1,i+1)],tx=next.x-prev.x,ty=next.y-prev.y,len=Math.hypot(tx,ty)||1,nx=-ty/len,ny=tx/len,taper=1-(i/(samples.length-1))*.82,width=widthBase*taper;left.push({x:samples[i].x+nx*width,y:samples[i].y+ny*width});right.push({x:samples[i].x-nx*width,y:samples[i].y-ny*width});}
  ctx.fillStyle=color==='#3d7a38'?'rgba(67,126,60,.40)':'rgba(77,142,67,.40)';ctx.beginPath();left.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));right.reverse().forEach((p)=>ctx.lineTo(p.x,p.y));ctx.closePath();ctx.fill();
  ctx.strokeStyle=color;ctx.lineWidth=Math.max(1.25,samples[0]?.scale*.010||1.4);ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();samples.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.stroke();
  for(let i=2;i<samples.length-1;i+=2){const p=samples[i],q=samples[Math.min(samples.length-1,i+1)],tx=q.x-p.x,ty=q.y-p.y,len=Math.hypot(tx,ty)||1,nx=-ty/len,ny=tx/len,leaflet=Math.max(6,p.scale*.18)*(1-(i/samples.length)*.28);ctx.lineWidth=Math.max(1,samples[0]?.scale*.0048||1);ctx.strokeStyle=i%4?'rgba(59,119,54,.84)':'rgba(78,148,69,.84)';ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+nx*leaflet+tx/len*leaflet*.12,p.y+ny*leaflet+ty/len*leaflet*.12);ctx.stroke();ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x-nx*leaflet+tx/len*leaflet*.12,p.y-ny*leaflet+ty/len*leaflet*.12);ctx.stroke();}
}
function drawCoconutTree3D(ctx,x,z,w,h,light,variant=0){
  const shade=1-Math.max(.05,Math.min(1,light/100));
  const trunkH=3.55 + (variant%3)*0.14;
  const baseWidth=.085 + (variant%4)*.012;
  const lean=Math.sin(z*.7 + variant*.8)*.12 + Math.cos(x*.45 + variant)*.07;
  const topPoint={x:x+lean,y:trunkH,z};
  const trunkFill=['#8f6040','#84563b','#996a46','#7f5234','#946445'][variant%5];
  const trunkStroke=['#6c442a','#5e3b24','#73492d','#644028','#70462d'][variant%5];
  scenePolygon(ctx,[{x:x-baseWidth,y:0,z:z-.03},{x:x+baseWidth,y:0,z:z+.03},{x:topPoint.x+baseWidth*.76,y:trunkH,z:z+.03},{x:topPoint.x-baseWidth*.76,y:trunkH,z:z-.03}],w,h,trunkFill,trunkStroke,.9);
  for(let ring=0.38; ring<trunkH; ring+=0.44){
    const p1=sceneProject({x:x-baseWidth*.92 + lean*(ring/trunkH),y:ring,z:z-.018},w,h);
    const p2=sceneProject({x:x+baseWidth*.92 + lean*(ring/trunkH),y:ring+.03,z:z+.018},w,h);
    ctx.strokeStyle='rgba(88,58,39,.36)'; ctx.lineWidth=Math.max(.8,p1.scale*.0024); ctx.beginPath(); ctx.moveTo(p1.x,p1.y); ctx.lineTo(p2.x,p2.y); ctx.stroke();
  }
  const crownBase={x:topPoint.x,y:trunkH+.02,z}; const crownRadius=.82+shade*.34; const frondCount=10+Math.round(shade*4);
  const crown=sceneProject(crownBase,w,h); const glow=ctx.createRadialGradient(crown.x,crown.y,1,crown.x,crown.y,Math.max(12,crown.scale*crownRadius*1.45)); glow.addColorStop(0,'rgba(85,146,65,.22)'); glow.addColorStop(1,'rgba(85,146,65,0)'); ctx.fillStyle=glow; ctx.beginPath(); ctx.arc(crown.x,crown.y,Math.max(9,crown.scale*crownRadius*.92),0,Math.PI*2); ctx.fill();
  for(let i=0;i<frondCount;i++){
    const angle=i/frondCount*Math.PI*2 + (variant*.13); const length=1.72 + shade*.34 + (i%3)*.04; const lift=.35 + Math.sin(i*1.3 + variant)*.05; const drop=.52 + Math.cos(i*.9 + variant)*.07;
    const start={x:crownBase.x,y:trunkH+.08,z:crownBase.z};
    const mid={x:crownBase.x+Math.cos(angle)*crownRadius*.56,y:trunkH+lift,z:crownBase.z+Math.sin(angle)*crownRadius*.56};
    const end={x:crownBase.x+Math.cos(angle)*length,y:trunkH-drop,z:crownBase.z+Math.sin(angle)*length};
    drawPalmFrond3D(ctx,start,mid,end,w,h, i%2 ? '#3d7a38' : '#4b8a43');
  }
  for(let i=0;i<3;i++){const p=sceneProject({x:crownBase.x+(i-1)*.09,y:trunkH-.15-i*.04,z:crownBase.z+.05*i},w,h);ctx.fillStyle='#7c4d28';ctx.beginPath();ctx.arc(p.x,p.y,Math.max(1.8,p.scale*.07),0,Math.PI*2);ctx.fill();}
}
function drawIntercrop3D(ctx,id,x,z,w,h,pulse){
  const kind=intercropCropKind(id); const base=sceneProject({x,y:0,z},w,h); ctx.save(); ctx.globalAlpha=.86+.14*pulse;
  const line='#2e843f', leaf=`rgba(81,165,66,${.78+.16*pulse})`, hi=`rgba(247,183,47,${.48+.20*pulse})`;
  if(kind==='small-tree'||kind==='shrub'){
    const height=kind==='small-tree'?2.2:1.55; const top=sceneProject({x,y:height,z},w,h); ctx.strokeStyle='#6c4a2d'; ctx.lineWidth=Math.max(1,base.scale*.055); ctx.beginPath(); ctx.moveTo(base.x,base.y); ctx.lineTo(top.x,top.y); ctx.stroke();
    for(let a=0;a<8;a++){const ang=a/8*Math.PI*2,p=sceneProject({x:x+Math.cos(ang)*.44,y:height-.12+Math.sin(a)*.06,z:z+Math.sin(ang)*.44},w,h);ctx.fillStyle=leaf;ctx.beginPath();ctx.ellipse(p.x,p.y,Math.max(3.6,p.scale*.12),Math.max(2.4,p.scale*.09),ang,0,Math.PI*2);ctx.fill();}
  } else if(kind==='vine'){
    const top=sceneProject({x,y:2.15,z},w,h); ctx.strokeStyle=line; ctx.lineWidth=1.8; ctx.beginPath(); ctx.moveTo(base.x,base.y); for(let i=1;i<=7;i++){const p=sceneProject({x:x+Math.sin(i*.9)*.12,y:i/7*2.15,z:z},w,h);ctx.lineTo(p.x,p.y);} ctx.stroke();
    for(let i=0;i<6;i++){const p=sceneProject({x:x+Math.sin(i)*.16,y:1.3+i*.10,z:z+Math.cos(i)*.07},w,h);ctx.fillStyle=i%2?leaf:hi;ctx.beginPath();ctx.ellipse(p.x,p.y,Math.max(2.5,p.scale*.06),Math.max(1.4,p.scale*.03),0,0,Math.PI*2);ctx.fill();}
  } else if(kind==='stalk'){
    for(let s=-1;s<=1;s++){
      const p0=sceneProject({x:x+s*.08,y:0,z},w,h),p1=sceneProject({x:x+s*.08,y:1.25+(s+1)*.10,z},w,h);ctx.strokeStyle=line;ctx.lineWidth=1.35;ctx.beginPath();ctx.moveTo(p0.x,p0.y);ctx.lineTo(p1.x,p1.y);ctx.stroke();
      const lf=sceneProject({x:x+s*.08+.12,y:.82,z:z+.05},w,h), rf=sceneProject({x:x+s*.08-.12,y:.92,z:z-.04},w,h);ctx.beginPath();ctx.moveTo(p1.x,p1.y);ctx.lineTo(lf.x,lf.y);ctx.moveTo(p1.x,p1.y);ctx.lineTo(rf.x,rf.y);ctx.stroke();
    }
  } else {
    for(let a=0;a<9;a++){const ang=a/9*Math.PI*2,p=sceneProject({x:x+Math.cos(ang)*.26,y:.20+Math.sin(a*.7)*.08,z:z+Math.sin(ang)*.26},w,h);ctx.strokeStyle=line;ctx.lineWidth=1.1;ctx.beginPath();ctx.moveTo(base.x,base.y);ctx.lineTo(p.x,p.y);ctx.stroke();ctx.fillStyle=leaf;ctx.beginPath();ctx.ellipse(p.x,p.y,Math.max(2,p.scale*.05),Math.max(3,p.scale*.07),ang,0,Math.PI*2);ctx.fill();}
    const core=sceneProject({x,y:.12,z},w,h);ctx.fillStyle=hi;ctx.beginPath();ctx.arc(core.x,core.y,Math.max(1.6,core.scale*.03),0,Math.PI*2);ctx.fill();
  }
  ctx.restore();
}
function drawIntercropScene(time=0){
  const canvas=$("intercrop3dCanvas");if(!canvas||state.section!=="intercropping")return;const rect=canvas.getBoundingClientRect();if(rect.width<10||rect.height<10)return;
  const dpr=Math.min(1.05,window.devicePixelRatio||1),w=Math.round(rect.width*dpr),h=Math.round(rect.height*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}const ctx=canvas.getContext('2d',{alpha:false});ctx.setTransform(dpr,0,0,dpr,0,0);const cw=rect.width,ch=rect.height;ctx.clearRect(0,0,cw,ch);
  const room=ctx.createLinearGradient(0,0,0,ch);room.addColorStop(0,'#f7f9fa');room.addColorStop(.55,'#edf1f2');room.addColorStop(1,'#dfe6e8');ctx.fillStyle=room;ctx.fillRect(0,0,cw,ch);const horizon=ctx.createLinearGradient(0,ch*.42,0,ch);horizon.addColorStop(0,'rgba(255,255,255,0)');horizon.addColorStop(1,'rgba(214,222,224,.80)');ctx.fillStyle=horizon;ctx.fillRect(0,ch*.42,cw,ch*.58);
  const platform=[{x:-10.8,y:-.28,z:-8.8},{x:10.8,y:-.28,z:-8.8},{x:10.8,y:-.28,z:8.8},{x:-10.8,y:-.28,z:8.8}];scenePolygon(ctx,platform,cw,ch,'rgba(248,251,252,.10)','rgba(170,180,184,.40)',1);for(let g=-10;g<=10;g+=1.55){scenePolygon(ctx,[{x:g,y:-.275,z:-8.8},{x:g+.02,y:-.275,z:-8.8},{x:g+.02,y:-.275,z:8.8},{x:g,y:-.275,z:8.8}],cw,ch,'rgba(121,133,138,.11)');scenePolygon(ctx,[{x:-10.8,y:-.274,z:g*.82},{x:10.8,y:-.274,z:g*.82},{x:10.8,y:-.274,z:g*.82+.02},{x:-10.8,y:-.274,z:g*.82+.02}],cw,ch,'rgba(121,133,138,.10)');}
  const scene=buildIntercropSceneLayout();scenePolygon(ctx,scene.footprint.map((p)=>({x:p.x,y:0,z:p.z})),cw,ch,'rgba(112,156,91,.88)','rgba(66,110,66,.60)',1);const pulse=.5+.5*Math.sin(time/1450),crop=state.intercropSelectedId,now=performance.now();if(!state.intercropSceneDepthOrder||now-state.intercropSceneDepthOrderAt>280){state.intercropSceneDepthOrder=[...scene.trees.map((item)=>({type:'tree',...item})),...scene.plants.map((item)=>({type:'plant',...item}))].sort((a,b)=>sceneTransform(b).z-sceneTransform(a).z);state.intercropSceneDepthOrderAt=now;}for(const item of state.intercropSceneDepthOrder){if(item.type==='tree')drawCoconutTree3D(ctx,item.x,item.z,cw,ch,state.intercropLight,item.variant||0);else drawIntercrop3D(ctx,crop,item.x,item.z,cw,ch,pulse);}
}
function intercropSceneLoop(time){if(state.section!=="intercropping"){state.intercropSceneAnimation=null;state.intercropSceneLastTime=0;state.intercropSceneLastRender=0;return;}const previous=state.intercropSceneLastTime||time,delta=Math.max(0,Math.min(50,time-previous));state.intercropSceneLastTime=time;if(!state.intercropSceneDrag)state.intercropCamera.yaw+=delta*.00015;if(time-(state.intercropSceneLastRender||0)>=55){drawIntercropScene(time);state.intercropSceneLastRender=time;}state.intercropSceneAnimation=requestAnimationFrame(intercropSceneLoop);}
function startIntercropScene(){ if(state.section!=="intercropping") return; if(!state.intercropSceneAnimation) state.intercropSceneAnimation=requestAnimationFrame(intercropSceneLoop); }
function resetIntercropCamera(){ state.intercropCamera={yaw:-.55,pitch:-.28,zoom:1.05}; state.intercropSceneLastTime=0; state.intercropSceneLastRender=0; drawIntercropScene(performance.now()); }
function setupIntercropSceneControls(){
  const canvas=$("intercrop3dCanvas"); if(!canvas||canvas.dataset.bound==='1') return;canvas.dataset.bound='1';
  canvas.addEventListener('pointerdown',e=>{canvas.setPointerCapture?.(e.pointerId);state.intercropSceneDrag={x:e.clientX,y:e.clientY};});
  canvas.addEventListener('pointermove',e=>{if(!state.intercropSceneDrag)return;const dx=e.clientX-state.intercropSceneDrag.x,dy=e.clientY-state.intercropSceneDrag.y;state.intercropSceneDrag={x:e.clientX,y:e.clientY};state.intercropCamera.yaw+=dx*.008;state.intercropCamera.pitch=Math.max(-.72,Math.min(.24,state.intercropCamera.pitch-dy*.006));state.intercropSceneDepthOrder=null;drawIntercropScene(performance.now());});
  const stop=e=>{state.intercropSceneDrag=null;try{canvas.releasePointerCapture?.(e.pointerId);}catch{}};canvas.addEventListener('pointerup',stop);canvas.addEventListener('pointercancel',stop);canvas.addEventListener('pointerleave',stop);
  canvas.addEventListener('wheel',e=>{e.preventDefault();state.intercropCamera.zoom=Math.max(.26,Math.min(3.6,state.intercropCamera.zoom*(e.deltaY>0?.91:1.10)));state.intercropSceneDepthOrder=null;drawIntercropScene(performance.now());},{passive:false});
}

function renderPestVisuals(data) {
  const pests = data?.pests || [];
  if ($("pestRankingChart")) {
    const ranked = [...pests].sort((a,b)=>Number(b.outbreak_score||0)-Number(a.outbreak_score||0));
    replaceChart("pestRanking", "pestRankingChart", {
      type:"bar",
      data:{ labels:ranked.map(p=>p.common_name), datasets:[{label:"Outbreak score", data:ranked.map(p=>Number(p.outbreak_score||0)), backgroundColor:ranked.map(p=>Number(p.outbreak_score||0)>=70?"rgba(183,70,60,.78)":Number(p.outbreak_score||0)>=40?"rgba(239,133,0,.78)":"rgba(45,121,61,.72)")}]},
      options:{ ...chartOptions("Risk score (0-100)"), indexAxis:"y", scales:{x:{min:0,max:100},y:{grid:{display:false}}}, plugins:{legend:{display:false}} }
    });
  }
  if ($("pestDriverChart")) {
    const totals = new Map();
    for (const pest of pests) for (const driver of pest.drivers || []) { const key=String(driver.name||"Driver"); const row=totals.get(key)||{sum:0,count:0}; row.sum+=Math.abs(Number(driver.value||0)); row.count+=1; totals.set(key,row); }
    const drivers=[...totals.entries()].map(([name,row])=>({name,value:row.count?row.sum/row.count:0})).sort((a,b)=>b.value-a.value).slice(0,8);
    replaceChart("pestDrivers", "pestDriverChart", { type:"bar", data:{labels:drivers.map(d=>d.name),datasets:[{label:"Average driver strength",data:drivers.map(d=>d.value),backgroundColor:"rgba(239,133,0,.72)"}]}, options:{...chartOptions("Driver strength"),scales:{x:{grid:{display:false}},y:{beginAtZero:true}},plugins:{legend:{display:false}}} });
  }
}

function renderPestCards(data) {
  const pests = data?.pests || [];
  if ($("pestHighestScore")) $("pestHighestScore").textContent = pests.length ? `${number(data.highest_outbreak_score, 0)}/100` : "—";
  if ($("pestTopRisk")) $("pestTopRisk").textContent = pests.length ? `Top risk: ${data.top_risk_pest}` : "Waiting for analysis";
  const deck = $("pestCardDeck");
  if (deck) deck.innerHTML = pests.length
    ? pests.map((pest, index) => {
        const score = Number(pest.outbreak_score || 0);
        const fallback = escapeHtml(pest.fallback_image_url || "/static/assets/pests/rhinoceros-beetle.svg");
        const source = pest.image_source_url
          ? `<a class="pest-photo-credit" href="${escapeHtml(pest.image_source_url)}" target="_blank" rel="noreferrer">${escapeHtml(pest.image_credit || "Photo source")}</a>`
          : "";
        return `<article class="pest-flash-card risk-${escapeHtml(String(pest.risk_class || "low").toLowerCase())}" data-pest-card="${index}">
          <div class="pest-card-inner">
            <section class="pest-card-face pest-card-front" aria-label="${escapeHtml(pest.common_name)} risk score">
              <div class="pest-photo-wrap"><img src="${escapeHtml(pest.image_url)}" data-fallback="${fallback}" alt="${escapeHtml(pest.image_description)}" loading="lazy">${source}</div>
              <div class="pest-card-content">
                <div class="pest-card-title"><div><strong>${escapeHtml(pest.common_name)}</strong><em>${escapeHtml(pest.scientific_name)}</em></div><div class="pest-card-score-stack">${pestScoreRingMarkup(score, "RISK")}</div></div>
                <div class="pest-score-track"><i style="width:${Math.min(100, score)}%"></i></div>
                <p>${escapeHtml(pest.characteristic_signs)}</p>
                <div class="pest-driver-chips">${(pest.drivers || []).slice(0, 3).map((driver) => `<span>${escapeHtml(driver.name)} ${number(driver.value, 0)}</span>`).join("")}</div>
                <button type="button" class="text-button pest-card-toggle" aria-expanded="false">View recommendation</button>
              </div>
            </section>
            <section class="pest-card-face pest-card-back" aria-label="${escapeHtml(pest.common_name)} recommendations">
              <div class="pest-card-back-head"><div><strong>${escapeHtml(pest.risk_class)} outbreak priority</strong><small>${escapeHtml(pest.affected_part)}</small></div>${pestScoreRingMarkup(score, "SCORE")}</div>
              <div class="pest-recommendation-scroll"><ul>${(pest.ai_recommendations || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul><div class="pest-formula">${escapeHtml(pest.formula)}</div></div>
              <button type="button" class="text-button pest-card-toggle" aria-expanded="true">Return to assessment</button>
            </section>
          </div>
        </article>`;
      }).join("")
    : '<div class="empty-state">No pest-specific scores are available.</div>';
  renderPestVisuals(data);
  document.querySelectorAll(".pest-photo-wrap img").forEach((image) => {
    image.addEventListener("error", () => {
      const fallback = image.dataset.fallback;
      if (fallback && image.src !== new URL(fallback, location.origin).href) image.src = fallback;
    }, { once: true });
  });
  document.querySelectorAll(".pest-card-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".pest-flash-card");
      card?.classList.toggle("flipped");
      const flipped = card?.classList.contains("flipped") || false;
      card?.querySelectorAll(".pest-card-toggle").forEach((control) => control.setAttribute("aria-expanded", String(flipped)));
    });
  });
}

function selectedRehabPlan() {
  const plans = state.health?.rehab?.plans || [];
  return plans[state.rehabPlanIndex] || plans[0] || null;
}

function changeRehabPlan(direction) {
  const plans = state.health?.rehab?.plans || [];
  if (!plans.length) return toast("Run the farm forecast to generate rehabilitation events first.", true);
  state.rehabPlanIndex = (state.rehabPlanIndex + direction + plans.length) % plans.length;
  state.rehabCalendarViewDate = null;
  state.rehabCalendarSelectedPhase = null;
  renderHealth();
  refreshHealthIndicatorsForPlan(selectedRehabPlan());
  requestAnimationFrame(() => {
    document.querySelector(`[data-rehab-plan="${state.rehabPlanIndex}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  });
}

function renderHealth() {
  if (!state.health) return;
  renderHealthDonuts();
  const plan = selectedRehabPlan();
  const priority = Number(plan?.counts?.["Needs Rehabilitation"] || 0);
  const priorityElement = $("healthPriorityCells");
  if (priorityElement) priorityElement.textContent = priority;

  // The Bayesian-evidence and suitability-evidence cards were intentionally removed
  // from the Farm Health UI in Phase 11.3.12. Keep these render hooks optional so
  // legacy analysis code cannot crash the whole Farm Intelligence workspace.
  const probabilityBar = $("pestProbabilityBar");
  if (probabilityBar) probabilityBar.style.width = `${Number(state.health.pest?.posterior_probability || 0) * 100}%`;
  const evidenceList = $("pestEvidenceList");
  if (evidenceList) {
    const evidence = state.health.pest?.evidence || state.health.pest?.evidence_items || [];
    evidenceList.innerHTML =
      (Array.isArray(evidence) ? evidence : [])
        .map((item) => `<div class="evidence-row"><span>${escapeHtml(item.name || item.evidence || "Evidence")}</span><strong>LR ${number(item.likelihood_ratio, 2)}</strong></div>`)
        .join("") ||
      `<div class="evidence-row"><span>Prior probability</span><strong>${percent(state.health.pest?.prior_probability || 0)}</strong></div><div class="evidence-row"><span>Posterior probability</span><strong>${percent(state.health.pest?.posterior_probability || 0)}</strong></div>`;
  }
  const suitabilityList = $("suitabilityFactors");
  if (suitabilityList) {
    const factors = state.health.suit?.components || state.health.suit?.factor_scores || {};
    suitabilityList.innerHTML = Object.entries(factors)
      .slice(0, 12)
      .map(([key, value]) => `<div class="factor-row"><span>${escapeHtml(title(key))}</span><strong>${number(Number(value) * 100, 0)}%</strong></div>`)
      .join("");
  }

  renderRehabEventStrip();
  renderRehabMap(plan, state.health.rehab);
  renderRehabProcedure(plan);
  renderHealthTreeChart();
  renderHealthOverviewChart();
  renderPestCards(state.health.specific || { pests: [] });
}

function rehabHeatColor(score) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  let a, b, t;
  if (value <= 50) {
    a = [47, 158, 91];
    b = [242, 201, 76];
    t = value / 50;
  } else {
    a = [242, 201, 76];
    b = [217, 72, 65];
    t = (value - 50) / 50;
  }
  const rgb = a.map((channel, index) => Math.round(channel + (b[index] - channel) * t));
  return `rgb(${rgb.join(",")})`;
}

function renderRehabEventStrip() {
  const plans = state.health?.rehab?.plans || [];
  $("rehabEventStrip").innerHTML = plans.length
    ? plans.map((plan, index) => `<button type="button" class="rehab-event-chip ${index === state.rehabPlanIndex ? "active" : ""}" data-rehab-plan="${index}">
        <span>${escapeHtml(plan.event_start_date)}</span>
        <strong>${escapeHtml(plan.event_label)}</strong>
        <small>${number(plan.peak_severity_percent, 0)}% severity · rehab ${escapeHtml(plan.recommended_rehabilitation_date)}</small>
      </button>`).join("")
    : '<div class="empty-state">No rehabilitation event plans are available.</div>';
  const previous = $("rehabPrevEvent");
  const next = $("rehabNextEvent");
  const disabled = plans.length < 2;
  if (previous) previous.disabled = disabled;
  if (next) next.disabled = disabled;
  if (plans.length) {
    const current = plans[state.rehabPlanIndex] || plans[0];
    previous?.setAttribute("title", `Previous event before ${current.event_start_date}`);
    next?.setAttribute("title", `Next event after ${current.event_start_date}`);
  }
  document.querySelectorAll("[data-rehab-plan]").forEach((button) => {
    button.addEventListener("click", () => {
      state.rehabPlanIndex = Number(button.dataset.rehabPlan) || 0;
      state.rehabCalendarViewDate = null;
      state.rehabCalendarSelectedPhase = null;
      renderHealth();
      refreshHealthIndicatorsForPlan(selectedRehabPlan());
    });
  });
}

function rehabPhaseRecords(plan) {
  if (!plan) return [];
  return [
    {key:"event",label:"Weather event",date:plan.event_start_date,detail:`${plan.event_label} begins; monitor conditions and avoid unsafe field work.`},
    {key:"inspection",label:"Field inspection",date:plan.recommended_assessment_date,detail:"Inspect damage, drainage, tree stability, symptoms, and priority cells once field access is safe."},
    {key:"rehabilitation",label:"Rehabilitation start",date:plan.recommended_rehabilitation_date,detail:"Begin the recommended rehabilitation work after inspection confirms the affected areas."},
    {key:"followup30",label:"30-day follow-up",date:plan.follow_up_30_date,detail:"Check early recovery, survival, sanitation, and whether rehabilitation actions are working."},
    {key:"followup90",label:"90-day review",date:plan.follow_up_90_date,detail:"Review longer-term recovery and decide whether another rehabilitation cycle is needed."},
  ].filter(item=>item.date);
}
function renderRehabCalendar(plan,{preserveView=false}={}) {
  const root=$("rehabSchedule"); if(!root) return;
  if(!plan){root.innerHTML='<div class="empty-state">Run the forecast to build the rehabilitation calendar.</div>';return;}
  const phases=rehabPhaseRecords(plan); const selectedKey=state.rehabCalendarSelectedPhase || phases[0]?.key;
  const selected=phases.find(p=>p.key===selectedKey)||phases[0]; state.rehabCalendarSelectedPhase=selected?.key||null;
  if(!preserveView||!state.rehabCalendarViewDate){const d=new Date(`${selected?.date||plan.event_start_date}T12:00:00`);state.rehabCalendarViewDate=new Date(d.getFullYear(),d.getMonth(),1);}
  const view=new Date(state.rehabCalendarViewDate); const year=view.getFullYear(),month=view.getMonth(); const first=new Date(year,month,1).getDay(); const days=new Date(year,month+1,0).getDate(); const cells=[];
  for(let i=0;i<first;i++) cells.push('<div class="rehab-calendar-empty"></div>');
  for(let day=1;day<=days;day++){
    const key=`${year}-${String(month+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`; const hits=phases.filter(p=>String(p.date).slice(0,10)===key); const markers=hits.map(p=>`<i class="${p.key}"></i>`).join(""); const active=hits.some(p=>p.key===selected?.key);
    cells.push(`<button type="button" class="rehab-calendar-day${hits.length?" has-phase":""}${active?" selected":""}" ${hits.length?`data-rehab-phase="${hits[0].key}"`:"disabled"}><span>${day}</span><em>${markers}</em></button>`);
  }
  root.innerHTML=`<div class="rehab-calendar-head"><button type="button" id="rehabCalPrev">‹</button><div><span>REHABILITATION CALENDAR</span><strong>${view.toLocaleString(undefined,{month:"long",year:"numeric"})}</strong></div><button type="button" id="rehabCalNext">›</button></div><div class="rehab-calendar-weekdays"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div><div class="rehab-calendar-grid">${cells.join("")}</div><div class="rehab-calendar-legend"><span><i class="event"></i>Event</span><span><i class="inspection"></i>Inspect</span><span><i class="rehabilitation"></i>Rehabilitate</span><span><i class="followup30"></i>Follow-up</span></div><div class="rehab-calendar-detail"><span>${escapeHtml(selected?.label||"")}</span><strong>${escapeHtml(selected?.date||"")}</strong><p>${escapeHtml(selected?.detail||"")}</p></div>`;
  root.querySelector('#rehabCalPrev')?.addEventListener('click',()=>{state.rehabCalendarViewDate=new Date(year,month-1,1);renderRehabCalendar(plan,{preserveView:true});});
  root.querySelector('#rehabCalNext')?.addEventListener('click',()=>{state.rehabCalendarViewDate=new Date(year,month+1,1);renderRehabCalendar(plan,{preserveView:true});});
  root.querySelectorAll('[data-rehab-phase]').forEach(btn=>btn.addEventListener('click',()=>{state.rehabCalendarSelectedPhase=btn.dataset.rehabPhase;renderRehabCalendar(plan,{preserveView:true});}));
}
async function refreshHealthIndicatorsForPlan(plan) {
  if (!plan || !state.health) return;
  const event = (state.latestForecast?.extreme_events || []).find((item) => String(item.start_date) === String(plan.event_start_date) && String(item.event_type || item.label) === String(plan.event_type || plan.event_label)) || null;
  const frame = event ? hazardRepresentativeForecastFrame(event) : nearestForecastFrameForDate(plan.event_start_date);
  if (!frame) return;
  const farm = getFarm();
  const severity = Math.max(0,Math.min(1,Number(plan.peak_severity_percent||0)/100));
  const eventType = String(plan.event_type||plan.event_label||"").toLowerCase();
  const eventSummary = event ? hazardEventWeatherSummary(event) : { rainTotal:Number(frame.rainfall_mm||0), tempPeak:Number(frame.temperature_max_c ?? frame.temperature_c ?? 27), humidityMean:Number(frame.humidity_percent||78) };
  const baselineAnnualRainfall = state.latestForecast ? state.latestForecast.monthly.slice(0,12).reduce((sum,row)=>sum+Number(row.rainfall_mm||0),0) : 2200;
  const isWet = eventType.includes("rain") || eventType.includes("typhoon");
  const isDry = eventType.includes("drought") || eventType.includes("heat");
  const eventDays = Math.max(1, Math.round((new Date(`${plan.event_end_date || plan.event_start_date}T12:00:00`) - new Date(`${plan.event_start_date}T12:00:00`)) / 86400000) + 1);
  const monthlyEquivalentRain = Math.max(0, Number(eventSummary.rainTotal || 0) * (30 / eventDays));
  const pestRain = isWet ? Math.max(monthlyEquivalentRain, 240 + 700 * severity) : isDry ? Math.min(monthlyEquivalentRain, 90 * (1-severity)) : Math.max(0, monthlyEquivalentRain);
  const pestHumidity = isWet ? Math.max(Number(eventSummary.humidityMean || frame.humidity_percent || 78), 80 + 16 * severity) : isDry ? Math.min(Number(frame.humidity_percent || 70), 68 - 16 * severity) : Number(frame.humidity_percent || 78);
  const eventAnnualRainfall = isDry
    ? Math.max(650, baselineAnnualRainfall * (1 - .58 * severity))
    : isWet ? Math.min(4800, baselineAnnualRainfall * (1 + .30 * severity)) : baselineAnnualRainfall;
  const eventTemp = isDry ? Math.max(Number(eventSummary.tempPeak || frame.temperature_c || 27), 29 + 7 * severity) : Number(frame.temperature_c || eventSummary.tempPeak || 27);
  try {
    const [pest,suit]=await Promise.all([
      api('/api/pest-risk/evaluate',{method:'POST',body:JSON.stringify({prior_probability:0.15,symptoms:farm.symptoms,humidity_percent:Math.max(30,Math.min(100,pestHumidity)),rainfall_mm_month:pestRain,average_tree_age:farm.trees.average_age_years})}),
      api('/api/suitability/evaluate',{method:'POST',body:JSON.stringify({soil_terrain:farm.soil_terrain,annual_rainfall_mm:eventAnnualRainfall,mean_temperature_c:eventTemp,humidity_percent:Math.max(30,Math.min(100,Number(frame.humidity_percent||eventSummary.humidityMean||78))),drought_exposure:isDry?Math.max(.35,.45+.5*severity):Math.max(.04,.10*(1-severity)),climate_stress:Math.max(.08,isDry?.35+.6*severity:.12+.45*severity)})})
    ]);
    if (selectedRehabPlan()?.id !== plan.id) return;
    const rawPestProbability = Number(pest.posterior_probability || 0);
    const weatherPestAdjustment = isWet
      ? Math.min(.28, .08 + .20 * severity + Math.max(0,pestHumidity-80)/180)
      : isDry ? -Math.min(.06,.04*severity) : 0;
    pest.event_conditioned_probability = Math.max(.001,Math.min(.999,rawPestProbability + weatherPestAdjustment));
    pest.event_conditioning = { event_type:eventType, rainfall_mm_month:pestRain, humidity_percent:pestHumidity, severity, raw_posterior_probability:rawPestProbability, weather_adjustment:weatherPestAdjustment };
    suit.event_conditioning = { event_type:eventType, annual_rainfall_mm:eventAnnualRainfall, mean_temperature_c:eventTemp, severity };
    state.health.pest=pest; state.health.suit=suit; state.health.eventFrame=frame; state.health.eventPlanId=plan.id;
    renderHealthDonuts(); renderHealthOverviewChart();
  } catch(error){ console.warn('Event-specific farm-health indicator refresh failed.',error); }
}

function renderRehabProcedure(plan) {
  if (!plan) {
    $("rehabSchedule").innerHTML = '<div><span>Event</span><strong>Waiting for forecast</strong></div>';
    $("rehabProcedure").innerHTML = '<div class="empty-state">Run the forecast and health analysis first.</div>';
    return;
  }
  renderRehabCalendar(plan);
  const phases = rehabPhaseRecords(plan);
  const selectedKey = state.rehabCalendarSelectedPhase || phases[0]?.key;
  const selected = phases.find((item) => item.key === selectedKey) || phases[0];
  const stepSummaries = (plan.procedure || []);
  const cards = phases.map((phase, index) => {
    const summary = stepSummaries[index] || phase.detail;
    const active = selected?.key === phase.key;
    return `<button type="button" class="rehab-step-card${active ? " active" : ""}" data-rehab-step="${escapeHtml(phase.key)}">
      <div class="rehab-step-top">
        <span class="rehab-step-index">${index + 1}</span>
        <span class="rehab-step-arrow" aria-hidden="true">${index < phases.length - 1 ? "→" : "✓"}</span>
      </div>
      <div class="rehab-step-icon" aria-hidden="true">${rehabStepIcon(phase.key)}</div>
      <div>
        <strong class="rehab-step-title">${escapeHtml(phase.label)}</strong>
        <div class="rehab-step-date">${escapeHtml(phase.date)}</div>
      </div>
      <div class="rehab-step-copy">${escapeHtml(summary)}</div>
      <span class="rehab-step-chip">${active ? "Selected step" : "Open step"}</span>
    </button>`;
  }).join("");
  $("rehabProcedure").innerHTML = `<div class="rehab-procedure-head"><div><strong>${escapeHtml(plan.event_label)}</strong><span>${number(plan.estimated_loss_tons, 2)} t estimated loss · ${number(plan.estimated_trees_affected, 0)} trees to inspect</span></div><span class="rehab-impact-badge">${number(plan.peak_severity_percent, 0)}/100</span></div>
    <div class="rehab-procedure-flow">${cards}</div>
    <div class="rehab-step-detail"><span>ACTIVE STEP</span><strong>${escapeHtml(selected?.label || plan.event_label)}</strong><p>${escapeHtml(selected?.detail || stepSummaries[0] || "Follow the highlighted step and verify field conditions before action.")}</p></div>
    <p class="rehab-warning">${escapeHtml(state.health.rehab.warning || "Field verification is required before work begins.")}</p>`;
  document.querySelectorAll('[data-rehab-step]').forEach((button) => button.addEventListener('click', () => {
    state.rehabCalendarSelectedPhase = button.dataset.rehabStep;
    renderRehabProcedure(plan);
    renderRehabCalendar(plan, { preserveView: true });
  }));
  const cached = state.rehabAiByPlan[plan.id];
  $("rehabAiResult").innerHTML = cached
    ? `<strong>AI recommendation · ${escapeHtml("CoCO-PILOT")}</strong>${renderPilotMarkdown(cached.answer)}`
    : `<strong>AI recommendation</strong><p>Use CoCO-PILOT to turn this event plan into a concise farm-specific work order.</p>`;
}

function pointInsidePolygon(lat, lng, polygon) {
  let inside = false;
  for (let i=0,j=polygon.length-1;i<polygon.length;j=i++) {
    const yi=Number(polygon[i][0]), xi=Number(polygon[i][1]);
    const yj=Number(polygon[j][0]), xj=Number(polygon[j][1]);
    const hit=((yi>lat)!==(yj>lat)) && (lng < (xj-xi)*(lat-yi)/((yj-yi)||1e-12)+xi);
    if(hit) inside=!inside;
  }
  return inside;
}
function clipFarmPolygonToCell(polygon, cellBounds) {
  if (!Array.isArray(polygon) || polygon.length < 3 || !Array.isArray(cellBounds) || cellBounds.length < 2) return [];
  const south=Math.min(Number(cellBounds[0][0]),Number(cellBounds[1][0]));
  const north=Math.max(Number(cellBounds[0][0]),Number(cellBounds[1][0]));
  let west=Math.min(Number(cellBounds[0][1]),Number(cellBounds[1][1]));
  let east=Math.max(Number(cellBounds[0][1]),Number(cellBounds[1][1]));
  const padLat=Math.max((north-south)*0.018,1e-9);
  const padLng=Math.max((east-west)*0.018,1e-9);
  const paddedSouth=south-padLat, paddedNorth=north+padLat; west-=padLng; east+=padLng;
  let subject=polygon.map(([lat,lng])=>({x:Number(lng),y:Number(lat)}));
  const clipEdge=(points,inside,intersect)=>{
    const out=[]; if(!points.length) return out;
    let previous=points.at(-1); let previousInside=inside(previous);
    for(const current of points){
      const currentInside=inside(current);
      if(currentInside){ if(!previousInside) out.push(intersect(previous,current)); out.push(current); }
      else if(previousInside) out.push(intersect(previous,current));
      previous=current; previousInside=currentInside;
    }
    return out;
  };
  const vertical=(a,b,x)=>{ const t=Math.abs(b.x-a.x)<1e-12?0:(x-a.x)/(b.x-a.x); return {x,y:a.y+(b.y-a.y)*t}; };
  const horizontal=(a,b,y)=>{ const t=Math.abs(b.y-a.y)<1e-12?0:(y-a.y)/(b.y-a.y); return {x:a.x+(b.x-a.x)*t,y}; };
  subject=clipEdge(subject,p=>p.x>=west-1e-12,(a,b)=>vertical(a,b,west));
  subject=clipEdge(subject,p=>p.x<=east+1e-12,(a,b)=>vertical(a,b,east));
  subject=clipEdge(subject,p=>p.y>=paddedSouth-1e-12,(a,b)=>horizontal(a,b,paddedSouth));
  subject=clipEdge(subject,p=>p.y<=paddedNorth+1e-12,(a,b)=>horizontal(a,b,paddedNorth));
  return subject.length>=3?subject.map(p=>[p.y,p.x]):[];
}

function renderRehabMap(plan, data) {
  state.layers.rehab.clearLayers();
  if (!plan || !data?.bounds) return;
  const bounds = data.bounds;
  state.rehabClipPolygon = Array.isArray(data.polygon) && data.polygon.length >= 3 ? data.polygon : null;
  for (const cell of plan.cells || []) {
    const clippedShape = state.rehabClipPolygon ? clipFarmPolygonToCell(state.rehabClipPolygon, cell.bounds) : [
      [Number(cell.bounds[0][0]),Number(cell.bounds[0][1])],
      [Number(cell.bounds[0][0]),Number(cell.bounds[1][1])],
      [Number(cell.bounds[1][0]),Number(cell.bounds[1][1])],
      [Number(cell.bounds[1][0]),Number(cell.bounds[0][1])],
    ];
    if (!clippedShape.length) continue;
    const gridCell = L.polygon(clippedShape, {
      renderer: state.renderers.rehabGrid,
      pane: "rehabGridPane",
      color: rehabHeatColor(cell.damage_score),
      opacity: .92,
      weight: .55,
      fillColor: rehabHeatColor(cell.damage_score),
      fillOpacity: .82,
      className: "rehab-grid-cell",
      interactive: true,
    }).addTo(state.layers.rehab);
    gridCell.bindTooltip(`${cell.class} · ${number(cell.damage_score, 0)}/100`);
    gridCell.on("click", () => {
      $("rehabDetails").innerHTML = `<strong>${escapeHtml(cell.class)} · ${number(cell.damage_score, 0)}/100</strong><br>${escapeHtml(cell.recommended_action)}<br><span>${escapeHtml(cell.explanation)}</span>`;
    });
  }
  if (data.polygon?.length) {
    L.polygon(data.polygon, { pane:"rehabOutlinePane", color: "#174c24", weight: 3, fillColor:"#f28b23", fillOpacity:.035, interactive: false }).addTo(state.layers.rehab);
  }
  const farmBounds = data.polygon?.length
    ? L.latLngBounds(data.polygon.map((point) => L.latLng(Number(point[0]), Number(point[1]))))
    : L.latLngBounds([[bounds.south, bounds.west], [bounds.north, bounds.east]]);
  requestAnimationFrame(() => {
    state.maps.rehab.invalidateSize({ pan:false });
    state.maps.rehab.fitBounds(farmBounds, { padding:[34,34], maxZoom:17, animate:false });
    setTimeout(() => {
      state.maps.rehab.invalidateSize({ pan:false });
      state.maps.rehab.fitBounds(farmBounds, { padding:[34,34], maxZoom:17, animate:false });
        }, 45);
  });
  $("rehabDetails").innerHTML = `<strong>${escapeHtml(plan.event_label)}</strong><br>
    ${plan.counts["No Damage"] || 0} green zones · ${plan.counts["Needs inspection"] || 0} yellow zones · ${plan.counts["Needs Rehabilitation"] || 0} red zones.<br>
    <span>Click the heatmap to inspect a management zone.</span>`;
}

async function generateRehabAiRecommendation() {
  const plan = selectedRehabPlan();
  if (!plan) return toast("Run a forecast and select a rehabilitation event first.", true);
  const button = $("generateRehabAiButton");
  button.disabled = true;
  $("rehabAiResult").innerHTML = '<strong>AI recommendation</strong><p>CoCO-PILOT is preparing a concise work plan…</p>';
  try {
    const status = await api("/api/assistant/status");
    if (!status.configured) throw new Error("Add an AI API key in Settings before generating an AI recommendation.");
    const response = await api("/api/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        message: plan.ai_prompt,
        history: [],
        context: { ...pilotContext(), rehabilitation_plan: plan },
        document_ids: state.pilotDocumentIds.map((item) => item.id),
      }),
    });
    state.rehabAiByPlan[plan.id] = response;
    $("rehabAiResult").innerHTML = `<strong>AI recommendation · ${escapeHtml("CoCO-PILOT")}</strong>${renderPilotMarkdown(response.answer)}`;
  } catch (error) {
    $("rehabAiResult").innerHTML = `<strong>AI recommendation unavailable</strong><p>${escapeHtml(error.message)}</p>`;
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function renderHealthTreeChart() {
  const farm = getFarm();
  const current = farm.trees;
  const final = state.latestForecast?.annual_states?.at(-1)?.states || current;
  const labels = [
    "Young",
    "Productive",
    "Aging",
    "Stressed",
    "Infested",
    "Recovering",
    "Dead",
  ];
  const keys = [
    "young",
    "productive",
    "aging",
    "stressed",
    "infested",
    "recovering",
    "dead",
  ];
  replaceChart("tree", "treeStateChart", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Current",
          data: keys.map((k) => current[k]),
          backgroundColor: "rgba(0,183,90,.52)",
        },
        {
          label: "Projected horizon",
          data: keys.map((k) => final[k]),
          backgroundColor: "rgba(255,176,0,.58)",
        },
      ],
    },
    options: chartOptions("Trees"),
  });
}

async function runFullAnalysis() {
  try {
    loading(true, "Running full analysis for report…");
    const d = await api("/api/analysis/full", {
      method: "POST",
      body: JSON.stringify({
        farm: getFarm(),
        scenario: AUTO_FORECAST_SCENARIO,
        period: "2041-2060",
        end_year: 2050,
        runs: AUTO_FORECAST_RUNS,
        seed: 42,
      }),
    });
    state.latestAnalysis = d;
    state.latestAnalysisId = d.analysis_id;
    toast("Full analysis refreshed.");
    return d;
  } catch (e) {
    toast(e.message, true);
    throw e;
  } finally {
    loading(false);
  }
}
function compactForecastForReport(forecast) {
  if (!forecast) return null;
  const frames = forecast.frames || [];
  const keep = new Set([0, frames.length - 1]);
  for (let i = 12; i < frames.length; i += 13) keep.add(i);
  const criticalIndexes = new Set();
  const rankedEvents = [...(forecast.extreme_events || [])]
    .sort((a, b) => Number(b.impact_index || 0) - Number(a.impact_index || 0))
    .slice(0, 4);
  for (const event of rankedEvents) {
    const index = frames.findIndex(
      (frame) =>
        frame.week_start <= event.start_date &&
        frame.week_end >= event.start_date,
    );
    if (index >= 0) criticalIndexes.add(index);
  }
  if (frames.length) {
    criticalIndexes.add(
      frames.reduce(
        (best, frame, index) =>
          Number(frame.rain_intensity_mm_h) >
          Number(frames[best].rain_intensity_mm_h)
            ? index
            : best,
        0,
      ),
    );
    criticalIndexes.add(
      frames.reduce(
        (best, frame, index) =>
          Number(frame.temperature_max_c) >
          Number(frames[best].temperature_max_c)
            ? index
            : best,
        0,
      ),
    );
  }
  return {
    farm: forecast.farm,
    map_bounds: forecast.map_bounds,
    farm_map_position: forecast.farm_map_position,
    scenario: forecast.scenario,
    intervention: forecast.intervention,
    effective_start_date: forecast.effective_start_date,
    effective_end_date: forecast.effective_end_date,
    timeline_resolution: forecast.timeline_resolution,
    posterior_summary: forecast.posterior_summary,
    annual_by_product: forecast.annual_by_product,
    extreme_events: forecast.extreme_events,
    official_production_reference: forecast.official_production_reference,
    product_model: forecast.product_model,
    critical_weather_frames: [...criticalIndexes]
      .sort((a, b) => a - b)
      .slice(0, 5)
      .map((index) => {
        const frame = frames[index];
        return {
          week_start: frame.week_start,
          week_end: frame.week_end,
          label: frame.label,
          rainfall_mm: frame.rainfall_mm,
          rain_intensity_mm_h: frame.rain_intensity_mm_h,
          temperature_c: frame.temperature_c,
          temperature_max_c: frame.temperature_max_c,
          wind_speed_kmh: frame.wind_speed_kmh,
          event: frame.event,
          event_severity: frame.event_severity,
          condition_class: frame.condition_class,
          farm_condition_score: frame.farm_condition_score,
          production_coconut_w_husk_tons: frame.production_coconut_w_husk_tons,
          spatial: frame.spatial,
          spatial_grid: frame.spatial_grid,
          grid_bounds: frame.grid_bounds,
          data_mode: frame.data_mode,
        };
      }),
    selected_weekly_frames: [...keep]
      .sort((a, b) => a - b)
      .map((index) => {
        const frame = frames[index];
        return {
          week_start: frame.week_start,
          week_end: frame.week_end,
          rainfall_mm: frame.rainfall_mm,
          temperature_c: frame.temperature_c,
          event: frame.event,
          condition_class: frame.condition_class,
          pest_probability: frame.pest_probability,
          production_coconut_w_husk_tons: frame.production_coconut_w_husk_tons,
          production_coconut_mature_tons: frame.production_coconut_mature_tons,
          production_coconut_young_tons: frame.production_coconut_young_tons,
          product_response_factors: frame.product_response_factors,
          data_mode: frame.data_mode,
        };
      }),
    warnings: forecast.warnings,
  };
}

async function generateReport() {
  try {
    if (!state.latestAnalysisId) await runFullAnalysis();
    loading(true, "Generating report…");
    const format = $("reportFormat").value;
    const supplement = compactForecastForReport(state.latestForecast);
    const payload = {
      analysis_id: state.latestAnalysisId,
      report_format: format,
    };
    if (supplement || state.health) {
      payload.analysis = {};
      if (supplement) payload.analysis.farm_site_forecast = supplement;
      if (state.health?.specific)
        payload.analysis.pest_specific = state.health.specific;
      if (state.health) {
        const selectedPlan = selectedRehabPlan();
        payload.analysis.farm_health_snapshot = {
          bayesian_pest: state.health.pest,
          land_suitability: state.health.suit,
          rehabilitation_summary: {
            selected_event: selectedPlan?.event_label || null,
            rehabilitation_date: selectedPlan?.recommended_rehabilitation_date || null,
            high_priority_cells: selectedPlan?.counts?.["Needs Rehabilitation"] || 0,
            rehabilitation_cells: selectedPlan?.counts?.["Needs Rehabilitation"] || 0,
            inspection_cells: selectedPlan?.counts?.["Needs inspection"] || 0,
            total_cells: selectedPlan?.cells?.length || 0,
          },
        };
        payload.analysis.rehabilitation_event_plans = state.health.rehab;
      }
    }
    const d = await api("/api/reports/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.latestReportId = d.report_id;
    $("reportResult").innerHTML =
      `<strong>Report ready</strong><br><a href="${escapeHtml(d.download_url)}" target="_blank">${escapeHtml(d.filename)}</a>`;
    window.open(d.download_url, "_blank");
    refreshDatabase();
  } catch (e) {
    toast(e.message, true);
  } finally {
    loading(false);
  }
}
async function saveCurrentForecast() {
  if (!state.latestForecast) return toast("Run a forecast first.", true);
  try {
    loading(true, "Saving weekly forecast…");
    const summary = {
      farm_name: state.latestForecast.farm.name,
      scenario: state.latestForecast.scenario,
      intervention: state.latestForecast.intervention,
      start: state.latestForecast.effective_start_date,
      end: state.latestForecast.effective_end_date,
      weeks: state.latestForecast.frames.length,
      final_median_tons:
        state.latestForecast.posterior_summary.final_median_tons,
    };
    const d = await api("/api/database/forecasts", {
      method: "POST",
      body: JSON.stringify({
        name: $("forecastSaveName").value,
        farm_id: state.selectedFarmId,
        summary,
        forecast: state.latestForecast,
      }),
    });
    $("forecastSaveResult").textContent = `Saved as ${d.forecast_id}`;
    toast("Forecast saved.");
    refreshDatabase();
  } catch (e) {
    toast(e.message, true);
  } finally {
    loading(false);
  }
}

async function refreshDatabase() {
  try {
    const [summary, farms, forecasts, analyses, reports] = await Promise.all([
      api("/api/database/summary"),
      api("/api/farms"),
      api("/api/database/forecasts"),
      api("/api/database/analyses"),
      api("/api/database/reports"),
    ]);
    $("dbFarmCount").textContent = summary.farms;
    $("dbForecastCount").textContent = summary.forecasts;
    $("dbAnalysisCount").textContent = summary.analyses;
    $("dbReportCount").textContent = summary.reports;
    state.farms = farms.farms;
    renderFarmDatabase();
    $("forecastDatabaseList").innerHTML =
      (forecasts.forecasts || [])
        .map((f) =>
          recordHtml(
            f.name,
            `${f.summary?.scenario || ""} · ${f.summary?.weeks || 0} weeks · ${new Date(f.updated_at).toLocaleString()}`,
            `<button data-load-forecast="${f.id}">Load</button><button data-delete-forecast="${f.id}">Delete</button>`,
          ),
        )
        .join("") || '<div class="empty-state">No saved forecasts.</div>';
    $("analysisDatabaseList").innerHTML =
      (analyses.analyses || [])
        .map((a) =>
          recordHtml(
            a.farm_name,
            `${a.scenario || ""} · through ${a.end_year || "—"} · ${new Date(a.created_at).toLocaleString()}`,
            `<button data-open-analysis="${a.id}">Open</button><button data-delete-analysis="${a.id}">Delete</button>`,
          ),
        )
        .join("") || '<div class="empty-state">No analyses.</div>';
    $("reportDatabaseList").innerHTML =
      (reports.reports || [])
        .map((r) =>
          recordHtml(
            r.filename,
            `${String(r.report_type).toUpperCase()} · ${new Date(r.created_at).toLocaleString()}`,
            `<button data-open-report="${r.id}">Download</button>`,
          ),
        )
        .join("") || '<div class="empty-state">No reports.</div>';
    bindDatabaseActions();
  } catch (e) {
    toast(e.message, true);
  }
}
function recordHtml(name, meta, actions) {
  return `<article class="record"><div><strong>${escapeHtml(name)}</strong><small>${escapeHtml(meta)}</small></div><div class="record-actions">${actions}</div></article>`;
}
function renderFarmDatabase() {
  $("farmDatabaseList").innerHTML =
    (state.farms || [])
      .map((f) =>
        recordHtml(
          f.name,
          `${f.location.province} · ${number(f.area_hectares, 2)} ha`,
          `<button data-db-farm="${f.id}">Load</button>`,
        ),
      )
      .join("") || '<div class="empty-state">No saved farms.</div>';
  document
    .querySelectorAll("[data-db-farm]")
    .forEach((b) =>
      b.addEventListener("click", () => loadSelectedFarm(b.dataset.dbFarm)),
    );
}
function bindDatabaseActions() {
  document.querySelectorAll("[data-load-forecast]").forEach((b) =>
    b.addEventListener("click", async () => {
      try {
        loading(true, "Loading saved forecast…");
        const d = await api(
          `/api/database/forecasts/${b.dataset.loadForecast}`,
        );
        state.latestForecast = d.forecast;
        state.forecastIndex = 0;
        renderForecast(state.latestForecast);
        showSection("outlook");
      } catch (e) {
        toast(e.message, true);
      } finally {
        loading(false);
      }
    }),
  );
  document.querySelectorAll("[data-delete-forecast]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (confirm("Delete this saved forecast?")) {
        await api(`/api/database/forecasts/${b.dataset.deleteForecast}`, {
          method: "DELETE",
        });
        refreshDatabase();
      }
    }),
  );
  document.querySelectorAll("[data-open-analysis]").forEach((b) =>
    b.addEventListener("click", async () => {
      const d = await api(`/api/analysis/${b.dataset.openAnalysis}`);
      state.latestAnalysis = d.result;
      state.latestAnalysisId = d.id;
      showSection("reports");
      toast("Analysis loaded for reporting.");
    }),
  );
  document.querySelectorAll("[data-delete-analysis]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (confirm("Delete this analysis?")) {
        await api(`/api/database/analyses/${b.dataset.deleteAnalysis}`, {
          method: "DELETE",
        });
        refreshDatabase();
      }
    }),
  );
  document
    .querySelectorAll("[data-open-report]")
    .forEach((b) =>
      b.addEventListener("click", () => {
        state.latestReportId = b.dataset.openReport;
        window.open(`/api/reports/${b.dataset.openReport}`, "_blank");
      }),
    );
}


function renderAutoWorkflowStatus(status) {
  state.autoWorkflowStatus = status || {};
  document.querySelectorAll('[data-auto-workflow-status]').forEach((strip) => {
    const phase9 = strip.querySelector('[data-auto-phase="9"]');
    const phase10 = strip.querySelector('[data-auto-phase="10"]');
    const msg = strip.querySelector('[data-auto-workflow-message]');
    const apply = (node, value) => {
      if (!node) return;
      node.classList.remove('running','complete','waiting','blocked','error');
      const normalized = String(value || 'waiting').toLowerCase();
      node.classList.add(normalized.includes('complete') ? 'complete' : normalized.includes('run') ? 'running' : normalized.includes('error') ? 'error' : normalized.includes('block') || normalized.includes('prereq') ? 'blocked' : 'waiting');
      const small = node.querySelector('small'); if (small) small.textContent = value || 'Waiting';
    };
    apply(phase9, status?.phase9 || 'Waiting');
    apply(phase10, status?.phase10 || 'Waiting');
    if (msg) msg.textContent = status?.message || 'Automatic workflow is waiting for eligible forecast and evidence records.';
  });
}
async function refreshAutoWorkflowStatus(kick = false) {
  try {
    if (kick) await api('/api/v2/workflows/auto-phase9-10/kick',{method:'POST'});
    const status = await api('/api/v2/workflows/auto-phase9-10/status');
    renderAutoWorkflowStatus(status);
    return status;
  } catch (error) {
    renderAutoWorkflowStatus({phase9:'Waiting',phase10:'Waiting',message:`Auto workflow status unavailable: ${error.message}`});
    return null;
  }
}
function setupInteractiveInformationPages() {
  const networkCopy = {
    1:["Farm evidence","Boundary, palm cohorts, field observations, soil, and management become versioned inputs for the downstream engines."],
    2:["Environmental state","The latest weather run and stress features attach time and location context to the farm evidence."],
    3:["Predictive engines","Production ML, Bayesian uncertainty, pest inference, and intercropping scoring produce independent analytical records."],
    4:["Optimization","Rehabilitation compares budget, labor, risk, and scenario outcomes before selecting a practical response."],
    5:["Traceable output","Phase 9 composes the integrated record; Phase 10 grounds CoCO-PILOT narratives and formal reports in that record."],
  };
  document.querySelectorAll('[data-network-node]').forEach((node) => {
    const activate = () => {
      document.querySelectorAll('[data-network-node]').forEach((item)=>item.classList.remove('active'));
      node.classList.add('active');
      const [titleText,copy]=networkCopy[Number(node.dataset.networkNode)] || ["Network stage",""];
      const detail=$("networkLiveDetail");
      if(detail) detail.innerHTML=`<span>LIVE TRACE</span><strong>${escapeHtml(titleText)}</strong><p>${escapeHtml(copy)}</p><div class="network-pulse-line"><i></i><i></i><i></i><i></i></div>`;
    };
    node.addEventListener('click',activate); node.addEventListener('keydown',(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}});
  });
  document.querySelectorAll('[data-report-stage]').forEach((button)=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-report-stage]').forEach((item)=>item.classList.remove('active')); button.classList.add('active');
  }));
  document.querySelectorAll('.interactive-formula-catalog article').forEach((card)=>{
    card.tabIndex=0;
    const toggle=()=>card.classList.toggle('expanded');
    card.addEventListener('click',toggle); card.addEventListener('keydown',(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});
  });
  document.querySelectorAll('[data-run-auto-workflow]').forEach((button)=>button.addEventListener('click',async()=>{
    button.disabled=true; await refreshAutoWorkflowStatus(true); setTimeout(()=>refreshAutoWorkflowStatus(false),1800); setTimeout(()=>{button.disabled=false;},2200);
  }));
}
function setPilotSphereState(mode='waiting') {
  const sphere=$("pilotNcsHologram"); if(!sphere) return;
  state.pilotSphereState=mode;
  sphere.classList.remove('waiting','typing','loading','speaking'); sphere.classList.add(mode);
}

function openWeatherModal(open) {
  const modal = $("weatherModal");
  const frame = $("weatherViewerFrame");
  const mount = open ? $("weatherModalMount") : $("weatherHomeMount");
  if (!modal || !frame || !mount) return;
  state.weatherModalOpen = open;
  mount.appendChild(frame);
  modal.classList.toggle("open", open);
  modal.setAttribute("aria-hidden", String(!open));
  document.body.classList.toggle("modal-open", open);
  if (open && state.previewEntered) playVoiceLine("weather-gis");
  setTimeout(() => {
    syncFarmToWeatherViewer();
    frame.contentWindow?.postMessage({ type: "COCO_AID_RESIZE" }, location.origin);
  }, 120);
}

function positionTutorial(target, step, titleText, bodyText) {
  const bubble = $("drawTutorial");
  if (!bubble || !target) return;
  bubble.hidden = false;
  $("drawTutorialTitle").textContent = titleText;
  $("drawTutorialText").textContent = bodyText;
  $("drawTutorialStep").textContent = `${step} of 3`;
  const rect = target.getBoundingClientRect();
  const landingRect = $("landing").getBoundingClientRect();
  bubble.style.left = `${Math.max(16, Math.min(landingRect.width - 320, rect.left - landingRect.left + rect.width + 14))}px`;
  bubble.style.top = `${Math.max(110, rect.top - landingRect.top - 16)}px`;
}

function startDrawTutorial() {
  $("landingMap").scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => {
    const polygonButton = $("landingMap")?.querySelector(".leaflet-draw-draw-polygon");
    positionTutorial(polygonButton, 1, "Choose the polygon tool", "Click this shape tool, then click around the edge of your farm.");
    polygonButton?.addEventListener("click", () => {
      setTimeout(() => positionTutorial($("landingMap"), 2, "Mark the farm corners", "Click each corner of the farm. Finish by clicking the first point again."), 80);
    }, { once: true });
  }, 650);
}

function completeDrawTutorial() {
  if (state.polygon.length < 3) return;
  positionTutorial($("landingContinue"), 3, "Boundary complete", "Review the calculated area, then continue to enter the farm details.");
}

function closeDrawTutorial() {
  const bubble = $("drawTutorial");
  if (bubble) bubble.hidden = true;
}

const ABOUT_MODULES=Object.freeze({foundation:{eyebrow:"LAYER 01 · EVIDENCE BASE",title:"Data Foundation",description:"Official PSA coconut-production records, farm geometry, tree condition, soil and management observations provide the traceable evidence base used by downstream engines.",inputs:"PSA records · farm polygon · field observations",output:"Versioned farm and evidence records",boundary:"The platform preserves whether data are official, observed, estimated, or modeled instead of presenting all values as equivalent evidence.",hue:148},weather:{eyebrow:"LAYER 02 · ATMOSPHERE",title:"Weather & Climate",description:"COCO-AID keeps genuine short-term numerical weather forecasts separate from long-term climate-conditioned daily simulation while feeding both into farm-response analysis.",inputs:"Open-Meteo window · climate parameters · farm location",output:"Weather features · hazards · modeled daily paths",boundary:"Provider-backed weather is limited to the supported forecast horizon. Dates beyond it are plausible modeled conditions, not exact future weather forecasts.",hue:198},models:{eyebrow:"LAYER 03 · INFERENCE",title:"Probabilistic Models",description:"Machine-learning estimates, Bayesian evidence updates, stochastic farm-state transitions, and Monte Carlo simulation quantify production, biological pressure, recovery, and downside risk.",inputs:"Farm evidence · weather features · parameter versions",output:"Distributions · probabilities · model scores",boundary:"Model outputs carry uncertainty and version metadata. Development validation does not guarantee field-level accuracy without longitudinal farm validation.",hue:42},intercrop:{eyebrow:"LAYER 04 · AGROECOSYSTEM",title:"Intercropping Potential",description:"Canopy-light compatibility and integrated farm conditions are used to rank intercrop candidates while preserving coconut competition and management constraints.",inputs:"Canopy light · farm condition · crop requirement profiles",output:"Ranked crop suitability · competition indicators",boundary:"Canopy-light bands are source-backed in the project catalog; several non-light agronomic ranges remain development assumptions pending expert and field calibration.",hue:92},decision:{eyebrow:"LAYER 05 · ACTION",title:"Decision & Reports",description:"Phase 9 integrates production, Bayesian, pest, intercropping, and rehabilitation records. Phase 10 converts the grounded record into an explainable narrative and formal reports.",inputs:"Integrated analytical records · intervention options",output:"Decision network · CoCO-PILOT explanation · DOCX/PDF",boundary:"Recommendations support planning and field inspection and should be confirmed with local agricultural experts, diagnostics, and measured farm observations.",hue:28}});
function selectAboutModule(key){const m=ABOUT_MODULES[key]||ABOUT_MODULES.foundation;state.aboutModule=ABOUT_MODULES[key]?key:"foundation";document.querySelectorAll("[data-about-module]").forEach((b)=>b.classList.toggle("active",b.dataset.aboutModule===state.aboutModule));[["aboutModuleEyebrow",m.eyebrow],["aboutModuleTitle",m.title],["aboutModuleDescription",m.description],["aboutModuleInputs",m.inputs],["aboutModuleOutput",m.output],["aboutModuleBoundary",m.boundary]].forEach(([id,v])=>{if($(id))$(id).textContent=v;});$("aboutHologramStage")?.style.setProperty("--about-hue",String(m.hue));}
function aboutHoloRotate(p){const cy=Math.cos(state.aboutHologramYaw),sy=Math.sin(state.aboutHologramYaw),cp=Math.cos(state.aboutHologramPitch),sp=Math.sin(state.aboutHologramPitch),x=cy*p.x-sy*p.z,z0=sy*p.x+cy*p.z,y=cp*p.y-sp*z0,z=sp*p.y+cp*z0;return{x,y,z};}
function drawAboutHologram(time=0){const canvas=$("aboutHologramCanvas");if(!canvas||state.section!=="about")return;const r=canvas.getBoundingClientRect();if(r.width<10||r.height<10)return;const dpr=Math.min(1.2,window.devicePixelRatio||1),w=Math.round(r.width*dpr),h=Math.round(r.height*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,r.width,r.height);const m=ABOUT_MODULES[state.aboutModule]||ABOUT_MODULES.foundation,hue=m.hue,rad=Math.min(r.width,r.height)*.27,cx=r.width/2,cy=r.height*.5,n=[];for(let lat=-2;lat<=2;lat++)for(let lon=0;lon<12;lon++){const phi=lat*.36,theta=lon/12*Math.PI*2;n.push(aboutHoloRotate({x:Math.cos(phi)*Math.cos(theta),y:Math.sin(phi),z:Math.cos(phi)*Math.sin(theta)}));}ctx.save();ctx.globalCompositeOperation="lighter";for(let i=0;i<n.length;i++){const a=n[i];for(let j=i+1;j<n.length;j++){const b=n[j],d=(a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2;if(d>.34)continue;ctx.strokeStyle=`hsla(${hue},70%,58%,.065)`;ctx.lineWidth=.7;ctx.beginPath();ctx.moveTo(cx+a.x*rad,cy-a.y*rad);ctx.lineTo(cx+b.x*rad,cy-b.y*rad);ctx.stroke();}}n.sort((a,b)=>a.z-b.z).forEach((p,i)=>{const depth=(p.z+1)/2,pulse=.75+.25*Math.sin(time/760+i*.42);ctx.fillStyle=`hsla(${hue},78%,58%,${.28+.52*depth})`;ctx.beginPath();ctx.arc(cx+p.x*rad,cy-p.y*rad,1.2+2*depth*pulse,0,Math.PI*2);ctx.fill();});ctx.restore();}
function aboutHologramLoop(time){if(state.section!=="about"){state.aboutHologramAnimation=null;state.aboutHologramLastRender=0;return;}if(!state.aboutHologramDrag)state.aboutHologramYaw+=.0022;if(time-(state.aboutHologramLastRender||0)>=40){drawAboutHologram(time);state.aboutHologramLastRender=time;}state.aboutHologramAnimation=requestAnimationFrame(aboutHologramLoop);}
function startAboutHologram(){if(state.section==="about"&&!state.aboutHologramAnimation)state.aboutHologramAnimation=requestAnimationFrame(aboutHologramLoop);}
function setupAboutExperience(){const canvas=$("aboutHologramCanvas");if(canvas&&canvas.dataset.bound!=="1"){canvas.dataset.bound="1";canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture?.(e.pointerId);state.aboutHologramDrag={x:e.clientX,y:e.clientY};});canvas.addEventListener("pointermove",e=>{if(!state.aboutHologramDrag)return;const dx=e.clientX-state.aboutHologramDrag.x,dy=e.clientY-state.aboutHologramDrag.y;state.aboutHologramDrag={x:e.clientX,y:e.clientY};state.aboutHologramYaw+=dx*.009;state.aboutHologramPitch=Math.max(-.65,Math.min(.65,state.aboutHologramPitch+dy*.006));drawAboutHologram(performance.now());});const release=e=>{state.aboutHologramDrag=null;try{canvas.releasePointerCapture?.(e.pointerId);}catch{}};canvas.addEventListener("pointerup",release);canvas.addEventListener("pointercancel",release);}document.querySelectorAll("[data-about-module]").forEach(b=>{if(b.dataset.bound==="1")return;b.dataset.bound="1";b.addEventListener("click",()=>selectAboutModule(b.dataset.aboutModule));});document.querySelectorAll("[data-about-jump]").forEach(b=>{if(b.dataset.bound==="1")return;b.dataset.bound="1";b.addEventListener("click",()=>$(b.dataset.aboutJump)?.scrollIntoView({behavior:"smooth",block:"start"}));});document.querySelectorAll(".about-card-toggle").forEach(b=>{if(b.dataset.bound==="1")return;b.dataset.bound="1";b.addEventListener("click",()=>{const c=b.closest(".about-card"),open=c?.classList.toggle("expanded"),symbol=b.querySelector("b");if(symbol)symbol.textContent=open?"−":"+";});});document.querySelectorAll(".interactive-formula-catalog article").forEach(c=>{if(c.dataset.bound==="1")return;c.dataset.bound="1";const t=()=>c.classList.toggle("expanded");c.addEventListener("click",t);c.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();t();}});});selectAboutModule(state.aboutModule);startAboutHologram();}

function pilotContext() {
  const selected = state.visualFrames?.[state.forecastIndex] || null;
  return {
    farm: getFarm(),
    forecast_summary: state.latestForecast?.posterior_summary || null,
    selected_frame: selected,
    hazards: (state.latestForecast?.extreme_events || []).slice(0, 12),
    pest_risk: state.health?.pest || state.latestAnalysis?.pest_risk || null,
    pest_specific: state.health?.specific || state.latestAnalysis?.pest_specific || null,
    suitability: state.health?.suit || state.latestAnalysis?.land_suitability || null,
    farm_condition: state.health?.assessment || state.latestAnalysis?.farm_assessment || null,
    recommended_intervention: state.latestAnalysis?.overview?.recommended_intervention || state.latestForecast?.recommended_intervention || null,
    rehabilitation_plan: selectedRehabPlan(),
  };
}

function openPilot(open = true) {
  const panel = $("cocoPilotPanel");
  panel?.classList.toggle("open", open);
  panel?.setAttribute("aria-hidden", String(!open));
  if (open) { setPilotSphereState("waiting"); setTimeout(() => $("pilotInput")?.focus(), 180); }
}

function renderPilotMarkdown(text) {
  let safe = escapeHtml(text);
  safe = safe.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/^###?\s+(.+)$/gm, "<h4>$1</h4>");
  safe = safe.replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>");
  safe = safe.replace(/((?:<li>.*?<\/li>\s*)+)/gs, "<ul>$1</ul>");
  safe = safe.replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  return `<p>${safe}</p>`;
}

function percentageDonuts(values) {
  if (!values?.length) return "";
  return `<div class="pilot-donuts">${values.slice(0, 3).map((value) => {
    const numeric = Math.max(0, Math.min(100, Number(value)));
    return `<div class="pilot-donut" style="--p:${numeric}"><span>${number(numeric, 1)}%</span></div>`;
  }).join("")}</div>`;
}

function appendPilotMessage(role, text, percentages = [], typing = false) {
  const messages = $("pilotMessages");
  messages?.querySelector(".pilot-welcome")?.remove();
  const article = document.createElement("article");
  article.className = `pilot-message ${role}`;
  const content = document.createElement("div");
  article.appendChild(content);
  if (role === "assistant") article.insertAdjacentHTML("beforeend", percentageDonuts(percentages));
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  if (!typing) {
    content.innerHTML = role === "assistant" ? renderPilotMarkdown(text) : `<p>${escapeHtml(text)}</p>`;
    messages.scrollTop = messages.scrollHeight;
    return Promise.resolve();
  }
  setPilotSphereState("speaking");
  return new Promise((resolve) => {
    let index = 0;
    const step = () => {
      index = Math.min(text.length, index + Math.max(2, Math.ceil(text.length / 160)));
      content.innerHTML = renderPilotMarkdown(text.slice(0, index));
      messages.scrollTop = messages.scrollHeight;
      if (index < text.length) setTimeout(step, 12);
      else { setPilotSphereState("waiting"); resolve(); }
    };
    step();
  });
}

function updatePilotAttachments() {
  const bar = $("pilotAttachmentBar");
  if (!bar) return;
  const labels = [];
  if (state.pilotContextAttached) labels.push("Current COCO-AID results");
  state.pilotDocumentIds.forEach((item) => labels.push(item.name));
  bar.hidden = !labels.length;
  bar.innerHTML = labels.map((label) => `<span>${escapeHtml(label)}</span>`).join("");
}

async function refreshPilotStatus() {
  try {
    const status = await api("/api/assistant/status");
    $("pilotStatus").textContent = status.configured ? `CoCO-PILOT ready` : "Add an AI key in Settings";
    $("geminiStatusText").textContent = status.configured ? `AI connection configured locally.` : "Not configured.";
  } catch {
    $("pilotStatus").textContent = "Assistant unavailable";
  }
}

async function configureGemini() {
  const key = $("geminiApiKeySetting").value.trim();
  if (!key) return toast("Paste an AI API key first.", true);
  try {
    await api("/api/assistant/configure", { method: "POST", body: JSON.stringify({ api_key: key }) });
    $("geminiApiKeySetting").value = "";
    await refreshPilotStatus();
    toast("CoCO-PILOT API key saved locally.");
  } catch (error) { toast(error.message, true); }
}

async function clearGemini() {
  try {
    await api("/api/assistant/configure", { method: "DELETE" });
    await refreshPilotStatus();
    toast("Local AI key cleared.");
  } catch (error) { toast(error.message, true); }
}

async function uploadPilotDocument(file) {
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    $("pilotStatus").textContent = "Reading document…";
    const response = await fetch("/api/assistant/upload-document", { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) throw new Error(formatApiErrorDetail(body, "Document upload failed"));
    state.pilotDocumentIds.push({ id: body.document_id, name: body.name });
    updatePilotAttachments();
    appendPilotMessage("assistant", `Attached **${body.name}**. Ask me about its findings or recommendations.`);
  } catch (error) { toast(error.message, true); }
  finally { refreshPilotStatus(); $("pilotFileInput").value = ""; }
}

async function attachLatestReportToPilot() {
  try {
    if (!state.latestReportId) {
      const listing = await api("/api/database/reports");
      state.latestReportId = listing.reports?.[0]?.id || null;
    }
    if (!state.latestReportId) return toast("Generate or save a report first.", true);
    const body = await api(`/api/assistant/attach-report/${state.latestReportId}`, { method: "POST" });
    state.pilotDocumentIds.push({ id: body.document_id, name: body.name });
    updatePilotAttachments();
    appendPilotMessage("assistant", `Attached the latest generated report: **${body.name}**.`);
  } catch (error) { toast(error.message, true); }
}

function appendPilotLoading() {
  setPilotSphereState("loading");
  const messages = $("pilotMessages");
  messages?.querySelector(".pilot-welcome")?.remove();
  messages?.querySelectorAll(".pilot-loading-message").forEach((node) => node.remove());
  const article = document.createElement("article");
  article.className = "pilot-message assistant pilot-loading-message";
  article.setAttribute("aria-label", "CoCO-PILOT is answering");
  article.innerHTML = '<span class="pilot-typing-dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="sr-only">CoCO-PILOT is answering</span>';
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function removePilotLoading(node = null) {
  node?.remove();
  $("pilotMessages")?.querySelectorAll(".pilot-loading-message").forEach((item) => item.remove());
}

async function sendPilotMessage(prompt = null) {
  const input = $("pilotInput");
  const message = String(prompt ?? input.value).trim();
  if (!message) return;
  openPilot(true);
  input.value = "";
  $("pilotTemplates").hidden = true;
  appendPilotMessage("user", message);
  const history = state.pilotHistory.slice(-10);
  state.pilotHistory.push({ role: "user", content: message });
  $("pilotSend").disabled = true;
  $("pilotStatus").textContent = "Answering…";
  const loadingMessage = appendPilotLoading();
  try {
    const response = await api("/api/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        history,
        context: state.pilotContextAttached ? pilotContext() : null,
        document_ids: state.pilotDocumentIds.map((item) => item.id),
      }),
    });
    removePilotLoading(loadingMessage);
    await appendPilotMessage("assistant", response.answer, response.percentages || [], true);
    state.pilotHistory.push({ role: "assistant", content: response.answer });
  } catch (error) {
    removePilotLoading(loadingMessage);
    const detail = String(error?.message || "Temporary service error");
    appendPilotMessage("assistant", `I could not complete that request. ${detail}`);
  } finally {
    removePilotLoading(loadingMessage);
    $("pilotSend").disabled = false;
    setPilotSphereState("waiting");
    refreshPilotStatus();
  }
}

function syncFarmToWeatherViewer() {
  [$("weatherViewerFrame"), $("weatherDedicatedFrame")].forEach((frame) => {
    if (frame?.contentWindow)
      frame.contentWindow.postMessage(
        { type: "COCO_AID_FARM", farm: getFarm() },
        location.origin,
      );
  });
  postWeatherTheme();
}
function bindEvents() {
  document
    .querySelectorAll(".nav-item[data-section]")
    .forEach((b) =>
      b.addEventListener("click", () => showSection(b.dataset.section)),
    );
  document
    .querySelectorAll("[data-nav-group-toggle]")
    .forEach((button) => button.addEventListener("click", () => {
      const groupName = button.dataset.navGroupToggle;
      if (!groupName) return;
      toggleNavGroup(groupName);
    }));
  document.querySelectorAll("[data-section-link]").forEach((a) =>
    a.addEventListener("click", (e) => {
      e.preventDefault();
      showSection(a.dataset.sectionLink);
    }),
  );
  $("menuButton")?.addEventListener("click", () => setNavigationOpen(true, { forceExpanded: true }));
  $("globalNavButton")?.addEventListener("click", toggleGlobalNavigation);
  document.addEventListener("pointerdown", (event) => {
    const sidebar = $("sidebar");
    const globalButton = $("globalNavButton");
    if (!sidebar?.classList.contains("open")) return;
    if (sidebar.contains(event.target) || globalButton?.contains(event.target)) return;
    setNavigationOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && $("sidebar")?.classList.contains("open")) setNavigationOpen(false);
  });
  window.addEventListener("resize", () => {
    applySidebarState();
    syncGlobalNavigationControl();
  }, { passive: true });
  $("sidebarCollapseButton")?.addEventListener("click", () => {
    const sidebar = $("sidebar");
    const finishSidebarTransition = () => {
      document.body.classList.remove("sidebar-transitioning");
      Object.values(state.maps).forEach((map) => map?.invalidateSize?.());
      window.dispatchEvent(new Event("resize"));
    };
    document.body.classList.add("sidebar-transitioning");
    state.settings.sidebarCollapsed = !state.settings.sidebarCollapsed;
    saveSettings();
    const onSidebarTransitionEnd = (event) => {
      if (event.target === sidebar && event.propertyName === "width") {
        sidebar.removeEventListener("transitionend", onSidebarTransitionEnd);
        finishSidebarTransition();
      }
    };
    sidebar?.addEventListener("transitionend", onSidebarTransitionEnd);
    setTimeout(() => {
      sidebar?.removeEventListener("transitionend", onSidebarTransitionEnd);
      finishSidebarTransition();
    }, 520);
  });
  updateNavigationState(state.section || "landing");
    $("themeButton").addEventListener("click", () => {
    state.settings.theme = state.settings.theme === "dark" ? "light" : "dark";
    saveSettings();
  });
  $("settingsButton").addEventListener("click", () => openSettings(true));
  $("settingsClose").addEventListener("click", () => openSettings(false));
  $("enterWebsiteButton")?.addEventListener("click", enterWebsite);
  $("experiencePreview")?.addEventListener("pointerdown", () => startBackgroundMusic(), { once: true });
  $("settingsDrawer")?.addEventListener("wheel", (event) => event.stopPropagation(), { passive: true });
  $("settingsDrawer")?.addEventListener("touchmove", (event) => event.stopPropagation(), { passive: true });
  $("drawerBackdrop").addEventListener("click", () => openSettings(false));
  $("darkThemeSetting").addEventListener("change", (e) => {
    state.settings.theme = e.target.checked ? "dark" : "light";
    saveSettings();
  });
  $("orbitSetting").addEventListener("change", (e) => {
    state.settings.orbits = e.target.checked;
    saveSettings();
  });
  $("bgmEnabledSetting")?.addEventListener("change", (e) => {
    state.settings.bgmEnabled = e.target.checked;
    saveSettings();
  });
  $("voiceEnabledSetting")?.addEventListener("change", (e) => {
    state.settings.voiceEnabled = e.target.checked;
    saveSettings();
  });
  $("voiceVolumeSetting")?.addEventListener("input", (e) => {
    state.settings.voiceVolume = Number(e.target.value);
    $("voiceVolumeOutput").textContent = `${e.target.value}%`;
    saveSettings();
  });
  $("testVoiceButton")?.addEventListener("click", () => playVoiceLine(state.section || "landing", { force: true }));
  $("stopAudioButton")?.addEventListener("click", stopVoiceLine);
  $("defaultScenarioSetting").addEventListener("change", (e) => {
    state.settings.scenario = e.target.value;
    saveSettings();
  });
  $("defaultInterventionSetting").addEventListener("change", (e) => {
    state.settings.intervention = e.target.value;
    saveSettings();
  });
  $("defaultRunsSetting").addEventListener("change", (e) => {
    state.settings.runs = Number(e.target.value);
    saveSettings();
  });
  $("rainOpacitySetting").addEventListener("input", (e) => {
    $("rainOpacityOutput").textContent = `${e.target.value}%`;
    state.settings.rainOpacity = Number(e.target.value);
    saveSettings();
    if (state.latestForecast) updateForecastFrame(state.forecastIndex);
  });
  $("timelineSpeedSetting")?.addEventListener("change", () => {
    state.settings.timelineSpeed = 500;
    saveSettings();
  });
  $("resetSettingsButton").addEventListener("click", () => {
    localStorage.removeItem("cocoAidSettings");
    location.reload();
  });
  $("heroDrawButton").addEventListener("click", () => showSection("farm-setup"));
  $("heroSetupButton").addEventListener("click", () => setNavigationOpen(true, { forceExpanded: true }));
  $("landingContinue").addEventListener("click", () =>
    showSection("farm-setup"),
  );
  $("landingClear").addEventListener("click", () => setPolygon([], "landing"));
  $("clearFarmPolygon").addEventListener("click", () => setPolygon([], "farm"));
  $("quickForecastButton").addEventListener("click", () =>
    state.polygon.length ? runForecast() : showSection("farm-setup"),
  );
  $("startForecastButton").addEventListener("click", runForecast);
  $("runForecastButton").addEventListener("click", runForecast);
  $("saveFarmButton").addEventListener("click", saveFarm);
  $("loadFarmButton").addEventListener("click", () => loadSelectedFarm());
  $("province").addEventListener("change", loadOfficialProfile);

  document
    .querySelectorAll("#farm-setup input")
    .forEach((i) => i.addEventListener("input", validateFarm));
  document.querySelectorAll(".subtab").forEach((b) =>
    b.addEventListener("click", () => {
      document
        .querySelectorAll(".subtab")
        .forEach((x) => x.classList.toggle("active", x === b));
      document
        .querySelectorAll(".form-tab")
        .forEach((x) =>
          x.classList.toggle(
            "active",
            x.dataset.formPanel === b.dataset.formTab,
          ),
        );
      setTimeout(() => state.maps.farm.invalidateSize(), 60);
    }),
  );
  $("forecastSlider").addEventListener("input", (e) =>
    updateForecastFrame(e.target.value),
  );
  $("forecastCalendarPrev")?.addEventListener("click", () => shiftForecastCalendarMonth(-1));
  $("forecastCalendarNext")?.addEventListener("click", () => shiftForecastCalendarMonth(1));
  $("forecastPrev").addEventListener("click", () =>
    updateForecastFrame(state.forecastIndex - 1),
  );
  $("forecastNext").addEventListener("click", () =>
    updateForecastFrame(state.forecastIndex + 1),
  );
  $("forecastPlay").addEventListener("click", toggleForecastPlay);
  document.querySelectorAll("[data-forecast-map-layer]").forEach((button) => {
    const name = button.dataset.forecastMapLayer;
    const visible = state.forecastMapLayers[name] !== false;
    button.classList.toggle("active", visible);
    button.setAttribute("aria-pressed", String(visible));
    const status = button.querySelector(".forecast-layer-status") || button.querySelector(":scope > b"); if (status) status.textContent = visible ? "ON" : "OFF";
    button.addEventListener("click", () => setForecastMapLayer(name, state.forecastMapLayers[name] === false));
  });
  document.querySelectorAll("[data-forecast-panel]").forEach((button) => button.addEventListener("click", () => setForecastPanel(button.dataset.forecastPanel)));
  document.querySelectorAll("[data-close-forecast-panel]").forEach((button) => button.addEventListener("click", () => {
    const panel = button.closest("[data-forecast-panel-body]"); if (panel) setForecastPanel(panel.dataset.forecastPanelBody, false);
  }));
  $("forecastTimelineCollapse")?.addEventListener("click", () => setForecastPanel("timeline"));
  $("productionIndexMode")?.addEventListener("click", () => {
    state.productionChartMode = "index";
    if (state.latestForecast) { renderProductionChart(state.latestForecast.weekly || state.latestForecast.frames); updateChartMarkers(Number(state.visualFrames[state.forecastIndex]?.week_index || 0)); }
  });
  $("productionTonsMode")?.addEventListener("click", () => {
    state.productionChartMode = "tons";
    if (state.latestForecast) { renderProductionChart(state.latestForecast.weekly || state.latestForecast.frames); updateChartMarkers(Number(state.visualFrames[state.forecastIndex]?.week_index || 0)); }
  });
  $("syncWeatherFarmButton")?.addEventListener("click", () => { syncFarmToWeatherViewer(); toast("Farm boundary synchronized with Weather GIS."); });
  $("expandWeatherButton")?.addEventListener("click", () => openWeatherModal(true));
  $("weatherFloatButton")?.addEventListener("click", () => openWeatherModal(true));
  $("weatherModalClose")?.addEventListener("click", () => openWeatherModal(false));
  $("weatherModal")?.addEventListener("click", (event) => { if (event.target === $("weatherModal")) openWeatherModal(false); });
  document
    .querySelectorAll(".chart-reset")
    .forEach((b) =>
      b.addEventListener("click", () => {
        const chart = state.charts[b.dataset.chart];
        chart?.resetZoom?.();
        const visual = state.visualFrames[state.forecastIndex] || {};
        const marker = Number.isFinite(Number(visual.week_index)) ? Number(visual.week_index) : state.forecastIndex;
        focusChartWindow(chart, marker);
        chart?.update?.("none");
      }),
    );
  $("hazardPrevEvent")?.addEventListener("click", () => changeHazardEvent(-1));
  $("hazardNextEvent")?.addEventListener("click", () => changeHazardEvent(1));
  $("refreshHazardsButton").addEventListener("click", () => {
    if (state.latestForecast) {
      renderHazards(state.latestForecast.extreme_events || []);
      toast("Hazard timeline refreshed.");
    } else toast("Run a forecast first.", true);
  });
  $("runHealthButton").addEventListener("click", runHealth);
  $("runPestAnalysisButton")?.addEventListener("click", runHealth);
  $("intercropCanopySlider")?.addEventListener("input", (event) => { state.intercropLight=Number(event.target.value)||36; renderIntercroppingWorkspace(); });
  $("intercropCropSelect")?.addEventListener("change", (event) => selectIntercropCandidate(event.target.value));
  $("intercropResetCamera")?.addEventListener("click", resetIntercropCamera);
  $("generateRehabAiButton")?.addEventListener("click", generateRehabAiRecommendation);
  $("runFullAnalysisButton").addEventListener("click", runFullAnalysis);
  $("generateReportButton").addEventListener("click", generateReport);
  $("saveForecastButton").addEventListener("click", saveCurrentForecast);
  $("refreshDatabaseButton").addEventListener("click", refreshDatabase);
  $("drawTutorialClose")?.addEventListener("click", closeDrawTutorial);
  $("landingContinue")?.addEventListener("click", closeDrawTutorial);
  $("cocoPilotButton")?.addEventListener("click", () => openPilot(true));
  $("pilotClose")?.addEventListener("click", () => openPilot(false));
  $("pilotSend")?.addEventListener("click", () => sendPilotMessage());
  $("pilotInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendPilotMessage(); }
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => sendPilotMessage(button.dataset.prompt)));
  $("pilotAttachContext")?.addEventListener("click", () => {
    state.pilotContextAttached = !state.pilotContextAttached;
    updatePilotAttachments();
    toast(state.pilotContextAttached ? "Current COCO-AID results attached." : "Current results detached.");
  });
  $("pilotAttachReport")?.addEventListener("click", attachLatestReportToPilot);
  $("pilotFileInput")?.addEventListener("change", (event) => uploadPilotDocument(event.target.files?.[0]));
  $("rehabPrevEvent")?.addEventListener("click", () => changeRehabPlan(-1));
  $("rehabNextEvent")?.addEventListener("click", () => changeRehabPlan(1));
  $("saveGeminiKeyButton")?.addEventListener("click", configureGemini);
  $("clearGeminiKeyButton")?.addEventListener("click", clearGemini);
  $("weatherViewerFrame").addEventListener("load", syncFarmToWeatherViewer);
  $("weatherDedicatedFrame")?.addEventListener("load", syncFarmToWeatherViewer);
  $("weatherPageSync")?.addEventListener("click", () => { syncFarmToWeatherViewer(); toast("Farm boundary synchronized with the Weather GIS."); });
  $("weatherPageExpand")?.addEventListener("click", () => openWeatherModal(true));
  $("refreshIntelligenceButton")?.addEventListener("click", () => window.phase11RefreshIntelligence?.());
  $("openPilotFromIntelligence")?.addEventListener("click", () => openPilot(true));
  window.addEventListener("message", (e) => {
    if (
      e.origin === location.origin &&
      e.data?.type === "COCO_AID_REQUEST_FARM"
    )
      syncFarmToWeatherViewer();
  });
}

async function boot() {
  const bootStartedAt = performance.now();
  startLoadingTips();
  loadSettings();
  $("appShell")?.setAttribute("aria-hidden", "true");
  if ($("appShell")) $("appShell").inert = true;
  bindEvents();
  startForecastFreshnessWatcher();
  const previewMusicStarted = await startBackgroundMusic();
  if (!previewMusicStarted && $("previewAudioHint")) {
    $("previewAudioHint").textContent = "Tap anywhere on this preview to enable background music if your browser blocks autoplay.";
  }
  $("openHazardInForecast")?.addEventListener("click", openSelectedHazardInForecast);
  setupInteractiveInformationPages();
  refreshAutoWorkflowStatus(false);
  if (!state.autoWorkflowTimer) state.autoWorkflowTimer = setInterval(() => { if (["intelligence","reports","database","about"].includes(state.section)) refreshAutoWorkflowStatus(false); }, 8000);
  $("pilotInput")?.addEventListener("input", (event) => {
    setPilotSphereState(String(event.target.value || "").trim() ? "typing" : "waiting");
    clearTimeout(state.pilotTypingTimer); state.pilotTypingTimer=setTimeout(()=>{ if (!$("pilotSend")?.disabled) setPilotSphereState("waiting"); },700);
  });
  $("pilotInput")?.addEventListener("focus",()=>{ if(!String($("pilotInput").value||"").trim()) setPilotSphereState("waiting"); });
  updatePilotAttachments();
  refreshPilotStatus();
  initMaps();
  setupIntercropSceneControls();
  validateFarm();
  try {
    const health = await api("/api/health");
    $("apiDot").classList.add("ok");
    $("apiText").textContent = `API ${health.api_version} ready`;
    const source = await api("/api/official-data/summary");
    $("dataStatusBadge").textContent = `PSA ${source.coverage} connected`;
  } catch (e) {
    $("apiDot").classList.add("bad");
    $("apiText").textContent = "Backend unavailable";
    toast(e.message, true);
  }
  try {
    const data = await api("/api/official-data/provinces");
    $("province").innerHTML = data.provinces
      .map(
        (p) =>
          `<option value="${escapeHtml(p.province)}">${escapeHtml(p.province)}</option>`,
      )
      .join("");
    $("province").value = "South Cotabato";
  } catch {}
  await Promise.allSettled([refreshFarms(), loadOfficialProfile()]);
  const hash = location.hash.slice(1);
  if (sectionMeta[hash]) showSection(hash);
  const remaining = Math.max(0, 1500 - (performance.now() - bootStartedAt));
  if (remaining) await new Promise((resolve) => setTimeout(resolve, remaining));
  loading(false);
}
document.addEventListener("DOMContentLoaded", () => {
  boot().catch((error) => {
    console.error("COCO-AID boot error", error);
    try { toast(`Interface initialization issue: ${error.message || error}`, true); } catch {}
  }).finally(() => loading(false));
});
