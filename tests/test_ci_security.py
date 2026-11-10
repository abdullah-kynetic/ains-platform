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
    import shutil

    for name in ['docs/security/accepted-risks.md', '.github/workflows/image.yml']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCRIPT.parents[2] / name, target)
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


def test_codeql_exception_has_reason_and_expiry_and_findings_are_explicit():
    risks = Path('docs/security/accepted-risks.md').read_text()
    assert 'CodeQL' in risks and 'Private repository' in risks
    assert re.search(r'2027-02-09', risks)
    assert 'Only the explicitly recorded findings below are suppressed' in risks


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


def test_failure_annotations_keep_only_metadata_and_fixed_diagnostic_labels(tmp_path):
    import json

    source, log, report = (tmp_path / name for name in ['findings.json', 'raw.log', 'safe.json'])
    source.write_text(json.dumps({'results': [{
        'check_id': 'rule\n::warning::injected', 'path': 'example.ts',
        'extra': {'severity': 'ERROR', 'lines': 'synthetic-sensitive-output'},
    }]}))
    log.write_text('Domain forbidden: synthetic-sensitive-output')
    result = subprocess.run([
        'python3', str(SCRIPT.with_name('report.py')), 'semgrep', '2',
        str(source), str(report), str(log),
    ], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'synthetic-sensitive-output' not in result.stdout + report.read_text()
    assert '\n::warning::injected' not in result.stdout
    assert 'rule%0A::warning::injected' in result.stdout
    assert 'network-denied' in result.stdout
    assert json.loads(report.read_text())['diagnostics'] == ['network-denied']


def test_approved_risks_generate_only_exact_scoped_suppressions(tmp_path):
    import json
    import runpy
    from datetime import date

    policy = runpy.run_path(str(SCRIPT.with_name('policy.py')))
    entries = policy['accepted_risks'](Path('docs/security/accepted-risks.md'), date(2026, 11, 10))
    assert len(entries) == 13
    policy['generate'](tmp_path, entries)
    ignored = (tmp_path / 'gitleaksignore').read_text().splitlines()
    assert len(ignored) == 3
    assert all(re.fullmatch(r'[0-9a-f]{40}:.+:generic-api-key:[0-9]+', line) for line in ignored)
    config = json.loads((tmp_path / 'zizmor.yml').read_text())
    line = Path('.github/workflows/image.yml').read_text().splitlines().index('  workflow_run:') + 1
    assert config == {'rules': {'dangerous-triggers': {'ignore': [f'image.yml:{line}']}}}


@pytest.mark.parametrize('change', ['expired', 'missing-reason', 'broad-fingerprint', 'too-long'])
def test_invalid_risks_fail_closed(tmp_path, change):
    import json
    import runpy
    from datetime import date

    policy = runpy.run_path(str(SCRIPT.with_name('policy.py')))
    entries = policy['accepted_risks'](Path('docs/security/accepted-risks.md'), date(2026, 11, 10))
    if change == 'expired':
        entries[0]['expires'] = '2026-11-10'
    elif change == 'missing-reason':
        entries[0]['reason'] = ''
    elif change == 'broad-fingerprint':
        entries[1]['fingerprint'] = '*'
    else:
        entries[0]['expires'] = '2027-02-09'
    source = tmp_path / 'accepted-risks.md'
    source.write_text('```json\n' + json.dumps(entries) + '\n```')
    with pytest.raises(ValueError):
        policy['accepted_risks'](source, date(2026, 11, 10))


def test_uv_resolution_has_a_seven_day_dependency_cooldown():
    import tomllib

    config = tomllib.loads(Path('pyproject.toml').read_text())
    assert config['tool']['uv']['exclude-newer'] == '7 days'


def test_container_findings_include_fix_versions_in_one_annotation(tmp_path):
    import json

    source, report = tmp_path / 'raw.json', tmp_path / 'safe.json'
    source.write_text(json.dumps({'Results': [{
        'Target': 'debian', 'Vulnerabilities': [
            {'VulnerabilityID': f'CVE-SYNTHETIC-{i}', 'Severity': 'HIGH',
             'PkgName': 'fixture-package', 'InstalledVersion': '1', 'FixedVersion': '2',
             'Description': 'synthetic-sensitive-output'} for i in range(20)
        ],
    }]}))
    result = subprocess.run([
        'python3', str(SCRIPT.with_name('report.py')), 'trivy-image', '1', str(source), str(report),
    ], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.count('::error title=Security finding metadata::') == 1
    assert 'CVE-SYNTHETIC-19' in result.stdout
    assert 'synthetic-sensitive-output' not in result.stdout + report.read_text()
    row = json.loads(report.read_text())['findings'][0]
    assert (row['package'], row['installed'], row['fixed']) == ('fixture-package', '1', '2')


def test_security_scans_source_without_creating_generated_dependency_fixtures():
    commands = [step.get('run', '') for step in WORKFLOW['jobs']['scan']['steps']]
    assert 'uv lock --check' in commands
    assert not any(
        token in command for command in commands for token in ['uv sync', 'npm ci', 'uv run']
    )
    # Frozen application installation remains enforced by CI's separate jobs.


def test_image_runtime_failure_prevents_saving_or_scanning_the_image(tmp_path):
    import shutil

    tools = tmp_path / 'bin'
    tools.mkdir()
    docker = tools / 'docker'
    docker.write_text(
        '#!/bin/sh\necho "$*" >> "$DOCKER_CALLS"\n'
        'case "$*" in *"/app/smoke.py"*) exit 17;; esac\nexit 0\n'
    )
    docker.chmod(0o755)
    for name in ['docs/security/accepted-risks.md', '.github/workflows/image.yml']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCRIPT.parents[2] / name, target)
    log = tmp_path / 'docker.log'
    result = subprocess.run(
        ['bash', str(SCRIPT), 'trivy-image'], cwd=tmp_path,
        env={**os.environ, 'PATH': f'{tools}:{os.environ["PATH"]}', 'DOCKER_CALLS': str(log)},
        capture_output=True, text=True,
    )
    assert result.returncode == 17
    calls = log.read_text().splitlines()
    assert calls[0] == 'build -t kien-api:ci .'
    assert '/app/smoke.py' in calls[1]
    assert len(calls) == 2


@pytest.mark.parametrize('scanner', ['semgrep', 'trivy-fs'])
@pytest.mark.parametrize(
    'case', ['approved', 'different-file', 'different-rule', 'error', 'bad-json'],
)
def test_scoped_filter_never_clears_unapproved_findings_or_scanner_errors(tmp_path, scanner, case):
    import json
    import runpy
    from datetime import date

    policy = runpy.run_path(str(SCRIPT.with_name('policy.py')))
    entries = policy['accepted_risks'](Path('docs/security/accepted-risks.md'), date(2026, 11, 10))
    risk = next(e for e in entries if e['scanner'] == scanner)
    rule = 'not-approved' if case == 'different-rule' else risk['finding']
    scope = 'app/not-approved.py' if case == 'different-file' else risk['scope']
    if scanner == 'semgrep':
        report = {'results': [{'check_id': rule, 'path': scope}], 'errors': []}
    else:
        report = {'Results': [{'Target': scope, 'Misconfigurations': [{'ID': rule}]}]}
    if case == 'error':
        report['errors'] = [{'type': 'synthetic scanner error'}]
    source = tmp_path / 'scanner.json'
    source.write_text('invalid-json' if case == 'bad-json' else json.dumps(report))
    result = policy['filter_report'](scanner, 1, source, entries)
    assert result == (0 if case == 'approved' else 1)
    assert policy['filter_report'](scanner, 2, source, entries) == 2
    if case == 'approved':
        assert json.loads(source.read_text())['KienAcceptedFindings'][0]['expires'] == '2027-02-07'


def test_trivy_exceptions_never_clear_secret_or_vulnerability_findings(tmp_path):
    import json
    import runpy
    from datetime import date

    policy = runpy.run_path(str(SCRIPT.with_name('policy.py')))
    entries = policy['accepted_risks'](Path('docs/security/accepted-risks.md'), date(2026, 11, 10))
    for category in ['Secrets', 'Vulnerabilities']:
        source = tmp_path / 'scanner.json'
        source.write_text(json.dumps({'Results': [{
            'Target': 'infra/aws/main.tf', 'Misconfigurations': [{'ID': 'AWS-0104'}],
            category: [{'ID': 'synthetic-new-finding'}],
        }]}))
        assert policy['filter_report']('trivy-fs', 1, source, entries) == 1


def test_scanner_error_metadata_never_exports_error_messages_or_source(tmp_path):
    import json

    source, report = tmp_path / 'raw.json', tmp_path / 'safe.json'
    source.write_text(json.dumps({'results': [], 'errors': [{
        'type': 'ParseError', 'level': 'warn', 'code': 3, 'path': 'synthetic.ts',
        'message': 'synthetic-sensitive-output', 'lines': 'synthetic-sensitive-output',
    }]}))
    result = subprocess.run([
        'python3', str(SCRIPT.with_name('report.py')), 'semgrep', '1', str(source), str(report),
    ], capture_output=True, text=True)
    assert 'synthetic-sensitive-output' not in result.stdout + report.read_text()
    assert 'ParseError' in result.stdout
    assert json.loads(report.read_text())['errors'] == [
        {'type': 'ParseError', 'level': 'warn', 'code': '3', 'path': 'synthetic.ts'},
    ]
