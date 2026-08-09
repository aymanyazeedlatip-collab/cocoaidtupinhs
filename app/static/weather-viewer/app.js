/* global L */
"use strict";

const API = {
  health: "/api/health",
  sources: "/api/sources",
  point: "/api/weather/point",
  grid: "/api/weather/frame",
  cube: "/api/weather/cube",
  geocode: "/api/geocode/search",
  radar: "/api/radar/frames",
  storms: "/api/storms/active",
  warnings: "/api/warnings/philippines",
};

const state = {
  map: null,
  marker: null,
  point: null,
  pointForecast: null,
  sources: [],
  radar: null,
  radarLayer: null,
  radarIndex: 0,
  satelliteLayer: null,
  forecastLayer: null,
  contourLayer: null,
  forecastVariable: "rain_clouds",
  forecastHour: 0,
  forecastPosition: 0,
  forecastTimes: [],
  gridData: null,
  cloudCube: null,
  cloudCubeSignature: null,
  cloudCubeCache: new Map(),
  cloudCubeRequestId: 0,
  cloudCubeAbortController: null,
  windGrid: null,
  stormLayer: null,
  stormData: null,
  timelineMode: "radar",
  playing: false,
  playTimer: null,
  gridRequestId: 0,
  gridDebounce: null,
  gridAbortController: null,
  gridCache: new Map(),
  lastGridSignature: null,
  windAnimation: null,
  windParticles: [],
  windLastFrame: 0,
  farmLayer: null,
  farmName: null,
  farmTerrain: null,
};

const el = {};

const WMO = {
  0: ["Clear sky", "☀"],
  1: ["Mainly clear", "🌤"],
  2: ["Partly cloudy", "⛅"],
  3: ["Overcast", "☁"],
  45: ["Fog", "🌫"],
  48: ["Depositing rime fog", "🌫"],
  51: ["Light drizzle", "🌦"],
  53: ["Drizzle", "🌦"],
  55: ["Heavy drizzle", "🌧"],
  56: ["Freezing drizzle", "🌧"],
  57: ["Heavy freezing drizzle", "🌧"],
  61: ["Light rain", "🌦"],
  63: ["Rain", "🌧"],
  65: ["Heavy rain", "🌧"],
  66: ["Freezing rain", "🌧"],
  67: ["Heavy freezing rain", "🌧"],
  71: ["Light snow", "🌨"],
  73: ["Snow", "🌨"],
  75: ["Heavy snow", "❄"],
  77: ["Snow grains", "❄"],
  80: ["Light showers", "🌦"],
  81: ["Showers", "🌧"],
  82: ["Violent showers", "⛈"],
  85: ["Snow showers", "🌨"],
  86: ["Heavy snow showers", "🌨"],
  95: ["Thunderstorm", "⛈"],
  96: ["Thunderstorm with hail", "⛈"],
  99: ["Severe thunderstorm with hail", "⛈"],
};

const VARIABLE_INFO = {
  precipitation: {
    title: "Forecast precipitation",
    unit: "mm",
    min: 0,
    max: 8,
    stops: [
      "#00000000",
      "#238cffaa",
      "#00c8dccc",
      "#55df94dd",
      "#ffe05bdd",
      "#ff8747ee",
      "#d33a84ee",
    ],
  },
  temperature_2m: {
    title: "2-m temperature",
    unit: "°C",
    min: 12,
    max: 38,
    stops: [
      "#5046b8cc",
      "#2c9ed6cc",
      "#5ed6c1cc",
      "#f2db67dd",
      "#ef8b43dd",
      "#c93e48dd",
    ],
  },
  cloud_cover: {
    title: "Total cloud cover",
    unit: "%",
    min: 0,
    max: 100,
    stops: ["#10203318", "#536a7f88", "#aab9c6cc", "#f4f8ffee"],
  },
  rain_clouds: {
    title: "Forecast rain intensity",
    unit: "mm/h",
    min: 0,
    max: 8,
    stops: [
      "#00000000",
      "#66d9ff99",
      "#0878ffcc",
      "#0739cfe6",
      "#ffe14fe6",
      "#ff3b30f2",
    ],
  },
  pressure_msl: {
    title: "Mean sea-level pressure",
    unit: "hPa",
    min: 990,
    max: 1025,
    stops: ["#4c6fffaa", "#43c2c9aa", "#e5d75aaa", "#ef7a52aa"],
  },
};

function cacheElements() {
  const ids = [
    "layersMobileButton",
    "detailsMobileButton",
    "layersPanel",
    "detailsPanel",
    "searchInput",
    "searchButton",
    "searchResults",
    "locateButton",
    "refreshButton",
    "sourcesButton",
    "sourceDot",
    "sourcesDialog",
    "closeSourcesButton",
    "sourcesList",
    "radarToggle",
    "satelliteToggle",
    "radarState",
    "observationOpacity",
    "forecastOpacity",
    "windToggle",
    "stormsToggle",
    "stormCount",
    "pagasaButton",
    "modelSelect",
    "mapMessage",
    "legend",
    "activeDataBadge",
    "validTimeBadge",
    "locationTitle",
    "locationCoords",
    "weatherLoading",
    "weatherEmpty",
    "weatherContent",
    "currentCondition",
    "currentTemp",
    "feelsLike",
    "weatherSymbol",
    "metricRain",
    "metricHumidity",
    "metricWind",
    "metricGust",
    "metricPressure",
    "metricCloud",
    "forecastTimezone",
    "hourlyForecast",
    "dailyForecast",
    "pointMetadata",
    "radarTimelineTab",
    "forecastTimelineTab",
    "previousFrameButton",
    "playButton",
    "nextFrameButton",
    "timelineLocal",
    "timelineUtc",
    "timelineSlider",
    "timelineKind",
    "timelineSource",
    "playbackSpeed",
    "windCanvas",
    "forecastStatus",
    "nextRainButton",
    "farmSiteBadge",
  ];
  ids.forEach((id) => {
    el[id] = document.getElementById(id);
  });
  el.forecastRadios = Array.from(
    document.querySelectorAll('input[name="forecastLayer"]'),
  );
  el.closeButtons = Array.from(document.querySelectorAll("[data-close]"));
}

function requireLeaflet() {
  if (typeof L === "undefined") {
    document.body.innerHTML =
      '<main style="padding:32px;color:white;background:#07111f;min-height:100vh;font-family:system-ui"><h1>Map library unavailable</h1><p>Leaflet could not load. Check your internet connection and refresh the page.</p></main>';
    throw new Error("Leaflet failed to load");
  }
}

function initMap() {
  state.map = L.map("map", {
    zoomControl: true,
    preferCanvas: true,
    worldCopyJump: true,
  }).setView([12.4, 122.0], 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>',
  }).addTo(state.map);
  state.stormLayer = L.layerGroup().addTo(state.map);
  state.farmLayer = L.featureGroup().addTo(state.map);

  state.map.on("click", (event) =>
    selectPoint(event.latlng.lat, event.latlng.lng, "Selected map location"),
  );
  state.map.on("moveend", () => {
    resizeWindCanvas();
    scheduleGridRefresh();
  });
  resizeWindCanvas();
}

function setupEvents() {
  el.searchButton.addEventListener("click", searchLocations);
  el.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchLocations();
  });
  el.locateButton.addEventListener("click", locateUser);
  el.refreshButton.addEventListener("click", refreshAll);
  el.sourcesButton.addEventListener("click", () =>
    el.sourcesDialog.showModal(),
  );
  el.closeSourcesButton.addEventListener("click", () =>
    el.sourcesDialog.close(),
  );
  el.closeButtons.forEach((button) =>
    button.addEventListener("click", () =>
      document.getElementById(button.dataset.close).classList.remove("open"),
    ),
  );
  el.layersMobileButton.addEventListener("click", () =>
    el.layersPanel.classList.toggle("open"),
  );
  el.detailsMobileButton.addEventListener("click", () =>
    el.detailsPanel.classList.toggle("open"),
  );
  el.radarToggle.addEventListener("change", updateRadarVisibility);
  el.satelliteToggle.addEventListener("change", updateSatelliteVisibility);
  el.stormsToggle.addEventListener("change", updateStormVisibility);
  el.windToggle.addEventListener("change", () => {
    if (!el.windToggle.checked) {
      stopWind();
      return;
    }
    if (state.cloudCube) renderInterpolatedForecastFrame();
    else scheduleGridRefresh(true);
  });
  el.nextRainButton.addEventListener("click", jumpToNextRain);
  el.observationOpacity.addEventListener("input", applyOpacity);
  el.forecastOpacity.addEventListener("input", applyOpacity);
  el.forecastRadios.forEach((radio) =>
    radio.addEventListener("change", () => {
      if (!radio.checked) return;
      if (state.playing) stopPlayback();
      state.forecastVariable = radio.value;
      switchTimeline("forecast");
      if (state.cloudCube) renderInterpolatedForecastFrame();
      else if (radio.value === "none" && !el.windToggle.checked) clearForecastLayers();
      else scheduleGridRefresh(true);
    }),
  );
  el.modelSelect.addEventListener("change", () => {
    state.cloudCube = null;
    state.cloudCubeSignature = null;
    if (state.point)
      loadPointForecast(state.point.lat, state.point.lng, state.point.name);
    scheduleGridRefresh(true);
  });
  el.pagasaButton.addEventListener("click", () =>
    window.open(
      "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin",
      "_blank",
      "noopener",
    ),
  );
  el.radarTimelineTab.addEventListener("click", () => switchTimeline("radar"));
  el.forecastTimelineTab.addEventListener("click", () =>
    switchTimeline("forecast"),
  );
  el.timelineSlider.addEventListener("input", timelineChanged);
  el.previousFrameButton.addEventListener("click", () => stepTimeline(-1));
  el.nextFrameButton.addEventListener("click", () => stepTimeline(1));
  el.playButton.addEventListener("click", togglePlayback);
  el.playbackSpeed.addEventListener("change", () => {
    if (state.playing) {
      stopPlayback();
      startPlayback();
    }
  });
  window.addEventListener("resize", resizeWindCanvas);
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || !event.data) return;
    if (event.data.type === "COCO_AID_FARM")
      renderLinkedFarm(event.data.farm || {});
    if (event.data.type === "COCO_AID_RESIZE") {
      setTimeout(() => { state.map?.invalidateSize(); resizeWindCanvas(); }, 80);
    }
    if (event.data.type === "COCO_AID_THEME") {
      document.documentElement.dataset.theme =
        event.data.theme === "dark" ? "dark" : "light";
    }
  });
}

function renderLinkedFarm(farm) {
  if (!state.farmLayer) return;
  state.farmLayer.clearLayers();
  const polygon = farm?.location?.polygon || farm?.polygon || [];
  const latitude = Number(farm?.location?.latitude ?? farm?.latitude);
  const longitude = Number(farm?.location?.longitude ?? farm?.longitude);
  state.farmName = farm?.name || "COCO-AID farm site";
  state.farmTerrain = {
    latitude,
    longitude,
    elevation_m: Number(farm?.soil_terrain?.elevation_m ?? 0),
    slope_degrees: Number(farm?.soil_terrain?.slope_degrees ?? 0),
  };
  let bounds = null;
  if (Array.isArray(polygon) && polygon.length >= 3) {
    const layer = L.polygon(polygon, {
      color: "#ffe05b",
      weight: 3,
      fillColor: "#56d99b",
      fillOpacity: 0.16,
      dashArray: "8 5",
    })
      .bindTooltip(`${escapeHtml(state.farmName)} · linked farm boundary`, {
        sticky: true,
      })
      .addTo(state.farmLayer);
    bounds = layer.getBounds();
  }
  if (finite(latitude) && finite(longitude)) {
    L.circleMarker([latitude, longitude], {
      radius: 8,
      color: "#ffffff",
      weight: 2,
      fillColor: "#43d39e",
      fillOpacity: 0.95,
    })
      .bindPopup(
        `<strong>${escapeHtml(state.farmName)}</strong><p>COCO-AID farm simulation site</p>`,
      )
      .addTo(state.farmLayer);
    if (!bounds)
      bounds = L.latLngBounds([
        [latitude - 0.08, longitude - 0.08],
        [latitude + 0.08, longitude + 0.08],
      ]);
    selectPoint(latitude, longitude, state.farmName);
  }
  if (bounds && bounds.isValid())
    state.map.fitBounds(bounds.pad(2.5), { maxZoom: 9, padding: [24, 24] });
  if (el.farmSiteBadge) {
    el.farmSiteBadge.textContent = `Farm site: ${state.farmName}`;
    el.farmSiteBadge.classList.remove("hidden");
  }
  showMessage("Farm boundary linked to the live weather viewer.");
}

function requestFarmFromParent() {
  if (window.parent !== window)
    window.parent.postMessage(
      { type: "COCO_AID_REQUEST_FARM" },
      window.location.origin,
    );
}

async function fetchJson(url, options = {}) {
  const { headers = {}, ...rest } = options;
  const response = await fetch(url, {
    ...rest,
    headers: { Accept: "application/json", ...headers },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = { detail: `HTTP ${response.status}` };
  }
  if (!response.ok) {
    const message = payload.detail || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function showMessage(message, duration = 4500) {
  el.mapMessage.textContent = message;
  el.mapMessage.classList.remove("hidden");
  clearTimeout(showMessage.timer);
  showMessage.timer = setTimeout(
    () => el.mapMessage.classList.add("hidden"),
    duration,
  );
}

async function loadHealthAndSources() {
  try {
    await fetchJson(API.health);
    const payload = await fetchJson(API.sources);
    state.sources = payload.sources || [];
    el.sourceDot.className = "ok";
    renderSources();
  } catch (error) {
    el.sourceDot.className = "error";
    showMessage(`Backend connection problem: ${error.message}`);
  }
}

function renderSources() {
  el.sourcesList.innerHTML = state.sources
    .map(
      (source) => `
    <article class="source-card">
      <div class="source-card-head"><strong>${escapeHtml(source.name)}</strong><span class="source-type">${escapeHtml(source.type)}</span></div>
      <p>${escapeHtml(source.attribution || "")}${source.limitations ? `<br>${escapeHtml(source.limitations.join(" "))}` : ""}</p>
      <a href="${safeUrl(source.url)}" target="_blank" rel="noopener">Official source ↗</a>
    </article>`,
    )
    .join("");
}

async function loadRadar() {
  el.radarState.textContent = "Loading";
  try {
    state.radar = await fetchJson(API.radar);
    state.radarIndex = Math.max(0, state.radar.frames.length - 1);
    el.radarState.textContent = `${state.radar.frames.length} frames`;
    if (el.radarToggle.checked) renderRadarFrame();
    if (state.timelineMode === "radar") configureTimeline();
  } catch (error) {
    state.radar = null;
    el.radarState.textContent = "Unavailable";
    showMessage(`Radar unavailable: ${error.message}`);
  }
}

function renderRadarFrame() {
  if (!state.radar || !state.radar.frames.length || !el.radarToggle.checked)
    return;
  const frame = state.radar.frames[state.radarIndex];
  const tileUrl = `${state.radar.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
  if (state.radarLayer) state.map.removeLayer(state.radarLayer);
  state.radarLayer = L.tileLayer(tileUrl, {
    opacity: Number(el.observationOpacity.value) / 100,
    maxNativeZoom: 7,
    maxZoom: 18,
    zIndex: 250,
    attribution: "Radar &copy; RainViewer",
  }).addTo(state.map);
  setDataBadges(
    frame.kind === "nowcast" ? "Radar nowcast" : "Radar observation",
    frame.time,
    "RainViewer",
  );
}

function updateRadarVisibility() {
  if (el.radarToggle.checked) {
    if (state.radar) renderRadarFrame();
    else loadRadar();
    switchTimeline("radar");
  } else if (state.radarLayer) {
    state.map.removeLayer(state.radarLayer);
    state.radarLayer = null;
  }
}

function updateSatelliteVisibility() {
  if (!el.satelliteToggle.checked) {
    if (state.satelliteLayer) state.map.removeLayer(state.satelliteLayer);
    state.satelliteLayer = null;
    return;
  }
  const date = new Date(Date.now() - 24 * 3600 * 1000)
    .toISOString()
    .slice(0, 10);
  state.satelliteLayer = L.tileLayer
    .wms("https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi", {
      layers: "MODIS_Terra_CorrectedReflectance_TrueColor",
      format: "image/jpeg",
      transparent: true,
      time: date,
      opacity: Number(el.observationOpacity.value) / 100,
      zIndex: 180,
      attribution: "Satellite imagery NASA EOSDIS GIBS",
    })
    .addTo(state.map);
  setDataBadges(
    "Satellite observation",
    `${date}T00:00:00Z`,
    "NASA GIBS daily imagery",
  );
}

function applyOpacity() {
  const obs = Number(el.observationOpacity.value) / 100;
  const fc = Number(el.forecastOpacity.value) / 100;
  if (state.radarLayer) state.radarLayer.setOpacity(obs);
  if (state.satelliteLayer) state.satelliteLayer.setOpacity(obs);
  if (state.forecastLayer) state.forecastLayer.setOpacity(fc);
  if (state.contourLayer) state.contourLayer.setOpacity(fc);
}

async function searchLocations() {
  const query = el.searchInput.value.trim();
  if (query.length < 2) return;
  el.searchResults.classList.remove("hidden");
  el.searchResults.innerHTML = '<div class="search-result">Searching…</div>';
  try {
    const payload = await fetchJson(
      `${API.geocode}?q=${encodeURIComponent(query)}&count=7`,
    );
    const results = payload.results || [];
    if (!results.length) {
      el.searchResults.innerHTML =
        '<div class="search-result">No matching locations found.</div>';
      return;
    }
    el.searchResults.innerHTML = results
      .map(
        (item, index) => `
      <button class="search-result" type="button" data-index="${index}">
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml([item.admin2, item.admin1, item.country].filter(Boolean).join(", "))}</span>
      </button>`,
      )
      .join("");
    Array.from(el.searchResults.querySelectorAll("button")).forEach((button) =>
      button.addEventListener("click", () => {
        const item = results[Number(button.dataset.index)];
        el.searchResults.classList.add("hidden");
        el.searchInput.value = item.name;
        state.map.setView([item.latitude, item.longitude], 9);
        selectPoint(
          item.latitude,
          item.longitude,
          [item.name, item.admin1, item.country].filter(Boolean).join(", "),
        );
      }),
    );
  } catch (error) {
    el.searchResults.innerHTML = `<div class="search-result">Search unavailable: ${escapeHtml(error.message)}</div>`;
  }
}

function locateUser() {
  if (!navigator.geolocation)
    return showMessage("Geolocation is not supported by this browser.");
  el.locateButton.disabled = true;
  navigator.geolocation.getCurrentPosition(
    (position) => {
      el.locateButton.disabled = false;
      const { latitude, longitude } = position.coords;
      state.map.setView([latitude, longitude], 10);
      selectPoint(latitude, longitude, "Current location");
    },
    (error) => {
      el.locateButton.disabled = false;
      showMessage(`Could not get your location: ${error.message}`);
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 },
  );
}

function selectPoint(lat, lng, name) {
  state.point = { lat, lng, name };
  if (state.marker) state.marker.setLatLng([lat, lng]);
  else
    state.marker = L.circleMarker([lat, lng], {
      radius: 7,
      color: "#fff",
      weight: 2,
      fillColor: "#268bff",
      fillOpacity: 1,
    }).addTo(state.map);
  loadPointForecast(lat, lng, name);
  if (window.innerWidth <= 820) el.detailsPanel.classList.add("open");
}

async function loadPointForecast(lat, lng, name) {
  el.weatherEmpty.classList.add("hidden");
  el.weatherContent.classList.add("hidden");
  el.weatherLoading.classList.remove("hidden");
  el.locationTitle.textContent = name;
  el.locationCoords.textContent = `${lat.toFixed(4)}°, ${lng.toFixed(4)}°`;
  try {
    const model = el.modelSelect.value;
    const payload = await fetchJson(
      `${API.point}?latitude=${lat}&longitude=${lng}&model=${encodeURIComponent(model)}`,
    );
    state.pointForecast = payload;
    if (!(state.forecastVariable === "rain_clouds" && state.cloudCube)) {
      state.forecastTimes =
        payload.hourly && payload.hourly.time
          ? payload.hourly.time.slice(0, 73)
          : [];
    }
    renderPointWeather(payload);
    if (state.timelineMode === "forecast") configureTimeline();
  } catch (error) {
    el.weatherEmpty.classList.remove("hidden");
    el.weatherEmpty.innerHTML = `<div class="empty-icon">!</div><strong>Forecast unavailable</strong><p>${escapeHtml(error.message)}</p>`;
  } finally {
    el.weatherLoading.classList.add("hidden");
  }
}

function renderPointWeather(data) {
  const current = data.current || {};
  const [condition, symbol] = wmo(current.weather_code);
  el.currentCondition.textContent = condition;
  el.currentTemp.textContent = finite(current.temperature_2m)
    ? `${Math.round(current.temperature_2m)}°`
    : "—";
  el.feelsLike.textContent = finite(current.apparent_temperature)
    ? `Feels like ${Math.round(current.apparent_temperature)}°C`
    : "Feels like —";
  el.weatherSymbol.textContent = symbol;
  el.metricRain.textContent = formatUnit(current.precipitation, "mm");
  el.metricHumidity.textContent = formatUnit(current.relative_humidity_2m, "%");
  el.metricWind.textContent = `${formatUnit(current.wind_speed_10m, "km/h")} ${compass(current.wind_direction_10m)}`;
  el.metricGust.textContent = formatUnit(current.wind_gusts_10m, "km/h");
  el.metricPressure.textContent = formatUnit(current.pressure_msl, "hPa");
  el.metricCloud.textContent = formatUnit(current.cloud_cover, "%");
  el.forecastTimezone.textContent = data.timezone || "Local time";
  renderHourly(data.hourly || {});
  renderDaily(data.daily || {});
  renderPointMetadata(data.metadata || {});
  el.weatherContent.classList.remove("hidden");
  el.weatherEmpty.classList.add("hidden");
}

function renderHourly(hourly) {
  const start = Math.max(
    0,
    (hourly.time || []).findIndex(
      (time) => new Date(time).getTime() >= Date.now() - 3600000,
    ),
  );
  const cards = [];
  for (
    let i = start;
    i < Math.min(start + 24, (hourly.time || []).length);
    i++
  ) {
    const [condition, symbol] = wmo(valueAt(hourly.weather_code, i));
    const time = new Date(hourly.time[i]);
    cards.push(`<div class="hour-card" title="${escapeHtml(condition)}">
      <span class="time">${time.toLocaleTimeString([], { hour: "numeric" })}</span>
      <span class="symbol">${symbol}</span>
      <strong>${Math.round(valueAt(hourly.temperature_2m, i) || 0)}°</strong>
      <span class="rain">${Math.round(valueAt(hourly.precipitation_probability, i) || 0)}%</span>
    </div>`);
  }
  el.hourlyForecast.innerHTML = cards.join("");
}

function renderDaily(daily) {
  const rows = [];
  for (let i = 0; i < (daily.time || []).length; i++) {
    const [condition, symbol] = wmo(valueAt(daily.weather_code, i));
    const date = new Date(`${daily.time[i]}T12:00:00`);
    rows.push(`<div class="day-row" title="${escapeHtml(condition)}">
      <span>${date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}</span>
      <span>${symbol}</span>
      <span class="rain">${Math.round(valueAt(daily.precipitation_probability_max, i) || 0)}% · ${round1(valueAt(daily.precipitation_sum, i))} mm</span>
      <span class="temps">${Math.round(valueAt(daily.temperature_2m_max, i) || 0)}° / ${Math.round(valueAt(daily.temperature_2m_min, i) || 0)}°</span>
    </div>`);
  }
  el.dailyForecast.innerHTML = rows.join("");
}

function renderPointMetadata(metadata) {
  const rows = [
    ["Source", metadata.source],
    ["Type", metadata.source_type],
    ["Forecast valid", metadata.forecast_valid_at],
    ["Retrieved", metadata.retrieved_at],
    ["Attribution", metadata.attribution],
    ["Limitations", (metadata.limitations || []).join(" ")],
  ];
  el.pointMetadata.innerHTML = rows
    .filter(([, value]) => value)
    .map(
      ([key, value]) =>
        `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(formatDateMaybe(value))}</dd>`,
    )
    .join("");
}

function switchTimeline(mode) {
  state.timelineMode = mode;
  el.radarTimelineTab.classList.toggle("active", mode === "radar");
  el.forecastTimelineTab.classList.toggle("active", mode === "forecast");
  configureTimeline();
}

function configureTimeline() {
  if (state.timelineMode === "radar") {
    const count = state.radar ? state.radar.frames.length : 0;
    el.timelineSlider.min = 0;
    el.timelineSlider.step = 1;
    el.timelineSlider.max = Math.max(0, count - 1);
    el.timelineSlider.value = Math.min(
      state.radarIndex,
      Math.max(0, count - 1),
    );
  } else {
    if (
      state.cloudCube &&
      state.cloudCube.times &&
      state.cloudCube.times.length
    ) {
      state.forecastTimes = state.cloudCube.times;
    } else if (!state.forecastTimes.length) {
      buildFallbackForecastTimes();
    }
    el.timelineSlider.min = 0;
    // Forecast playback uses the provider's original hourly numerical-model frames.
    el.timelineSlider.step = 1;
    el.timelineSlider.max = Math.max(0, state.forecastTimes.length - 1);
    el.timelineSlider.value = Math.min(
      state.forecastPosition,
      Number(el.timelineSlider.max),
    );
  }
  updateTimelineLabels();
}

function buildFallbackForecastTimes() {
  const now = new Date();
  now.setUTCMinutes(0, 0, 0);
  state.forecastTimes = Array.from({ length: 121 }, (_, index) =>
    new Date(now.getTime() + index * 3600000).toISOString(),
  );
}

function timelineChanged() {
  if (state.timelineMode === "radar") {
    state.radarIndex = Number(el.timelineSlider.value);
    renderRadarFrame();
  } else {
    state.forecastPosition = Number(el.timelineSlider.value);
    state.forecastHour = Math.floor(state.forecastPosition);
    if (state.cloudCube) renderInterpolatedForecastFrame();
    else scheduleGridRefresh(true);
  }
  updateTimelineLabels();
}

function stepTimeline(delta) {
  const max = Number(el.timelineSlider.max);
  let current = Number(el.timelineSlider.value);
  let next = current + delta;
  if (next > max) next = 0;
  if (next < 0) next = max;
  el.timelineSlider.value = next;
  timelineChanged();
}

function togglePlayback() {
  state.playing ? stopPlayback() : startPlayback();
}
function startPlayback() {
  state.playing = true;
  el.playButton.textContent = "❚❚";
  if (state.timelineMode === "forecast") {
    const hourDuration = Number(el.playbackSpeed.value);
    state.playTimer = setInterval(
      () => {
        const max = Number(el.timelineSlider.max);
        let next = Number(el.timelineSlider.value) + 1;
        if (next > max) next = 0;
        el.timelineSlider.value = next;
        timelineChanged();
      },
      Math.max(120, hourDuration),
    );
  } else {
    state.playTimer = setInterval(
      () => stepTimeline(1),
      Number(el.playbackSpeed.value),
    );
  }
}
function stopPlayback() {
  state.playing = false;
  el.playButton.textContent = "▶";
  clearInterval(state.playTimer);
  state.playTimer = null;
}

function updateTimelineLabels() {
  let time = null;
  let kind = "";
  let source = "";
  if (
    state.timelineMode === "radar" &&
    state.radar &&
    state.radar.frames.length
  ) {
    const frame = state.radar.frames[state.radarIndex];
    time = frame.time;
    kind = frame.kind === "nowcast" ? "Radar nowcast" : "Radar observation";
    source = "RainViewer";
  } else if (state.timelineMode === "forecast" && state.forecastTimes.length) {
    const position = state.forecastPosition;
    time = interpolatedForecastTime(position);
    kind = "Hourly deterministic forecast";
    source = modelLabel();
  }
  if (!time) return;
  const date = new Date(time);
  el.timelineLocal.textContent = date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  el.timelineUtc.textContent = `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
  el.timelineKind.textContent = kind;
  el.timelineSource.textContent = source;
}

function interpolatedForecastTime(position) {
  if (!state.forecastTimes.length) return null;
  const low = Math.max(
    0,
    Math.min(state.forecastTimes.length - 1, Math.floor(position)),
  );
  const high = Math.max(
    0,
    Math.min(state.forecastTimes.length - 1, Math.ceil(position)),
  );
  const fraction = Math.max(0, Math.min(1, position - low));
  const first = new Date(state.forecastTimes[low]).getTime();
  const second = new Date(state.forecastTimes[high]).getTime();
  return new Date(first + (second - first) * fraction).toISOString();
}

function scheduleGridRefresh(immediate = false) {
  clearTimeout(state.gridDebounce);
  const needsGrid = state.forecastVariable !== "none" || el.windToggle.checked;
  if (!needsGrid) return;
  state.gridDebounce = setTimeout(loadForecastCube, immediate ? 0 : 1200);
}

function snapOutward(value, step, direction) {
  const scaled = value / step;
  return (direction === "down" ? Math.floor(scaled) : Math.ceil(scaled)) * step;
}

function safeBounds() {
  const bounds = state.map.getBounds();
  let west = bounds.getWest(),
    east = bounds.getEast(),
    south = bounds.getSouth(),
    north = bounds.getNorth();
  const center = bounds.getCenter();
  const maxSpan = 17.0;
  if (east - west > maxSpan) {
    west = center.lng - maxSpan / 2;
    east = center.lng + maxSpan / 2;
  }
  if (north - south > maxSpan) {
    south = center.lat - maxSpan / 2;
    north = center.lat + maxSpan / 2;
  }
  const step = 0.25;
  west = snapOutward(Math.max(-179.75, west), step, "down");
  east = snapOutward(Math.min(179.75, east), step, "up");
  south = snapOutward(Math.max(-85, south), step, "down");
  north = snapOutward(Math.min(85, north), step, "up");
  return {
    west: roundCoord(west),
    east: roundCoord(east),
    south: roundCoord(south),
    north: roundCoord(north),
  };
}

function roundCoord(value) {
  return Math.round(value * 100) / 100;
}

function gridSignature(body) {
  return JSON.stringify({
    west: body.west,
    south: body.south,
    east: body.east,
    north: body.north,
    rows: body.rows,
    cols: body.cols,
    variables: [...body.variables].sort(),
    hour_index: body.hour_index,
    model: body.model,
  });
}

function rememberGrid(signature, payload) {
  state.gridCache.set(signature, payload);
  if (state.gridCache.size > 48) {
    const oldest = state.gridCache.keys().next().value;
    state.gridCache.delete(oldest);
  }
}

function cubeSignature(body) {
  return JSON.stringify({
    west: body.west,
    south: body.south,
    east: body.east,
    north: body.north,
    rows: body.rows,
    cols: body.cols,
    model: body.model,
  });
}

function rememberCloudCube(signature, payload) {
  state.cloudCubeCache.set(signature, payload);
  if (state.cloudCubeCache.size > 12) {
    const oldest = state.cloudCubeCache.keys().next().value;
    state.cloudCubeCache.delete(oldest);
  }
}

async function loadForecastCube() {
  const requestId = ++state.cloudCubeRequestId;
  const bounds = safeBounds();
  const body = {
    ...bounds,
    rows: 6,
    cols: 6,
    model: el.modelSelect.value,
  };
  const signature = cubeSignature(body);
  const cached = state.cloudCubeCache.get(signature);
  if (cached) {
    applyCloudCube(cached, signature, requestId);
    return;
  }

  if (state.cloudCubeAbortController) state.cloudCubeAbortController.abort();
  state.cloudCubeAbortController = new AbortController();
  el.forecastStatus.className = "layer-status loading";
  el.forecastStatus.textContent =
    "Loading one reusable 384-hour (16-day) multi-variable forecast cube. Forecast playback uses the original hourly provider frames.";
  setDataBadges(
    "Loading forecast cloud cube",
    state.forecastTimes[state.forecastHour],
    modelLabel(),
  );

  try {
    const payload = await fetchJson(API.cube, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: state.cloudCubeAbortController.signal,
    });
    if (requestId !== state.cloudCubeRequestId) return;
    rememberCloudCube(signature, payload);
    applyCloudCube(payload, signature, requestId);
  } catch (error) {
    if (error.name === "AbortError" || requestId !== state.cloudCubeRequestId)
      return;
    el.forecastStatus.className = "layer-status error";
    el.forecastStatus.textContent =
      error.status === 429
        ? "The weather provider is cooling down. Keep the map still; a cached forecast will be reused when available."
        : `Animated rain clouds unavailable: ${error.message}`;
    showMessage(`Animated rain clouds unavailable: ${error.message}`);
    setDataBadges("Forecast unavailable", null, modelLabel());
  }
}

function applyCloudCube(payload, signature, requestId) {
  if (requestId !== state.cloudCubeRequestId) return;
  state.cloudCube = payload;
  state.cloudCubeSignature = signature;
  state.forecastTimes = payload.times || [];
  const maxPosition = Math.max(0, state.forecastTimes.length - 1);
  state.forecastPosition = Math.min(state.forecastPosition, maxPosition);
  state.forecastHour = Math.floor(state.forecastPosition);
  configureTimeline();
  renderInterpolatedForecastFrame();
}

function cubeMatrix(cube, variable, position) {
  const pointSeries = cube && cube.values ? cube.values[variable] : null;
  if (
    !Array.isArray(pointSeries) ||
    pointSeries.length !== cube.rows * cube.cols
  )
    return null;
  const low = Math.max(
    0,
    Math.min((cube.times || []).length - 1, Math.floor(position)),
  );
  const high = Math.max(
    0,
    Math.min((cube.times || []).length - 1, Math.ceil(position)),
  );
  const fraction = Math.max(0, Math.min(1, position - low));
  const matrix = Array.from({ length: cube.rows }, () =>
    Array(cube.cols).fill(null),
  );
  for (let index = 0; index < pointSeries.length; index++) {
    const series = pointSeries[index] || [];
    const a = Number(series[low]);
    const b = Number(series[high]);
    let value = null;
    if (Number.isFinite(a) && Number.isFinite(b))
      value = a + (b - a) * fraction;
    else if (Number.isFinite(a)) value = a;
    else if (Number.isFinite(b)) value = b;
    matrix[Math.floor(index / cube.cols)][index % cube.cols] = value;
  }
  return matrix;
}

function frameFromCube(cube, position, variables) {
  const values = {};
  variables.forEach((variable) => {
    values[variable] = cubeMatrix(cube, variable, position);
  });
  return {
    west: cube.west,
    south: cube.south,
    east: cube.east,
    north: cube.north,
    rows: cube.rows,
    cols: cube.cols,
    latitudes: cube.latitudes,
    longitudes: cube.longitudes,
    valid_time: interpolatedForecastTime(position),
    values,
    elevation_m: cube.elevation_m || null,
    metadata: cube.metadata,
  };
}

function renderInterpolatedForecastFrame() {
  const cube = state.cloudCube;
  if (!cube) return;
  const variables = [
    "precipitation",
    "temperature_2m",
    "cloud_cover",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "relative_humidity_2m",
  ];
  const frame = frameFromCube(cube, state.forecastPosition, variables);

  if (state.forecastVariable === "rain_clouds") {
    renderRainCloudFrame(frame);
  } else if (state.forecastVariable === "none") {
    clearForecastLayers();
    el.legend.classList.add("hidden");
  } else {
    renderForecastLayer(frame, state.forecastVariable);
  }

  if (el.windToggle.checked) {
    state.windGrid = frame;
    resizeWindCanvas();
    startWind();
  } else {
    stopWind();
  }
  setDataBadges(
    "Hourly deterministic forecast",
    frame.valid_time,
    cube.metadata?.source || modelLabel(),
  );
  updateTimelineLabels();
}

function renderRainCloudFrame(prebuiltFrame = null) {
  const cube = state.cloudCube;
  if (!cube || state.forecastVariable !== "rain_clouds") return;
  const frame = prebuiltFrame || frameFromCube(cube, state.forecastPosition, [
    "cloud_cover",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
  ]);
  const cloudMatrix = frame.values.cloud_cover;
  const precipitationMatrix = frame.values.precipitation;
  if (!cloudMatrix || !precipitationMatrix) {
    el.forecastStatus.className = "layer-status error";
    el.forecastStatus.textContent =
      "The forecast source did not return cloud and precipitation fields.";
    return;
  }

  const canvas = drawRainCloudCanvas(frame);
  const bounds = [
    [frame.south, frame.west],
    [frame.north, frame.east],
  ];
  const imageUrl = canvas.toDataURL("image/png");
  if (state.contourLayer) {
    state.map.removeLayer(state.contourLayer);
    state.contourLayer = null;
  }
  if (state.forecastLayer) {
    state.forecastLayer.setBounds(bounds);
    state.forecastLayer.setUrl(imageUrl);
    state.forecastLayer.setOpacity(Number(el.forecastOpacity.value) / 100);
  } else {
    state.forecastLayer = L.imageOverlay(imageUrl, bounds, {
      opacity: Number(el.forecastOpacity.value) / 100,
      interactive: false,
      zIndex: 225,
    }).addTo(state.map);
  }

  if (el.windToggle.checked) {
    state.windGrid = frame;
    startWind();
  }

  renderRainCloudLegend(frame);
  const cloudStats = matrixStats(cloudMatrix);
  const rainStats = matrixStats(precipitationMatrix);
  const stale =
    cube.metadata && cube.metadata.is_stale ? " · cached fallback" : "";
  el.forecastStatus.className = "layer-status";
  el.forecastStatus.textContent = `Rain-intensity overlay up to ${Number(rainStats.max).toFixed(1)} mm/h · supporting cloud cover ${formatRange(cloudStats.min, cloudStats.max, "%")} · valid ${formatDateMaybe(frame.valid_time)}${stale}. Transparent means no measurable rain.`;
  setDataBadges(
    "Animated rain-intensity forecast",
    frame.valid_time,
    cube.metadata.source,
  );
  updateTimelineLabels();
}

function bilinearValue(matrix, y, x) {
  const rows = matrix.length;
  const cols = matrix[0] ? matrix[0].length : 0;
  if (!rows || !cols) return 0;
  const y0 = Math.max(0, Math.min(rows - 1, Math.floor(y)));
  const y1 = Math.max(0, Math.min(rows - 1, Math.ceil(y)));
  const x0 = Math.max(0, Math.min(cols - 1, Math.floor(x)));
  const x1 = Math.max(0, Math.min(cols - 1, Math.ceil(x)));
  const fy = y - y0;
  const fx = x - x0;
  const q00 = Number(matrix[y0][x0]);
  const q01 = Number(matrix[y0][x1]);
  const q10 = Number(matrix[y1][x0]);
  const q11 = Number(matrix[y1][x1]);
  const a = Number.isFinite(q00) ? q00 : 0;
  const b = Number.isFinite(q01) ? q01 : a;
  const c = Number.isFinite(q10) ? q10 : a;
  const d = Number.isFinite(q11) ? q11 : c;
  return (
    a * (1 - fx) * (1 - fy) +
    b * fx * (1 - fy) +
    c * (1 - fx) * fy +
    d * fx * fy
  );
}

const RAIN_INTENSITY_STOPS = [
  { value: 0.0, color: [102, 217, 255, 0.0] },
  { value: 0.05, color: [102, 217, 255, 0.42] },
  { value: 0.5, color: [8, 120, 255, 0.68] },
  { value: 2.0, color: [7, 57, 207, 0.82] },
  { value: 4.0, color: [255, 225, 79, 0.88] },
  { value: 8.0, color: [255, 59, 48, 0.95] },
  { value: 20.0, color: [180, 0, 32, 0.98] },
];

function rainIntensityColor(precipitation) {
  const value = Math.max(0, Number(precipitation) || 0);
  if (value < 0.01) return [0, 0, 0, 0];
  for (let index = 1; index < RAIN_INTENSITY_STOPS.length; index++) {
    const lower = RAIN_INTENSITY_STOPS[index - 1];
    const upper = RAIN_INTENSITY_STOPS[index];
    if (value <= upper.value) {
      const fraction = Math.max(
        0,
        Math.min(1, (value - lower.value) / (upper.value - lower.value)),
      );
      return lower.color.map(
        (component, channel) =>
          component + (upper.color[channel] - component) * fraction,
      );
    }
  }
  return RAIN_INTENSITY_STOPS[RAIN_INTENSITY_STOPS.length - 1].color;
}

function drawRainCloudCanvas(frame) {
  const source = document.createElement("canvas");
  source.width = 300;
  source.height = 210;
  const ctx = source.getContext("2d");
  const image = ctx.createImageData(source.width, source.height);
  const clouds = frame.values.cloud_cover;
  const rain = frame.values.precipitation;

  for (let py = 0; py < source.height; py++) {
    const gy = (py / (source.height - 1)) * (frame.rows - 1);
    for (let px = 0; px < source.width; px++) {
      const gx = (px / (source.width - 1)) * (frame.cols - 1);
      const cloud = Math.max(0, Math.min(100, bilinearValue(clouds, gy, gx)));
      const precip = Math.max(0, bilinearValue(rain, gy, gx));
      const color = rainIntensityColor(precip);
      const index = (py * source.width + px) * 4;

      if (color[3] <= 0) {
        image.data[index + 3] = 0;
        continue;
      }

      // Cloud cover only shapes the edge opacity. Hue is controlled exclusively by rain intensity.
      const cloudSupport = 0.82 + 0.18 * Math.max(0, Math.min(1, cloud / 100));
      image.data[index] = Math.round(color[0]);
      image.data[index + 1] = Math.round(color[1]);
      image.data[index + 2] = Math.round(color[2]);
      image.data[index + 3] = Math.round(
        255 * Math.min(1, color[3] * cloudSupport),
      );
    }
  }
  ctx.putImageData(image, 0, 0);

  const canvas = document.createElement("canvas");
  canvas.width = 900;
  canvas.height = 630;
  const output = canvas.getContext("2d");
  output.imageSmoothingEnabled = true;
  output.imageSmoothingQuality = "high";
  output.filter = "blur(2.5px) saturate(1.15)";
  output.drawImage(source, -4, -4, canvas.width + 8, canvas.height + 8);
  output.filter = "none";
  return canvas;
}

function renderRainCloudLegend(frame) {
  const rainStats = matrixStats(frame.values.precipitation);
  el.legend.innerHTML = `<div class="legend-title"><strong>Forecast rain intensity</strong><span>mm/h</span></div>
    <div class="legend-gradient rain-intensity-gradient"></div>
    <div class="legend-scale rain-intensity-scale"><span>Trace</span><span>Light</span><span>Moderate</span><span>Heavy</span></div>
    <div class="legend-thresholds"><span>0.05</span><span>0.5</span><span>2</span><span>4</span><span>8+</span></div>
    <div class="legend-note">Blue → yellow → red indicates increasing hourly rain. Current map maximum: ${Number(rainStats.max).toFixed(1)} mm/h.</div>`;
  el.legend.classList.remove("hidden");
}

async function jumpToNextRain() {
  el.nextRainButton.disabled = true;
  try {
    if (!state.cloudCube) await loadForecastCube();
    const cube = state.cloudCube;
    if (!cube) throw new Error("The cloud forecast has not loaded yet.");
    const target = state.point || {
      lat: state.map.getCenter().lat,
      lng: state.map.getCenter().lng,
    };
    const row = Math.max(
      0,
      Math.min(
        cube.rows - 1,
        Math.round(
          ((cube.north - target.lat) / (cube.north - cube.south)) *
            (cube.rows - 1),
        ),
      ),
    );
    const col = Math.max(
      0,
      Math.min(
        cube.cols - 1,
        Math.round(
          ((target.lng - cube.west) / (cube.east - cube.west)) *
            (cube.cols - 1),
        ),
      ),
    );
    const series = cube.values.precipitation[row * cube.cols + col] || [];
    const start = Math.max(0, Math.ceil(state.forecastPosition));
    let found = -1;
    for (let index = start; index < series.length; index++) {
      if (Number(series[index]) >= 0.1) {
        found = index;
        break;
      }
    }
    if (found < 0) {
      showMessage(
        "No measurable rain was found near the selected point during the available 16-day map forecast.",
      );
      return;
    }
    const radio = el.forecastRadios.find(
      (item) => item.value === "rain_clouds",
    );
    if (radio) radio.checked = true;
    state.forecastVariable = "rain_clouds";
    switchTimeline("forecast");
    state.forecastPosition = Math.max(0, found - 3);
    state.forecastHour = Math.floor(state.forecastPosition);
    el.timelineSlider.value = state.forecastPosition;
    renderInterpolatedForecastFrame();
    if (!state.playing) startPlayback();
    showMessage(
      `Rain near the selected point is forecast around ${formatDateMaybe(cube.times[found])}. Playback started three hours earlier so you can watch it approach.`,
      7000,
    );
  } catch (error) {
    showMessage(error.message);
  } finally {
    el.nextRainButton.disabled = false;
  }
}

async function loadForecastGrid() {
  const requestId = ++state.gridRequestId;
  const bounds = safeBounds();
  const variables = [];
  if (state.forecastVariable !== "none") variables.push(state.forecastVariable);
  if (el.windToggle.checked)
    variables.push("wind_speed_10m", "wind_direction_10m");
  if (!variables.length) return;

  const body = {
    ...bounds,
    rows: 6,
    cols: 6,
    variables: [...new Set(variables)],
    hour_index: state.forecastHour,
    model: el.modelSelect.value,
  };
  const signature = gridSignature(body);
  const cached = state.gridCache.get(signature);
  if (cached) {
    applyGridPayload(cached, requestId);
    return;
  }

  if (state.gridAbortController) state.gridAbortController.abort();
  state.gridAbortController = new AbortController();
  state.lastGridSignature = signature;
  el.forecastStatus.className = "layer-status loading";
  el.forecastStatus.textContent =
    "Loading one shared weather grid. Layer and timeline changes will reuse the local cache.";
  setDataBadges(
    "Loading forecast grid",
    state.forecastTimes[state.forecastHour],
    modelLabel(),
  );

  try {
    const payload = await fetchJson(API.grid, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: state.gridAbortController.signal,
    });
    if (requestId !== state.gridRequestId) return;
    rememberGrid(signature, payload);
    applyGridPayload(payload, requestId);
  } catch (error) {
    if (error.name === "AbortError" || requestId !== state.gridRequestId)
      return;
    el.forecastStatus.className = "layer-status error";
    el.forecastStatus.textContent =
      error.status === 429
        ? "The provider is cooling down. Stop moving the map for a few minutes; cached layers will remain available."
        : `Forecast layer unavailable: ${error.message}`;
    showMessage(`Forecast map unavailable: ${error.message}`);
    setDataBadges("Forecast unavailable", null, modelLabel());
  }
}

function applyGridPayload(payload, requestId) {
  if (requestId !== state.gridRequestId) return;
  state.gridData = payload;
  if (state.forecastVariable !== "none")
    renderForecastLayer(payload, state.forecastVariable);
  else clearForecastLayers();
  if (el.windToggle.checked) {
    state.windGrid = payload;
    startWind();
  }
  if (state.forecastVariable === "none") {
    const staleNote =
      payload.metadata && payload.metadata.is_stale ? " · cached fallback" : "";
    el.forecastStatus.className = "layer-status";
    el.forecastStatus.textContent = `${payload.metadata.source_type}${staleNote}. Wind grid valid ${formatDateMaybe(payload.valid_time)}. ${payload.rows}×${payload.cols} sampled grid.`;
  }
  setDataBadges(
    payload.metadata.source_type,
    payload.valid_time,
    payload.metadata.source,
  );
  updateTimelineLabels();
}

function clearForecastLayers() {
  if (state.forecastLayer) state.map.removeLayer(state.forecastLayer);
  if (state.contourLayer) state.map.removeLayer(state.contourLayer);
  state.forecastLayer = null;
  state.contourLayer = null;
  el.legend.classList.add("hidden");
}

function renderForecastLayer(grid, variable) {
  const baseInfo = VARIABLE_INFO[variable];
  const matrix = grid.values[variable];
  if (!baseInfo || !matrix) {
    el.forecastStatus.className = "layer-status error";
    el.forecastStatus.textContent =
      "The selected field was not included in the provider response.";
    return;
  }

  const stats = matrixStats(matrix);
  if (!stats.values.length) {
    el.forecastStatus.className = "layer-status error";
    el.forecastStatus.textContent =
      "The selected field contains no usable values for this map area and time.";
    return;
  }
  const info = adaptiveInfo(baseInfo, variable, stats);
  const canvas =
    variable === "pressure_msl"
      ? drawPressureCanvas(grid, info)
      : drawRasterCanvas(grid, variable, info);
  const bounds = [
    [grid.south, grid.west],
    [grid.north, grid.east],
  ];
  const imageUrl = canvas.toDataURL("image/png");
  const opacity = Number(el.forecastOpacity.value) / 100;
  if (variable === "pressure_msl") {
    if (state.forecastLayer) {
      state.map.removeLayer(state.forecastLayer);
      state.forecastLayer = null;
    }
    if (state.contourLayer) {
      state.contourLayer.setBounds(bounds);
      state.contourLayer.setUrl(imageUrl);
      state.contourLayer.setOpacity(opacity);
    } else {
      state.contourLayer = L.imageOverlay(imageUrl, bounds, {
        opacity,
        interactive: false,
        zIndex: 220,
      }).addTo(state.map);
    }
  } else {
    if (state.contourLayer) {
      state.map.removeLayer(state.contourLayer);
      state.contourLayer = null;
    }
    if (state.forecastLayer) {
      state.forecastLayer.setBounds(bounds);
      state.forecastLayer.setUrl(imageUrl);
      state.forecastLayer.setOpacity(opacity);
    } else {
      state.forecastLayer = L.imageOverlay(imageUrl, bounds, {
        opacity,
        interactive: false,
        zIndex: 220,
      }).addTo(state.map);
    }
  }
  renderLegend(info);

  if (variable === "precipitation" && stats.max < 0.05) {
    el.forecastStatus.className = "layer-status";
    el.forecastStatus.textContent = `No measurable hourly precipitation is forecast in the visible sampled area at ${formatDateMaybe(grid.valid_time)}.`;
  } else {
    el.forecastStatus.className = "layer-status";
    el.forecastStatus.textContent = `${info.title}: ${formatRange(stats.min, stats.max, info.unit)} · valid ${formatDateMaybe(grid.valid_time)}${grid.metadata.is_stale ? " · cached fallback" : ""}.`;
  }
}

function matrixStats(matrix) {
  const values = matrix
    .flat()
    .filter((value) => value !== null && value !== undefined && value !== "")
    .map(Number)
    .filter(Number.isFinite)
    .sort((a, b) => a - b);
  if (!values.length) return { values, min: 0, max: 0, p90: 0, p95: 0 };
  const at = (q) =>
    values[
      Math.min(
        values.length - 1,
        Math.max(0, Math.floor((values.length - 1) * q)),
      )
    ];
  return {
    values,
    min: values[0],
    max: values[values.length - 1],
    p90: at(0.9),
    p95: at(0.95),
  };
}

function adaptiveInfo(baseInfo, variable, stats) {
  const info = { ...baseInfo };
  if (variable === "temperature_2m") {
    info.min = Math.floor(stats.min - 1);
    info.max = Math.ceil(stats.max + 1);
  } else if (variable === "precipitation") {
    info.min = 0;
    info.max = Math.max(
      1,
      Math.ceil(Math.max(stats.p95, stats.max * 0.7) * 2) / 2,
    );
  } else if (variable === "pressure_msl") {
    info.min = Math.floor(stats.min - 1);
    info.max = Math.ceil(stats.max + 1);
  }
  return info;
}

function drawRasterCanvas(grid, variable, info) {
  const source = document.createElement("canvas");
  source.width = grid.cols;
  source.height = grid.rows;
  const sourceContext = source.getContext("2d");
  const matrix = grid.values[variable];

  for (let row = 0; row < grid.rows; row++) {
    for (let col = 0; col < grid.cols; col++) {
      const value = Number(matrix[row][col]);
      if (!Number.isFinite(value)) continue;
      if (variable === "precipitation" && value < 0.02) {
        sourceContext.clearRect(col, row, 1, 1);
        continue;
      }
      sourceContext.fillStyle = scaleColor(
        value,
        info.min,
        info.max,
        info.stops,
      );
      sourceContext.fillRect(col, row, 1, 1);
    }
  }

  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 500;
  const context = canvas.getContext("2d");
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  // Extend half a cell so edge grid points cover the full geographic bounds.
  context.drawImage(
    source,
    -canvas.width / (grid.cols * 2),
    -canvas.height / (grid.rows * 2),
    (canvas.width * (grid.cols + 1)) / grid.cols,
    (canvas.height * (grid.rows + 1)) / grid.rows,
  );
  return canvas;
}

function drawPressureCanvas(grid, info) {
  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 500;
  const ctx = canvas.getContext("2d");
  const matrix = grid.values.pressure_msl;
  const cellW = canvas.width / (grid.cols - 1);
  const cellH = canvas.height / (grid.rows - 1);
  ctx.fillStyle = "rgba(7,17,31,.10)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const flat = matrix.flat().map(Number).filter(Number.isFinite);
  if (!flat.length) return canvas;
  const spread = Math.max(...flat) - Math.min(...flat);
  const interval = spread < 4 ? 1 : 2;
  const min = Math.floor(Math.min(...flat) / interval) * interval;
  const max = Math.ceil(Math.max(...flat) / interval) * interval;
  ctx.lineWidth = 2;
  ctx.font = "bold 13px system-ui";
  for (let level = min; level <= max; level += interval) {
    ctx.strokeStyle = scaleColor(level, info.min, info.max, info.stops);
    ctx.fillStyle = "rgba(255,255,255,.95)";
    let labelled = false;
    for (let r = 0; r < grid.rows - 1; r++) {
      for (let c = 0; c < grid.cols - 1; c++) {
        const values = [
          matrix[r][c],
          matrix[r][c + 1],
          matrix[r + 1][c + 1],
          matrix[r + 1][c],
        ].map(Number);
        if (!values.every(Number.isFinite)) continue;
        const intersections = contourIntersections(
          values,
          level,
          c * cellW,
          r * cellH,
          cellW,
          cellH,
        );
        if (intersections.length >= 2) {
          ctx.beginPath();
          ctx.moveTo(intersections[0][0], intersections[0][1]);
          ctx.lineTo(intersections[1][0], intersections[1][1]);
          ctx.stroke();
          if (!labelled && c > 0 && r > 0) {
            ctx.fillText(
              String(level),
              intersections[0][0] + 3,
              intersections[0][1] - 3,
            );
            labelled = true;
          }
        }
      }
    }
  }
  return canvas;
}

function formatRange(min, max, unit) {
  const digits = Math.abs(max - min) < 2 ? 1 : 0;
  return `${Number(min).toFixed(digits)}–${Number(max).toFixed(digits)} ${unit}`;
}

function contourIntersections(v, level, x, y, w, h) {
  const points = [];
  const edges = [
    [v[0], v[1], [x, y], [x + w, y]],
    [v[1], v[2], [x + w, y], [x + w, y + h]],
    [v[2], v[3], [x + w, y + h], [x, y + h]],
    [v[3], v[0], [x, y + h], [x, y]],
  ];
  edges.forEach(([a, b, p1, p2]) => {
    if ((a < level && b >= level) || (b < level && a >= level)) {
      const t = (level - a) / (b - a || 1e-9);
      points.push([p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t]);
    }
  });
  return points;
}

function renderLegend(info) {
  const midpoint = (info.min + info.max) / 2;
  el.legend.innerHTML = `<div class="legend-title"><strong>${escapeHtml(info.title)}</strong><span>${escapeHtml(info.unit)}</span></div>
    <div class="legend-gradient" style="background:linear-gradient(90deg,${info.stops.join(",")})"></div>
    <div class="legend-scale"><span>${roundLegend(info.min)}</span><span>${roundLegend(midpoint)}</span><span>${roundLegend(info.max)}+</span></div>`;
  el.legend.classList.remove("hidden");
}

function roundLegend(value) {
  return Math.abs(value) < 10 && !Number.isInteger(value)
    ? value.toFixed(1)
    : String(Math.round(value));
}

function resizeWindCanvas() {
  if (!state.map) return;
  const size = state.map.getSize();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  el.windCanvas.width = Math.round(size.x * dpr);
  el.windCanvas.height = Math.round(size.y * dpr);
  el.windCanvas.style.width = `${size.x}px`;
  el.windCanvas.style.height = `${size.y}px`;
  el.windCanvas.dataset.pixelRatio = String(dpr);
  const ctx = el.windCanvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  seedWindParticles();
}

function seedWindParticles() {
  if (!state.map) return;
  const size = state.map.getSize();
  const count = Math.max(
    95,
    Math.min(340, Math.floor((size.x * size.y) / 4200)),
  );
  state.windParticles = Array.from({ length: count }, () => ({
    x: Math.random() * size.x,
    y: Math.random() * size.y,
    age: Math.random() * 90,
  }));
}

function startWind() {
  if (!state.windGrid || !el.windToggle.checked) return;
  resizeWindCanvas();
  if (!state.windParticles.length) seedWindParticles();
  if (!state.windAnimation) {
    state.windLastFrame = 0;
    state.windAnimation = requestAnimationFrame(animateWind);
  }
}

function stopWind() {
  if (state.windAnimation) cancelAnimationFrame(state.windAnimation);
  state.windAnimation = null;
  const ctx = el.windCanvas.getContext("2d");
  const ratio = Number(el.windCanvas.dataset.pixelRatio || 1);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, el.windCanvas.clientWidth, el.windCanvas.clientHeight);
}

function drawWindArrow(ctx, x, y, vector, alpha) {
  const magnitude = Math.max(0.001, Math.hypot(vector.u, vector.v));
  const ux = vector.u / magnitude;
  const uyScreen = -vector.v / magnitude;
  const shaft = Math.max(7, Math.min(18, 7 + magnitude * 0.32));
  const x2 = x + ux * shaft;
  const y2 = y + uyScreen * shaft;
  const head = Math.max(3.2, Math.min(5.8, shaft * 0.34));
  const angle = Math.atan2(y2 - y, x2 - x);
  ctx.globalAlpha = alpha;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x2, y2);
  ctx.moveTo(x2, y2);
  ctx.lineTo(
    x2 - head * Math.cos(angle - Math.PI / 6),
    y2 - head * Math.sin(angle - Math.PI / 6),
  );
  ctx.moveTo(x2, y2);
  ctx.lineTo(
    x2 - head * Math.cos(angle + Math.PI / 6),
    y2 - head * Math.sin(angle + Math.PI / 6),
  );
  ctx.stroke();
}

function animateWind(timestamp) {
  if (!el.windToggle.checked || !state.windGrid) {
    stopWind();
    return;
  }
  const ctx = el.windCanvas.getContext("2d");
  const size = state.map.getSize();
  const ratio = Number(el.windCanvas.dataset.pixelRatio || 1);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  const dt = Math.min(
    2,
    Math.max(0.35, (timestamp - (state.windLastFrame || timestamp)) / 16.67),
  );
  state.windLastFrame = timestamp;
  ctx.clearRect(0, 0, size.x, size.y);
  const dark = document.documentElement.dataset.theme === "dark";
  ctx.strokeStyle = dark ? "rgba(224,255,236,.92)" : "rgba(247,255,250,.96)";
  ctx.shadowColor = dark ? "rgba(78,224,142,.38)" : "rgba(18,83,52,.45)";
  ctx.shadowBlur = 2.2;
  ctx.lineWidth = 1.35;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const p of state.windParticles) {
    const latlng = state.map.containerPointToLatLng([p.x, p.y]);
    const vector = windAt(latlng.lat, latlng.lng);
    if (
      !vector ||
      p.age > 120 ||
      p.x < -24 ||
      p.y < -24 ||
      p.x > size.x + 24 ||
      p.y > size.y + 24
    ) {
      p.x = Math.random() * size.x;
      p.y = Math.random() * size.y;
      p.age = 0;
      continue;
    }
    const magnitude = Math.max(0.1, Math.hypot(vector.u, vector.v));
    const movement = Math.max(0.55, Math.min(3.8, magnitude * 0.055)) * dt;
    const nx = p.x + (vector.u / magnitude) * movement;
    const ny = p.y - (vector.v / magnitude) * movement;
    const alpha = Math.max(0.28, 1 - p.age / 150);
    drawWindArrow(ctx, p.x, p.y, vector, alpha);
    p.x = nx;
    p.y = ny;
    p.age += 1;
  }
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 0;
  state.windAnimation = requestAnimationFrame(animateWind);
}

function gridFraction(grid, lat, lng) {
  if (!grid || lat < grid.south || lat > grid.north || lng < grid.west || lng > grid.east)
    return null;
  const row = ((grid.north - lat) / Math.max(1e-9, grid.north - grid.south)) * (grid.rows - 1);
  const col = ((lng - grid.west) / Math.max(1e-9, grid.east - grid.west)) * (grid.cols - 1);
  return { row, col };
}

function vectorMatrixAt(grid, row, col) {
  const speeds = grid.values.wind_speed_10m;
  const directions = grid.values.wind_direction_10m;
  if (!speeds || !directions) return null;
  const rows = grid.rows;
  const cols = grid.cols;
  const r0 = Math.max(0, Math.min(rows - 1, Math.floor(row)));
  const r1 = Math.max(0, Math.min(rows - 1, Math.ceil(row)));
  const c0 = Math.max(0, Math.min(cols - 1, Math.floor(col)));
  const c1 = Math.max(0, Math.min(cols - 1, Math.ceil(col)));
  const fy = row - r0;
  const fx = col - c0;
  const weights = [
    [r0, c0, (1 - fx) * (1 - fy)],
    [r0, c1, fx * (1 - fy)],
    [r1, c0, (1 - fx) * fy],
    [r1, c1, fx * fy],
  ];
  let u = 0;
  let v = 0;
  let total = 0;
  for (const [r, c, weight] of weights) {
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

function terrainAt(grid, row, col) {
  const elevation = grid.elevation_m;
  if (!Array.isArray(elevation) || !Array.isArray(elevation[0])) return null;
  const sample = (r, c) => bilinearValue(
    elevation,
    Math.max(0, Math.min(grid.rows - 1, r)),
    Math.max(0, Math.min(grid.cols - 1, c)),
  );
  const center = sample(row, col);
  const eastGradient = (sample(row, col + 0.65) - sample(row, col - 0.65)) / 1.3;
  const northGradient = -(sample(row + 0.65, col) - sample(row - 0.65, col)) / 1.3;
  if (![center, eastGradient, northGradient].every(Number.isFinite)) return null;
  return { elevation: center, gx: eastGradient, gy: northGradient };
}

function applyTerrainDeflection(vector, terrain) {
  if (!terrain) return vector;
  const gradientMagnitude = Math.hypot(terrain.gx, terrain.gy);
  if (gradientMagnitude < 2) return vector;
  const gx = terrain.gx / gradientMagnitude;
  const gy = terrain.gy / gradientMagnitude;
  const alongGradient = vector.u * gx + vector.v * gy;
  const terrainStrength = Math.max(
    0,
    Math.min(0.72, gradientMagnitude / 420 + Math.max(0, terrain.elevation - 250) / 3500),
  );
  let u = vector.u;
  let v = vector.v;
  if (alongGradient > 0) {
    u -= gx * alongGradient * terrainStrength;
    v -= gy * alongGradient * terrainStrength;
    const tangentX = -gy;
    const tangentY = gx;
    const turnSign = vector.u * tangentY - vector.v * tangentX >= 0 ? 1 : -1;
    const turn = alongGradient * terrainStrength * 0.58 * turnSign;
    u += tangentX * turn;
    v += tangentY * turn;
  }
  const slowdown = 1 - terrainStrength * 0.24;
  return { u: u * slowdown, v: v * slowdown };
}

function applyFarmTerrainProxy(vector, lat, lng) {
  const terrain = state.farmTerrain;
  if (!terrain || !finite(terrain.latitude) || !finite(terrain.longitude)) return vector;
  const slope = Math.max(0, Number(terrain.slope_degrees || 0));
  const elevation = Math.max(0, Number(terrain.elevation_m || 0));
  if (slope < 2 && elevation < 250) return vector;
  const dy = (lat - terrain.latitude) * 111;
  const dx = (lng - terrain.longitude) * 111 * Math.cos((lat * Math.PI) / 180);
  const distance = Math.hypot(dx, dy);
  const radius = Math.max(4, Math.min(28, 5 + slope * 0.7 + elevation / 180));
  if (distance >= radius || distance < 0.05) return vector;
  const rx = dx / distance;
  const ry = dy / distance;
  const influence = Math.pow(1 - distance / radius, 2) * Math.min(0.55, slope / 35 + elevation / 4500);
  const inward = -(vector.u * rx + vector.v * ry);
  if (inward <= 0) return vector;
  const tangentX = -ry;
  const tangentY = rx;
  const sign = vector.u * tangentX + vector.v * tangentY >= 0 ? 1 : -1;
  return {
    u: vector.u + rx * inward * influence + tangentX * inward * influence * 0.75 * sign,
    v: vector.v + ry * inward * influence + tangentY * inward * influence * 0.75 * sign,
  };
}

function windAt(lat, lng) {
  const grid = state.windGrid;
  if (!grid || !grid.values.wind_speed_10m || !grid.values.wind_direction_10m)
    return null;
  const position = gridFraction(grid, lat, lng);
  if (!position) return null;
  const base = vectorMatrixAt(grid, position.row, position.col);
  if (!base) return null;
  const terrainAdjusted = applyTerrainDeflection(base, terrainAt(grid, position.row, position.col));
  return applyFarmTerrainProxy(terrainAdjusted, lat, lng);
}

async function loadStorms() {
  try {
    state.stormData = await fetchJson(API.storms);
    el.stormCount.textContent = String((state.stormData.events || []).length);
    renderStorms();
  } catch (error) {
    el.stormCount.textContent = "!";
    showMessage(`Cyclone feed unavailable: ${error.message}`);
  }
}

function renderStorms() {
  state.stormLayer.clearLayers();
  if (!el.stormsToggle.checked || !state.stormData) return;
  (state.stormData.events || []).forEach((event) => {
    if (!finite(event.latitude) || !finite(event.longitude)) return;
    const color =
      event.alert_level === "Red"
        ? "#ff4e5b"
        : event.alert_level === "Orange"
          ? "#ff9e43"
          : "#55d59a";
    const marker = L.circleMarker([event.latitude, event.longitude], {
      radius: 10,
      color: "#fff",
      weight: 2,
      fillColor: color,
      fillOpacity: 0.9,
    });
    marker.bindPopup(
      `<div class="storm-popup"><strong>${escapeHtml(event.name)}</strong><p>${escapeHtml(event.alert_level || "GDACS event")} alert</p><p>${escapeHtml(event.description || "No detailed description supplied.")}</p>${event.source_url ? `<a href="${safeUrl(event.source_url)}" target="_blank" rel="noopener">Open GDACS event ↗</a>` : ""}<p><b>Important:</b> Check PAGASA for official Philippine warnings.</p></div>`,
    );
    marker.addTo(state.stormLayer);
    if (event.track && event.track.length > 1)
      L.polyline(event.track, { color, weight: 3, dashArray: "6 6" }).addTo(
        state.stormLayer,
      );
  });
}

function updateStormVisibility() {
  if (el.stormsToggle.checked) {
    if (!state.map.hasLayer(state.stormLayer))
      state.stormLayer.addTo(state.map);
    renderStorms();
  } else state.map.removeLayer(state.stormLayer);
}

async function refreshAll() {
  el.sourceDot.className = "";
  await Promise.allSettled([loadHealthAndSources(), loadRadar(), loadStorms()]);
  if (state.point)
    await loadPointForecast(state.point.lat, state.point.lng, state.point.name);
  scheduleGridRefresh(true);
  showMessage("Data refresh completed.");
}

function setDataBadges(type, time, source) {
  el.activeDataBadge.textContent = type || "Weather data";
  el.validTimeBadge.textContent = time
    ? `${formatDateMaybe(time)} · ${source || ""}`
    : source || "Waiting for data";
}

function wmo(code) {
  return WMO[Number(code)] || ["Weather", "☁"];
}
function valueAt(array, index) {
  return Array.isArray(array) ? array[index] : null;
}
function finite(value) {
  return Number.isFinite(Number(value));
}
function round1(value) {
  return finite(value) ? Number(value).toFixed(1) : "—";
}
function formatUnit(value, unit) {
  return finite(value) ? `${round1(value)} ${unit}` : "—";
}
function compass(degrees) {
  if (!finite(degrees)) return "";
  const points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return points[Math.round(Number(degrees) / 45) % 8];
}
function modelLabel() {
  return el.modelSelect.options[el.modelSelect.selectedIndex].textContent;
}
function formatDateMaybe(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}
function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>'"]/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        char
      ],
  );
}
function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}
function hexToRgba(hex) {
  const clean = hex.replace("#", "");
  const full = clean.length === 6 ? `${clean}ff` : clean.padEnd(8, "f");
  return [0, 2, 4, 6].map((i) => parseInt(full.slice(i, i + 2), 16));
}
function scaleColor(value, min, max, stops) {
  const t = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));
  const pos = t * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(pos));
  const f = pos - i;
  const a = hexToRgba(stops[i]),
    b = hexToRgba(stops[i + 1]);
  const c = a.map((v, j) => Math.round(v + (b[j] - v) * f));
  return `rgba(${c[0]},${c[1]},${c[2]},${c[3] / 255})`;
}

async function init() {
  cacheElements();
  requireLeaflet();
  initMap();
  setupEvents();
  buildFallbackForecastTimes();
  configureTimeline();
  await Promise.allSettled([loadHealthAndSources(), loadRadar(), loadStorms()]);
  state.map.invalidateSize();
  scheduleGridRefresh(true);
  requestFarmFromParent();
}

document.addEventListener("DOMContentLoaded", init);
