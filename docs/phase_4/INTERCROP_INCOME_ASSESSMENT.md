# Assessment of the New PCA Region XII Income Workbook

**Restricted source:** `Income_Assessment_RXII_2024.xlsx`  
**SHA-256:** `29a36f885cdacab4fe88b289ccf03b306a6ad2a247dadcbc63b362c45242e270`

The workbook was inspected as a structured spreadsheet and contains three sheets:

- `SM5 a farmers`: 199 coconut income-reference records;
- `SM 5 a Summary`: summary formulas, including broken external references such as `[1]edited!R39`;
- `Edited`: 127 intercrop records comprising 59 cacao and 68 coffee records.

## Sanitized empirical profiles

### Cacao

- 59 records;
- median area: 1 ha, range 0.5–3 ha;
- median gross income per hectare: PHP 32,000;
- interquartile range: PHP 30,720–36,000;
- mean: PHP 39,454.92;
- maximum: PHP 153,600;
- recorded unit price: PHP 80;
- recorded frequency: 12 per year.

### Coffee

- 68 records;
- median area: 1 ha, range 1–2 ha;
- median gross income per hectare: PHP 49,660;
- interquartile range: PHP 30,550–84,600;
- mean: PHP 59,336.81;
- maximum: PHP 158,400;
- recorded unit prices: PHP 200 or PHP 260;
- harvest-frequency text is recorded as `once`/`Once` rather than a numeric annual frequency.

## Data-quality findings

- 1 explicit duplicate farmer entry;
- 61 text dates requiring normalization;
- 14 malformed dates using year `214`;
- 3 records with source remarks;
- 84 missing PCA-investment values;
- incomplete and semantically ambiguous cost coverage;
- coffee's `Gross Income Per Month` field behaves as one reported harvest income, not a reliable monthly series;
- broken external formulas in the summary sheet.

## Approved use

The workbook is useful for sanitized gross-revenue priors, site-level sensitivity analysis, and scenario ranges for cacao and coffee in the future intercropping engine.

## Prohibited or deferred use

It is not sufficient to:

- train a supervised intercropping model by itself;
- calculate net profit or ROI;
- treat gross revenue as guaranteed income;
- combine coconut and intercrop income without period/unit reconciliation;
- expose farmer names or row-level records through public APIs.

Phase 4 stores only three sanitized site/crop aggregate profiles. The raw workbook remains restricted and is never returned by the API.
