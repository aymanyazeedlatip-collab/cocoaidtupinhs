"use strict";
(() => {
  function boot() {
    document.documentElement.dataset.theme = "light";
    const map = document.getElementById("map");
    if (map && !document.querySelector(".weather-scan-indicator")) {
      const indicator = document.createElement("div");
      indicator.className = "weather-scan-indicator";
      indicator.innerHTML = "<span></span> Live atmospheric scan";
      map.parentElement?.appendChild(indicator);
    }
    document.querySelectorAll("button:not([aria-label])").forEach((button) => {
      const text = button.textContent.trim();
      if (text) button.setAttribute("aria-label", text);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
