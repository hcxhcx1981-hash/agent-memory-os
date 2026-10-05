"""Thin Agnes Code router using only the public Memory OS CLI."""
import json
import re
import subprocess
import sys
from pathlib import Path

class AgnesCodeAdapter:
    NATIVE_PARTS={'.agnes','.codex','.hermes','.workbuddy','.codebuddy','sessions','file-history'}
    READ_COMMANDS={'get','retrieve','inject','smart-retrieve','smart-inject','why','explain'}
    def __init__(self, project_root, store=None):
        self.root=Path(project_root).resolve()
        self.store=Path(store or self.root/'storage'/'agnes-code-memory.json').absolute()
        self._validate_store()
    def _validate_store(self):
        if self.store.name!='agnes-code-memory.json':
            raise ValueError('Use an independent Memory OS Agnes Code store')
        for path in (self.store,Path(str(self.store)+'.smart.json')):
            resolved=path.resolve()
            if self.NATIVE_PARTS & {p.casefold() for p in (*path.parts,*resolved.parts)} or resolved.name!=path.name:
                raise ValueError('Native memory and store aliases are forbidden')
        if Path(str(self.store)+'.move-journal.json').exists():
            raise ValueError('Pending migration requires separate governance recovery')
    def call(self,*args):
        self._validate_store()
        readonly=['--read-only'] if args and args[0] in self.READ_COMMANDS else []
        result=subprocess.run([sys.executable,'-B','-m','cli',*readonly,'--store',str(self.store),*args],cwd=self.root,capture_output=True,encoding='utf-8',check=True)
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
    def context(self,task,project,*,machine=None,needs_memory=False,budget=500):
        if needs_memory is not True or re.fullmatch(r'[0-9\s+*/().=-]+',task):
            return {'context':'','memory_ids':[],'memory_retrieval_triggered':False}
        return self.inspect(task,project,machine,budget=budget)
    def inspect(self,task,project,machine,operation='inject',budget=500,record_id=None):
        if operation not in ('inject','retrieve','smart-retrieve','why','explain'):
            raise ValueError('Inspector is read-only')
        if not all(isinstance(v,str) and v.strip() for v in (task,project,machine)):
            raise ValueError('Explicit task, project and machine required')
        if not isinstance(budget,int) or isinstance(budget,bool) or budget<0:
            raise ValueError('Nonnegative character budget required')
        if re.fullmatch(r'[0-9\s+*/().=-]+',task):
            return {'context':'','memory_ids':[],'memory_retrieval_triggered':False}
        found=self.call('smart-retrieve',task,'--project',project,'--machine',machine,'--agent','agnes-code')
        rows=[row for row in found['results'] if set(row['record']['agent_scope']) & {'agnes-code','global'}]
        selected,lines=[],[]
        for row in rows:
            r=row['record'];line='['+r['type']+'] '+r['summary']
            if len('\n'.join(lines+[line]))<=budget:
                selected.append(row);lines.append(line)
        if operation=='explain':
            if not any(row['memory_id']==record_id for row in selected):
                raise ValueError('Record outside allowed context or budget')
            return self.call('explain',record_id)
        if operation=='why':
            return dict(results=[{k:v for k,v in row.items() if k!='record'} for row in selected],memory_retrieval_triggered=True)
        if operation in ('retrieve','smart-retrieve'):
            return dict(results=[dict(memory_id=row['memory_id'],summary=row['record']['summary'],score=row['score']) for row in selected],memory_retrieval_triggered=True)
        context='\n'.join(lines)
        return dict(context=context,memory_ids=[row['memory_id'] for row in selected],characters=len(context),memory_retrieval_triggered=True,source='agent-memory-os/agnes-code-store',reference_only=True)
    def supersede(self,old_id,candidate_file,reason,*,human_confirmed=False):
        path=self.candidate(candidate_file,human_confirmed)
        if path is None:return {'decision':'NEEDS_CONFIRMATION'}
        old=self.call('get',old_id)
        new=json.loads(Path(path).read_text(encoding='utf-8'))
        if old['agent_scope']!=['agnes-code'] or old['project']!=new['project']:
            raise ValueError('Record outside Agnes Code project scope')
        return self.call('supersede',old_id,'--candidate',path,'--reason',reason)
