import copy
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from core.engine import Memory
from core.migration import move_record, atomic_json, marker
from adapters.codex.adapter import CodexAdapter

ROOT = Path(__file__).resolve().parents[1]

class StoreIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.source = Memory(Path(self.temp.name)/'hermes.json')
        self.target = Memory(Path(self.temp.name)/'codex.json')
        self.c = dict(content='Orion default log format compact-json',type='PROJECT',confirmed=True,
            source_type='import',project='Project-Orion',machine='Win10-Admin',confidence=0.95,
            metadata={'legacy_source':'codex_legacy_memory','legacy_id_prefix':'fictional'},tags=['log'])
        self.r = self.source.add(self.c)['record']
        self.adapter = CodexAdapter(ROOT,self.target.path)

    def move(self):
        return move_record(self.source.path,self.target.path,self.r['id'],['codex'],'codex')

    def test_move_id_provenance_audit(self):
        new = self.move()['record']
        self.assertEqual(new['id'],self.r['id'])
        for key in ('content','created_at','project','machine','confidence','source_type'):
            self.assertEqual(new[key],self.r[key])
        self.assertEqual(new['metadata']['legacy_source'],'codex_legacy_memory')
        self.assertEqual(new['metadata']['source_agent'],'codex')
        self.assertEqual(self.source.get(new['id'])['status'],'RETIRED')
        self.assertEqual([e['event'] for e in self.target.load()['audit']],['CREATE','MOVE_IN'])

    def test_failed_target_stage_rolls_back(self):
        with patch.object(Memory,'save',side_effect=OSError('fictional failure')):
            with self.assertRaises(OSError):self.move()
        self.assertEqual(self.source.get(self.r['id'])['status'],'ACTIVE')
        self.assertEqual(self.target.load()['records'],[])

    def test_failed_source_commit_rolls_back(self):
        original = Memory.save
        def fail(store,data):
            if store.path.resolve()==self.source.path.resolve():raise OSError('fictional failure')
            return original(store,data)
        with patch.object(Memory,'save',fail):
            with self.assertRaises(OSError):self.move()
        self.assertEqual(self.source.get(self.r['id'])['status'],'ACTIVE')
        self.assertEqual(self.target.load()['records'],[])

    def test_failed_activation_no_double_active(self):
        original = Memory.save;counter = [0]
        def fail(store,data):
            if store.path.resolve()==self.target.path.resolve():
                counter[0]+=1
                if counter[0]==2:raise OSError('fictional failure')
            return original(store,data)
        with patch.object(Memory,'save',fail):
            with self.assertRaises(OSError):self.move()
        self.assertEqual(self.source.get(self.r['id'])['status'],'ACTIVE')
        self.assertEqual(self.target.load()['records'],[])

    def test_interrupted_journal_recovers_before_read(self):
        src,dst=self.source.path.resolve(),self.target.path.resolve()
        before=self.source.load();empty=self.target.load();authority=marker(src)
        atomic_json(authority,dict(journal=str(authority),source=str(src),target=str(dst),
            source_before=before,target_before=empty,committed=False))
        atomic_json(marker(dst),{'journal':str(authority)})
        staged=copy.deepcopy(self.r);staged['status']='RETIRED'
        atomic_json(dst,dict(empty,records=[staged]))
        self.assertEqual(self.target.load()['records'],[])
        self.assertEqual(self.source.get(self.r['id'])['status'],'ACTIVE')

    def test_gate_conflict_has_no_side_effects(self):
        self.target.add(dict(self.c,content='Orion format verbose',agent_scope=['codex'],metadata={'fact_key':'format'}))
        self.source=Memory(Path(self.temp.name)/'conflict-source.json')
        self.r=self.source.add(dict(self.c,metadata={'fact_key':'format'}))['record']
        self.assertEqual(self.move()['decision'],'CONFLICT')
        self.assertEqual(self.source.get(self.r['id'])['status'],'ACTIVE')
        self.assertEqual(len(self.target.load()['records']),1)

    def test_project_and_machine_isolation(self):
        self.move()
        self.assertEqual(self.adapter.inspect('log','Project-Orion','Win10-Admin')['memory_ids'],[self.r['id']])
        for project,machine in [('Project-Other','Win10-Admin'),('Project-Orion','Win11-Admin')]:
            self.assertEqual(self.adapter.inspect('log',project,machine)['memory_ids'],[])

    def test_explicit_global_user_and_hermes_only(self):
        for scope in ([],['hermes'],['codex'],['global']):
            self.target.add(dict(self.c,content='stable preference '+str(scope),type='USER',project=None,
                agent_scope=scope,machine=None,metadata={}))
        rows=self.adapter.inspect('preference',None,'Win10-Admin','retrieve')['results']
        self.assertEqual({tuple(r['record']['agent_scope']) for r in rows},{('codex',),('global',)})

    def test_codex_only_not_hermes_and_explain_why(self):
        self.move()
        self.assertEqual(self.source.search('log',project='Project-Orion',agent='hermes'),[])
        self.assertEqual(self.target.search('log',project='Project-Orion',agent='hermes'),[])
        self.assertEqual(self.adapter.inspect('log','Project-Orion','Win10-Admin','explain',record_id=self.r['id'])['status'],'ACTIVE')
        self.assertTrue(self.adapter.inspect('log','Project-Orion','Win10-Admin','why')['results'])
        with self.assertRaises(ValueError):
            self.adapter.inspect('log','Other','Win10-Admin','explain',record_id=self.r['id'])

    def test_readonly_unrelated_and_duplicate_move(self):
        self.move();before=self.target.path.read_bytes()
        self.assertFalse(self.adapter.inspect('27+15',None,'Win10-Admin')['memory_retrieval_triggered'])
        with self.assertRaises(ValueError):self.adapter.inspect('log','Project-Orion','Win10-Admin','add')
        with self.assertRaises(ValueError):self.move()
        self.assertEqual(before,self.target.path.read_bytes())

    def test_readonly_refuses_recovery_and_writes(self):
        with self.assertRaises(ValueError):
            Memory(self.target.path,read_only=True).add(self.c)
        authority=marker(self.target.path.resolve())
        atomic_json(authority,{'journal':str(authority)})
        before=authority.read_bytes()
        with self.assertRaises(ValueError):Memory(self.target.path,read_only=True).load()
        self.assertEqual(before,authority.read_bytes())
        with self.assertRaises(ValueError):CodexAdapter(ROOT,self.target.path)

    def test_native_and_unscoped_bridge_refused(self):
        with self.assertRaises(ValueError):CodexAdapter(ROOT,Path(self.temp.name)/'native.sqlite')
        with self.assertRaises(ValueError):CodexAdapter(ROOT,Path(self.temp.name)/'.CODEX'/'memory.json')
        with self.assertRaises(ValueError):CodexAdapter(ROOT,Path(self.temp.name)/'native.SQLITE')
        with self.assertRaises(ValueError):self.adapter.call('export')
        with self.assertRaises(ValueError):self.adapter.call('add')

        # Non-interference measures Adapter/CLI access, not a running host's DB quiescence.
        self.move()
        bootstrap = """
import sys, runpy, json, os
opened=[]
def audit(event,args):
    if event.startswith('sqlite3.'):
        raise AssertionError('SQLite access forbidden')
    if event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0]);opened.append(path)
        if '.codex' in path.replace(chr(92),'/').casefold().split('/'):
            raise AssertionError('Native Codex access forbidden')
sys.addaudithook(audit)
sys.argv=['cli',*sys.argv[1:]]
try: runpy.run_module('cli',run_name='__main__')
finally: print(json.dumps(opened),file=sys.stderr)
"""
        original=subprocess.run
        traces=[]
        def traced(command,**kwargs):
            self.assertEqual(command[:5],[sys.executable,'-B','-m','cli','--read-only'])
            result=original([sys.executable,'-B','-c',bootstrap,*command[4:]],**kwargs)
            traces.extend(json.loads(result.stderr))
            return result
        with patch('adapters.codex.adapter.subprocess.run',traced):
            for operation in ('retrieve','smart-retrieve','inject','why','explain'):
                self.adapter.inspect('log','Project-Orion','Win10-Admin',operation,record_id=self.r['id'])
        data_paths={Path(name).resolve() for name in traces if str(name).endswith('.json')}
        self.assertEqual(data_paths,{self.target.path.resolve()})
