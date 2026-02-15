from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

OUT_DIR = Path('artifacts') / 'reports'
OUT_JSON = OUT_DIR / 'rag_artifact_consistency_audit.json'
OUT_CSV = OUT_DIR / 'rag_artifact_consistency_matrix.csv'
OUT_MD = OUT_DIR / 'rag_artifact_consistency_audit.md'

REQUIRED_RUN_FILES = [
    'request.json',
    'tool_calls.json',
    'recommendation.json',
    'validation.json',
    'llm_rounds.json',
    'llm_response.txt',
    'rag_hits.json',
    'icar_zone_match.json',
    'rag_rerank.json',
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _is_url(text: str) -> bool:
    t = (text or '').strip().lower()
    return t.startswith('http://') or t.startswith('https://')


def _pick_source_ref(hit: dict[str, Any]) -> str:
    text = str(hit.get('text', ''))
    for line in text.splitlines():
        if line.startswith('SOURCE_REF:'):
            return line.split(':', 1)[1].strip()
    return ''


def audit() -> dict[str, Any]:
    runs_dir = Path('artifacts') / 'runs'
    run_dirs = sorted([p for p in runs_dir.glob('*') if p.is_dir()])

    matrix_rows: list[dict[str, Any]] = []
    zone_counts: dict[str, int] = {}
    issues: list[dict[str, Any]] = []

    for run_dir in run_dirs:
        row: dict[str, Any] = {'run_dir': run_dir.name}

        missing_files = [f for f in REQUIRED_RUN_FILES if not (run_dir / f).exists()]
        row['has_required_files'] = len(missing_files) == 0
        row['missing_files'] = '|'.join(missing_files)

        if missing_files:
            matrix_rows.append(row)
            issues.append({'run_dir': run_dir.name, 'issue': 'missing_required_files', 'details': missing_files})
            continue

        request = _load_json(run_dir / 'request.json')
        rec = _load_json(run_dir / 'recommendation.json')
        tool_calls = _load_json(run_dir / 'tool_calls.json')
        validation = _load_json(run_dir / 'validation.json')
        rag_hits = _load_json(run_dir / 'rag_hits.json')
        zone_match = _load_json(run_dir / 'icar_zone_match.json')
        rag_rerank = _load_json(run_dir / 'rag_rerank.json')
        llm_text = (run_dir / 'llm_response.txt').read_text(encoding='utf-8').strip()

        zone = str(rec.get('zone_resolution', 'unknown'))
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

        row['zone_resolution'] = zone
        row['geocode_called'] = 'geocode_location' in (tool_calls if isinstance(tool_calls, list) else [])
        row['zone_consistent_with_icar_zone_match'] = zone == str(zone_match.get('zone_resolution', zone))

        expected_queries = rag_rerank.get('queries', []) if isinstance(rag_rerank, dict) else []
        row['rag_queries_count'] = len(expected_queries)

        hits = rag_hits if isinstance(rag_hits, list) else []
        row['rag_hits_count'] = len(hits)
        row['rag_hits_nonempty_when_queries_present'] = (len(expected_queries) == 0) or (len(hits) > 0)

        source_refs = [_pick_source_ref(h) for h in hits]
        url_refs = [s for s in source_refs if _is_url(s)]
        compiled_hits = sum(1 for h in hits if 'compiled notes' in str(h.get('text', '')).lower())
        row['authentic_source_ref_ratio'] = (len(url_refs) / len(hits)) if hits else 1.0
        row['compiled_notes_hits'] = compiled_hits

        row['validation_valid'] = bool(validation.get('valid', False))
        row['llm_response_nonempty'] = len(llm_text) > 0

        warns = rec.get('warnings', []) if isinstance(rec, dict) else []
        row['fallback_warning_present'] = any('LLM fallback applied'.lower() in str(w).lower() for w in warns)
        row['rerank_conflict_present'] = bool(rec.get('rerank_conflict'))

        # Consistency checks
        if row['geocode_called'] and zone == 'unknown':
            issues.append({'run_dir': run_dir.name, 'issue': 'geocode_but_unknown_zone', 'details': request.get('recommendation_input', {})})
        if row['authentic_source_ref_ratio'] < 1.0:
            issues.append({'run_dir': run_dir.name, 'issue': 'non_url_source_ref_in_hits', 'details': row['authentic_source_ref_ratio']})
        if compiled_hits > 0:
            issues.append({'run_dir': run_dir.name, 'issue': 'compiled_notes_hit_detected', 'details': compiled_hits})

        matrix_rows.append(row)

    # Cross-artifact completeness checks
    expected_prompt_outputs = [
        'artifacts/llm_prompt_outputs_main.json',
        'artifacts/llm_prompt_outputs_rag_live.json',
        'artifacts/llm_prompt_outputs_run2.json',
    ]
    missing_prompt_outputs = [p for p in expected_prompt_outputs if not Path(p).exists()]

    suite_dirs = [p for p in (Path('artifacts') / 'suites').glob('*') if p.is_dir()]
    suite_with_summary = [p for p in suite_dirs if (p / 'compliance_summary.json').exists()]

    summary = {
        'runs_total': len(run_dirs),
        'runs_with_required_files': sum(1 for r in matrix_rows if r.get('has_required_files')),
        'zone_resolution_distribution': zone_counts,
        'validation_valid_rate': (
            sum(1 for r in matrix_rows if r.get('validation_valid') is True) / max(1, sum(1 for r in matrix_rows if 'validation_valid' in r))
        ),
        'fallback_warning_rate': (
            sum(1 for r in matrix_rows if r.get('fallback_warning_present') is True) / max(1, len(matrix_rows))
        ),
        'geocode_unknown_zone_count': sum(1 for r in matrix_rows if r.get('geocode_called') and r.get('zone_resolution') == 'unknown'),
        'compiled_notes_hit_runs': sum(1 for r in matrix_rows if (r.get('compiled_notes_hits') or 0) > 0),
        'missing_prompt_output_files': missing_prompt_outputs,
        'suite_dirs_total': len(suite_dirs),
        'suite_dirs_with_compliance_summary': len(suite_with_summary),
    }

    if missing_prompt_outputs:
        issues.append(
            {
                'run_dir': 'GLOBAL',
                'issue': 'missing_prompt_output_files',
                'details': missing_prompt_outputs,
            }
        )
    if len(suite_dirs) == 0:
        issues.append(
            {
                'run_dir': 'GLOBAL',
                'issue': 'no_suite_directories_found',
                'details': 'artifacts/suites has no completed suite outputs',
            }
        )
    elif len(suite_with_summary) < len(suite_dirs):
        issues.append(
            {
                'run_dir': 'GLOBAL',
                'issue': 'suite_missing_compliance_summary',
                'details': f'{len(suite_with_summary)}/{len(suite_dirs)}',
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({'summary': summary, 'issues': issues, 'matrix_rows': matrix_rows}, indent=2), encoding='utf-8')

    # CSV matrix
    fields = [
        'run_dir',
        'has_required_files',
        'missing_files',
        'zone_resolution',
        'geocode_called',
        'zone_consistent_with_icar_zone_match',
        'rag_queries_count',
        'rag_hits_count',
        'rag_hits_nonempty_when_queries_present',
        'authentic_source_ref_ratio',
        'compiled_notes_hits',
        'validation_valid',
        'llm_response_nonempty',
        'fallback_warning_present',
        'rerank_conflict_present',
    ]
    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in matrix_rows:
            writer.writerow({k: r.get(k) for k in fields})

    md = [
        '# RAG Artifact Consistency Audit',
        '',
        '## Summary',
        '',
        f"- Runs total: `{summary['runs_total']}`",
        f"- Runs with required files: `{summary['runs_with_required_files']}`",
        f"- Zone distribution: `{summary['zone_resolution_distribution']}`",
        f"- Validation valid rate: `{summary['validation_valid_rate']:.2%}`",
        f"- Fallback warning rate: `{summary['fallback_warning_rate']:.2%}`",
        f"- Geocode-but-unknown-zone count: `{summary['geocode_unknown_zone_count']}`",
        f"- Compiled-notes-hit runs: `{summary['compiled_notes_hit_runs']}`",
        f"- Missing prompt output files: `{summary['missing_prompt_output_files']}`",
        f"- Suite dirs with compliance summary: `{summary['suite_dirs_with_compliance_summary']}/{summary['suite_dirs_total']}`",
        '',
        '## Key Issues',
        '',
    ]
    if issues:
        for i in issues[:100]:
            md.append(f"- `{i['run_dir']}`: `{i['issue']}` | `{i['details']}`")
    else:
        md.append('- None detected.')

    md += [
        '',
        '## Outputs',
        '',
        f"- JSON: `{OUT_JSON}`",
        f"- CSV: `{OUT_CSV}`",
    ]

    OUT_MD.write_text('\n'.join(md), encoding='utf-8')
    return {'summary': summary, 'issues_count': len(issues), 'json': str(OUT_JSON), 'csv': str(OUT_CSV), 'md': str(OUT_MD)}


if __name__ == '__main__':
    result = audit()
    print(json.dumps(result, indent=2))
