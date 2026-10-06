"""Thin Hermes compatibility router; storage only through public CLI."""
import argparse,json,subprocess,sys,tempfile,os,re
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
STORE=ROOT/'storage/hermes-memory.json'
TRACE=ROOT/'storage/hermes-router-events.jsonl'
NATIVE_PARTS={'.agnes','.codex','.hermes','.workbuddy','.codebuddy','hermes-data','sessions','file-history'}

def validate_paths():
    if STORE.name!='hermes-memory.json' or TRACE.suffix.casefold()!='.jsonl':
        raise ValueError('Use an independent Hermes store and diagnostics trace')
    native_home=Path(os.environ.get('HERMES_HOME') or Path.home()/'AppData/Local/hermes').resolve()
    for path in (STORE,Path(str(STORE)+'.smart.json'),TRACE):
        resolved=path.resolve()
        if NATIVE_PARTS & {p.casefold() for p in (*path.parts,*resolved.parts)} or resolved.is_relative_to(native_home) or resolved.name!=path.name:
            raise ValueError('Native memory, history and store aliases are forbidden')
    if Path(str(STORE)+'.move-journal.json').exists():
        raise ValueError('Pending migration requires separate governance recovery')
def call(*args):
    validate_paths()
    readonly=['--read-only'] if args and args[0] in ('get','retrieve','inject','smart-retrieve','smart-inject','why','explain') else []
    p=subprocess.run([sys.executable,'-B','-m','cli',*readonly,'--store',str(STORE),*args],cwd=ROOT,capture_output=True,encoding='utf-8',check=True)
    return json.loads(p.stdout)
def emit(event):
    event['timestamp']=datetime.now(timezone.utc).isoformat()
    TRACE.parent.mkdir(exist_ok=True)
    with TRACE.open('a',encoding='utf-8') as f:f.write(json.dumps({k:v for k,v in event.items() if k!='context'})+'\n')
    print(json.dumps(event,ensure_ascii=False))
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['write','observe','read','supersede','promote']);p.add_argument('--project');p.add_argument('--key',default='default_theme');p.add_argument('--value');p.add_argument('--id');p.add_argument('--user-confirmed',action='store_true');p.add_argument('--text');p.add_argument('--task');p.add_argument('--machine');p.add_argument('--type',dest='kind',choices=['USER','PROJECT','DECISION','WORKFLOW','EPISODIC']);p.add_argument('--store');p.add_argument('--trace');a=p.parse_args()
    global STORE,TRACE
    if a.store:STORE=Path(a.store)
    if a.trace:TRACE=Path(a.trace)
    validate_paths()
    if a.action=='read':
        task=a.task or a.key
        if not a.project or not a.machine or not task.strip():
            raise ValueError('Explicit task, project and machine required')
        if re.fullmatch(r'[0-9\s+*/().=-]+',task):
            print(json.dumps(dict(MEMORY_RETRIEVAL_TRIGGERED=False,INJECTED_MEMORY_IDS=[],context='')));return
        scope=['--agent','hermes','--project',a.project,'--machine',a.machine]
        retrieved=[row['record'] for row in call('smart-retrieve',task,*scope)['results'] if set(row['record']['agent_scope']) & {'hermes','global'}]
        v=call('smart-inject',task,*scope,'--budget','500')
        allowed={r['id'] for r in retrieved}
        if not set(v['memory_ids'])<=allowed:
            # Empty legacy scopes are not permission to share with Hermes.
            lines,ids=[],[]
            for r in retrieved:
                line='['+r['type']+'] '+r['summary']
                if len('\n'.join(lines+[line]))<=500:lines.append(line);ids.append(r['id'])
            v=dict(context='\n'.join(lines),memory_ids=ids)
        emit(dict(MEMORY_RETRIEVAL_TRIGGERED=True,INJECTED_MEMORY_IDS=v['memory_ids'],retrieved_ids=[r['id'] for r in retrieved],context=v['context'],reference_only=True));return
    if a.action=='promote':
        args=['promote',a.id]+(['--user-confirmed'] if a.user_confirmed else [])
        v=call(*args)
        emit(dict(MEMORY_WRITE_TRIGGERED=True,MEMORY_DECISION=v['decision'],MEMORY_ID=v.get('record',{}).get('id') or v.get('memory_id'),OBSERVATION_ID=v.get('observation_id')));return
    if a.action!='observe' and not a.user_confirmed:raise ValueError('Explicit user confirmation required')
    if not a.text and a.value is None:raise ValueError('A factual text or value is required')
    c=dict(content=a.text or f'{a.key}={a.value}',summary=a.text or f'{a.key}={a.value}',type=a.kind or ('PROJECT' if a.project else None),project=a.project,machine=a.machine,agent_scope=['hermes'],confirmed=a.user_confirmed,source_type='user',tags=[] if a.text else [a.key],metadata={'source_agent':'hermes',**({} if a.text else {'fact_key':a.key})})
    fd,path=tempfile.mkstemp(suffix='.json');os.close(fd)
    try:
        Path(path).write_text(json.dumps(c),encoding='utf-8')
        if a.action=='supersede':
            v=call('supersede',a.id,'--candidate',path,'--reason','Explicit user confirmation of replacement')
        else:
            args=['observe','--candidate',path]+(['--user-confirmed'] if a.user_confirmed else [])
            v=call(*args)
        emit(dict(MEMORY_WRITE_TRIGGERED=True,MEMORY_DECISION=v['decision'],MEMORY_ID=v.get('record',{}).get('id') or v.get('memory_id'),OBSERVATION_ID=v.get('observation_id'),MEMORY_REASON=v.get('reason'),PROMOTION_EVIDENCE=v.get('promotion'),PROMOTION_RECOMMENDED=v.get('promotion',{}).get('recommend',False),CONFLICT_TRIGGERED=v['decision']=='CONFLICT',conflicts_with=v.get('conflicts_with',[]),SUPERSEDE_CHAIN=v.get('record',{}).get('supersedes',[])))
    finally:Path(path).unlink(missing_ok=True)
if __name__=='__main__':main()
