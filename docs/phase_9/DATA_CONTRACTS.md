# Phase 9 Data Contracts

The phase introduces strict Pydantic contracts for `DecisionSupportRequest`, component resolution, evidence, recommendations, traceability edges, overview, persistent records, summaries, and engine output.

Every request includes a farm identifier, production forecast identifier, versioned optional record identifiers, requested components, failure policy, generation time, and farm-data version. Unknown fields are rejected.

Every recommendation contains its priority, action, rationale, confidence, source components, concrete evidence fields, field-confirmation requirement, and limitations.
