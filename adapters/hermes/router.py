"""Thin Hermes compatibility router; storage only through public CLI."""
import argparse,json,subprocess,sys,tempfile,os
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
STORE=ROOT/'storage/hermes-memory.json'
TRACE=ROOT/'storage/hermes-router-events.jsonl'
def call(*args):
    p=subprocess.run([sys.executable,'-m','cli','--store',str(STORE),*args],cwd=ROOT,capture_output=True,encoding='utf-8',check=True)
    return json.loads(p.stdout)
def emit(event):
    event['timestamp']=datetime.now(timezone.utc).isoformat()
    TRACE.parent.mkdir(exist_ok=True)
    with TRACE.open('a',encoding='utf-8') as f:f.write(json.dumps({k:v for k,v in event.items() if k!='context'})+'\n')
    print(json.dumps(event,ensure_ascii=False))
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['write','read','supersede']);p.add_argument('--project',required=True);p.add_argument('--key',default='default_theme');p.add_argument('--value');p.add_argument('--id');p.add_argument('--user-confirmed',action='store_true');a=p.parse_args()
    if a.action=='read':
        task=a.key
        retrieved=call('retrieve',task,'--project',a.project,'--agent','hermes')
        v=call('inject',task,'--project',a.project,'--agent','hermes','--budget','500')
        emit(dict(MEMORY_RETRIEVAL_TRIGGERED=True,INJECTED_MEMORY_IDS=v['memory_ids'],retrieved_ids=[r['id'] for r in retrieved],context=v['context']));return
    if not a.user_confirmed:raise ValueError('Explicit user confirmation required')
    c=dict(content=f'{a.key}={a.value}',summary=f'{a.key}={a.value}',type='PROJECT',project=a.project,confirmed=True,source_type='user',tags=[a.key],metadata={'fact_key':a.key})
    fd,path=tempfile.mkstemp(suffix='.json');os.close(fd)
    try:
        Path(path).write_text(json.dumps(c),encoding='utf-8')
        v=call('evaluate','--candidate',path)
        if a.action=='supersede':
            v=call('supersede',a.id,'--candidate',path,'--reason','Explicit user confirmation of replacement')
        elif v['decision']=='ACCEPT':v=call('add','--candidate',path)
        emit(dict(MEMORY_WRITE_TRIGGERED=True,MEMORY_DECISION=v['decision'],MEMORY_ID=v.get('record',{}).get('id'),CONFLICT_TRIGGERED=v['decision']=='CONFLICT',conflicts_with=v.get('conflicts_with',[]),SUPERSEDE_CHAIN=v.get('record',{}).get('supersedes',[])))
    finally:Path(path).unlink(missing_ok=True)
if __name__=='__main__':main()
