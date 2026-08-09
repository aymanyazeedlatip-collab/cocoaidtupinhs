from __future__ import annotations

import io
import math
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _rain_color(value: float) -> tuple[int, int, int, int]:
    if not np.isfinite(value) or value < 0.03:
        return (0, 0, 0, 0)
    stops = [
        (0.03, (95, 218, 255, 40)),
        (0.6, (48, 172, 255, 120)),
        (2.0, (20, 102, 232, 185)),
        (5.0, (10, 47, 175, 220)),
        (10.0, (255, 225, 48, 235)),
        (18.0, (255, 137, 38, 242)),
        (30.0, (224, 37, 42, 248)),
    ]
    value = float(np.clip(value, stops[0][0], stops[-1][0]))
    upper = 1
    while upper < len(stops) and value > stops[upper][0]:
        upper += 1
    upper = min(len(stops) - 1, upper)
    lower = max(0, upper - 1)
    span = max(1e-9, stops[upper][0] - stops[lower][0])
    t = (value - stops[lower][0]) / span
    return tuple(int(round(stops[lower][1][i] + (stops[upper][1][i] - stops[lower][1][i]) * t)) for i in range(4))


def _generated_grid(frame: dict[str, Any], size: int = 48) -> np.ndarray:
    raw = frame.get("spatial_grid")
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        arr = np.asarray(raw, dtype=float)
        if arr.ndim == 2 and arr.size:
            return arr
    spatial = frame.get("spatial") or [0.5, 0.5, 0.15, 0.0, 1]
    cx, cy, spread, peak, seed = [float(v) for v in spatial[:5]]
    rng = np.random.default_rng(int(seed) % (2**32 - 1))
    blobs = [(cx, cy, max(0.04, spread), max(0.0, peak))]
    for _ in range(5):
        blobs.append((
            (cx + rng.uniform(-1.25, 1.25) * spread) % 1.0,
            (cy + rng.uniform(-1.25, 1.25) * spread) % 1.0,
            spread * rng.uniform(0.45, 1.35),
            peak * rng.uniform(0.18, 0.70),
        ))
    ys, xs = np.mgrid[0:1:complex(size), 0:1:complex(size)]
    grid = np.zeros((size, size), dtype=float)
    for bx, by, bs, bp in blobs:
        grid += bp * np.exp(-((xs - bx) ** 2 + (ys - by) ** 2) / (2 * max(1e-4, bs) ** 2))
    return grid


def _resample_grid(grid: np.ndarray, width: int, height: int) -> np.ndarray:
    # PIL's bicubic interpolation creates a smooth visual surface from the coarse
    # model grid without changing its spatial domain or claiming finer data.
    minimum = float(np.nanmin(grid)) if np.isfinite(grid).any() else 0.0
    maximum = float(np.nanmax(grid)) if np.isfinite(grid).any() else 0.0
    if maximum <= minimum:
        return np.full((height, width), minimum, dtype=float)
    normalized = np.clip((grid - minimum) / (maximum - minimum), 0, 1)
    image = Image.fromarray(np.uint8(normalized * 255), mode="L")
    image = image.resize((width, height), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(2.2))
    return np.asarray(image, dtype=float) / 255.0 * (maximum - minimum) + minimum


def weather_snapshot(frame: dict[str, Any], farm: dict[str, Any] | None = None, width: int = 1180, height: int = 640) -> io.BytesIO:
    image = Image.new("RGB", (width, height), (243, 246, 244))
    draw = ImageDraw.Draw(image)
    # A neutral schematic map background. It is intentionally not a fabricated
    # geographic basemap; the colored field is the modeled rain surface.
    for x in range(0, width, 80):
        draw.line((x, 0, x, height), fill=(220, 225, 222), width=1)
    for y in range(0, height, 70):
        draw.line((0, y, width, y), fill=(220, 225, 222), width=1)
    draw.rounded_rectangle((28, 28, width - 28, height - 28), radius=24, outline=(120, 130, 125), width=2)

    grid = _generated_grid(frame)
    smooth = _resample_grid(grid, width - 56, height - 56)
    rgba = np.zeros((height - 56, width - 56, 4), dtype=np.uint8)
    for y in range(rgba.shape[0]):
        for x in range(rgba.shape[1]):
            rgba[y, x] = _rain_color(float(smooth[y, x]))
    overlay = Image.fromarray(rgba, mode="RGBA").filter(ImageFilter.GaussianBlur(1.2))
    image.paste(overlay, (28, 28), overlay)
    draw = ImageDraw.Draw(image)

    # Farm location marker centered when exact map position is unavailable.
    fx = float((farm or {}).get("map_x", 0.5))
    fy = float((farm or {}).get("map_y", 0.5))
    px = int(28 + np.clip(fx, 0, 1) * (width - 56))
    py = int(28 + np.clip(fy, 0, 1) * (height - 56))
    draw.ellipse((px - 14, py - 14, px + 14, py + 14), fill=(255, 255, 255), outline=(20, 70, 42), width=4)
    draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(20, 70, 42))

    try:
        font_large = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 20)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    date_label = str(frame.get("label") or frame.get("week_start") or frame.get("date") or "Critical forecast date")
    event = str(frame.get("event") or "normal").replace("_", " ").title()
    line1 = f"{date_label} - {event}"
    line2 = (
        f"Rain {float(frame.get('rainfall_mm', 0.0)):.1f} mm | "
        f"Peak {float(frame.get('rain_intensity_mm_h', 0.0)):.1f} mm/h | "
        f"Max temperature {float(frame.get('temperature_max_c', frame.get('temperature_c', 0.0))):.1f} C | "
        f"Wind {float(frame.get('wind_speed_kmh', 0.0)):.1f} km/h"
    )
    box = (48, 45, min(width - 48, 1040), 130)
    draw.rounded_rectangle(box, radius=14, fill=(255, 255, 255, 235), outline=(90, 100, 95), width=1)
    draw.text((65, 58), line1, font=font_large, fill=(0, 0, 0))
    draw.text((65, 99), line2, font=font_small, fill=(0, 0, 0))

    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


def simple_donut_image(values: list[tuple[str, float, tuple[int, int, int]]], title: str, size: int = 640) -> io.BytesIO:
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    center = size // 2
    radius = int(size * 0.34)
    box = (center - radius, center - radius, center + radius, center + radius)
    total = sum(max(0.0, value) for _, value, _ in values) or 1.0
    start = -90.0
    for _, value, color in values:
        extent = 360.0 * max(0.0, value) / total
        draw.pieslice(box, start=start, end=start + extent, fill=color, outline="white", width=3)
        start += extent
    inner = int(radius * 0.60)
    draw.ellipse((center - inner, center - inner, center + inner, center + inner), fill="white")
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        font_label = ImageFont.truetype("DejaVuSans.ttf", 20)
    except OSError:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), title, font=font_title)
    draw.text(((size - (bbox[2] - bbox[0])) / 2, 28), title, font=font_title, fill="black")
    y = size - 130
    for label, value, color in values:
        draw.rectangle((55, y, 75, y + 20), fill=color)
        draw.text((88, y - 2), f"{label}: {value:.1f}", font=font_label, fill="black")
        y += 34
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


def farm_location_snapshot(farm: dict[str, Any] | None, width: int = 1180, height: int = 560) -> io.BytesIO:
    farm = farm or {}
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    margin = 46
    draw.rectangle((margin, margin, width - margin, height - margin), outline=(70, 70, 70), width=2)
    for fraction in (0.25, 0.5, 0.75):
        x = margin + int((width - 2 * margin) * fraction)
        y = margin + int((height - 2 * margin) * fraction)
        draw.line((x, margin, x, height - margin), fill=(215, 215, 215), width=1)
        draw.line((margin, y, width - margin, y), fill=(215, 215, 215), width=1)

    polygon = farm.get("polygon") or []
    clean = []
    for point in polygon:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                clean.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                pass
    latitude = float(farm.get("latitude") or (sum(p[0] for p in clean) / len(clean) if clean else 0.0))
    longitude = float(farm.get("longitude") or (sum(p[1] for p in clean) / len(clean) if clean else 0.0))
    if len(clean) >= 3:
        lats = [p[0] for p in clean]
        lons = [p[1] for p in clean]
        lat_span = max(max(lats) - min(lats), 0.0004)
        lon_span = max(max(lons) - min(lons), 0.0004)
        lat_min, lat_max = min(lats) - lat_span * 0.28, max(lats) + lat_span * 0.28
        lon_min, lon_max = min(lons) - lon_span * 0.28, max(lons) + lon_span * 0.28
        points = []
        for lat, lon in clean:
            x = margin + (lon - lon_min) / (lon_max - lon_min) * (width - 2 * margin)
            y = height - margin - (lat - lat_min) / (lat_max - lat_min) * (height - 2 * margin)
            points.append((x, y))
        draw.polygon(points, fill=(230, 230, 230), outline=(0, 0, 0))
        draw.line(points + [points[0]], fill=(0, 0, 0), width=4)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(0, 0, 0))
    else:
        cx, cy = width // 2, height // 2
        draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), outline=(0, 0, 0), width=4)
        draw.line((cx, cy - 28, cx, cy + 28), fill=(0, 0, 0), width=2)
        draw.line((cx - 28, cy, cx + 28, cy), fill=(0, 0, 0), width=2)

    try:
        font_title = ImageFont.truetype("DejaVuSerif-Bold.ttf", 27)
        font_body = ImageFont.truetype("DejaVuSerif.ttf", 19)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    label = str(farm.get("name") or "Farm site")
    draw.rectangle((58, 58, min(width - 58, 730), 146), fill="white", outline=(110, 110, 110), width=1)
    draw.text((76, 72), label, font=font_title, fill="black")
    draw.text((76, 112), f"Centroid: {latitude:.6f}, {longitude:.6f} | Area: {float(farm.get('area_hectares') or 0):.3f} ha", font=font_body, fill="black")
    # North arrow and scale-neutral note.
    draw.line((width - 95, 125, width - 95, 72), fill="black", width=3)
    draw.polygon([(width - 95, 58), (width - 104, 78), (width - 86, 78)], fill="black")
    draw.text((width - 106, 130), "N", font=font_body, fill="black")
    draw.text((margin + 8, height - margin - 28), "Farm boundary diagram based on user-entered coordinates; not a cadastral survey.", font=font_body, fill="black")
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
