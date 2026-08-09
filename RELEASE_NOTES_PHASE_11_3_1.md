# COCOAID Phase 11.3.1 Home Hologram and Navigation Hotfix

## Scope

This release is a frontend-only corrective update to the Phase 11.3 full-screen Home landing page. Analytical engines, API contracts, database migrations, trained models, report generation, Weather GIS behavior, music, and voice narration remain unchanged.

## Changes

- Removed every visible annotation from the Home coconut hologram, including status, interaction instructions, and analytical captions.
- Increased the parametric coconut mesh contrast with bright white depth-weighted lines, stronger glow, larger stage coverage, and explicit canvas layering.
- Preserved the original three orbit-ring structures and animations while changing the ring lines and orbit nodes to white.
- Increased hologram visibility on tablet and mobile layouts.
- Moved the global Menu button to the left side.
- Connected the Menu button position to the off-canvas sidebar edge.
- First Menu click opens the fully expanded sidebar.
- Second Menu click minimizes the open sidebar to a 78-pixel icon-only rail.
- Clicking the control again expands the rail.
- Clicking outside the sidebar closes it without suppressing the clicked page control.
- Removed the full-screen click-blocking navigation backdrop.
- Preserved Escape-to-close and automatic close after choosing a navigation destination.

## Interface identity

- Interface: `phase11-agritech-interface-1.3.1`
- Design system: `cocoaid-official-agritech-1.3.1`
