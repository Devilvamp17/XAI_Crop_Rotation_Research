# SHAP and LIME Interpretation Guide
SHAP and LIME are local explanation tools with different assumptions. SHAP attributes contribution values to each feature for a given prediction and supports global ranking via mean absolute contribution. LIME fits a local surrogate around one sample and is useful when local fidelity is acceptable.

How to interpret responsibly:
- Treat top SHAP features as influential signals, not direct causal proof.
- Use LIME rules as local approximations; verify fidelity before strong interpretation.
- Cross-check explanation with agronomic plausibility (e.g., nutrient and season effects).

Farmer-facing communication should convert explanation output into actionable checks:
- which inputs should be re-measured,
- what seasonal constraints apply,
- when to seek manual agronomy review.

Low-confidence scenarios require explicit risk framing: avoid definitive prescriptions and recommend pilot testing or expert validation.
