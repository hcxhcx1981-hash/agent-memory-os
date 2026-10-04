import json
import tempfile
import unittest
from pathlib import Path
from core.engine import Memory

class EmptyStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'memory.json';self.memory=Memory(self.path)
        self.c=dict(content='Fictional Nova color is amber',type='PROJECT',project='Nova',confirmed=True,source_type='user')
    def test_missing_store_add(self):
        self.assertEqual(self.memory.add(self.c)['decision'],'ACCEPT')
        self.assertEqual(self.memory.load()['schema_version'],'memory_store.v1')
    def test_empty_evaluate(self):
        self.path.write_text('{}',encoding='utf-8')
        self.assertEqual(self.memory.evaluate(self.c)['decision'],'ACCEPT')
        self.assertEqual(self.path.read_text(encoding='utf-8'),'{}')
    def test_empty_add(self):
        self.path.write_text('{}',encoding='utf-8')
        self.assertEqual(self.memory.add(self.c)['decision'],'ACCEPT')
        self.assertEqual(len(self.memory.load()['records']),1)
        self.assertEqual(len(self.memory.load()['audit']),1)
    def test_partial_and_standard(self):
        for data in ({'records':[]},{'audit':[]},{'schema_version':'memory_store.v1'},{'schema_version':'memory_store.v1','records':[],'audit':[]}):
            with self.subTest(data=data):
                self.path.write_text(json.dumps(data),encoding='utf-8')
                self.assertEqual(self.memory.load(),dict(schema_version='memory_store.v1',records=[],audit=[]))
    def test_invalid_records(self):
        self.check_bad('{"records":{}}','records')
    def test_invalid_audit(self):
        self.check_bad('{"audit":null}','audit')
    def test_malformed(self):
        self.check_bad('{broken','')
    def test_wrong_root_or_schema(self):
        for text in ('[]','null','{"schema_version":"unknown"}'):
            self.check_bad(text,'')
    def check_bad(self,text,message):
        self.path.write_text(text,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,message):self.memory.add(self.c)
        self.assertEqual(self.path.read_text(encoding='utf-8'),text)
