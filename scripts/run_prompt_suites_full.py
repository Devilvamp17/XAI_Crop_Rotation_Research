from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

OUT_DIR = Path('artifacts') / 'reports'
OUT_JSON = OUT_DIR / 'prompt_suite_execution_summary.json'
OUT_MD = OUT_DIR / 'prompt_suite_execution_summary.md'


def _run(cmd: list[str], timeout_s: int = 1800) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return {
            'cmd': ' '.join(cmd),
            'returncode': p.returncode,
            'timeout': False,
            'stdout': p.stdout[-4000:],
            'stderr': p.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'cmd': ' '.join(cmd),
            'returncode': 124,
            'timeout': True,
            'stdout': (exc.stdout or '')[-4000:] if isinstance(exc.stdout, str) else '',
            'stderr': (exc.stderr or '')[-4000:] if isinstance(exc.stderr, str) else '',
        }


def _count_cases(json_path: Path) -> dict[str, int] | None:
    if not json_path.exists():
        return None
    try:
        obj = json.loads(json_path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(obj, list):
        return None
    total = len(obj)
    passed = sum(1 for x in obj if x.get('ok'))
    return {'total': total, 'passed': passed, 'failed': total - passed}


def run_all(agent_api: str, include_extensive: bool, timeout_s: int) -> dict:
    suites = [
        {
            'name': 'main',
            'cmd': [
                'uv', 'run', 'python', 'scripts/run_prompt_suite.py',
                '--prompts', 'prompts/llm_prompt_suite.json',
                '--out-json', 'artifacts/llm_prompt_outputs_main.json',
                '--out-md', 'artifacts/llm_prompt_outputs_main.md',
                '--agent-api', agent_api,
            ],
            'json_out': Path('artifacts/llm_prompt_outputs_main.json'),
        },
        {
            'name': 'rag_live',
            'cmd': [
                'uv', 'run', 'python', 'scripts/run_prompt_suite.py',
                '--prompts', 'prompts/llm_prompt_suite_rag_live.json',
                '--out-json', 'artifacts/llm_prompt_outputs_rag_live.json',
                '--out-md', 'artifacts/llm_prompt_outputs_rag_live.md',
                '--agent-api', agent_api,
            ],
            'json_out': Path('artifacts/llm_prompt_outputs_rag_live.json'),
        },
        {
            'name': 'run2',
            'cmd': [
                'uv', 'run', 'python', 'scripts/run_prompt_suite.py',
                '--prompts', 'prompts/llm_prompt_suite_run2.json',
                '--out-json', 'artifacts/llm_prompt_outputs_run2.json',
                '--out-md', 'artifacts/llm_prompt_outputs_run2.md',
                '--agent-api', agent_api,
            ],
            'json_out': Path('artifacts/llm_prompt_outputs_run2.json'),
        },
    ]

    if include_extensive:
        suites.append(
            {
                'name': 'extensive',
                'cmd': [
                    'uv', 'run', 'python', 'scripts/run_prompt_suite_extensive.py',
                    '--agent-api', agent_api,
                    '--out-root', 'artifacts/suites',
                ],
                'json_out': None,
            }
        )

    results = []
    for s in suites:
        res = _run(s['cmd'], timeout_s=timeout_s)
        counts = _count_cases(s['json_out']) if s['json_out'] else None
        results.append({
            'name': s['name'],
            **res,
            'counts': counts,
            'json_output_exists': bool(s['json_out'] and s['json_out'].exists()),
        })

    ok = all(r['returncode'] == 0 for r in results)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {'ok': ok, 'results': results}
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    md = ['# Prompt Suite Execution Summary', '', f'Overall OK: `{ok}`', '']
    for r in results:
        md += [
            f"## {r['name']}",
            f"- Command: `{r['cmd']}`",
            f"- Return code: `{r['returncode']}`",
            f"- Timeout: `{r['timeout']}`",
            f"- JSON output exists: `{r['json_output_exists']}`",
        ]
        if r.get('counts'):
            c = r['counts']
            md.append(f"- Cases: total={c['total']} passed={c['passed']} failed={c['failed']}")
        if r.get('stdout'):
            md += ['- Stdout:', '```text', r['stdout'].strip(), '```']
        if r.get('stderr'):
            md += ['- Stderr:', '```text', r['stderr'].strip(), '```']
        md.append('')

    OUT_MD.write_text('\n'.join(md), encoding='utf-8')
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description='Run all prompt suites with integrity summary')
    parser.add_argument('--agent-api', default='http://127.0.0.1:8100')
    parser.add_argument('--include-extensive', action='store_true')
    parser.add_argument('--timeout-s', type=int, default=1800)
    args = parser.parse_args()

    result = run_all(agent_api=args.agent_api, include_extensive=args.include_extensive, timeout_s=args.timeout_s)
    print(str(OUT_JSON))
    print(str(OUT_MD))
    raise SystemExit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
