# Phase 3 Release Notes

Phase 3 adds the Weather Assimilation Engine without replacing the legacy Weather GIS or retained ML artifacts.

## Added

- Migration 3 weather-run and feature schema
- Normalized weather-run repository
- Agricultural feature adapter
- 16-day live-weather enforcement
- Expanded Open-Meteo agricultural variables
- Versioned run comparison
- Executable v3 weather-assimilation engine
- `/api/v2/weather/*` endpoints
- Offline/stale-cache disclosure and cooldown handling
- Phase 3 verification and manifests

## Preserved

- v2.11 frontend and analytical endpoints
- Existing trained model artifacts and checksums
- Phase 2 PCA data foundation and farmer privacy boundary
- Long-term climate-conditioned simulation as a separate subsystem
