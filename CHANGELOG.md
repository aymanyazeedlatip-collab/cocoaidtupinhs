# COCOAID v3 Phase 11.3.23 — Final Supabase Storage Startup Hotfix

- Fixed Render startup failure when hosted Supabase wraps `NoSuchBucket` as HTTP 400 with `statusCode: 404`.
- Added structured Supabase Storage error parsing rather than relying only on the outer HTTP status.
- First deployment now creates the private `cocoaid-state` bucket automatically for both literal 404 and wrapped `NoSuchBucket` responses.
- Added bucket propagation retry/backoff and upload recovery for short Storage consistency delays.
- Preserved zero-cost Render Free + Supabase Free + Vercel Hobby deployment architecture.

# COCOAID v3 Phase 11.3.7 — Hourly Forecast Calendar + Collision-Safe Map UI

- Standardized the genuine 16-day provider window to hourly Open-Meteo frames in both Long-Term Model Forecast and Weather GIS playback.
- Replaced the visible forecast slider with a month calendar plus hourly provider-frame picker; long-range modeled weather remains daily through 2050.
- Matched Productivity wind rendering to the Weather GIS particle/arrow algorithm and terrain-aware vector handling.
- Enforced a full-viewport Productivity map with liquid-glass floating controls, mutually exclusive drawers, and explicit desktop/tablet/mobile collision lanes.
- Completed browser geometry audits at 1440×900, 1024×768, and 390×844 with no audited control intersections.
- Expanded the verified automated inventory to 323 passing tests.

# COCOAID v3 Phase 11.3.5 — Farmer Wizard + Long-Term Forecast UX

- Enriched the existing Home sections with faded project photography, farmer-facing analytical reference graphics, and transparently labeled development-validation performance benchmarks.
- Converted Farm Profile into a map-first, one-stage-at-a-time wizard while preserving four logical input stages and all backend field contracts.
- Added grouped plain-language input blocks, sequential validation, a locked Start Forecast action until setup completion, and a dedicated Save Farm Shape Changes control during Leaflet edit mode.
- Added the mini coconut-tree hologram and high-contrast orange copy to the loading screen.
- Renamed Productivity to Long-Term Model Forecast, kept the first 16 days explicitly provider-backed, and labeled the remaining path to 2050 as modeled weather.
- Removed farmer-facing Scenario, Strategy, and Runs controls while keeping fixed internal compatibility values.
- Added adaptive farm-boundary framing, compact Rain/Wind/Farm map controls, live frame weather readouts, and periodic stale-forecast refresh while Productivity is open.
- Validated 307 automated tests plus Phase 1–11 and installation verification.

# COCOAID v3 Phase 11.3.3 — Guided Farmer Experience

- Extended Home from a single-screen hero into a full-screen first viewport with scrollable farmer-oriented information sections below it.
- Preserved the Phase 11.3.2 coconut/coconut-tree hologram animation unchanged.
- Made analytical-page background photography cover the complete viewport width while keeping content centered and readable.
- Rebuilt Farm Profile as a numbered four-step guided workflow with plain-language labels, progress guidance, automatic Basic Details → Tree Data advancement, back/continue controls, and farmer-friendly helpers.
- Added simplified tree-condition and soil-condition inputs that populate the existing analytical fields without changing backend contracts.
- Added large Polygon, Square, and Edit farm-map controls with explicit drawing instructions.
- Added post-draw focus mode that darkens and desaturates the basemap while highlighting the completed farm boundary in orange.
- Reset scroll position when switching workspace tabs so users always land at the top of the selected page.
- Preserved every existing Farm Profile backend field ID and API contract.
- Validated 288 automated tests plus Phase 1–11 and general installation verification.

# COCOAID v3 Phase 11

- Rebuilt the interface with solid white official agri-tech styling and logo-derived colors.
- Added full-screen interactive coconut holograms with scan and user rotation controls.
- Added Weather GIS and Decision Network navigation pages.
- Added chart zoom, reset, PNG, CSV, and full-screen controls.
- Preserved music and voice-line assets through checksum verification.
- Updated DOCX/PDF formal reports to official Times New Roman presentation.
- Added Phase 11 status API, documentation, manifests, and tests.
- Expanded the complete inventory to 269 passing tests across 86 test files.

# COCOAID v3 Phase 10

- Added Migration 10 for CoCO-PILOT narratives and formal report records.
- Added deterministic grounded explanation modes with citations and recursive PII redaction.
- Added optional validated Google AI rewriting with deterministic fallback.
- Added versioned DOCX and PDF report generation with SHA-256 checksums and content fingerprints.
- Added eight Phase 10 API endpoints and `run_phase10_workflow.bat`.
- Expanded the suite to 259 passing tests across 84 test files.


## v3.0 Phase 9

- Added migration 9 and the executable `v3.decision_support` engine.
- Added dependency validation across production, Bayesian, pest, intercropping, and rehabilitation records.
- Added complete, partial, and strict failure policies without fabricated fallback outputs.
- Added persistent evidence-linked recommendations, consolidated overview, and traceability edges.
- Added Phase 9 status, compose, listing, and retrieval APIs.
- Added `run_phase9_workflow.bat` to avoid manual JSON editing during verification.
- Added Phase 9 manifests, verification, documentation, and 252-test release validation.

# COCOAID v3 Phase 7 - Intercropping Potential Engine

- Added migration 7 for requirement profiles, assessment runs, cell-candidate assessments, and decomposed component scores.
- Added executable `v3.intercropping` version `1.0.0`.
- Added 35 versioned crop requirement profiles and preserved 81 PCA canopy-light records.
- Added palm-age interpolation, spacing/design matching, bounded canopy adjustments, and traceable light estimates.
- Added nine-component weighted geometric suitability scoring with hard light and slope constraints.
- Added coconut competition, optional Phase 6 pest conflict, and ecological-benefit adjustments.
- Added sanitized cacao and coffee gross-revenue scenarios without profit or ROI claims.
- Added `/api/v2/intercropping/*` endpoints, Phase 7 manifests, documentation, verification, and exact Windows setup instructions.
- Expanded the automated suite to 231 passing tests across 69 fully isolated test-file processes.

# Changelog

## COCOAID v3 Phase 5

- Added the `v3.bayesian` experimental particle-filter engine.
- Added migration 5 for Bayesian evidence, runs, posteriors, parameters, and assimilation audits.
- Added seeded seven-state palm and soil-state propagation with planting-position conservation.
- Added reliability-gated evidence and sequential posterior updates.
- Added posterior production intervals and decline, recovery, mortality, and outbreak probabilities.
- Linked successful posterior runs to the Phase 4 production record without retraining the ML model.
- Added a complete isolated-batch test runner and Phase 5 release verification.

## COCOAID v3 Phase 4

- Added production migration, feature adapter, engine, persistence, APIs, and validation.
- Preserved the retained model artifact without retraining.
- Added PCA named-variety adjustment and product conversions.
- Added actual-versus-predicted monitoring and v2.11 shadow comparison.
- Integrated the PCA Region XII income workbook as restricted-source sanitized aggregates.
- Increased the regression suite to 185 tests.

# Version 3.0 Phase 3 - Weather Assimilation

### Weather data boundary

- Added a strict current-plus-16-day live forecast limit across point, grid, cube, and normalized weather responses.
- Expanded agricultural provider variables with VPD, ET0, soil moisture, solar radiation, humidity, pressure, and gust fields.
- Kept dates beyond Day 16 inside the separately labeled climate-conditioned farm simulation.

### Versioning and feature engineering

- Added migration 3 with normalized weather runs, values, feature sets, and feature derivations.
- Added deterministic payload hashing, run deduplication, history/current/forecast classification, and versioned run comparison.
- Added `weather-features-1.0.0` for rainfall, moisture balance, dry-day, heat, gust, radiation, humidity, VPD, and soil-moisture features.
- Marked Forecast API past-day values as reference-only rather than measured observations.

### Reliability and interfaces

- Added memory/disk cache disclosure, offline-cache metadata, HTTP 429 cooldown, and stale fallback without fabricated weather.
- Added executable `v3.weather_assimilation` engine and `/api/v2/weather/*` endpoints.
- Added Phase 3 documentation, manifests, verification, and 169 passing tests with warnings treated as errors.

# COCOAID v3 Phase 2 - Data Foundation

- Added HTTPX2 as the supported Starlette TestClient transport and made warnings fail the test suite.
- Added migration 2 with normalized PCA reference and restricted farmer-registry tables.
- Added checksum-verified source and parameter catalogs.
- Added 30 varieties, 408 variety parameters, five pest/disease profiles, 35 intercrops, 81 canopy-light values, and two fertilization scenarios.
- Added a streaming XLSX importer with PII separation, quarantine, validation flags, and duplicate detection.
- Added database backup/restore tooling and privacy-safe data-foundation APIs.
- Expanded the automated suite from 135 to 146 tests.

# COCOAID v3 Rehaul Changelog

## Phase 1 - Core Architecture and Data Contracts

- Added 17 strict canonical v3 contracts with stable JSON Schema hashes.
- Added canonical units, explicit conversions, source provenance, and run lineage.
- Added shared analytical engine interface and legacy/planned engine catalog.
- Added immutable parameter-set registry with content hashes.
- Extended model registry with artifact SHA-256, feature order, model cards, and runtime compatibility.
- Pinned `scikit-learn==1.9.0` to match preserved model serialization.
- Added `/api/v2` health, contracts, validation, engines, models, parameters, units, and migration endpoints.
- Added structured application errors, request IDs, and processing-time headers.
- Added versioned and checksummed SQLite migration infrastructure.
- Preserved every v2.11 route and frontend workflow.
- Expanded the automated suite from 111 to 135 passing tests.

## v2.11.0

- Fixed navigation labels being clipped to icon width.
- Added smooth animated sidebar collapse and expansion.
- Added responsive coconut-farm background refitting during sidebar transitions.
- Added post-transition map resize handling.

## v2.10.0

- Converted the pre-entry preview to a light visual theme while preserving its technology animations.
- Moved best-effort background-music startup to the preview screen and added a preview-interaction fallback for browser autoplay restrictions.
- Fixed the music level at 10% and removed voice-based music ducking.
- Added a desktop collapse/open control for the primary navigation sidebar.
- Removed the navigation-brand subtext and Settings voice line.
- Made the Settings drawer independently scrollable with contained wheel and touch behavior.

## v2.9.0

- Added an animated pre-entry preview portal with a user-gesture website entrance.
- Added bundled background music and personal-agent voice lines for every main section, Settings, Weather GIS, and forecast completion.
- Added independent music and voice toggles plus volume controls in Settings.
- Extended the faded coconut-farm background across all application tabs.
- Changed the sidebar descriptor from Agri-climate intelligence to Cocon.

## v2.9.0

- Added wraparound left/right navigation for the Extreme Weather event timeline.
- Reduced the loading screen to a minimalist logo ring and rotating farm tips.
- Fixed Farm Health priority-cell typography and containment.
- Added a twelve-equation formula catalogue to About.
- Added one-time automatic climate-map fitting to the user-drawn farm boundary.

## v2.6.0

- Added a layout-preserving liquid-glass visual system to the main application and Weather GIS.
- Added controlled backdrop blur, translucent refraction layers, illuminated inner borders, dark smoked-glass surfaces, and unsupported-browser fallbacks.
- Fixed Pest-specific outbreak section overflow and alignment for the heading, highest-score card, empty state, and generated pest cards.
- Integrated the supplied official Weather GIS and CoCO-PILOT icons into the floating tools, modal/header identities, and Weather GIS favicon.
- Preserved the v2.5 analytical, forecasting, rehabilitation, report, database, and assistant behavior.

## v2.5.0

- Added final saturated agri-tech UI overhaul.
- Integrated supplied COCO-AID wordmark, logo, favicon, and coconut-farm landing background.
- Added branded loading screen with animated circular progress, slowly rotating logo, progress sweep, and rotating tips.
- Added complete About page with researcher and school credits.
- Enriched chart colors and aligned the embedded Weather GIS visual identity.
- Preserved existing simulation, farm health, event rehabilitation, reports, database, and CoCO-PILOT behavior.

# Changelog

## Version 2.2.1 - Forecast validation and terrain-aware wind arrows

- Fixed repeated `422 Unprocessable Content` responses from `/api/farm-site/forecast`.
- Added readable validation-error responses and client-side input normalization.
- Restored support for 5,000-run legacy settings and added duplicate-request protection.
- Added directional wind-arrow rendering to the farm outlook and Weather GIS.
- Added elevation-grid terrain deflection to the live Weather GIS flow field.
- Added local farm elevation/slope deflection to the long-term outlook visualization.
- Added regression coverage for the 422 bug, legacy settings, elevation transport, and wind-arrow contracts.

## Version 2.2.0 - Daily motion, Weather GIS interpolation, and pest photo update

- Added daily visual frames and one-week-per-second playback through 2050.
- Added climate-projection wind particles and focused factor charts.
- Generalized Weather GIS interpolation to every forecast layer and repaired wind visibility.
- Added distinct normalized product trajectories backed by weather-responsive Mature and Young equations.
- Added real field pest photographs, attribution, and 3D recommendation-card flips.
- Removed numbered report Section 11 while retaining provenance as a subsection under the final numbered section.
- Added v2.2 regression tests and installation checks.

## Version 2.1.0 - Smooth weather, product differentiation, and pest-health overhaul

### Forecast visualization

- Replaced visible climate-grid blocks with a 44 x 44 generated/model grid rendered into a 320 x 240 bilinearly interpolated image surface.
- Added smoothstep interpolation, blur, and restrained saturation so rainfall appears as a continuous blue-yellow-red weather-report heat field rather than map squares.
- Kept fixed physical rain-intensity thresholds and transparent no-rain pixels.

### Production mathematics and hazards

- Added separate Mature and Young weather-response factors for moisture adequacy, humidity, heat, wind, pest pressure, excess rain, farm condition, and event severity.
- Preserved the identity Coconut with husk = Coconut Mature + Coconut Young for every weekly and annual record.
- Reworked hazard losses around event type, peak and mean severity, duration, baseline weekly production, and modeled deficit.
- Added date-highlighted hazard rail, explicit severity and estimated-loss axes, loss fraction, and affected-tree inspection estimates.

### Farm health and reports

- Added automatically generated Bayesian-pest, land-suitability, and farm-condition donut charts.
- Added eight illustrated pest-specific outbreak-priority cards with 0-100 scores, climate/vulnerability/symptom drivers, formulas, and IPM-oriented recommendations.
- Farm health now runs automatically after Farm Site Forecast.
- Rebuilt PDF and DOCX reports with formal black text, Times New Roman document styling, corrected numerical formatting, critical-weather heatmap snapshots, pest-specific tables, product-response equations, and updated hazard fields.

### Verification

- Added regression tests for pest scores, weather-responsive product shares, hazard severity/loss consistency, smooth-heatmap UI contracts, automatic farm-health execution, report sections, embedded report images, and Times New Roman DOCX styles.
- 64 automated tests pass.

## Version 2.0.0 - Official PSA data and agri-tech workflow overhaul

### Official data

- Added the uploaded PSA table `2E4EVCP1` covering three coconut product groups, 2010-2026, for all listed provinces.
- Added tidy, annual, province-profile, and source-metadata files with per-cell provenance.
- Uses official completed annual records through 2025 and labels 2026/gap estimates separately.
- Calibrates mature/young production shares and seasonal allocation from the selected province, with region/national fallback.

### User experience and interface

- Rebuilt the application as a guided landing -> farm setup -> forecast -> hazards -> health -> reports -> database workflow.
- Added a clean agri-tech visual system, orbit background, light/dark theme, responsive navigation, restrained transitions, and a dedicated settings drawer.
- Restyled the embedded Weather GIS to match the main website.
- Added interactive zoom/pan/reset behavior to analytical charts and synchronized date markers across forecast charts.

### Forecasting and visualization

- Changed the farm outlook to weekly resolution through 2050.
- Added three production series: Coconut (w/ husk), Coconut Mature, and Coconut Young.
- Added rainfall, mean/max temperature, humidity, cloud, wind, pressure, farm condition, pest probability, official history, hazards, and tree-state graphs.
- Fixed cross-year weekly aggregation by deriving annual product totals from daily allocations.
- Added partial-year coverage labels and scaled uncertainty intervals for the selected start year.
- Made displayed Mature + Young production exactly conserve the displayed Coconut (w/ husk) total after rounding.
- Added a TV-style farm forecast map with rain-intensity field, wind particles, farm status, and synchronized timeline.

### Hazards, health, reports, and storage

- Added an extreme-weather event timeline with estimated production loss and trees requiring inspection.
- Consolidated Bayesian pest, suitability mathematics, tree states, and rehabilitation mapping in Farm Health.
- Added saved weekly forecasts and database browsing.
- Added DOCX export and expanded PDF/DOCX reports with official production, weekly outlook, three-product annual series, and extreme events.

### Reliability

- Added official-data, forecast-conservation, database-forecast, DOCX, supplemental-report, and new UI-contract tests.
- Retained explicit distinctions among official records, preliminary/estimated gaps, short-term forecasts, and long-term projections.

## Version 1.1.0 - Weather GIS and farm-site forecast integration

### Live Weather integration

- Embedded the complete Weather GIS v1.3 interface in the COCO-AID Live Weather section.
- Replaced visible coarse rectangles with a smooth transparent → blue → deep-blue → yellow → red rain-intensity field.
- Preserved radar, satellite reference, temperature, cloud, pressure-contour, wind-particle, storm, geocoding, point-forecast, timeline, opacity, and source-status tools.
- Added automatic farm polygon and coordinate synchronization to the weather viewer.
- Added compatibility API routes for the embedded standalone viewer without duplicating provider requests.
- Reused one cached 6×6 multi-variable forecast cube instead of refetching each layer.

### Hybrid daily outlook through 2050

- Added `POST /api/farm-site/forecast`.
- Uses current deterministic provider forecast grids for the available short-term dates when online.
- Switches visibly and explicitly to a climate-conditioned stochastic weather path after the numerical forecast horizon.
- Generates one selectable daily frame from the requested start date through December 31, 2050.
- Connects the weather trajectory to the existing Bayesian pest, seven-state farm, production, intervention, and Monte Carlo models.
- Displays a TV-style map, farm-condition polygon, wind particles, date timeline, daily rain, temperature, cloud, wind, pest probability, daily production equivalent, cumulative production, tree-state distribution, and annual production path.
- Uses actual provider precipitation-grid geometry for short-term merged dates and smooth generated spatial fields for later simulated dates.
- Makes the simulated field intersect the farm whenever the farm's generated rainfall is positive, preventing disagreement between map appearance and farm metrics.
- Starts at the selected date rather than displaying already elapsed dates from January 1.
- Adds short-term versus simulated data-mode badges and source metadata.

### Reliability and performance

- Limited OpenBLAS, MKL, OpenMP, NumExpr, and Accelerate thread counts before NumPy/scikit-learn import. This fixed severe oversubscription that could make small simulations appear frozen.
- Added sample-path state counts to Monte Carlo output so the displayed daily farm state follows the same sampled trajectory rather than posterior mean states.
- Added tests for forecast-cube aggregation, date boundaries, mode switching, embedded viewer delivery, spatial grids, and scientific labels.


## Version 1.0.0 - audited release

### Correctness fixes

- Fixed a production-model normalization error that could make a more infested farm outperform an otherwise identical healthier farm.
- Replaced self-normalized tree health/capacity factors with explicit reference-state assumptions.
- Standardized the default rehabilitation threshold at 85% of baseline production plus a healthy/recovering-state requirement.
- Recovery year now requires a sustained three-year recovery and is reported only for paths still recovered at the horizon.
- Added annualized weather-loss rate and mean affected years beside cumulative horizon probability.
- Made climate sample mode reproducible across Python processes with SHA-256 seeding.
- Applied lower/upper climate uncertainty to mean, minimum, and maximum temperature consistently.
- Removed unsupported SSP-driven typhoon-frequency changes and fixed latitude handling.
- Added distance-to-reference disclosure for compact climate projections.
- Fixed polygon ray-casting that could exclude every rehabilitation cell.
- Fixed polygonless rehabilitation bounds that previously represented substantially more area than entered.
- Removed fabricated sinusoidal within-farm differences; cells now explicitly report a uniform baseline when no measured raster exists.
- Added proper polygon centroid, drawn-area discrepancy, yield consistency, and density checks.
- Included requested variable names in weather-grid cache keys.
- Added persistent point-weather caching and bounded weather-grid lock cleanup.
- Restricted static-file fallback to the actual static directory.
- Rejected invalid one- or two-vertex farm polygons.

### Performance and reliability

- Vectorized annual Monte Carlo state transitions and production calculations.
- Reused one prepared model/context object across scenario comparisons.
- Reduced comparison payload size by returning one complete recommended simulation rather than six duplicate full trajectories.
- Added model-artifact compatibility checking and automatic development-model retraining during setup.
- Added single-thread numerical-library settings to batch files for predictable laptop performance.
- Improved launcher port checking and browser-open health waiting.

### Interface and reporting

- Removed the fabricated demonstration chart displayed before any analysis ran.
- Updated the frontend for the compact scenario-comparison response.
- Added saved-farm load/delete controls and management inputs.
- Added current-location selection, animated radar frames, active-storm markers, and pressure contours.
- Added clearer cumulative-versus-annualized weather-risk interpretation.
- Added climate-reference distance warnings and farm-input validation findings.
- Restored saved farm polygons when loading profiles.
- Improved rehabilitation-map transparency and outside-polygon filtering status.
- Escaped user-entered text in PDF reports and added scenario, trajectory, spatial, reproducibility, and limitation sections.

## Version 2.3.0 - Weather popup, guided drawing, and CoCO-PILOT

### Weather and long-term projection

- Removed wind visualization from the long-term climate-conditioned projection.
- Changed playback to one second per two simulated days.
- Removed Weather GIS from the tab navigation.
- Added one shared Weather GIS iframe that moves between the Home section and a large floating modal, preserving all map state.

### User experience

- Added a three-step farm-drawing coachmark tutorial.
- Improved rehabilitation-map default framing.
- Removed redundant workspace heading copy.
- Updated the coconut black-headed caterpillar image to a close-up field photograph with attribution and an offline fallback.

### CoCO-PILOT

- Added optional Gemini-powered coconut-farming chat.
- Added local API-key configuration and deletion.
- Added compact assistant formatting, typewriter animation, one-click prompt templates, contextual website data, saved-report reading, PDF/DOCX upload, and percentage donut cards.
- Added document extraction limits and local secret/cache exclusions.

### Reporting

- Added a formal farm-location and boundary-shape figure near the beginning of PDF reports.

### Verification

- Added release tests for playback, absence of long-term wind, shared Weather GIS state, draw tutorial, rehabilitation framing, Gemini configuration, mocked chat, document extraction, and the farm-location report section.
- Fixed SQLite connection lifecycle so every transaction closes its connection, eliminating resource-leak warnings during sustained analytical workloads and tests.

## 2.4.0

- Updated CoCO-PILOT to an automatically selected compatible Flash model with automatic model fallback.
- Added event-specific rehabilitation plans and smooth green-yellow-red heatmaps.
- Added inspection, rehabilitation, and follow-up dates for every projected hazard.
- Added built-in and Gemini-generated rehabilitation procedures.
- Added rehabilitation schedules to report supplements, including yellow inspection and red rehabilitation zone counts.
- Calibrated moderate event maps to avoid misleading all-green output when a documented loss requires inspection.
- Expanded the test suite to 85 tests.


## v2.4.1

- Removed explicit 3.5 model references and switched CoCO-PILOT to automatic compatible Flash-model selection.
- Added retries and clear handling for provider timeouts, 5xx responses, rejected keys, unavailable models, and unreadable responses.
- Increased answer capacity and added one automatic continuation when the provider reports a token-length stop.
- Added a three-dot animated answering indicator.
- Added previous and next rehabilitation-event arrows with wraparound date navigation.


## Phase 6: Pest-Risk Inference

The PCA-backed `v3.pest_inference` engine is available with five profiles, status-controlled evidence, spatial pressure, conditional/expected loss separation, and migration 6. See `docs/phase_6/`.

## Phase 6.2: Windows setup path hotfix

- Replaced the repository-local Windows `.venv` with a short versioned environment under LocalAppData.
- Added shared environment activation for every supplied batch launcher.
- Added automatic removal and recreation of unusable partial environments.
- Preinstalls and verifies a binary `lxml` wheel before the remaining requirements.
- Disables pip caching during setup to avoid reuse of partial extractions.
- Ships a flat ZIP layout to prevent duplicate nested extraction folders.
- Added setup-path regression tests and exact recovery documentation.


## v3.0 Phase 8

- Added migration 8 and `v3.rehabilitation` 1.0.0.
- Added evidence-linked triggers and actions with cost, labor, timing, recovery ranges, and confirmation requirements.
- Added mandatory no-action, pest, fertility, replanting, intercropping, and combined scenarios.
- Added budget/labor feasibility and comparative expected utility.
- Added Phase 8 APIs, manifests, verification, tests, and documentation.

## v3.0 Phase 8.1

- Added exact line/column diagnostics for malformed JSON requests without echoing request bodies.
- Added a one-click Phase 8 resume workflow that eliminates manual JSON editing from pest assessment onward.
- Added Phase 8.1 verification and regression tests.

## 2026-08-06 — Phase 11.2.1 Entry Page Carousel

- Removed the entry-page wordmark and changed the primary heading to **Welcome to COCO-AID**.
- Added a seven-image looping cross-fade background carousel using the user-provided coconut farm and farmer photographs.
- Added a faint green-to-orange overlay, four centered orbital animations, and a restrained carousel progress line.
- Kept the coconut hologram exclusive to the Home page.
- Preserved all analytical engines, audio files, reports, migrations, and API contracts.
- Verified all 272 automated tests, Phase 3–11 setup verification scripts, static asset delivery, JavaScript syntax, and duplicate-ID safety.

## Phase 11.3.4
- Evidence-rich Home sections, grouped Farm Profile inputs, and dedicated boundary-edit save control.

## Phase 11.3.23 Zero-Cost Deployment Hotfix

- Replaced paid Render Standard + disk deployment with Render Free.
- Added private Supabase Storage synchronization for SQLite state, reports, and assistant document extracts.
- Added automatic restore on Render cold starts.
- Preserved automatic Phase 9/10 orchestration with no manual IDs.
- Added zero-cost deployment verifier and deployment regression tests.
- Validated 408 automated tests plus the full Phase 3–11 verifier chain.
