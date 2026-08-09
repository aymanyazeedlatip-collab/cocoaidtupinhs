# Testing

Run on Windows with `test.bat`, or manually:

```powershell
.\.venv\Scripts\activate
python -m pytest -q
```

The suite covers:

- Bayes theorem, likelihood ratios, and Beta updating
- Suitability membership functions
- State conservation and transition behavior
- Pest/weather effects on production
- Reproducible Monte Carlo outputs and scenario comparison
- Climate-period and scenario behavior
- Weather provider parsing, caching, variable-aware keys, errors, and offline mode
- PSA source metadata, province profiles, annual status, and mature/young conservation
- Weekly forecast start/end dates, short-term/stochastic mode switching, product conservation, partial-year coverage, and annual totals
- Farm CRUD and validation
- Saved forecast storage and deletion
- Full analysis, PDF, and DOCX report generation
- Static-route traversal protection
- Main UI ID consistency and required workflow elements
- Embedded Weather GIS delivery

External providers are mocked during automated tests to avoid rate limits and nondeterministic failures. A local server smoke test should also verify `/api/health`, the main page, `/weather-viewer`, a 2026-2050 forecast, and report download.
