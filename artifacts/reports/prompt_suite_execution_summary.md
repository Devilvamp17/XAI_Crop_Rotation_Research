# Prompt Suite Execution Summary

Overall OK: `True`

## main
- Command: `uv run python scripts/run_prompt_suite.py --prompts prompts/llm_prompt_suite.json --out-json artifacts/llm_prompt_outputs_main.json --out-md artifacts/llm_prompt_outputs_main.md --agent-api http://127.0.0.1:8100`
- Return code: `0`
- Timeout: `False`
- JSON output exists: `True`
- Cases: total=13 passed=13 failed=0
- Stdout:
```text
Prompt cases: 13 | Passed: 13 | Failed: 0
JSON report: artifacts/llm_prompt_outputs_main.json
Markdown report: artifacts/llm_prompt_outputs_main.md
```

## rag_live
- Command: `uv run python scripts/run_prompt_suite.py --prompts prompts/llm_prompt_suite_rag_live.json --out-json artifacts/llm_prompt_outputs_rag_live.json --out-md artifacts/llm_prompt_outputs_rag_live.md --agent-api http://127.0.0.1:8100`
- Return code: `0`
- Timeout: `False`
- JSON output exists: `True`
- Cases: total=12 passed=12 failed=0
- Stdout:
```text
Prompt cases: 12 | Passed: 12 | Failed: 0
JSON report: artifacts/llm_prompt_outputs_rag_live.json
Markdown report: artifacts/llm_prompt_outputs_rag_live.md
```

## run2
- Command: `uv run python scripts/run_prompt_suite.py --prompts prompts/llm_prompt_suite_run2.json --out-json artifacts/llm_prompt_outputs_run2.json --out-md artifacts/llm_prompt_outputs_run2.md --agent-api http://127.0.0.1:8100`
- Return code: `0`
- Timeout: `False`
- JSON output exists: `True`
- Cases: total=8 passed=8 failed=0
- Stdout:
```text
Prompt cases: 8 | Passed: 8 | Failed: 0
JSON report: artifacts/llm_prompt_outputs_run2.json
Markdown report: artifacts/llm_prompt_outputs_run2.md
```
