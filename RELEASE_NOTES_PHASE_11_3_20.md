# COCOAID Phase 11.3.20

## Intercropping performance
- Cached farm-shape scene layout instead of rebuilding geometry on every animation frame.
- Reused depth ordering between frames and reduced idle redraw cadence.
- Reduced canvas pixel-density overhead and eliminated per-plant shadow blur.
- Preserved broad coconut-frond surfaces while reducing redundant leaf-segment projection work.
- Reversed vertical camera drag direction and expanded zoom range.

## Intercrop photo resilience
- Added concurrency-limited photo retrieval rather than firing all candidate requests simultaneously.
- Added persistent browser caching of resolved crop photos.
- Added per-card error fallback so no crop image area remains blank.
- Broken cached remote images are invalidated and retried once before retaining the local fallback.

## About experience
- Rebuilt About as an interactive research-system page.
- Added a draggable holographic systems sphere, selectable architecture layers, research-principle expanders, interactive equations, animated workflow, and research metadata.

Interface version: `phase11-agritech-interface-1.3.20`.
