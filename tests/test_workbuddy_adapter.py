import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from adapters.workbuddy.adapter import WorkBuddyAdapter
from core.engine import Memory

ROOT = Path(__file__).resolve().parents[1]

# The same audit guard runs in the Inspector and every CLI child, before imports.
# It rejects native paths, SQLite and all filesystem writes, including mutations.
AUDITED_ENTRY = r'''
import sys, os, json, runpy, subprocess
opened=[]
def audit(event,args):
    if event.startswith('sqlite3.'):
        raise AssertionError('SQLite access forbidden')
    if event in ('os.remove','os.rename','os.mkdir','os.rmdir'):
        raise AssertionError('Filesystem mutation forbidden')
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0]);parts=path.replace(chr(92),'/').casefold().split('/')
        if {'.workbuddy','.codebuddy','.codex','.hermes','.agnes','sessions','file-history'} & set(parts):
            raise AssertionError('Native memory/history access forbidden')
        if path.lower().endswith(('.db','.sqlite','.env')):
            raise AssertionError('Private file access forbidden')
        mode,flags=args[1:3]
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            raise AssertionError('Write forbidden')
        opened.append(path)
sys.addaudithook(audit)
if sys.argv[1]=='inspector':
    original=subprocess.run;child_code=sys.argv[2]
    def traced(command,**kwargs):
        assert command[:5]==[sys.executable,'-B','-m','cli','--read-only']
        result=original([sys.executable,'-B','-c',child_code,'cli',*command[4:]],**kwargs)
        print(result.stderr,file=sys.stderr,end='')
        return result
    subprocess.run=traced
    sys.argv=['inspector',*sys.argv[3:]];module='adapters.workbuddy.inspector'
else:
    sys.argv=['cli',*sys.argv[2:]];module='cli'
try:runpy.run_module(module,run_name='__main__')
finally:print('AUDIT='+json.dumps(opened),file=sys.stderr)
'''


class WorkBuddyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.store = self.directory / 'workbuddy-memory.json'
        self.memory = Memory(self.store)
        self.candidate = dict(content='WB log format fictional-json', tags=['log', 'format'],
                              type='PROJECT', confirmed=True, source_type='user',
                              project='WB-Orion', machine='Mac-Win10', agent_scope=['workbuddy'],
                              metadata={'source_agent': 'workbuddy'})
        self.record = self.add(self.candidate)
        self.adapter = WorkBuddyAdapter(ROOT, self.store)

    def add(self, candidate):
        result = self.memory.add(candidate)
        self.assertEqual(result['decision'], 'ACCEPT')
        return result['record']

    def inspect(self, **kwargs):
        args = dict(task='log format', project='WB-Orion', machine='Mac-Win10')
        args.update(kwargs)
        return self.adapter.inspect(**args)

    def test_workbuddy_and_explicit_global_only(self):
        allowed = {self.record['id']}
        for scope in ([], ['codex'], ['hermes'], ['agnes-code'], ['global']):
            record = self.add(dict(self.candidate, content='log format '+str(scope),
                                   agent_scope=scope))
            if scope == ['global']:
                allowed.add(record['id'])
        result = self.inspect()
        self.assertEqual(set(result['memory_ids']), allowed)
        self.assertTrue(result['reference_only'])

    def test_project_machine_and_relevance(self):
        for changes in (dict(project='Other'), dict(machine='Win10-Admin'), dict(task='unrelated cooking')):
            with self.subTest(changes=changes):
                self.assertEqual(self.inspect(**changes)['memory_ids'], [])

    def test_inactive_and_expired(self):
        self.memory.retire(self.record['id'], 'fictional test')
        expiry = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        self.add(dict(self.candidate, type='EPISODIC', content='expired log format', expires_at=expiry))
        self.assertEqual(self.inspect()['memory_ids'], [])

    def test_budget(self):
        result = self.inspect()
        for operation in ('inject', 'retrieve', 'smart-retrieve', 'why'):
            empty = self.inspect(operation=operation, budget=result['characters']-1)
            self.assertEqual(empty.get('memory_ids', empty.get('results')), [])
        self.assertEqual(self.inspect(budget=result['characters'])['memory_ids'], [self.record['id']])

    def test_unrelated_bypasses_cli(self):
        with patch.object(self.adapter, '_call', side_effect=AssertionError('Unexpected retrieval')):
            self.assertFalse(self.inspect(task='27+15')['memory_retrieval_triggered'])

    def test_explicit_inputs_and_read_operations(self):
        for changes in (dict(project=''), dict(machine=''), dict(task=''), dict(budget=-1),
                        dict(budget=True), dict(operation='add')):
            with self.assertRaises(ValueError):
                self.inspect(**changes)
        for command in ('add', 'export', 'retire', 'move'):
            with self.assertRaises(ValueError):
                self.adapter._call(command)

    def test_other_stores_and_native_paths_refused(self):
        for name in ('codex-memory.json', 'hermes-memory.json', 'agnes-code-memory.json',
                     'workbuddy.db', 'native.sqlite'):
            with self.assertRaises(ValueError):
                WorkBuddyAdapter(ROOT, self.directory/name)
        for part in ('.workbuddy', '.WORKBUDDY', '.codebuddy', '.codex', '.hermes',
                     '.agnes', 'sessions', 'file-history'):
            with self.assertRaises(ValueError):
                WorkBuddyAdapter(ROOT, self.directory/part/'workbuddy-memory.json')

    def test_pending_migration_refused(self):
        Path(str(self.store)+'.move-journal.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.inspect()

    def test_why_and_scoped_explain(self):
        self.assertEqual(self.inspect(operation='why')['results'][0]['memory_id'], self.record['id'])
        self.assertEqual(self.inspect(operation='explain', record_id=self.record['id'])['status'], 'ACTIVE')
        for changes in (dict(project='Other'), dict(machine='Other'), dict(budget=0),
                        dict(record_id='unknown')):
            with self.assertRaises(ValueError):
                self.inspect(operation='explain', **{'record_id': self.record['id'], **changes})

    def test_cli_entry_and_scope_requirement(self):
        command = [sys.executable, '-B', '-m', 'adapters.workbuddy.inspector',
                   'inject', '--store', str(self.store), '--task', 'log', '--machine', 'Mac-Win10']
        self.assertNotEqual(subprocess.run(command, cwd=ROOT, capture_output=True).returncode, 0)
        result = subprocess.run(command+['--project', 'WB-Orion'], cwd=ROOT,
                                capture_output=True, encoding='utf-8', check=True)
        self.assertEqual(json.loads(result.stdout)['memory_ids'], [self.record['id']])

    def test_read_only_cannot_write(self):
        before = self.store.read_bytes()
        result = subprocess.run([sys.executable, '-B', '-m', 'cli', '--read-only', '--store',
                                 str(self.store), 'retire', self.record['id'], '--reason', 'fictional'],
                                cwd=ROOT, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.store.read_bytes())

    def test_inspector_and_cli_access_audit_all_operations(self):
        before = hashlib.sha256(self.store.read_bytes()).hexdigest()
        data_paths = set()
        for operation in WorkBuddyAdapter.OPERATIONS:
            command = [sys.executable, '-B', '-c', AUDITED_ENTRY, 'inspector', AUDITED_ENTRY,
                       operation, '--store', str(self.store), '--task', 'log format',
                       '--project', 'WB-Orion', '--machine', 'Mac-Win10']
            if operation == 'explain':
                command += ['--id', self.record['id']]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', check=True)
            for line in result.stderr.splitlines():
                if line.startswith('AUDIT='):
                    data_paths.update(Path(name).resolve() for name in json.loads(line[6:])
                                      if name.endswith('.json'))
        self.assertEqual(data_paths, {self.store.resolve()})
        self.assertEqual(before, hashlib.sha256(self.store.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
