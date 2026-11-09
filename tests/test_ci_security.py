import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = yaml.safe_load(Path('.github/workflows/security.yml').read_text())
SCANNERS = {
    'pip-audit', 'npm', 'gitleaks', 'trufflehog', 'trivy-fs',
    'trivy-image', 'semgrep', 'bandit', 'zizmor',
}
SCRIPT = Path('scripts/security/scan.sh').resolve()


def test_security_covers_all_scanners_on_pr_and_main_without_fail_open():
    triggers = WORKFLOW.get('on') or WORKFLOW[True]
    assert set(triggers) == {'pull_request', 'push'}
    assert triggers['push']['branches'] == ['main']
    assert WORKFLOW['permissions'] == {'contents': 'read'}
    job = WORKFLOW['jobs']['scan']
    assert job['strategy']['fail-fast'] is False
    assert set(job['strategy']['matrix']['scanner']) == SCANNERS
    assert not job.get('continue-on-error', False)
    for step in job['steps']:
        assert not step.get('continue-on-error', False)
        if 'uses' in step:
            assert re.search(r'@[0-9a-f]{40}$', step['uses'])
    artifact = job['steps'][-1]
    assert artifact['if'] == 'always()'
    assert artifact['with']['path'] == 'security-reports/'
    assert job['steps'][0]['with']['fetch-depth'] == 0
    assert job['steps'][0]['with']['persist-credentials'] is False


@pytest.mark.parametrize('scanner', sorted(SCANNERS))
@pytest.mark.parametrize('tool_exit', [0, 1, 7])
def test_scanner_propagates_failure_without_leaking_raw_output(tmp_path, scanner, tool_exit):
    tools = tmp_path / 'bin'
    tools.mkdir()
    # Fake tools exercise the runner's actual success/error handling, not scanners.
    stub = '#!/bin/sh\necho synthetic-sensitive-output\nexit "$TOOL_EXIT"\n'
    for name in ['uv', 'uvx', 'npm', 'docker']:
        path = tools / name
        path.write_text(stub)
        path.chmod(0o755)
    (tmp_path / 'web').mkdir()
    result = subprocess.run(
        ['bash', str(SCRIPT), scanner], cwd=tmp_path,
        env={**os.environ, 'PATH': f'{tools}:{os.environ["PATH"]}',
             'TOOL_EXIT': str(tool_exit)},
        capture_output=True, text=True,
    )
    assert result.returncode == tool_exit
    assert 'synthetic-sensitive-output' not in result.stdout + result.stderr
    report = (tmp_path / 'security-reports' / f'{scanner}.txt').read_text()
    assert report == f'Scanner: {scanner}\nExit status: {tool_exit}\n'


def test_unknown_scanner_is_rejected(tmp_path):
    result = subprocess.run(['bash', str(SCRIPT), '../unsafe'], cwd=tmp_path, capture_output=True)
    assert result.returncode == 2
    assert not (tmp_path / 'security-reports').exists()


def test_codeql_exception_has_reason_and_expiry_and_no_findings_are_suppressed():
    risks = Path('docs/security/accepted-risks.md').read_text()
    assert 'CodeQL' in risks and 'Private repository' in risks
    assert re.search(r'2027-02-09', risks)
    assert 'No scanner finding is currently suppressed' in risks


@pytest.mark.parametrize('scanner,payload', [
    ('gitleaks', '[{"RuleID":"generic-api-key","File":"fixture.py","Secret":"hidden"}]'),
    ('trufflehog', '{"Verified":true,"DetectorName":"test","Raw":"hidden"}'),
    ('semgrep', '{"results":[{"check_id":"test","path":"fixture.py",'
     '"extra":{"severity":"ERROR","lines":"hidden"}}]}'),
    ('trivy-fs', '{"Results":[{"Target":"fixture.py","Secrets":'
     '[{"RuleID":"test","Severity":"HIGH","Match":"hidden"}]}]}'),
    ('bandit', '{"results":[{"test_id":"B1","filename":"fixture.py",'
     '"issue_severity":"HIGH","code":"hidden"}]}'),
])
def test_reports_export_actionable_metadata_without_secret_values(tmp_path, scanner, payload):
    import json

    source, report = tmp_path / 'raw.json', tmp_path / 'report.json'
    source.write_text(payload)
    result = subprocess.run([
        'python3', str(SCRIPT.with_name('report.py')), scanner, '1', str(source), str(report),
    ], capture_output=True, text=True)
    assert result.returncode == 0
    body = report.read_text()
    assert 'hidden' not in body
    data = json.loads(body)
    assert data['exit_status'] == 1
    assert data['findings']
    assert set(data['findings'][0]) == {'id', 'location', 'severity'}


def test_native_and_inline_suppressions_are_rejected(tmp_path, monkeypatch):
    import runpy

    policy = runpy.run_path(str(SCRIPT.with_name('policy.py')))
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'web').mkdir()
    source = Path('web/example.ts')
    for comment in ['// nosemgrep: rule', '/* nosemgrep */', '# nosec']:
        source.write_text(comment + '\n')
        assert len(policy['violations']([Path('.gitleaksignore'), source])) == 2
    source.write_text('// no suppression\n')
    assert policy['violations']([source, Path('docs/security/accepted-risks.md')]) == []


@pytest.mark.parametrize('name', ['ci.yml', 'image.yml', 'security.yml'])
def test_all_workflow_actions_are_pinned_and_checkout_credentials_are_not_persisted(name):
    workflow = yaml.safe_load(Path('.github/workflows', name).read_text())
    for job in workflow['jobs'].values():
        for step in job['steps']:
            if 'uses' in step:
                assert re.search(r'@[0-9a-f]{40}$', step['uses'])
                if step['uses'].startswith('actions/checkout@'):
                    assert step['with']['persist-credentials'] is False


def test_ci_installs_from_frozen_lockfiles():
    workflow = yaml.safe_load(Path('.github/workflows/ci.yml').read_text())
    commands = [step.get('run') for job in workflow['jobs'].values() for step in job['steps']]
    assert 'uv sync --frozen' in commands
    assert 'npm ci' in commands
