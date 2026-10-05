"""Read-only WorkBuddy inspector over the public Memory OS CLI."""
import json
import re
import subprocess
import sys
from pathlib import Path


class WorkBuddyAdapter:
    OPERATIONS = ('retrieve', 'smart-retrieve', 'inject', 'why', 'explain')
    NATIVE_PARTS = {'.workbuddy', '.codebuddy', '.codex', '.hermes', '.agnes',
                    'sessions', 'file-history'}

    def __init__(self, root=None, store=None):
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        self.store = Path(store or self.root / 'storage' / 'workbuddy-memory.json').absolute()
        self._validate_paths()

    def _validate_paths(self):
        # Resolve again before every call: reject symlink/junction aliases too.
        for path in (self.store, Path(str(self.store) + '.smart.json')):
            resolved = path.resolve()
            if self.NATIVE_PARTS & {part.casefold() for part in (*path.parts, *resolved.parts)}:
                raise ValueError('Native memory and history paths are forbidden')
            if resolved.name != path.name:
                raise ValueError('Store aliases are forbidden')
        if self.store.name != 'workbuddy-memory.json':
            raise ValueError('Use an independent workbuddy-memory.json store')
        if Path(str(self.store) + '.move-journal.json').exists():
            raise ValueError('Pending migration requires separate governance recovery')

    def _call(self, *args):
        if not args or args[0] not in ('smart-retrieve', 'explain'):
            raise ValueError('Only scoped read operations are allowed')
        self._validate_paths()
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'cli', '--read-only', '--store',
             str(self.store), *args], cwd=self.root, capture_output=True,
            encoding='utf-8', check=True)
        return json.loads(result.stdout)

    def inspect(self, task, project, machine, operation='inject', budget=1000, record_id=None):
        if operation not in self.OPERATIONS:
            raise ValueError('Read-only operations only')
        if not all(isinstance(value, str) and value.strip() for value in (task, project, machine)):
            raise ValueError('Explicit task, project and machine are required')
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
            raise ValueError('Budget must be a nonnegative integer')
        if re.fullmatch(r'[\d\s+*/().=-]+', task):
            return dict(context='', memory_ids=[], characters=0, memory_retrieval_triggered=False)
        found = self._call('smart-retrieve', task, '--project', project,
                           '--machine', machine, '--agent', 'workbuddy')
        # Public smart-retrieve owns ACTIVE/TTL/project/machine/relevance filtering.
        # Empty agent scopes are intentionally excluded, even for USER records.
        rows = [row for row in found['results'] if
                set(row['record']['agent_scope']) & {'workbuddy', 'global'}]
        selected, lines = [], []
        for row in rows:
            record = row['record']
            line = '[' + record['type'] + '] ' + record['summary']
            if len('\n'.join(lines + [line])) <= budget:
                selected.append(row)
                lines.append(line)
        if operation == 'explain':
            if not any(row['memory_id'] == record_id for row in selected):
                raise ValueError('Record outside allowed context or budget')
            return self._call('explain', record_id)
        if operation == 'why':
            return dict(results=[{k: v for k, v in row.items() if k != 'record'}
                                 for row in selected], memory_retrieval_triggered=True)
        if operation in ('retrieve', 'smart-retrieve'):
            return dict(results=[dict(memory_id=row['memory_id'],
                                      summary=row['record']['summary'],
                                      type=row['record']['type'], score=row['score'])
                                 for row in selected], memory_retrieval_triggered=True)
        context = '\n'.join(lines)
        return dict(context=context, memory_ids=[row['memory_id'] for row in selected],
                    characters=len(context), memory_retrieval_triggered=True,
                    source='agent-memory-os/workbuddy-store', reference_only=True)
