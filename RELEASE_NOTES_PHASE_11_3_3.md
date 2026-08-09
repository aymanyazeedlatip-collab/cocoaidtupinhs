# COCOAID Phase 11.3.3

## Scrollable Home and guided Farm Profile

### Home

- Kept the first Home section at full viewport height and preserved the Phase 11.3.2 hologram animation unchanged.
- Added scrollable sections explaining the farmer workflow, decision-support outputs, evidence safeguards, and a direct call to begin Farm Profile.
- Added automatic scroll reset when switching workspace tabs.

### Full-bleed analytical pages

- Removed the side gaps around faded background photography on non-Home tabs.
- Background images now cover the complete viewport while analytical content remains centered within a readable maximum width.

### Farm Profile

- Reorganized the form into four numbered farmer-facing steps: Basic Details, Tree Data, Soil & Care, and Tree Health.
- Preserved all existing field IDs and analytical contracts.
- Added a sticky progress guide with simple instructions and contextual next actions.
- Added automatic progression from Basic Details to Tree Data after the key identity fields are completed by the farmer.
- Added explicit back and continue controls for predictable navigation.
- Added a tree-condition helper that estimates the existing tree-state fields and remains editable afterward.
- Added simple slope, fertility, and drainage choices that populate the existing numeric analytical fields.

### Farm boundary map

- Added large, labeled **Draw a Polygon**, **Draw a Square**, and **Edit Shape** controls connected to the existing Leaflet Draw toolbar.
- Added live farmer-facing instructions before and after drawing.
- After a valid farm boundary is completed, the basemap transitions to grayscale and darker brightness while the selected farm boundary remains highlighted with a thick orange outline and translucent orange fill.

### Compatibility and verification

- No API, model, database-migration, report, or analytical-engine contract was intentionally changed.
- Interface version is `phase11-agritech-interface-1.3.3`.
- Frontend assets are cache-busted with `v=11.3.3`.
- 288 automated tests pass: 225 unit, 54 integration, and 9 mathematical tests.
- Phase 1 through Phase 11 verification and the general installation verifier pass.
