import unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
from adapters.hermes import router

class RouterTests(unittest.TestCase):
    def test_public_cli_store_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(router, 'STORE', Path(t)/'isolated.json'):
                self.assertEqual(router.call('retrieve','default_theme','--project','Other','--agent','hermes'), [])
    def test_diagnostics_exclude_context(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'trace.jsonl'
            with patch.object(router,'TRACE',target), patch('builtins.print'):
                router.emit({'MEMORY_RETRIEVAL_TRIGGERED': True, 'INJECTED_MEMORY_IDS': [], 'context': 'fictional-context'})
            event=json.loads(target.read_text())
            self.assertNotIn('context',event)
            self.assertTrue(event['MEMORY_RETRIEVAL_TRIGGERED'])

    def test_v011_write_read_conflict_supersede_regression(self):
        import subprocess,sys
        from core.engine import Memory
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'host.json';trace=Path(t)/'trace.jsonl'
            def run(action,*args):
                cmd=[sys.executable,str(root/'adapters/hermes/router.py'),action,'--store',str(store),'--trace',str(trace),'--project','Project-Mercury',*args]
                result=subprocess.run(cmd,cwd=root,capture_output=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return json.loads(result.stdout)
            first=run('write','--value','graphite-purple','--user-confirmed')
            self.assertEqual(first['MEMORY_DECISION'],'ACCEPT');old=first['MEMORY_ID']
            self.assertEqual(run('read')['INJECTED_MEMORY_IDS'],[old])
            conflict=run('write','--value','obsidian-green','--user-confirmed')
            self.assertTrue(conflict['CONFLICT_TRIGGERED'])
            self.assertEqual(Memory(store).get(old)['status'],'ACTIVE')
            new=run('supersede','--id',old,'--value','obsidian-green','--user-confirmed')['MEMORY_ID']
            self.assertEqual(run('read')['INJECTED_MEMORY_IDS'],[new])
            self.assertEqual(Memory(store).get(old)['superseded_by'],new)
            self.assertEqual(Memory(store).get(new)['supersedes'],[old])
            self.assertNotIn('context',trace.read_text())
    def test_observation_recommendation_no_silent_promotion(self):
        import subprocess,sys
        from core.engine import Memory
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'host.json';trace=Path(t)/'trace.jsonl'
            for index in range(3):
                p=subprocess.run([sys.executable,str(root/'adapters/hermes/router.py'),'observe','--text','用户偏好黑紫配色','--store',str(store),'--trace',str(trace)],cwd=root,capture_output=True,encoding='utf-8')
                self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
                self.assertEqual(r['MEMORY_DECISION'],'OBSERVED')
                self.assertIn('MEMORY_REASON',r)
                self.assertEqual(r['PROMOTION_EVIDENCE']['repeat_count'],index+1)
                self.assertEqual(r['PROMOTION_RECOMMENDED'],index==2)
            self.assertEqual(Memory(store).load()['records'],[])
