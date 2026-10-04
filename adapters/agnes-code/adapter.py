"""Thin Agnes Code router using only the public Memory OS CLI."""
import json
import re
import subprocess
import sys
from pathlib import Path

class AgnesCodeAdapter:
    def __init__(self, project_root, store=None):
        self.root=Path(project_root).resolve()
        self.store=Path(store or self.root/'storage'/'agnes-code-memory.json').resolve()
        if self.store.name in ('hermes-memory.json','codex-memory.json') or self.store.suffix.casefold() in ('.sqlite','.db') or {'.agnes','.codex'} & {p.casefold() for p in self.store.parts}:
            raise ValueError('Use an independent Memory OS Agnes Code store')
    def call(self,*args):
        result=subprocess.run([sys.executable,'-B','-m','cli','--store',str(self.store),*args],cwd=self.root,capture_output=True,encoding='utf-8',check=True)
        return json.loads(result.stdout)
    def candidate(self,path,human_confirmed):
        if human_confirmed is not True:return None
        path=Path(path).resolve()
        candidate=json.loads(path.read_text(encoding='utf-8'))
        if candidate.get('confirmed') is not True or candidate.get('source_type')=='model':return None
        if candidate.get('agent_scope')!=['agnes-code'] or not candidate.get('project'):
            raise ValueError('Explicit Agnes Code scope and project required')
        return str(path)
    def remember(self,candidate_file,*,human_confirmed=False):
        path=self.candidate(candidate_file,human_confirmed)
        if path is None:return {'decision':'NEEDS_CONFIRMATION'}
        verdict=self.call('evaluate','--candidate',path)
        return self.call('add','--candidate',path) if verdict['decision']=='ACCEPT' else verdict
    def context(self,task,project,*,needs_memory=False,budget=500):
        if needs_memory is not True or re.fullmatch(r'[0-9\s+*/().=-]+',task):
            return {'context':'','memory_ids':[],'memory_retrieval_triggered':False}
        if not task.strip() or not project:raise ValueError('Task and project required')
        scope=['--project',project,'--agent','agnes-code']
        if not self.call('retrieve',task,*scope):return {'context':'','memory_ids':[]}
        return self.call('inject',task,*scope,'--budget',str(budget))
    def supersede(self,old_id,candidate_file,reason,*,human_confirmed=False):
        path=self.candidate(candidate_file,human_confirmed)
        if path is None:return {'decision':'NEEDS_CONFIRMATION'}
        old=self.call('get',old_id)
        new=json.loads(Path(path).read_text(encoding='utf-8'))
        if old['agent_scope']!=['agnes-code'] or old['project']!=new['project']:
            raise ValueError('Record outside Agnes Code project scope')
        return self.call('supersede',old_id,'--candidate',path,'--reason',reason)
