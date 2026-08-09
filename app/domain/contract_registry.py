from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel

from app.core.errors import ContractNotFoundError
from app.domain.analysis import AnalysisRun, ContractCatalogEntry, EngineResultEnvelope
from app.domain.base import CONTRACT_SCHEMA_VERSION
from app.domain.bayesian import (
    BayesianDiagnostics, BayesianEngineOutput, BayesianEvidenceObservation, BayesianPosterior,
    BayesianSimulationRequest, EvidenceAssimilationResult, StatePosteriorInterval,
)
from app.domain.farm import FarmCell, FarmObservation, FarmProfile, ProductionRecord, TreeCohort
from app.domain.intercropping import (
    CanopyLightEstimate, IntercropAssessment, IntercropAssessmentRequest,
    IntercropCandidate, IntercropCandidateAssessment, IntercropCandidateSnapshot,
    IntercropCellContext, IntercropEconomicPotential, IntercropEngineOutput,
    IntercropEngineSummary, SuitabilityComponent,
)
from app.domain.pest import (
    PestAssessment, PestAssessmentRequest, PestEngineOutput, PestFarmContext,
    PestObservation, PestProfileAssessment, PestEvidenceContribution,
    PestManagementAction, PestAssessmentSummary,
)
from app.domain.production import (
    LegacyProductionFeatureSnapshot, ProductEstimate, ProductionActualInput,
    ProductionEngineOutput, ProductionEngineRequest, ProductionForecast, ProductionShadowComparison,
)
from app.domain.provenance import DataProvenance, RunProvenance
from app.domain.coco_pilot import (
    CocoPilotCitation, CocoPilotRedactionSummary, CocoPilotRequest, CocoPilotResponse,
    FormalReportRecord, FormalReportRequest,
)
from app.domain.decision_support import (
    DecisionComponentResult, DecisionEvidence, DecisionOverview, DecisionRecommendation,
    DecisionSupportEngineOutput, DecisionSupportRecord, DecisionSupportRequest,
    DecisionSupportSummary, DecisionTraceEdge,
)
from app.domain.rehabilitation import (
    CostEstimate, RehabilitationAction, RehabilitationCellContext,
    RehabilitationEngineOutput, RehabilitationEngineSummary, RehabilitationPlan,
    RehabilitationPlanRequest, RehabilitationScenarioResult, RehabilitationTrigger,
)
from app.domain.weather import WeatherAssimilationPayload, WeatherFeatureSet, WeatherModelRun

ModelType = type[BaseModel]


class ContractRegistry:
    def __init__(self) -> None:
        self._contracts: dict[str, tuple[ModelType, str]] = {}

    def register(self, model: ModelType, description: str) -> None:
        name = model.__name__
        if name in self._contracts and self._contracts[name][0] is not model:
            raise ValueError(f"Contract {name} is already registered")
        self._contracts[name] = (model, description)

    def names(self) -> list[str]:
        return sorted(self._contracts)

    def model(self, name: str) -> ModelType:
        item = self._contracts.get(name)
        if item is None:
            raise ContractNotFoundError(f"Unknown data contract: {name}", details={"available": self.names()})
        return item[0]

    def schema(self, name: str) -> dict:
        return self.model(name).model_json_schema()

    def entry(self, name: str) -> ContractCatalogEntry:
        model, description = self._contracts.get(name, (None, None))
        if model is None or description is None:
            raise ContractNotFoundError(f"Unknown data contract: {name}", details={"available": self.names()})
        schema = model.model_json_schema()
        encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return ContractCatalogEntry(
            name=name,
            module=model.__module__,
            schema_version=CONTRACT_SCHEMA_VERSION,
            schema_sha256=hashlib.sha256(encoded).hexdigest(),
            description=description,
        )

    def catalog(self) -> list[ContractCatalogEntry]:
        return [self.entry(name) for name in self.names()]

    def validate(self, name: str, payload: object) -> BaseModel:
        return self.model(name).model_validate(payload)


contract_registry = ContractRegistry()
for _model, _description in (
    (FarmProfile, "Canonical farm identity, location, area, and source lineage."),
    (FarmCell, "Spatial analysis cell belonging to a farm."),
    (TreeCohort, "A palm cohort with variety, age, count, and health state."),
    (FarmObservation, "A time-stamped real-world or reported farm observation."),
    (ProductionRecord, "Observed production for a product and time period."),
    (WeatherModelRun, "Immutable observed, forecast, historical, or climate weather run."),
    (WeatherAssimilationPayload, "Provider payload and run settings accepted by the executable weather assimilation engine."),
    (WeatherFeatureSet, "Versioned agricultural weather features derived from a weather run."),
    (ProductionEngineRequest, "Validated inputs for the retained production model and Phase 4 adapter."),
    (LegacyProductionFeatureSnapshot, "Immutable ordered feature payload supplied to the retained production model."),
    (ProductEstimate, "A direct or variety-converted coconut product quantity."),
    (ProductionShadowComparison, "Comparison between the v2.11 bounded correction and v3 outputs."),
    (ProductionEngineOutput, "Complete Phase 4 production result with traceable features and shadow comparison."),
    (ProductionActualInput, "Observed production used for later actual-versus-predicted monitoring."),
    (ProductionForecast, "Traceable product forecast separating raw ML, named-variety adjustment, and Bayesian status."),
    (BayesianEvidenceObservation, "Typed, status-controlled farm evidence for Bayesian updating."),
    (BayesianSimulationRequest, "Reproducible particle-filter request linked to a Phase 4 production forecast."),
    (StatePosteriorInterval, "Credible interval for a palm-state count or soil-state index."),
    (EvidenceAssimilationResult, "Trace of whether and how one observation updated particle weights."),
    (BayesianDiagnostics, "Particle-filter diagnostics, conservation status, seed, and effective sample size."),
    (BayesianPosterior, "Posterior farm state and uncertainty after evidence assimilation."),
    (BayesianEngineOutput, "Complete Phase 5 posterior, evidence trace, and diagnostics."),
    (PestAssessment, "Compatibility pest-specific probability, conditional loss, and expected loss contract."),
    (PestObservation, "Status-controlled pest or disease evidence with optional Bayesian prevalence linkage."),
    (PestFarmContext, "Cell-level palm, management, drainage, wound, and symptom context for Phase 6 inference."),
    (PestAssessmentRequest, "Traceable request for one or more PCA-supported pest-specific assessments."),
    (PestEvidenceContribution, "Decomposable evidence contribution with likelihood ratio and log-odds delta."),
    (PestManagementAction, "PCA-sourced management action without invented chemical dosage."),
    (PestProfileAssessment, "One PCA pest or disease probability with conditional and expected production loss."),
    (PestAssessmentSummary, "Cross-profile inspection-priority summary with overlap warning."),
    (PestEngineOutput, "Complete Phase 6 multi-profile pest inference result and evidence audit."),
    (IntercropCandidate, "Reference requirements for a possible intercrop."),
    (SuitabilityComponent, "One decomposable weighted component of an intercropping score."),
    (IntercropAssessment, "Compatibility cell-level intercropping assessment contract."),
    (IntercropCellContext, "Cell canopy, soil, space, slope, management, and market context for Phase 7."),
    (IntercropAssessmentRequest, "Traceable multi-cell, multi-candidate Phase 7 assessment request."),
    (CanopyLightEstimate, "PCA-table canopy transmission estimate with explicit interpolation trace."),
    (IntercropEconomicPotential, "Gross-revenue scenario or explicit unavailable state."),
    (IntercropCandidateSnapshot, "Immutable candidate light and requirement profile snapshot."),
    (IntercropCandidateAssessment, "One candidate-by-cell suitability result with competition and pest penalties."),
    (IntercropEngineSummary, "Cross-cell summary and best candidate map."),
    (IntercropEngineOutput, "Complete Phase 7 intercropping potential run."),
    (CostEstimate, "Transparent materials, labor, other-cost, and person-day estimate."),
    (RehabilitationTrigger, "Evidence-linked rehabilitation trigger with explicit confirmation semantics."),
    (RehabilitationCellContext, "Palm-state, soil, drainage, damage, and operational context for one farm cell."),
    (RehabilitationPlanRequest, "Budget-, labor-, and risk-aware Phase 8 planning request."),
    (RehabilitationAction, "Cell-linked action with timing, evidence, cost, recovery range, and confirmation requirement."),
    (RehabilitationScenarioResult, "Comparable no-action or intervention scenario with uncertainty, feasibility, and utility."),
    (RehabilitationPlan, "Budget-constrained, evidence-linked rehabilitation work plan and scenario comparison."),
    (RehabilitationEngineSummary, "Compact Phase 8 planning and feasibility summary."),
    (RehabilitationEngineOutput, "Complete Phase 8 rehabilitation and scenario-optimization result."),
    (DecisionSupportRequest, "Phase 9 request linking versioned analytical outputs into one decision-support run."),
    (DecisionComponentResult, "Resolution status and summary for one analytical component."),
    (DecisionEvidence, "Traceable evidence supporting a deterministic decision recommendation."),
    (DecisionRecommendation, "Prioritized, evidence-linked farm-management recommendation."),
    (DecisionTraceEdge, "Dependency and lineage edge between analytical component records."),
    (DecisionOverview, "Consolidated production, risk, intercropping, and rehabilitation overview."),
    (DecisionSupportRecord, "Persistent integrated decision-support record for one farm run."),
    (DecisionSupportSummary, "Compact status and completeness summary for a decision-support run."),
    (DecisionSupportEngineOutput, "Complete Phase 9 integrated decision-support network output."),
    (CocoPilotRequest, "Phase 10 grounded explanation request linked to one decision-support run."),
    (CocoPilotCitation, "Traceable analytical or PCA source citation used by CoCO-PILOT."),
    (CocoPilotRedactionSummary, "Privacy boundary and PII-removal summary for one assistant run."),
    (CocoPilotResponse, "Grounded deterministic or validated optional-AI explanation."),
    (FormalReportRequest, "Request for a versioned DOCX or PDF report from a saved decision-support run."),
    (FormalReportRecord, "Stored formal-report artifact metadata, checksum, fingerprint, and provenance."),
    (AnalysisRun, "Top-level orchestration record for a multi-engine analysis."),
    (EngineResultEnvelope, "Standard success, failure, skip, or degraded engine result."),
    (DataProvenance, "Source, timing, quality, and transformation lineage for data."),
    (RunProvenance, "Model, parameter, source, seed, and farm versions for a run."),
):
    contract_registry.register(_model, _description)
