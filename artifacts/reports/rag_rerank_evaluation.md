# RAG Rerank Evaluation

Total scenarios: 3
Passed: 3
Pass rate: 100.00%

## punjab_rabi
- Expected top: `wheat`
- Final top: `wheat`
- Zone resolution: `state`
- Season: `rabi`
- Passed: `True`

## wb_kharif
- Expected top: `rice`
- Final top: `rice`
- Zone resolution: `state`
- Season: `kharif`
- Passed: `True`

## unknown_location
- Expected top: `None`
- Final top: `rice`
- Zone resolution: `unknown`
- Season: `kharif`
- Passed: `True`
