# Phase 1 Core Architecture

COCOAID v3 is being introduced beside the frozen v2.11 runtime. Phase 1 does not replace the existing weather, production, pest, simulation, GIS, reporting, or frontend behavior. It establishes strict boundaries that later phases must implement against.

## Runtime layers

```text
HTTP API
├── /api/*       frozen-compatible v2.11 routes
└── /api/v2/*    v3 contract and registry routes
        ↓
Application services and future run orchestrator
        ↓
Analytical engine interfaces
├── weather assimilation
├── production
├── Bayesian farm state
├── pest inference
├── intercropping
└── rehabilitation
        ↓
Domain contracts and registries
├── canonical units
├── data provenance
├── model versions
├── parameter versions
└── source versions
        ↓
Repositories and versioned database migrations
```

## Dependency rules

1. API handlers validate and route requests. They do not contain scientific formulas.
2. Analytical engines accept and return registered Pydantic contracts.
3. Engines may depend on lower-level engines only through explicit identifiers and versions.
4. Domain models do not import API, database, provider, or frontend modules.
5. Legacy code remains callable while v3 engines are implemented and shadow-tested.
6. CoCO-PILOT will consume structured engine outputs rather than directly calculating farm decisions.

## New packages

| Package | Responsibility |
| --- | --- |
| `app/domain` | Strict canonical contracts, enums, provenance, and units |
| `app/engines` | Shared engine interface, descriptors, and registry |
| `app/parameters` | Immutable parameter-set descriptors and hashes |
| `app/api/v2` | Read-only architecture/contract API and contract validation |
| `app/storage/migrations` | Ordered, checksummed, reversible migration framework |
| `app/core/error_handlers.py` | Centralized validation and application error responses |
| `app/core/middleware.py` | Request correlation IDs and timing headers |

## Compatibility controls

- `/api/health` still reports API version `2.11.0`.
- `/api/v2/health` reports contract version `3.0.0-draft.1`.
- The v2.11 UI continues to call the original routes.
- Existing SQLite tables remain unchanged and are now represented by migration version 1.
- Existing model files are not retrained or modified.
- Exact serialized model runtime is pinned to `scikit-learn==1.9.0`.
