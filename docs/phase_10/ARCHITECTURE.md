# Phase 10 Architecture

Phase 10 adds two services above the Phase 9 integrated decision-support record:

1. **CoCO-PILOT grounding service**: converts saved analytical fields into a deterministic, evidence-linked explanation. Google AI is optional and may only rewrite the deterministic text after safety and numeric validation.
2. **Formal report service**: creates DOCX and PDF artifacts directly from the saved Phase 9 record. Numeric tables are generated from structured database fields, never from LLM text.

Processing flow:

```text
Decision-support run
        +
Public PCA source registry
        ↓
PII redaction and source manifest
        ↓
Deterministic explanation
        ↓ optional validated rewrite
CoCO-PILOT record
        ↓
Versioned DOCX/PDF formal report
```

The assistant does not override source engines, create observations, or generate chemical dosage.
