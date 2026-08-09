# COCO-AID v2.4 User Guide

## 1. Start the application

Run `setup.bat` once, then `run.bat`. Open `http://127.0.0.1:8000`.

## 2. Landing page

Use **Draw my farm** to sketch a farm boundary on the quick map, or choose **Enter farm details**. A drawn boundary transfers to Farm Setup and updates its calculated area and centroid.

## 3. Farm Setup

Complete the three subtabs:

- Identity and boundary
- Trees and production
- Soil and management

The seven tree-state counts must add exactly to Total Trees. The interface recalculates the total while you edit. Choose the province to load the corresponding PSA production profile. Save the farm to the local database before running forecasts so it can be reopened later.

## 4. Farm Site Forecast

Choose:

- SSP climate scenario
- Rehabilitation strategy
- Monte Carlo run count

Select **Run Forecast**. The result provides a daily visual frame for every date through 2050, linked to weekly agricultural control points. Playback advances at the configured long-term rate; the default is one second for two simulated days. Short-term provider values are used only when current provider data overlap the selected start date; later dates are labeled climate-conditioned projections.

The map displays rain intensity using transparent, blue, yellow, and red thresholds. The slider and play controls move the same date marker through:

- Coconut (w/ husk), Mature, and Young production
- Rainfall and mean/maximum temperature
- Humidity, cloud, wind, and pressure charts
- Farm condition and pest probability

Use mouse-wheel zoom, drag zoom, and pan on each chart. Use **Reset** to return to the full horizon.

Expand **Open full live Weather GIS** for radar, satellite reference, short-term rain fields, wind arrows, pressure, temperature, cloud, storms, and point forecasts.

## 5. Extreme Weather

The event timeline identifies selected-trajectory periods for typhoon exposure, drought, extreme rain, heat stress, and near-term rain forecasts. Later event dates are scenario-dependent estimates, not exact forecasts. Select a timeline card or chart bar to highlight an event.

## 6. Farm Health and event-linked rehabilitation

Farm Health runs automatically after a Farm Site Forecast and calculates:

- Bayesian pest posterior
- Eight pest-specific outbreak-priority scores
- Agronomic suitability
- Current/projected tree states
- One rehabilitation heatmap for every projected major weather event

Choose an event chip above the map to switch among typhoon, extreme-rain, drought, heat-stress, and other event plans. Each map uses:

- Green - No Damage
- Yellow - Needs inspection
- Red - Needs Rehabilitation

The selected event also shows the predicted event dates, field-assessment date, recommended rehabilitation start, 30-day review, and 90-day review. Click any map zone to inspect its numeric damage score and recommendation. The heatmap is a decision-support estimate based on the entered farm conditions and event severity; it is not a measured post-event damage survey.

A built-in event-specific procedure is available without an API key. Configure CoCO-PILOT in Settings and select **Generate AI recommendation** to obtain a compact procedure tailored to the selected event and current farm context.

The Bayesian and suitability equations are shown alongside their factors. Rehabilitation spatial detail becomes more reliable when measured terrain, drainage, canopy, soil, and field-inspection data are supplied.

## 7. Reports

Run or refresh the full analysis, choose PDF or DOCX, and generate the report. Generate the Farm Site Forecast first to include the weekly outlook, three-product annual series, and extreme events.

## 8. Database

The Database tab lists saved farms, forecasts, analyses, and reports. Forecasts can be loaded back into the interactive timeline.

## 9. Settings

The settings drawer controls:

- Light or dark theme
- Orbit background animation
- Default climate scenario
- Default rehabilitation strategy
- Default run count
- Wind arrows
- Rain opacity
- Timeline playback speed

Settings are stored in the browser on the same computer.

## Weather GIS access

The same Weather GIS viewer appears under Home and in the floating Weather button. Opening the floating window moves the existing viewer into the modal; it does not create a second map. Closing it returns the viewer to Home with its selected place, farm polygon, layer, timeline, and animation state intact.

## Guided farm drawing

Choose **Draw my farm** on Home. COCO-AID highlights the polygon-drawing tool, then the map area, and then the continuation control. Complete the polygon by clicking the first point again.

## CoCO-PILOT

Configure a Gemini API key in Settings, then open the lower-right CoCO-PILOT button. Version 2.4 prefers an automatically selected compatible Flash model and can fall back to the current Flash alias when Google retires an older model identifier. Use a starter prompt or type a concise question. **Attach current context** sends the current farm, selected forecast state, hazards, and health summaries. You may attach the latest saved report or upload a PDF/DOCX. Uploaded document text is sent to Gemini only when you submit a chat message that includes that attachment.
