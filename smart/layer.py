"""Optional deterministic smart layer. Core records retain memory_record.v1."""
import copy
import hashlib
import json
import math
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Protocol
from core.engine import Memory, sensitive, normalized, fact_key, now

class Judge(Protocol):
    """Optional future judge: recommendations only, never write authority."""
    def judge(self, candidate: dict) -> dict: ...

class SemanticRetriever(Protocol):
    """Future scoring interface; caller must still enforce lifecycle/scope."""
    def relevance(self, task: str, record: dict) -> float: ...

class SemanticJudge:
    def judge(self, c):
        text=c.get('content','') if isinstance(c,dict) else ''
        result=dict(should_remember=False,memory_type='EPISODIC',stability_score=0.2,
                    future_value_score=0.2,confidence=0.8,reason='No clear durable meaning',
                    suggested_fact_key=None,suggested_scope={},suggested_ttl=604800,risk_flags=[])
        if not isinstance(text,str) or not text.strip():
            result['risk_flags']=['invalid'];return result
        if not isinstance(c.get('metadata',{}),dict):
            result.update(reason='Invalid metadata',risk_flags=['invalid']);return result
        if sensitive(json.dumps(c,ensure_ascii=False)):
            result.update(reason='Sensitive candidate',risk_flags=['sensitive']);return result
        if c.get('source_type')=='model' or re.search(r'可能|大概|猜测|也许|probably|perhaps|might',text,re.I):
            result.update(reason='Inference cannot become a permanent fact',risk_flags=['inference']);return result
        if re.search(r'心情|情绪|mood|sad today',text,re.I):
            result.update(reason='Transient personal state',risk_flags=['transient_private']);return result
        if len(text)>2000 or re.search(r'(^|\n)(user|assistant|system)\s*:|Traceback|DEBUG\s',text,re.I):
            result.update(reason='Unfiltered chat/log',risk_flags=['raw_input']);return result
        temporary=bool(re.search(r'今天|暂时|这次|today|temporary|this time',text,re.I))
        durable=bool(re.search(r'以后|长期|一直|总是|每次|默认|forever|always|default|from now',text,re.I)) or (c.get('metadata',{}).get('trusted_explicit_intent') is True and c.get('confirmed') is True and c.get('source_type','user')=='user')
        preference=bool(re.search(r'喜欢|偏好|不喜欢|只用于|prefer|like|avoid',text,re.I))
        alias=re.search(r'(?:以后\s*)?([A-Za-z][\w-]*)\s*(?:就是|代表|means)\s*(.+)',text,re.I)
        project_fact=bool(re.search(r'[A-Za-z]:[\\/]|项目路径|项目.*架构|project.*path|版本|version',text,re.I))
        kind=c.get('type') or ('WORKFLOW' if alias else 'PROJECT' if project_fact or c.get('project') else 'USER' if preference or durable else 'EPISODIC')
        stability=0.95 if durable or alias or project_fact else 0.75 if preference else 0.4
        future=0.95 if alias or project_fact else 0.85 if durable or preference else 0.4
        if temporary:kind='EPISODIC';stability=0.2;future=0.3
        scope={k:c[k] for k in ('project','machine','agent_scope') if c.get(k)}
        if 'machine' not in scope:
            machine=re.search(r'Win(?:10|11)|Windows\s*(?:10|11)',text,re.I)
            if machine:scope['machine']=canonical_machine(machine.group())
        key=fact_key(c)
        if alias:key='alias.'+alias.group(1).casefold()
        if not key and preference:key='ui.preference' if re.search(r'UI|配色|背景|主题',text,re.I) else 'user.preference'
        result.update(should_remember=durable or preference or alias is not None or project_fact or temporary,
                      memory_type=kind,stability_score=stability,future_value_score=future,
                      reason='Explicit durable meaning' if durable or alias or project_fact else 'Repeated preference may become stable' if preference else 'Temporary context only',
                      suggested_fact_key=key,suggested_scope=scope,suggested_ttl=604800 if temporary or kind=='EPISODIC' else None)
        return result

def revision(record):
    return hashlib.sha256(json.dumps([record['content'],record['summary'],record['updated_at']],ensure_ascii=False).encode()).hexdigest()

def canonical_machine(value):
    return re.sub(r'[\s_-]+','',value.casefold()).replace('windows','win') if value else None

def primary_interaction_color(text):
    text=normalized(text)
    match=re.search(r'(紫色|蓝色|绿色|红色|橙色|黄色)(?:为|是|作为)主交互色|主交互色(?:改为|为|是|[:=：])(紫色|蓝色|绿色|红色|橙色|黄色)',text)
    return next((value for value in match.groups() if value),None) if match else None

def direct_contradiction(a,b):
    color_a,color_b=primary_interaction_color(a),primary_interaction_color(b)
    if color_a and color_b and color_a!=color_b:return True
    def affirmative(text):
        text=re.sub(r'不(?=喜欢|偏好|允许)|not ', '',text,flags=re.I)
        return re.sub(r'dislike','like',text,flags=re.I)
    if normalized(a)!=normalized(b) and normalized(affirmative(a))==normalized(affirmative(b)):
        return True
    for positive,negative in (('深色','浅色'),('启用','禁用'),('允许','禁止')):
        if positive in a and negative in b and normalized(a.replace(positive,''))==normalized(b.replace(negative,'')):return True
        if negative in a and positive in b and normalized(a.replace(negative,''))==normalized(b.replace(positive,'')):return True
    return False

def terms(text):
    tokens=set(re.findall(r'[a-z0-9_]+(?:-[a-z0-9_]+)*',text.casefold()))
    # Chinese bigrams support matching phrases without embeddings or external segmenters.
    for span in re.findall(r'[\u4e00-\u9fff]+',text):
        tokens.update(span[i:i+2] for i in range(len(span)-1))
        if len(span)==1:tokens.add(span)
    return tokens

class SmartMemory:
    def __init__(self, store, judge=None, read_only=False):
        self.core=Memory(store,read_only=read_only)
        self.path=Path(str(store)+'.smart.json')
        self.judge=judge or SemanticJudge()
    def load(self):
        if not self.path.exists():return dict(schema_version='smart_state.v1',observations=[],relationships=[],audit=[])
        return json.loads(self.path.read_text(encoding='utf-8'))
    def save(self,d):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        p=self.path.with_suffix('.tmp');p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(p,self.path)
    def event(self,d,event,id,reason):
        d['audit'].append(dict(timestamp=now(),event=event,memory_ids=[id],reason=reason,source_type='smart'))
    def reject(self,reason):
        d=self.load();id=str(uuid.uuid4())
        # Never retain rejected raw candidate data.
        d['observations'].append(dict(id=id,status='REJECTED',reason=reason,created_at=now()))
        self.event(d,'REJECT',id,reason);self.save(d)
        return dict(decision='REJECT',reason=reason,observation_id=id)
    def gate(self,c):
        verdict=self.core.evaluate(c)
        if verdict['decision']=='REJECT':return verdict
        conflicts=[]
        for r in self.core.load()['records']:
            if r['status']!='ACTIVE' or self.core.expired(r):continue
            if any(r[field]!=c.get(field,[] if field=='agent_scope' else None) for field in ('project','machine','agent_scope')):continue
            if direct_contradiction(r['content'],c['content']):conflicts.append(r['id'])
        if conflicts:return dict(decision='CONFLICT',reason='Direct contradiction; explicit lifecycle review required',conflicts_with=conflicts)
        return verdict
    def observe(self,c,explicit=False):
        # Always apply deterministic safety even when an optional judge is supplied.
        judge_input=copy.deepcopy(c)
        if isinstance(judge_input,dict) and isinstance(judge_input.get('metadata',{}),dict):
            metadata=judge_input.setdefault('metadata',{})
            metadata.pop('trusted_explicit_intent',None)
            if explicit is True and c.get('confirmed') is True and c.get('source_type','user')=='user':metadata['trusted_explicit_intent']=True
        baseline=SemanticJudge().judge(judge_input)
        if baseline['risk_flags'] or not baseline['should_remember']:
            return self.reject(baseline['reason'])
        if not isinstance(c,dict):return self.reject('Invalid candidate')
        if c.get('source_type','user') not in ('user','import','system'):return self.reject('Untrusted source')
        j=self.judge.judge(judge_input)
        # Optional judge cannot lift deterministic safety, confirmation, or stability limits.
        for k in ('stability_score','future_value_score','confidence'):
            if not isinstance(j.get(k),(int,float)) or not math.isfinite(j[k]) or not 0<=j[k]<=1:return self.reject('Invalid judge score')
        j=copy.deepcopy(j)
        j['stability_score']=min(j['stability_score'],baseline['stability_score'])
        j['memory_type']=baseline['memory_type']
        j['suggested_scope']=baseline['suggested_scope']
        j['suggested_ttl']=baseline['suggested_ttl']
        j['confidence']=min(j['confidence'],baseline['confidence'])
        if sensitive(json.dumps(j,ensure_ascii=False)):return self.reject('Unsafe judge recommendation')
        if j.get('risk_flags') or not j.get('should_remember'):return self.reject('Judge recommends rejection')
        candidate=copy.deepcopy(c);candidate['type']=j['memory_type']
        for k,v in baseline['suggested_scope'].items():
            if not candidate.get(k):candidate[k]=v
        if baseline['suggested_fact_key'] and baseline['suggested_fact_key'].startswith('alias.'):
            candidate.setdefault('metadata',{})['fact_key']=baseline['suggested_fact_key']
        candidate['confirmed']=True  # Validation probe only; never written on this basis.
        check=self.gate(candidate)
        if check['decision']=='REJECT':return self.reject(check['reason'])
        # Never invent confirmation: explicit must be supplied by a trusted user-facing caller.
        can_write=explicit and c.get('confirmed') is True and j['stability_score']>=0.7
        candidate['confirmed']=c.get('confirmed') is True
        if j['suggested_ttl'] and not candidate.get('expires_at'):
            candidate['expires_at']=(datetime.now(timezone.utc)+timedelta(seconds=j['suggested_ttl'])).isoformat()
        d=self.load()
        fingerprint=hashlib.sha256(json.dumps([normalized(c['content']),candidate.get('project'),candidate.get('machine'),candidate.get('agent_scope',[])],sort_keys=True).encode()).hexdigest()
        entry=next((r for r in d['observations'] if r.get('fingerprint')==fingerprint and r['status'] in ('OBSERVED','CANDIDATE') and not self.stage_expired(r)),None)
        if not entry:
            entry=dict(id=str(uuid.uuid4()),status='OBSERVED',candidate=candidate,judge=j,fingerprint=fingerprint,
                       repeat_count=0,created_at=now(),updated_at=now(),expires_at=candidate.get('expires_at'),source_quality=1.0 if c.get('source_type','user')=='user' else 0.6,
                       explicit_user_confirmation=can_write,conflict_state=check['decision'],reason=j['reason'])
            d['observations'].append(entry)
        entry['repeat_count']+=1;entry['updated_at']=now()
        self.event(d,'OBSERVE',entry['id'],'Bounded fact observation')
        self.save(d)
        if can_write:return self.promote(entry['id'],True)
        return dict(decision='OBSERVED',reason=j['reason'],observation_id=entry['id'],judge=j,promotion=self.recommendation(entry))
    def stage_expired(self,r):
        return bool(r.get('expires_at') and datetime.fromisoformat(r['expires_at'])<=datetime.now(timezone.utc))
    def recommendation(self,r):
        elapsed=max(0,(datetime.fromisoformat(r['updated_at'])-datetime.fromisoformat(r['created_at'])).total_seconds())
        if r['status'] not in ('OBSERVED','CANDIDATE') or self.stage_expired(r):return dict(recommend=False,reason='Not a live observation')
        v=self.gate(dict(r['candidate'],confirmed=True))
        conflicts=v['decision']=='CONFLICT'
        explicit=r.get('explicit_user_confirmation',False)
        evidence_score=round(0.4*min(1,r['repeat_count']/3)+0.2*min(1,elapsed/86400)+0.2*r['source_quality']+0.2*r['judge']['stability_score'],4)
        eligible=(r['repeat_count']>=3 or explicit) and r['source_quality']>=0.8 and r['judge']['stability_score']>=0.7 and not conflicts and v['decision']!='REJECT' and (explicit or evidence_score>=0.72)
        return dict(recommend=eligible,reason='Stable repeated preference; ask user to confirm' if eligible and not explicit else 'Explicit user-confirmed durable fact' if eligible else 'Insufficient stability/source evidence or conflict',repeat_count=r['repeat_count'],evidence_score=evidence_score,time_span_seconds=elapsed,source_quality=r['source_quality'],explicit_user_confirmation=explicit,stability_score=r['judge']['stability_score'],conflict_state=v['decision'],risk_flags=r['judge']['risk_flags'])
    def promotion_candidates(self):
        return [dict(observation_id=r['id'],**self.recommendation(r)) for r in self.load()['observations'] if r['status'] in ('OBSERVED','CANDIDATE') and self.recommendation(r)['recommend']]
    def promote(self,id,confirmed=False):
        d=self.load();r=next(r for r in d['observations'] if r['id']==id)
        if r['status'] not in ('OBSERVED','CANDIDATE') or self.stage_expired(r):raise ValueError('Only live candidates can promote')
        if confirmed is not True:return dict(decision='NEEDS_CONFIRMATION',reason='Human confirmation required',observation_id=id)
        c=copy.deepcopy(r['candidate']);c['confirmed']=True
        if r['judge']['stability_score']<0.7:return dict(decision='OBSERVED',reason='Temporary observations cannot promote permanently',observation_id=id)
        if r['source_quality']<0.8:return dict(decision='REJECT',reason='Insufficient trusted source quality',observation_id=id)
        # Revalidate sources and relationships at final write time, never just at proposal time.
        if r.get('consolidates'):
            sources=self.validate_sources(r['consolidates'])
            if any(r['source_revisions'].get(x['id'])!=revision(x) for x in sources):raise ValueError('Sources changed after proposal; review a new candidate')
            c['content']='；'.join(x['content'] for x in sources)
            c['summary']=c['content']
        c.setdefault('metadata',{})['smart_stability']=r['judge']['stability_score']
        # Promotion never authorizes implicit UPDATE or supersede.
        verdict=self.gate(c)
        if verdict['decision'] not in ('ACCEPT','DUPLICATE'):
            r['conflict_state']=verdict['decision'];self.event(d,'PROMOTION_BLOCKED',id,verdict['reason']);self.save(d)
            return dict(verdict,observation_id=id)
        result=self.core.add(c)
        if result['decision'] in ('ACCEPT','DUPLICATE'):
            memory_id=result.get('record',{}).get('id') or result.get('memory_id')
            r.update(status='ACTIVE',memory_id=memory_id,explicit_user_confirmation=True,updated_at=now())
            self.event(d,'PROMOTE',id,'User confirmed; formal Core Gate passed')
            if r.get('consolidates'):
                d['relationships'].append(dict(schema_version='memory_relationship.v1',id=str(uuid.uuid4()),target_id=memory_id,derived_from=r['consolidates'],consolidates=r['consolidates'],source_revisions=r['source_revisions'],source_disposition='retained',created_at=now()))
            self.save(d)
        return dict(result,observation_id=id)
    def validate_sources(self,ids):
        if len(set(ids))!=len(ids) or len(ids)<2:raise ValueError('Need distinct source IDs')
        records=[self.core.get(id) for id in ids]
        if any(r['status']!='ACTIVE' or self.core.expired(r) for r in records):raise ValueError('Sources must be live ACTIVE')
        if any((r['project'],r['machine'],r['agent_scope'],r['type'])!=(records[0]['project'],records[0]['machine'],records[0]['agent_scope'],records[0]['type']) for r in records):raise ValueError('Incompatible scopes or types')
        keys={}
        for r in records:
            key=fact_key(r)
            if r['conflicts_with']:raise ValueError('Unresolved source conflict')
            if key and key in keys and normalized(keys[key])!=normalized(r['content']):raise ValueError('Conflicting fact keys cannot consolidate')
            if key:keys[key]=r['content']
        # Reject known contradictory clauses; unknown semantics remain subject to human review.
        for a in records:
            for b in records:
                if a['id']!=b['id'] and direct_contradiction(a['content'],b['content']):raise ValueError('Conflicting primary-interaction color or negation; consolidation blocked')
        return records
    def consolidate(self,ids):
        records=self.validate_sources(ids);first=records[0]
        content='；'.join(r['content'] for r in records)
        c=dict(content=content,summary=content,type=first['type'],project=first['project'],machine=first['machine'],agent_scope=first['agent_scope'],confirmed=False,source_type='user',metadata={'derived_from':ids,'consolidates':ids})
        j=SemanticJudge().judge(dict(c,content='长期偏好：'+content))
        # Lossless concatenation only; no model rewriting or invented factual clauses.
        if len(content)>2000:raise ValueError('Consolidation exceeds Core bounded candidate limit')
        d=self.load();id=str(uuid.uuid4())
        d['observations'].append(dict(id=id,status='CANDIDATE',candidate=c,judge=j,consolidates=ids,source_revisions={x['id']:revision(x) for x in records},repeat_count=1,created_at=now(),updated_at=now(),expires_at=None,source_quality=1.0,explicit_user_confirmation=False,reason='Lossless source consolidation; originals retained'))
        self.event(d,'CONSOLIDATE_PROPOSE',id,'Lossless candidate; user review required');self.save(d)
        return dict(decision='CANDIDATE',observation_id=id,candidate=c,source_memory_ids=ids,source_disposition='retained',reason='All original clauses retained verbatim; confirm before promoting')
    def retrieval(self,task,project=None,agent=None,machine=None,kind=None,limit=10):
        if not task.strip():raise ValueError('Task is required')
        task_terms=terms(task);rows=[]
        inferred_machine=re.search(r'Win(?:10|11)|Windows\s*(?:10|11)',task,re.I)
        machine=machine or (inferred_machine.group() if inferred_machine else None)
        records=self.core.load()['records'];relations=self.load()['relationships']
        for r in records:
            reason=None
            if r['status']!='ACTIVE' or self.core.expired(r):reason='inactive_or_expired'
            elif r['project'] and r['project']!=project:reason='project_scope_mismatch'
            elif r['machine'] and canonical_machine(r['machine'])!=canonical_machine(machine):reason='machine_scope_mismatch'
            elif r['agent_scope'] and agent not in r['agent_scope'] and 'global' not in r['agent_scope']:reason='agent_scope_mismatch'
            elif kind and r['type']!=kind:reason='memory_type_mismatch'
            elif any(x['target_id']==r['id'] and not self.relationship_valid(x) for x in relations):reason='derived_source_changed'
            hay=terms(r['content']+' '+r['title']+' '+' '.join(r['tags']))
            matched=sorted(task_terms & hay)
            if not reason and not matched:reason='no_task_relevance'
            factors={}
            if not reason:
                age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(r['updated_at'])).total_seconds()/86400)
                stability=r['metadata'].get('smart_stability',0.5)
                if not isinstance(stability,(float,int)) or not math.isfinite(stability):stability=0.5
                factors=dict(task_relevance=50*len(matched)/max(1,len(task_terms)),project_scope=10 if r['project'] else 0,agent_scope=5 if r['agent_scope'] else 0,machine_scope=10 if r['machine'] else 0,memory_type=5 if kind and r['type']==kind else 2 if r['type'] in ('PROJECT','WORKFLOW','DECISION') else 1,priority=r['priority']/10,recency=5/(1+age/30),confidence=5*r['confidence'],stability=5*max(0,min(1,stability)),relationship=3 if any(x['target_id']==r['id'] and self.relationship_valid(x) for x in relations) else 0,active_lifecycle_state=1)
            rows.append(dict(memory_id=r['id'],score=round(sum(factors.values()),4),matched_factors=factors,matched_terms=matched,excluded_reason=reason,record=r))
        selected=sorted([r for r in rows if not r['excluded_reason']],key=lambda r:(r['score'],r['memory_id']),reverse=True)[:max(0,limit)]
        return dict(results=selected,excluded=[{k:v for k,v in r.items() if k!='record'} for r in rows if r['excluded_reason']])
    def relationship_valid(self,rel):
        try:
            records=self.validate_sources(rel['derived_from'])
            return all(rel.get('source_revisions',{}).get(r['id'])==revision(r) for r in records)
        except (ValueError,StopIteration):return False
    def inject(self,task,project=None,agent=None,machine=None,kind=None,budget=1000):
        if budget<0:raise ValueError('Budget must be nonnegative')
        ranked=self.retrieval(task,project,agent,machine,kind,limit=100)
        lines=[];ids=[];selection=[]
        relationships=self.load()['relationships']
        for row in ranked['results']:
            r=row['record']
            rel=next((x for x in relationships if x['target_id']==r['id']),None)
            # A retained source later retired/superseded must invalidate its derived context.
            if rel and (not self.relationship_valid(rel) or set(rel['derived_from']) & set(ids)):continue
            line=f"[{r['type']}] {r['summary']}"
            if len('\n'.join(lines+[line]))>budget:continue
            covered=set(x for rel in relationships if rel['target_id'] in ids for x in rel['derived_from'])
            if r['id'] in covered:continue
            lines.append(line);ids.append(r['id']);selection.append({k:v for k,v in row.items() if k!='record'})
        return dict(context='\n'.join(lines),memory_ids=ids,characters=len('\n'.join(lines)),budget=budget,selection=selection)
    def explain(self,id):
        d=self.load();r=next((r for r in d['observations'] if r['id']==id or r.get('memory_id')==id),None)
        if r:
            effective_status=r['status']
            if effective_status=='ACTIVE' and r.get('memory_id'):
                current=self.core.get(r['memory_id']);effective_status='EXPIRED' if self.core.expired(current) else current['status']
            elif r['status'] in ('OBSERVED','CANDIDATE') and self.stage_expired(r):effective_status='EXPIRED'
            return dict(id=id,status=effective_status,reason=r.get('reason'),judge=r.get('judge'),promotion=self.recommendation(r) if r['status'] in ('OBSERVED','CANDIDATE') else None,relationships=[x for x in d['relationships'] if x['target_id']==id or id in x['derived_from']],audit=[e for e in d['audit'] if r['id'] in e['memory_ids']])
        record=self.core.get(id)
        return dict(id=id,status=record['status'],reason='Confirmed candidate passed deterministic Core Gate',audit=[e for e in self.core.load()['audit'] if id in e['memory_ids']],relationships=[x for x in d['relationships'] if x['target_id']==id or id in x['derived_from']])
