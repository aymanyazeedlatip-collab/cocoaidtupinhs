# Phase 6 Data Contracts

Contract API version: `3.0.0-draft.6`.

New contracts:

- `PestObservation`: status-controlled evidence with optional prevalence fraction and optional Bayesian linkage.
- `PestFarmContext`: palm inventory, maintenance, sanitation, drainage, wounds, storm damage, and symptom codes.
- `NearbyConfirmedPestCase`: distance, probability, and evidence status for spatial pressure.
- `PestAssessmentRequest`: production-linked multi-profile inference request.
- `PestEvidenceContribution`: factor-level likelihood ratio and log-odds contribution.
- `PestManagementAction`: source-linked PCA action text.
- `PestProfileAssessment`: one pest/disease probability, conditional loss, expected loss, and inspection plan.
- `PestEngineOutput`: complete run, summary, evidence audit, versions, and warnings.

Unknown fields are rejected. All probabilities use `0–1`; loss is stored in tonnes; timestamps require time zones.
