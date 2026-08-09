# COCO-AID v2.4.0 - the current compatible Flash model and Event Rehabilitation

## Gemini compatibility

- CoCO-PILOT now prefers `gemini-flash-latest`.
- Existing installations that still reference a retired Gemini model automatically retry with `gemini-flash-latest` and then `gemini-flash-latest`.
- The resolved working model is stored locally so later requests avoid a retired identifier.
- API keys remain local, excluded from release archives, and are sent in the `x-goog-api-key` header.

## Event-linked rehabilitation planning

- Farm Health now creates a separate plan for every projected extreme-weather period.
- Each plan includes the event period, field-assessment date, rehabilitation date seven days after event end, 30-day review, and 90-day review.
- Every plan has a smooth event-conditioned heatmap:
  - Green - No Damage
  - Yellow - Needs inspection
  - Red - Needs Rehabilitation
- Typhoon, extreme-rain, drought, and heat-stress maps use different event-footprint equations and farm vulnerability modifiers.
- Moderate loss events now create inspection zones instead of misleading all-green maps.
- The map is a planning surface, not a post-event remote-sensing damage product. Field verification remains required.

## Rehabilitation procedures and CoCO-PILOT

- Built-in hazard-specific procedures appear immediately without an API key.
- **Generate AI recommendation** asks CoCO-PILOT to convert the selected plan into a concise farm-specific work order.
- Recommendations prioritize safety, inspection, sanitation, drainage or moisture management, integrated pest management, local extension consultation, and follow-up monitoring.

## Reports

- PDF and DOCX reports include the event-linked rehabilitation schedule.
- The schedule displays both yellow inspection zones and red rehabilitation zones.
- Baseline current-condition grids are labeled separately from event-linked hazard maps to avoid contradictory interpretation.

## Verification

- 85 automated tests passed.
- Python compilation passed.
- Main and Weather GIS JavaScript syntax checks passed.
- HTML duplicate-ID and JavaScript DOM-reference checks passed.
- CSS parsing passed.
- Model-artifact and installation verification passed.
- A 100-run 2026-2050 release smoke forecast generated 8,931 daily visual frames and 1,276 weekly agricultural control points.
- Multi-event rehabilitation planning, full analysis, PDF report generation, DOCX report generation, and local downloads passed.
- The generated PDF was rendered to images and inspected for clipping and table layout.
