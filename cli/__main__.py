import argparse,json,sys
from core.engine import Memory

def main():
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser(description='Agent Memory OS V0.2 (optional smart layer)')
    p.add_argument('--store',default='storage/memory.json')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('add','evaluate'):
        s=sub.add_parser(name);s.add_argument('--candidate',required=True,help='UTF-8 JSON file')
    for name in ('search','retrieve','inject'):
        s=sub.add_parser(name);s.add_argument('task');s.add_argument('--project');s.add_argument('--agent');s.add_argument('--budget',type=int,default=1000)
    for name in ('get','retire','supersede'):
        s=sub.add_parser(name);s.add_argument('id')
        if name!='get': s.add_argument('--reason',required=True)
        if name=='supersede': s.add_argument('--candidate',required=True)
    sub.add_parser('conflicts');sub.add_parser('expire')
    s=sub.add_parser('export');s.add_argument('--format',choices=('json','markdown'),default='json')
    # V0.1 commands retain their original behavior.
    for name in ('judge','observe'):
        s=sub.add_parser(name);s.add_argument('--candidate',required=True)
        if name=='observe': s.add_argument('--user-confirmed',action='store_true')
    sub.add_parser('promotion-candidates')
    s=sub.add_parser('promote');s.add_argument('id');s.add_argument('--user-confirmed',action='store_true')
    s=sub.add_parser('consolidate');s.add_argument('ids',nargs='+')
    s=sub.add_parser('explain');s.add_argument('id')
    for name in ('why','smart-retrieve','smart-inject'):
        s=sub.add_parser(name);s.add_argument('task');s.add_argument('--project');s.add_argument('--agent');s.add_argument('--machine');s.add_argument('--type',dest='kind');s.add_argument('--budget',type=int,default=1000)
    a=p.parse_args();m=Memory(a.store)
    try:
        if a.command in ('judge','observe','promotion-candidates','promote','consolidate','explain','why','smart-retrieve','smart-inject'):
            from smart.layer import SmartMemory
            layer=SmartMemory(a.store)
            if a.command in ('judge','observe'):
                with open(a.candidate,encoding='utf-8-sig') as f:c=json.load(f)
                result=layer.judge.judge(c) if a.command=='judge' else layer.observe(c,a.user_confirmed)
            elif a.command=='promotion-candidates':result=layer.promotion_candidates()
            elif a.command=='promote':result=layer.promote(a.id,a.user_confirmed)
            elif a.command=='consolidate':result=layer.consolidate(a.ids)
            elif a.command=='explain':result=layer.explain(a.id)
            elif a.command=='smart-inject':result=layer.inject(a.task,a.project,a.agent,a.machine,a.kind,a.budget)
            else:result=layer.retrieval(a.task,a.project,a.agent,a.machine,a.kind)
        elif a.command in ('add','evaluate','supersede'):
            c=json.loads(open(a.candidate,encoding='utf-8-sig').read())
            result=m.supersede(a.id,c,a.reason) if a.command=='supersede' else getattr(m,a.command)(c)
        elif a.command in ('search','retrieve'): result=m.search(a.task,a.project,a.agent)
        elif a.command=='inject': result=m.inject(a.task,a.project,a.agent,a.budget)
        elif a.command=='get': result=m.get(a.id)
        elif a.command=='retire': result=m.retire(a.id,a.reason)
        elif a.command=='expire': result=m.expire()
        elif a.command=='conflicts': result=[e for e in m.load()['audit'] if e['reason']=='Fact changed; explicit supersede required']
        else:
            result=m.load()
            if a.format=='markdown':
                print('\n\n'.join(f"## {r['title']} ({r['status']})\n{r['content']}" for r in result['records']));return
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,StopIteration,OSError,TypeError) as e:
        safe_reasons={'Conflicting primary-interaction color or negation; consolidation blocked','Conflicting fact keys cannot consolidate','Sources must be live ACTIVE','Incompatible scopes or types','Unresolved source conflict','Need distinct source IDs','Sources changed after proposal; review a new candidate'}
        if str(e) in safe_reasons:
            print(json.dumps({'decision':'BLOCKED','error':str(e)}))
        else:
            print(json.dumps({'error':'Invalid operation or candidate; check schema and record ID'}))
        sys.exit(2)
if __name__=='__main__': main()
