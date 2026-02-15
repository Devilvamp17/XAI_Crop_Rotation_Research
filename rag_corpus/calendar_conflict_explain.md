# Explaining Calendar Conflicts
A calendar conflict occurs when the model's raw top crop has high statistical probability but poor seasonal suitability. The adjusted ranking may then prefer a different crop with stronger seasonal alignment.

Interpretation framework:
- Raw confidence: model fit to feature pattern.
- Seasonal suitability: operational feasibility in current month/region.
- Final adjusted confidence: practical decision score after combining both.

When conflict appears, communicate explicitly:
- "Model preferred A by raw probability, but seasonal suitability was low, so final recommendation is B."

This preserves transparency and avoids the false impression that either the model or calendar is "wrong." They answer different questions: pattern fit vs practical timing.
