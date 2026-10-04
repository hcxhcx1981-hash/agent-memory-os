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
