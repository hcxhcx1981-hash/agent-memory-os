"""Executable fictional Quick Start and full CLI demo; no external services."""
import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quickstart-only', action='store_true')
    parser.add_argument('--command', help='Installed memory executable; otherwise use python -m cli')
    parser.add_argument('--store', type=Path, help='A new, nonexistent store (never overwrites a store)')
    args = parser.parse_args()
    store = (args.store or ROOT / 'work' / ('demo-' + uuid.uuid4().hex) / 'memory.json').resolve()
    if store.exists() or Path(str(store) + '.smart.json').exists():
        parser.error('Choose a new store; existing data will not be overwritten')
    store.parent.mkdir(parents=True, exist_ok=True)
    executable = args.command
    if executable and Path(executable).is_file():
        executable = str(Path(executable).resolve())
    command = [executable] if executable else [sys.executable, '-m', 'cli']
    # Installed mode deliberately runs outside the source tree.
    cwd = store.parent if args.command else ROOT

    def run(*parts, expected=None):
        result = subprocess.run(command + ['--store', str(store), *map(str, parts)],
                                cwd=cwd, capture_output=True, text=True, encoding='utf-8', check=True)
        value = json.loads(result.stdout)
        if expected is not None:
            assert value['decision'] == expected, (parts[0], value)
        print(parts[0] + ': ' + json.dumps(value, ensure_ascii=True))
        return value

    def candidate(name, content, confirmed=True, **extra):
        path = store.parent / (name + '.json')
        path.write_text(json.dumps(dict(content=content, confirmed=confirmed, source_type='user', **extra)), encoding='utf-8')
        return path

    first = ROOT / 'examples/theme.json'
    change = ROOT / 'examples/theme-change.json'
    run('evaluate', '--candidate', first, expected='ACCEPT')
    old = run('add', '--candidate', first, expected='ACCEPT')['record']
    run('add', '--candidate', first, expected='DUPLICATE')
    assert [r['id'] for r in run('retrieve', 'default_theme', '--project', 'Project-Mercury')] == [old['id']]
    assert run('inject', 'default_theme', '--project', 'Project-Mercury', '--budget', 300)['memory_ids'] == [old['id']]
    run('evaluate', '--candidate', change, expected='CONFLICT')
    # This scripted confirmation is for fictional demonstration data only.
    new = run('supersede', old['id'], '--candidate', change, '--reason', 'Demo user explicitly confirmed replacement')['record']
    assert new['supersedes'] == [old['id']]
    assert run('get', old['id'])['superseded_by'] == new['id']
    assert run('inject', 'default_theme', '--project', 'Project-Mercury')['memory_ids'] == [new['id']]
    assert run('inject', 'arithmetic', '--project', 'Project-Other')['memory_ids'] == []
    if not args.quickstart_only:
        temporary = candidate('temporary', '今天暂时使用测试工作流', type='EPISODIC', project='Project-Demo')
        record = run('add', '--candidate', temporary, expected='ACCEPT')['record']
        assert record['type'] == 'EPISODIC' and record['expires_at']
        preference = candidate('report', 'Project-Aurora 的报告默认使用 compact-dark 风格', confirmed=False, type='PROJECT', project='Project-Aurora')
        observation = None
        for _ in range(3):
            observation = run('observe', '--candidate', preference, expected='OBSERVED')['observation_id']
        assert any(row['observation_id'] == observation for row in run('promotion-candidates'))
        run('promote', observation, expected='NEEDS_CONFIRMATION')
        run('explain', observation)
        run('promote', observation, '--user-confirmed', expected='ACCEPT')
        sources = []
        for index, text in enumerate(['UI 使用深色背景', '紫色为主交互色', '绿色只用于成功状态', '避免浅蓝白 SaaS 风']):
            path = candidate('ui-' + str(index), text, type='PROJECT', project='Project-Aurora')
            sources.append(run('add', '--candidate', path, expected='ACCEPT')['record']['id'])
        proposal = run('consolidate', *sources, expected='CANDIDATE')
        assert proposal['source_memory_ids'] == sources
        run('promote', proposal['observation_id'], expected='NEEDS_CONFIRMATION')
        aggregate = run('promote', proposal['observation_id'], '--user-confirmed', expected='ACCEPT')['record']
        assert run('explain', aggregate['id'])['relationships'][0]['derived_from'] == sources
        run('why', 'UI', '--project', 'Project-Aurora')
        assert run('smart-inject', 'UI', '--project', 'Project-Aurora')['memory_ids'] == [aggregate['id']]
        for source in sources:
            assert run('get', source)['status'] == 'ACTIVE'
    print('DEMO=PASS')
    print('Fictional store retained for inspection: ' + str(store))


if __name__ == '__main__':
    main()
