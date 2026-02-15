# Ablation Table

| component_removed | metric | full_value | ablated_value_or_proxy | delta | notes |
| --- | --- | --- | --- | --- | --- |
| full | mean_final_confidence | 0.2977985772853037 | 0.2977985772853037 | 0.0 | baseline from archived full pipeline |
| no_calendar | mean_final_confidence | 0.2977985772853037 | 0.5519541990466235 | 0.2541556217613198 | proxy using raw*dq*disagreement; calendar_conflict_rate=0.0000 |
| no_rag | llm_quality_delta | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE | no controlled with/without-RAG paired run found |
| no_validation | invalid_outputs_unblocked_rate | 0.0 | 1.3902439024390243 | 1.3902439024390243 | proxy from archived validation failures prevented by validation layer |
| no_disagreement | mean_final_confidence | 0.2977985772853037 | 0.3355638770559213 | 0.0377652997706176 | proxy; disagreement_detected_rate=0.8293 |
| no_quality_factor | mean_final_confidence | 0.2977985772853037 | 0.3234029186205348 | 0.025604341335231096 | proxy from confidence_components |

