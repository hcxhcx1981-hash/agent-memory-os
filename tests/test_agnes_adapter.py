import importlib.util
import json
import tempfile
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta, timezone
import unittest
from pathlib import Path
from unittest.mock import patch
from core.engine import Memory
from tests.test_workbuddy_adapter import AUDITED_ENTRY

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('agnes_adapter',ROOT/'adapters/agnes-code/adapter.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Adapter=module.AgnesCodeAdapter

class AgnesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Path(self.tmp.name)/'agnes-code-memory.json';self.store.write_text('{}',encoding='utf-8')
        self.a=Adapter(ROOT,self.store)
        self.c=Path(self.tmp.name)/'candidate.json'
        self.candidate=dict(content='Project-Nova output format is dense-markdown',type='PROJECT',project='Project-Nova',machine='Mac-Win10',agent_scope=['agnes-code'],confirmed=True,source_type='user',metadata={'source_agent':'agnes-code','fact_key':'output_format'})
        self.save()
    def save(self):self.c.write_text(json.dumps(self.candidate),encoding='utf-8')
    def write(self):return self.a.remember(self.c,human_confirmed=True)
    def test_write_confirmation(self):
        self.assertEqual(self.a.remember(self.c)['decision'],'NEEDS_CONFIRMATION')
        self.assertEqual(self.write()['decision'],'ACCEPT')
    def test_read_new_router(self):
        self.write();fresh=Adapter(ROOT,self.store)
        self.assertIn('dense-markdown',fresh.context('output format','Project-Nova',machine='Mac-Win10',needs_memory=True)['context'])
    def test_conflict(self):
        self.write();self.candidate['content']='Project-Nova output format is compact-json';self.save()
        self.assertEqual(self.write()['decision'],'CONFLICT')
        self.assertIn('dense-markdown',self.a.context('output format','Project-Nova',machine='Mac-Win10',needs_memory=True)['context'])
    def test_supersede_new_router(self):
        old=self.write()['record']['id'];self.candidate['content']='Project-Nova output format is compact-json';self.save()
        self.assertEqual(self.a.supersede(old,self.c,'Confirmed replacement')['decision'],'NEEDS_CONFIRMATION')
        with patch.object(self.a,'call',wraps=self.a.call) as calls:
            result=self.a.supersede(old,self.c,'Confirmed replacement',human_confirmed=True)
            self.assertEqual(result['decision'],'ACCEPT')
            self.assertNotIn('add',[c.args[0] for c in calls.call_args_list])
        previous=self.a.call('get',old);replacement=self.a.call('get',result['record']['id'])
        self.assertEqual(previous['status'],'SUPERSEDED')
        self.assertEqual(previous['superseded_by'],replacement['id'])
        self.assertEqual(replacement['supersedes'],[old])
        self.assertEqual(replacement['status'],'ACTIVE')
        context=Adapter(ROOT,self.store).context('output format','Project-Nova',machine='Mac-Win10',needs_memory=True)['context']
        self.assertIn('compact-json',context);self.assertNotIn('dense-markdown',context)
    def test_store_and_project_isolation(self):
        self.write()
        for name in ('hermes-memory.json','codex-memory.json','workbuddy-memory.json','native.sqlite'):
            with self.assertRaises(ValueError):Adapter(ROOT,Path(self.tmp.name)/name)
        self.assertEqual(self.a.context('output format','Other',machine='Mac-Win10',needs_memory=True)['context'],'')
        self.assertEqual(self.a.call('retrieve','output format','--project','Project-Nova','--agent','hermes'),[])
        self.assertEqual(self.a.call('retrieve','output format','--project','Project-Nova','--agent','codex'),[])
    def test_unrelated_no_cli(self):
        with patch.object(self.a,'call',side_effect=AssertionError('Must skip CLI')):
            self.assertEqual(self.a.context('27+15','Project-Nova',needs_memory=True)['context'],'')
            self.assertEqual(self.a.context('unrelated','Project-Nova')['context'],'')
    def test_model_and_wrong_scope(self):
        self.candidate['source_type']='model';self.save()
        self.assertEqual(self.write()['decision'],'NEEDS_CONFIRMATION')
        self.candidate['source_type']='user';self.candidate['agent_scope']=['hermes'];self.save()
        with self.assertRaises(ValueError):self.write()
    def test_machine_and_other_agent_isolation(self):
        own=self.write()['record']['id']
        for scope in ([],['workbuddy'],['codex'],['hermes'],['global']):
            result=Memory(self.store).add(dict(self.candidate,content='output format '+str(scope),agent_scope=scope,metadata={}))
            self.assertEqual(result['decision'],'ACCEPT')
        result=self.a.inspect('output format','Project-Nova','Mac-Win10')
        self.assertIn(own,result['memory_ids'])
        self.assertEqual(len(result['memory_ids']),2)  # own and explicit global
        self.assertTrue(result['reference_only'])
        self.assertEqual(self.a.inspect('output format','Project-Nova','Other')['memory_ids'],[])
        with self.assertRaises(ValueError):self.a.context('output format','Project-Nova',needs_memory=True)
    def test_budget_relevance_and_lifecycle(self):
        record=self.write()['record']
        self.assertEqual(self.a.inspect('output format','Project-Nova','Mac-Win10',budget=0)['memory_ids'],[])
        self.assertEqual(self.a.inspect('cooking','Project-Nova','Mac-Win10')['memory_ids'],[])
        self.assertFalse(self.a.inspect('27+15','Project-Nova','Mac-Win10')['memory_retrieval_triggered'])
        Memory(self.store).retire(record['id'],'fictional test')
        expiry=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        result=Memory(self.store).add(dict(self.candidate,content='expired output format',type='EPISODIC',expires_at=expiry))
        self.assertEqual(result['decision'],'ACCEPT')
        self.assertEqual(self.a.inspect('output format','Project-Nova','Mac-Win10')['memory_ids'],[])
    def test_why_explain_and_readonly(self):
        mid=self.write()['record']['id'];before=self.store.read_bytes()
        self.assertEqual(self.a.inspect('output format','Project-Nova','Mac-Win10','why')['results'][0]['memory_id'],mid)
        self.assertEqual(self.a.inspect('output format','Project-Nova','Mac-Win10','explain',record_id=mid)['status'],'ACTIVE')
        for operation in ('retrieve','smart-retrieve','inject'):
            self.a.inspect('output format','Project-Nova','Mac-Win10',operation)
        self.assertEqual(before,self.store.read_bytes())
        with self.assertRaises(ValueError):self.a.inspect('output format','Other','Mac-Win10','explain',record_id=mid)
        with self.assertRaises(ValueError):self.a.inspect('output format','Project-Nova','Mac-Win10','add')
        r=subprocess.run([sys.executable,'-B','-m','cli','--read-only','--store',str(self.store),'retire',mid,'--reason','fictional'],cwd=ROOT,capture_output=True)
        self.assertNotEqual(r.returncode,0);self.assertEqual(before,self.store.read_bytes())
    def test_native_paths_and_migration_refused(self):
        for part in ('.agnes','.AGNES','.workbuddy','.codebuddy','.hermes','.codex','sessions','file-history'):
            with self.assertRaises(ValueError):Adapter(ROOT,Path(self.tmp.name)/part/'agnes-code-memory.json')
        Path(str(self.store)+'.move-journal.json').write_text('{}')
        with self.assertRaises(ValueError):self.a.inspect('output format','Project-Nova','Mac-Win10')
    def test_scoped_inspector_and_cli_access_audit(self):
        mid=self.write()['record']['id'];before=hashlib.sha256(self.store.read_bytes()).hexdigest()
        bootstrap=AUDITED_ENTRY.replace('adapters.workbuddy.inspector','adapters.agnes-code.inspector')
        paths=set()
        for operation in ('inject','retrieve','smart-retrieve','why','explain'):
            args=[operation,'--store',str(self.store),'--task','output format','--project','Project-Nova','--machine','Mac-Win10']
            if operation=='explain':args+=['--id',mid]
            r=subprocess.run([sys.executable,'-B','-c',bootstrap,'inspector',bootstrap,*args],cwd=ROOT,capture_output=True,encoding='utf-8',check=True)
            for line in r.stderr.splitlines():
                if line.startswith('AUDIT='):paths.update(Path(p).resolve() for p in json.loads(line[6:]) if p.endswith('.json'))
        self.assertEqual(paths,{self.store.resolve()})
        self.assertEqual(before,hashlib.sha256(self.store.read_bytes()).hexdigest())
