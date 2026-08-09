# Phase 11 Current State

- Active interface version: `phase11-agritech-interface-1.3.3`.
- Home uses a full-screen first viewport followed by scrollable farmer-oriented explanation and action sections.
- The alternating coconut-fruit/coconut-tree hologram from Phase 11.3.2 is preserved.
- Analytical pages use edge-to-edge background photography with centered readable content.
- Farm Profile is a numbered, guided four-step workflow with automatic progression and simplified helper controls.
- Farm boundary drawing has explicit Polygon/Square controls and an orange focus mode over a darkened basemap after completion.
- All pre-existing Farm Profile backend field IDs and API contracts remain intact.
- Existing music and voice-line assets remain checksum-preserved.
- Formal DOCX/PDF reports use the official Times New Roman presentation.
- 288 automated tests pass: 225 unit, 54 integration, and 9 mathematical tests.
- Next planned work is continued Phase 11 UI refinement before Phase 12 validation and calibration.

---

# Current project state — Phase 11 complete

The active development baseline is the Phase 11 official agri-tech interface. Phases 0–10 analytical and data layers remain unchanged and accessible. The next planned phase is scientific validation, calibration, and release hardening.

## v3.0 Phase 10

- `v3.coco_pilot` grounded explanation service is available.
- Formal DOCX and PDF report generation is available.
- Current contract version: `3.0.0-draft.10`.
- Current migration head: 10.
- Next planned phase: Phase 11 interface and user-experience rebuild.

---

# COCOAID v3 Rehaul State

Contract version: 3.0.0-draft.10
Completed phase: Phase 9, Integrated Decision-Support Network
Legacy runtime: COCO-AID v2.11.0 remains active and regression-tested

Phase 9 adds a versioned integration engine that validates linked outputs from production, Bayesian, pest, intercropping, and rehabilitation modules; discloses partial failures; and persists evidence-linked recommendations without mutating source analyses.
Next phase: Phase 10, CoCO-PILOT and formal report generation

Phase 7 adds migration 7 and the executable `v3.intercropping` engine. It combines PCA canopy-light parameters, versioned crop requirements, farm-cell context, weather-linked water conditions, optional Phase 6 pest compatibility, and sanitized cacao/coffee economic aggregates. The result remains a transparent evidence-based suitability assessment rather than a field-validated supervised machine-learning model.

---

# COCO-AID Project State

Version: 2.11.0
Calculation version: coco-aid-math-2.4.1
Parameter version: psa-calibrated-parameters-2.4.1
Status: Audited research prototype with a layout-preserving liquid-glass interface, compatible assistant fallback, and event-linked rehabilitation planning

## Completed

- Light-theme pre-entry technological preview page with best-effort immediate background music and user-interaction fallback
- Bundled looping background music fixed at 10% plus personal-agent voice lines for working tabs, Weather GIS, and forecast completion
- Independent music and narration toggles, fixed 10% music level, and adjustable narration volume
- Coconut-farm photographic background treatment across every tab
- Collapsible desktop navigation sidebar with persistent local preference
- Independently scrollable Settings drawer with contained wheel and touch interaction
- Liquid-glass light/dark interface with browser fallbacks and reduced-motion support
- Official Weather GIS and CoCO-PILOT icon integration
- Pest-specific outbreak panel overflow and alignment repair
- Official PSA coconut production data processed into tidy, annual, metadata, and province-profile files
- Three weather-responsive product series for Coconut (w/ husk), Coconut Mature, and Coconut Young
- Farm drawing, guided coachmarks, area/centroid calculation, farm persistence, and profile restoration
- Daily long-term climate-conditioned map frames through 2050 linked to weekly agricultural control points
- Long-term playback set to one second for two simulated days
- One shared Weather GIS iframe synchronized between Home and a large floating modal
- Live weather layers, radar, satellite reference, storm information, point weather, interpolation, and provider caching
- Extreme-weather timeline with date ranges, severity, duration, and estimated impact
- Bayesian pest posterior, eight pest-specific assessments, land suitability, and farm-condition scoring
- Separate green/yellow/red rehabilitation heatmaps generated for every projected damaging weather event
- Event-linked inspection, rehabilitation, 30-day review, and 90-day review dates
- Hazard-specific rehabilitation procedures for typhoon, extreme rain, drought, heat stress, and other events
- CoCO-PILOT automatic compatible Flash-model support with automatic fallback to the current Flash alias
- CoCO-PILOT event-plan context and AI rehabilitation recommendation generation
- PDF and DOCX report sections for event-linked rehabilitation schedules
- Floating CoCO-PILOT assistant with local Gemini API key configuration
- SQLite farms, forecasts, analyses, and report records
- Automated mathematical, data, model, API, report, UI-contract, assistant, provider, and security tests

## Data status

- PSA completed values are retained as official source observations.
- Preliminary or unavailable source periods remain marked separately in processed provenance.
- Long-term weather is a plausible climate-conditioned scenario, not an exact daily forecast.
- Rehabilitation heatmaps are model-estimated inspection priorities, not post-event remote-sensing damage maps.
- Individual-farm agricultural and rehabilitation models still require field validation.
- CoCO-PILOT only sends context or attached extracted document text when the user submits a chat request.

## Online dependencies

- OpenStreetMap/Leaflet resources and map tiles
- Open-Meteo, RainViewer, NASA GIBS, and supplemental storm providers
- External pest photographs, with bundled local fallbacks
- Gemini API for CoCO-PILOT

Core farm setup, Bayesian calculations, long-term simulation, scenario comparison, rehabilitation planning, local database, and reports remain available without live providers.

## Remaining research work

- Validate transitions, product-response equations, pest likelihood ratios, and intervention effects with longitudinal farms
- Calibrate event-specific rehabilitation thresholds with post-event field surveys
- Ingest farm-relevant NEX-GDDP-CMIP6 or WorldClim data
- Add measured within-farm terrain, soil, canopy, drainage, and pest rasters
- Validate probability calibration on independent locations
- Evaluate CoCO-PILOT procedures with coconut pathologists, agriculturists, and extension specialists

## Release verification target

- Python source compilation
- Main and Weather GIS JavaScript syntax validation
- No duplicate HTML IDs or missing required DOM references
- Installation verification and model-artifact loading
- Full automated test suite
- Forecast, rehabilitation-plan, and report API smoke tests
- PDF report rendered and visually inspected
- ZIP extracted and retested before delivery
- No API keys, virtual environment, Python caches, generated reports, or transient database records in the release archive

- Sidebar labels now retain full width in expanded mode and transition cleanly into the compact icon rail.
- Page photography reflows with the content viewport after navigation resizing.


## Phase 3 completion summary

- Migration 3 adds immutable weather runs, long-form values, feature sets, and feature derivations.
- Live point and map weather are bounded to current conditions and no more than 16 days.
- Open-Meteo agricultural variables now include VPD, ET0, soil moisture, and solar radiation where supplied.
- Historical provider values are retained only for reference-labeled lagged feature engineering.
- The executable `v3.weather_assimilation` engine produces versioned feature sets.
- New APIs expose status, assimilation, stored runs, features, and run comparison.
- Offline and stale cache use is explicit; no synthetic live-weather fallback is introduced.
- 169 automated tests pass with warnings treated as errors.


## Phase 4 completion summary

- Migration 4 adds normalized production and intercropping-economic tables.
- The retained production model is executed through `production-feature-adapter-1.0.0`.
- Every model input payload is versioned and hashed.
- Named PCA varieties resolve their true Tall, Dwarf, or Hybrid class before prediction.
- Raw ML, variety-adjusted, and future Bayesian layers are never conflated.
- PCA component references generate traceable product conversions.
- Actual production can be linked for exact product-and-unit performance monitoring.
- The Region XII income workbook contributes sanitized cacao and coffee scenario priors only.
- 185 automated tests pass with warnings treated as errors.


## Phase 5 completion summary

- Migration 5 stores evidence observations, runs, posteriors, parameter summaries, and evidence-assimilation audits.
- `v3.bayesian` propagates seven palm states plus soil-fertility and soil-water indices.
- The simulator supports 100–5,000 particles and deterministic random seeds.
- Predicted and suspected records are stored but never used as Bayesian evidence.
- Farmer-reported, field-confirmed, and expert-confirmed evidence use explicit reliability weights.
- Sequential runs can carry state and moment-matched parameter posteriors forward.
- Successful runs populate the linked Phase 4 posterior layer without retraining the ML model.
- 197 automated tests pass with warnings treated as errors.


## Phase 6 completion summary

- Migration 6 stores pest observations, assessment runs, profile assessments, evidence contributions, and source-linked actions.
- `v3.pest_inference` version `1.0.0` is available and experimental.
- Five PCA profiles are supported: bud and nut rot, coconut leaf beetle, rhinoceros beetle, Asiatic palm weevil, and coconut scale insect.
- Predicted and suspected evidence is stored but cannot alter outbreak probability.
- Field prevalence can create a linked Phase 5 Bayesian observation.
- Spatial pressure decays with distance from confirmed cases.
- Conditional loss and expected loss are calculated and stored separately.
- Asiatic palm weevil remains separate from the legacy red palm weevil profile.
- 210 automated tests pass across 62 fully isolated test-file processes.

## Phase 6.2 setup reliability hotfix

Windows installation now resolves a short external environment under LocalAppData, records it in `.cocoaid_venv_path`, and shares that environment across all batch launchers. The change prevents deep `lxml` resource paths from exceeding legacy Windows path limits even when the source project is extracted into a long folder. The analytical contract remains `3.0.0-draft.6`; no scientific model behavior changed.


## Phase 7 completion summary

- Migration 7 stores intercropping requirement profiles, assessment runs, candidate-by-cell assessments, and component scores.
- `v3.intercropping` version `1.0.0` is available and experimental.
- Thirty-five crop profiles and eighty-one PCA canopy-light records are versioned and provenance-linked.
- Nine decomposable suitability components feed a weighted geometric score.
- Light and slope hard constraints cap unsuitable candidates so favorable secondary factors cannot hide a critical failure.
- Coconut competition, pest conflicts, and ecological benefits remain separate and inspectable.
- Sanitized cacao and coffee data support gross-revenue ranges only; profit and ROI are not claimed.
- Every result records limiting factors, confidence, data quality, source parameters, planting windows, and layout guidance.
- 231 automated tests pass across 69 fully isolated test-file processes.


## Phase 8 completion summary

- Migration 8 stores rehabilitation plans, evidence-linked actions, and all six scenario results.
- `v3.rehabilitation` version `1.0.0` is available and experimental.
- `no_action` is mandatory and remains feasible under zero budget.
- Predicted hazards and inferred pest risks cannot be treated as confirmed damage or automatic treatment.
- Costs, labor, schedules, recovery ranges, feasibility, and utility components are persisted and traceable.
- Production, Bayesian, pest, intercropping, and weather outputs are consumed through versioned links.

## Phase 11.2.1 Entry Page State

The active entry page now uses a fullscreen seven-image background carousel with cross-fade transitions, a subtle green-to-orange overlay, and centered orbital animations. The entry page has no COCOAID type logo and displays the exact heading `Welcome to COCO-AID`. The coconut hologram remains restricted to the Home page. Interface version: `phase11-agritech-interface-1.2.1`.

## Phase 11.3 Home Landing State

The Home tab is now a single full-screen, full-bleed coconut-farm landing page. The global navigation remains off-canvas and is hidden during the opening carousel; it appears only as a compact Menu control after entry and opens only when selected. The Home hero displays `Plant Sharper, Harvest Better`, uses a simplified two-action farmer workflow, and removes the previous white hologram card. The original three orbit rings and their animation definitions remain preserved. The coconut body is now rendered as an interactive parametric 3D wireframe mesh with perspective projection, coconut tapering and ridges, a stem, and three eye points. Interface version: `phase11-agritech-interface-1.3.0`.


## Phase 11.3.1 Home Hotfix State

The Home hologram is annotation-free and uses a high-contrast white parametric mesh. Its three original orbit rings retain their animation and are now white. The Menu control is positioned on the left and follows the sidebar edge. Navigation cycles from closed to expanded, then to a 78-pixel icon-only state, while outside page clicks remain functional because the blocking backdrop has been disabled. Interface version: `phase11-agritech-interface-1.3.2`.


## Phase 11.3.3 Guided Home and Farm Profile State

The Home tab now keeps its first visual section at one full viewport while allowing natural scrolling into workflow, decision-support, evidence, and call-to-action sections. Non-Home pages use full-bleed background photography without the previous side gaps. Farm Profile now guides farmers through Basic Details, Tree Data, Soil & Care, and Tree Health with numbered instructions, plain-language helpers, automatic progression, and explicit map drawing controls. Completed boundaries trigger a focused visual state: the basemap desaturates and darkens while the farm polygon remains highlighted in orange. The analytical DOM IDs and backend contracts are preserved. Interface version: `phase11-agritech-interface-1.3.3`.
