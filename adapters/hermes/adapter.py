"""Reference adapter. Only the public CLI is used; no direct storage access."""
import json, subprocess, sys
from pathlib import Path

class HermesAdapter:
    def __init__(self, project_root, store):
        self.root = Path(project_root).resolve()
        self.store = str(Path(store).resolve())
    def call(self, *args):
        result = subprocess.run([sys.executable, '-m', 'cli', '--store', self.store, *args], cwd=self.root, capture_output=True, text=True, encoding='utf-8', check=True)
        return json.loads(result.stdout)
    def remember(self, candidate_file):
        path = str(Path(candidate_file).resolve())
        verdict = self.call('evaluate', '--candidate', path)
        if verdict['decision'] == 'ACCEPT':
            return self.call('add', '--candidate', path)
        return verdict
    def context(self, task, project):
        return self.call('inject', task, '--project', project, '--agent', 'hermes')
