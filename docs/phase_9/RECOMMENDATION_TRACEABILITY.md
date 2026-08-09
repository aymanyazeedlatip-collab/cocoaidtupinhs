# Recommendation Traceability

Recommendations are deterministic interpretations of saved analytical outputs. They are not generated independently by an LLM.

Each recommendation stores:

- Source engine and component
- Source record identifier
- Exact field and value used
- Human-readable explanation
- Priority and confidence
- Field-confirmation requirement
- Limitations

The trace graph links upstream and downstream records so an old decision record can be reconstructed even after later forecasts are created.
