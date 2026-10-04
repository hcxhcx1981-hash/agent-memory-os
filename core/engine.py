"""Agent-neutral deterministic memory governance, schema memory_record.v1."""
import json, re, uuid, os
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

TYPES = ('USER','PROJECT','DECISION','WORKFLOW','EPISODIC')
STATUSES = ('ACTIVE','SUPERSEDED','RETIRED','EXPIRED','REJECTED')
def now(): return datetime.now(timezone.utc).isoformat()
def normalized(s): return re.sub(r'\s+', '', s).casefold()
def sensitive(s):
    return bool(re.search(r'(?i)(api[ _-]?key|token|cookie|password|密码|口令|身份证|手机号|私钥|authorization|bearer|secret|session|authentication|认证信息)"?\s*[:=：]|sk-[a-z0-9_-]{8,}|-----BEGIN .*PRIVATE KEY|[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|(?<!\d)\d{17}[\dXx](?!\d)|(?:住址|家庭地址|精确位置)\s*[:：=]', s))

def fact_key(c):
    explicit=c.get('metadata',{}).get('fact_key')
    if explicit: return explicit
    text=c.get('content','')
    match=re.match(r'\s*(默认模型|default model|项目路径|project path|版本|version|状态|status)\s*[:=：]\s*(.+)',text,re.I)
    return match.group(1).casefold() if match else None

class Memory:
    def __init__(self, path, read_only=False):
        self.path=Path(path)
        self.read_only=read_only
    def load(self):
        from core.migration import recover, marker
        if self.read_only and marker(self.path.resolve()).exists():
            raise ValueError("Pending migration; read-only access refused")
        if not self.read_only:
            recover(self.path)
        if not self.path.exists(): return {'schema_version':'memory_store.v1','records':[], 'audit':[]}
        return json.loads(self.path.read_text(encoding='utf-8'))
    def save(self, data):
        if self.read_only:
            raise ValueError("Read-only store cannot write")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(temp,self.path)
    def audit(self,d,event,ids,reason,source):
        d['audit'].append(dict(timestamp=now(),event=event,memory_ids=ids,reason=reason,source_type=source))
    def evaluate(self,c,d=None):
        d=self.load() if d is None else d
        if not isinstance(c,dict): return dict(decision='REJECT',reason='Candidate must be an object')
        text=c.get('content',''); kind=c.get('type')
        if not isinstance(text,str) or not text.strip(): return dict(decision='REJECT',reason='Empty content')
        # Scan every caller-supplied field before anything can be persisted.
        if sensitive(json.dumps(c,ensure_ascii=False)): return dict(decision='REJECT',reason='Sensitive data')
        if c.get('source_type','user') not in ('user','import','system','model'): return dict(decision='REJECT',reason='Invalid source type')
        if c.get('source_type')=='model' or c.get('confirmed') is not True or re.search(r'大概|可能|猜测|probably|perhaps',text,re.I):
            return dict(decision='REJECT',reason='Unconfirmed fact or model inference')
        if len(text)>2000 or re.search(r'(^|\n)(user|assistant|system)\s*:|Traceback|DEBUG\s',text,re.I):
            return dict(decision='REJECT',reason='Raw chat/log or oversized candidate')
        if kind is None:
            kind='EPISODIC' if re.search(r'今天|暂时|today|temporary',text,re.I) else 'PROJECT' if re.search(r'路径|版本|架构|path|version',text,re.I) else 'WORKFLOW' if re.search(r'流程|规则|SOP|workflow',text,re.I) else 'DECISION' if re.search(r'默认模型|决定|decision|default model',text,re.I) else 'USER'
        if kind not in TYPES: return dict(decision='REJECT',reason='Invalid memory type')
        if re.search(r'今天|暂时|today|temporary',text,re.I): kind='EPISODIC'
        if not isinstance(c.get('priority',50),int) or not 0<=c.get('priority',50)<=100: return dict(decision='REJECT',reason='Invalid priority')
        if not isinstance(c.get('confidence',1), (int,float)) or not 0<=c.get('confidence',1)<=1: return dict(decision='REJECT',reason='Invalid confidence')
        for field in ('title','summary'):
            if field in c and not isinstance(c[field],str): return dict(decision='REJECT',reason='Invalid required text field')
        for field in ('title','summary','project','machine'):
            if c.get(field) is not None and not isinstance(c[field],str): return dict(decision='REJECT',reason='Invalid text field')
        for field in ('tags','agent_scope'):
            if not isinstance(c.get(field,[]),list) or any(not isinstance(x,str) for x in c.get(field,[])): return dict(decision='REJECT',reason='Invalid list field')
        if not isinstance(c.get('metadata',{}),dict): return dict(decision='REJECT',reason='Invalid metadata')
        if c.get('confidence',1)<0.8: return dict(decision='REJECT',reason='Low confidence')
        if c.get('expires_at'):
            try:
                expiry=datetime.fromisoformat(c['expires_at'])
                if expiry.tzinfo is None: raise ValueError('Timezone required')
            except (ValueError,TypeError): return dict(decision='REJECT',reason='Invalid expiry')
        active=[r for r in d['records'] if r['status']=='ACTIVE' and not self.expired(r) and r['project']==c.get('project') and r['agent_scope']==c.get('agent_scope',[]) and r['machine']==c.get('machine')]
        key=fact_key(c)
        conflicts=[]
        for r in active:
            if normalized(text)==normalized(r['content']): return dict(decision='DUPLICATE',reason='Exact duplicate',memory_id=r['id'],type=kind)
            if key and fact_key(r)==key:
                conflicts.append(r['id']); continue
            if SequenceMatcher(None,normalized(text),normalized(r['content'])).ratio()>=0.92:
                return dict(decision='DUPLICATE',reason='Near duplicate; retain existing fact',memory_id=r['id'],type=kind)
        parent=c.get('metadata',{}).get('supplements')
        if parent:
            old=next((r for r in active if r['id']==parent),None)
            if old is None or normalized(old['content']) not in normalized(text): return dict(decision='REJECT',reason='Supplement must retain original content and scope')
            if not conflicts: return dict(decision='UPDATE',reason='Explicit additive supplement',memory_id=parent,type=kind)
        if conflicts: return dict(decision='CONFLICT',reason='Fact changed; explicit supersede required',conflicts_with=conflicts,type=kind)
        return dict(decision='ACCEPT',reason='Confirmed bounded candidate',type=kind)
    def expired(self,r):
        return bool(r['expires_at'] and datetime.fromisoformat(r['expires_at']).astimezone(timezone.utc)<=datetime.now(timezone.utc))
    def record(self,c,kind):
        stamp=now()
        return dict(schema_version='memory_record.v1',id=str(uuid.uuid4()),type=kind,status='ACTIVE',title=c.get('title',c['content'][:80]),content=c['content'],summary=c.get('summary',c['content'][:200]),tags=c.get('tags',[]),project=c.get('project'),machine=c.get('machine'),agent_scope=c.get('agent_scope',[]),priority=c.get('priority',50),confidence=c.get('confidence',1.0),source_type=c.get('source_type','user'),created_at=stamp,updated_at=stamp,expires_at=c.get('expires_at') or ((datetime.now(timezone.utc)+timedelta(days=7)).isoformat() if kind=='EPISODIC' else None),supersedes=[],superseded_by=None,conflicts_with=[],metadata=c.get('metadata',{}))
    def add(self,c):
        d=self.load(); v=self.evaluate(c,d)
        if v['decision']=='ACCEPT':
            r=self.record(c,v['type']);d['records'].append(r);self.audit(d,'CREATE',[r['id']],v['reason'],r['source_type']);v['record']=r
        elif v['decision']=='UPDATE':
            r=next(r for r in d['records'] if r['id']==v['memory_id'])
            before={k:r[k] for k in ('content','summary','updated_at')}
            r.update(content=c['content'],summary=c.get('summary',c['content'][:200]),updated_at=now())
            self.audit(d,'UPDATE',[r['id']],v['reason'],r['source_type'])
            d['audit'][-1]['before']=before
            v['record']=r
        elif v['decision'] in ('REJECT','CONFLICT'):
            # Do not retain rejected candidate text, metadata, or credentials.
            self.audit(d,'REJECT',v.get('conflicts_with',[]),v['reason'],'gate')
        self.save(d);return v
    def get(self,id):
        return next(r for r in self.load()['records'] if r['id']==id)
    def supersede(self,id,c,reason):
        d=self.load();old=next(r for r in d['records'] if r['id']==id)
        if old['status']!='ACTIVE' or self.expired(old): raise ValueError('Only active records can be superseded')
        for field in ('project','machine','agent_scope'):
            c.setdefault(field,old[field])
            if c[field]!=old[field]: raise ValueError('Supersede scope mismatch')
        c.setdefault('type',old['type']);c.setdefault('metadata',old['metadata'])
        v=self.evaluate(c,d)
        if v['decision'] not in ('ACCEPT','CONFLICT'): return v
        if set(v.get('conflicts_with',[]))-{id}: raise ValueError('Resolve other conflicts first')
        if sensitive(reason): raise ValueError('Sensitive reason')
        new=self.record(c,v['type']);new['supersedes']=[id]
        old.update(status='SUPERSEDED',superseded_by=new['id'],updated_at=now())
        d['records'].append(new);self.audit(d,'SUPERSEDE',[id,new['id']],reason,new['source_type']);self.audit(d,'CREATE',[new['id']],'Replacement record',new['source_type']);self.save(d)
        return dict(decision='ACCEPT',reason=reason,record=new)
    def retire(self,id,reason):
        if sensitive(reason): raise ValueError('Sensitive reason')
        d=self.load();r=next(r for r in d['records'] if r['id']==id)
        if r['status']!='ACTIVE': raise ValueError('Only active records can be retired')
        r.update(status='RETIRED',updated_at=now());self.audit(d,'RETIRE',[id],reason,r['source_type']);self.save(d);return r
    def expire(self):
        d=self.load();ids=[]
        for r in d['records']:
            if r['status']=='ACTIVE' and self.expired(r):
                r.update(status='EXPIRED',updated_at=now());ids.append(r['id']);self.audit(d,'EXPIRE',[r['id']],'TTL elapsed',r['source_type'])
        self.save(d);return ids
    def search(self,task='',project=None,agent=None,kind=None,limit=10):
        words=re.findall(r'\w+',task.casefold()); matches=[]
        for r in self.load()['records']:
            if r['status']!='ACTIVE' or self.expired(r): continue
            if r['project'] is not None and r['project']!=project: continue
            if r['agent_scope'] and agent not in r['agent_scope'] and 'global' not in r['agent_scope']: continue
            if kind and r['type']!=kind: continue
            hay=(r['title']+' '+r['content']+' '+' '.join(r['tags'])).casefold()
            relevance=sum(w in hay for w in words)
            if words and not relevance: continue
            matches.append((relevance,r['priority'],r['updated_at'],r))
        matches.sort(key=lambda x:x[:3],reverse=True)
        return [x[3] for x in matches[:max(0,limit)]]
    def inject(self,task,project=None,agent=None,budget=1000):
        lines=[];ids=[]
        for r in self.search(task,project,agent,limit=100):
            line=f"[{r['type']}] {r['summary']}"
            if len('\n'.join(lines+[line]))>budget: continue
            lines.append(line);ids.append(r['id'])
        return dict(context='\n'.join(lines),memory_ids=ids,characters=len('\n'.join(lines)),budget=budget)
