# Phase 11.3.11 Verification Report

## Automated test inventory
- Unit tests: **282 passed**
- Integration tests: **54 passed**
- Mathematical tests: **9 passed**
- Total: **345 passed**

## Focused validation
- Hazard event weather consistency regression passed.
- Extreme-rain events in the deterministic regression horizon contain at least 70 mm accumulated event rainfall.
- Heat-stress events in the deterministic regression horizon have event-period peak temperature >= 33 °C.
- Legacy hazard-list marker is disabled so it cannot cover dates.
- Selected Threat broadcast map is absent from the DOM.
- Four hazard overview cards include visual gauges.
- Rehabilitation calendar is located in the Farm Health side rail while the map remains the dominant column.
- Pest Risk enhanced layout and typography regression passed.
- JavaScript syntax validation passed.
- Python compilation of the modified forecast engine passed.
- Duplicate DOM IDs: 0.
- Unresolved `$()` DOM references: 0.

## Release verifiers
Phases 1, 2, 3, 4, 5, 6, 6.2, 7, 8, 8.1, 9, 10, and 11 all passed after the change set.

## Environment note
The verification environment has scikit-learn 1.8.0 while the project requirements pin scikit-learn 1.9.0. The model registry therefore reports compatibility mode during tests. The packaged requirements retain the exact 1.9.0 runtime target.
