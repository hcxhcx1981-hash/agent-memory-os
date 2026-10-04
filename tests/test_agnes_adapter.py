import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.candidate=dict(content='Project-Nova output format is dense-markdown',type='PROJECT',project='Project-Nova',agent_scope=['agnes-code'],confirmed=True,source_type='user',metadata={'source_agent':'agnes-code','fact_key':'output_format'})
        self.save()
    def save(self):self.c.write_text(json.dumps(self.candidate),encoding='utf-8')
    def write(self):return self.a.remember(self.c,human_confirmed=True)
    def test_write_confirmation(self):
        self.assertEqual(self.a.remember(self.c)['decision'],'NEEDS_CONFIRMATION')
        self.assertEqual(self.write()['decision'],'ACCEPT')
    def test_read_new_router(self):
        self.write();fresh=Adapter(ROOT,self.store)
        self.assertIn('dense-markdown',fresh.context('output format','Project-Nova',needs_memory=True)['context'])
    def test_conflict(self):
        self.write();self.candidate['content']='Project-Nova output format is compact-json';self.save()
        self.assertEqual(self.write()['decision'],'CONFLICT')
        self.assertIn('dense-markdown',self.a.context('output format','Project-Nova',needs_memory=True)['context'])
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
        context=Adapter(ROOT,self.store).context('output format','Project-Nova',needs_memory=True)['context']
        self.assertIn('compact-json',context);self.assertNotIn('dense-markdown',context)
    def test_store_and_project_isolation(self):
        self.write()
        for name in ('hermes-memory.json','codex-memory.json','native.sqlite'):
            with self.assertRaises(ValueError):Adapter(ROOT,Path(self.tmp.name)/name)
        self.assertEqual(self.a.context('output format','Other',needs_memory=True)['context'],'')
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
