"""On-demand read-only adapter; native Codex memory is never accessed."""
import json
import re
import subprocess
import sys
from pathlib import Path

class CodexAdapter:
    def __init__(self, root=None, store=None):
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        self.store = Path(store or self.root / 'storage' / 'codex-memory.json').resolve()
        if '.codex' in {part.casefold() for part in self.store.parts} or self.store.suffix.casefold() in ('.sqlite', '.db'):
            raise ValueError('Native databases and native Codex directories are forbidden')
        if Path(str(self.store) + '.move-journal.json').exists():
            raise ValueError('Pending move requires governance recovery before read-only inspection')
        if self.store == (self.root / 'storage' / 'hermes-memory.json').resolve():
            raise ValueError('Codex must not use the Hermes store')

    def call(self, *args):
        if not args or args[0] not in ('smart-retrieve', 'explain'):
            raise ValueError('Private CLI bridge accepts scoped read operations only')
        result = subprocess.run([sys.executable, '-B', '-m', 'cli', '--read-only', '--store', str(self.store), *args],
            cwd=self.root, capture_output=True, encoding='utf-8', check=True)
        return json.loads(result.stdout)

    def inspect(self, task, project, machine, operation='inject', budget=1000, record_id=None):
        if operation not in ('retrieve', 'smart-retrieve', 'inject', 'why', 'explain'):
            raise ValueError('Read-only operations only')
        if not task.strip() or not machine:
            raise ValueError('Task and explicit machine required')
        if budget < 0:
            raise ValueError('Budget must be nonnegative')
        if re.fullmatch(r'[\d\s+*/().=-]+', task):
            return dict(context='', memory_ids=[], characters=0, memory_retrieval_triggered=False)
        found = self.call('smart-retrieve', task, '--machine', machine, '--agent', 'codex',
                          *(['--project', project] if project else []))
        rows = [row for row in found['results'] if
                set(row['record']['agent_scope']) & {'codex', 'global'}]
        if operation == 'explain':
            if not any(row['memory_id'] == record_id for row in rows):
                raise ValueError('Record outside allowed context')
            return self.call('explain', record_id)
        if operation in ('retrieve', 'smart-retrieve'):
            return dict(results=rows, memory_retrieval_triggered=True)
        if operation == 'why':
            return dict(results=[{k:v for k,v in row.items() if k!='record'} for row in rows],
                        memory_retrieval_triggered=True)
        lines, ids = [], []
        for row in rows:
            record = row['record']
            line = '[' + record['type'] + '] ' + record['summary']
            if len('\n'.join(lines + [line])) <= budget:
                lines.append(line);ids.append(record['id'])
        return dict(context='\n'.join(lines), memory_ids=ids, characters=len('\n'.join(lines)),
                    memory_retrieval_triggered=True, source='agent-memory-os/codex-store')
