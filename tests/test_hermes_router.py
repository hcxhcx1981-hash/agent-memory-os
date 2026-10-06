import unittest, tempfile, json
import subprocess,sys,os,hashlib
from pathlib import Path
from unittest.mock import patch
from adapters.hermes import router

# Router may append its independent diagnostics only. Both Router and CLI child
# reject native paths, SQLite and any other write. This is a Python access audit.
AUDITED_READ=r'''
import sys,os,json,runpy,subprocess
from pathlib import Path
opened=[]
trace=Path(sys.argv[3]).resolve() if sys.argv[1]=='router' else None
native=Path(os.environ.get('HERMES_HOME') or Path.home()/'AppData/Local/hermes').resolve()
def audit(event,args):
    if event.startswith('sqlite3.'):raise AssertionError('SQLite forbidden')
    if event in ('os.remove','os.rename','os.rmdir'):raise AssertionError('Mutation forbidden')
    if event=='os.mkdir' and (trace is None or Path(args[0]).resolve()!=trace.parent):raise AssertionError('mkdir forbidden')
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=Path(os.fsdecode(args[0])).resolve()
        if {'.hermes','.agnes','.codex','.workbuddy','.codebuddy','hermes-data','sessions','file-history'} & {s.casefold() for s in p.parts} or p.is_relative_to(native):raise AssertionError('Native access forbidden')
        mode,flags=args[1:3]
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and p!=trace:raise AssertionError('Only independent diagnostics may be appended')
        if p==trace and writing and mode!='a':raise AssertionError('Trace must be append-only')
        opened.append(str(p))
sys.addaudithook(audit)
if sys.argv[1]=='router':
    script,child_code=sys.argv[2],sys.argv[4];original=subprocess.run
    def traced(command,**kwargs):
        assert command[:5]==[sys.executable,'-B','-m','cli','--read-only']
        result=original([sys.executable,'-B','-c',child_code,'cli',*command[4:]],**kwargs)
        print(result.stderr,file=sys.stderr,end='');return result
    subprocess.run=traced
    sys.argv=[script,*sys.argv[5:]]
    try:runpy.run_path(script,run_name='__main__')
    finally:print('AUDIT='+json.dumps(opened),file=sys.stderr)
else:
    sys.argv=['cli',*sys.argv[2:]]
    try:runpy.run_module('cli',run_name='__main__')
    finally:print('AUDIT='+json.dumps(opened),file=sys.stderr)
'''

class RouterTests(unittest.TestCase):
    def test_public_cli_store_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(router, 'STORE', Path(t)/'hermes-memory.json'):
                self.assertEqual(router.call('retrieve','default_theme','--project','Other','--agent','hermes'), [])
    def test_diagnostics_exclude_context(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'trace.jsonl'
            with patch.object(router,'TRACE',target), patch('builtins.print'):
                router.emit({'MEMORY_RETRIEVAL_TRIGGERED': True, 'INJECTED_MEMORY_IDS': [], 'context': 'fictional-context'})
            event=json.loads(target.read_text())
            self.assertNotIn('context',event)
            self.assertTrue(event['MEMORY_RETRIEVAL_TRIGGERED'])

    def test_v011_write_read_conflict_supersede_regression(self):
        import subprocess,sys
        from core.engine import Memory
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'hermes-memory.json';trace=Path(t)/'trace.jsonl'
            def run(action,*args):
                cmd=[sys.executable,'-B',str(root/'adapters/hermes/router.py'),action,'--store',str(store),'--trace',str(trace),'--project','Project-Mercury','--machine','Mac-Win10',*args]
                result=subprocess.run(cmd,cwd=root,capture_output=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return json.loads(result.stdout)
            first=run('write','--value','graphite-purple','--user-confirmed')
            self.assertEqual(first['MEMORY_DECISION'],'ACCEPT');old=first['MEMORY_ID']
            self.assertEqual(run('read')['INJECTED_MEMORY_IDS'],[old])
            conflict=run('write','--value','obsidian-green','--user-confirmed')
            self.assertTrue(conflict['CONFLICT_TRIGGERED'])
            self.assertEqual(Memory(store).get(old)['status'],'ACTIVE')
            new=run('supersede','--id',old,'--value','obsidian-green','--user-confirmed')['MEMORY_ID']
            self.assertEqual(run('read')['INJECTED_MEMORY_IDS'],[new])
            self.assertEqual(Memory(store).get(old)['superseded_by'],new)
            self.assertEqual(Memory(store).get(new)['supersedes'],[old])
            self.assertNotIn('context',trace.read_text())
    def test_observation_recommendation_no_silent_promotion(self):
        import subprocess,sys
        from core.engine import Memory
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'hermes-memory.json';trace=Path(t)/'trace.jsonl'
            for index in range(3):
                p=subprocess.run([sys.executable,str(root/'adapters/hermes/router.py'),'observe','--text','用户偏好黑紫配色','--store',str(store),'--trace',str(trace)],cwd=root,capture_output=True,encoding='utf-8')
                self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
                self.assertEqual(r['MEMORY_DECISION'],'OBSERVED')
                self.assertIn('MEMORY_REASON',r)
                self.assertEqual(r['PROMOTION_EVIDENCE']['repeat_count'],index+1)
                self.assertEqual(r['PROMOTION_RECOMMENDED'],index==2)
            self.assertEqual(Memory(store).load()['records'],[])

class ScopedRouterTests(unittest.TestCase):
    def setUp(self):
        from core.engine import Memory
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=Path(tmp.name)/'hermes-memory.json';self.trace=Path(tmp.name)/'trace.jsonl'
        self.memory=Memory(self.store)
        self.candidate=dict(content='Orion research output format fictional-pack',type='PROJECT',project='Orion',machine='Mac-Win10',agent_scope=['hermes'],confirmed=True,source_type='user')
        self.record=self.memory.add(self.candidate)['record']
    def read(self,project='Orion',machine='Mac-Win10',task='research output',audited=False):
        args=['read','--store',str(self.store),'--trace',str(self.trace),'--project',project,'--machine',machine,'--task',task]
        if audited:
            cmd=[sys.executable,'-B','-c',AUDITED_READ,'router',str(router.ROOT/'adapters/hermes/router.py'),str(self.trace),AUDITED_READ,*args]
        else:cmd=[sys.executable,'-B',str(router.ROOT/'adapters/hermes/router.py'),*args]
        return subprocess.run(cmd,cwd=router.ROOT,capture_output=True,encoding='utf-8',check=True)
    def test_project_machine_and_explicit_agent_scope(self):
        for scope in ([],['codex'],['workbuddy'],['agnes-code'],['global']):
            self.memory.add(dict(self.candidate,content='research output '+str(scope),agent_scope=scope))
        result=json.loads(self.read().stdout)
        self.assertEqual(len(result['INJECTED_MEMORY_IDS']),2)
        self.assertIn(self.record['id'],result['INJECTED_MEMORY_IDS'])
        self.assertTrue(result['reference_only'])
        for kwargs in (dict(project='Other'),dict(machine='Other'),dict(task='cooking')):
            self.assertEqual(json.loads(self.read(**kwargs).stdout)['INJECTED_MEMORY_IDS'],[])
    def test_unrelated_does_not_retrieve_or_append_trace(self):
        self.assertFalse(json.loads(self.read(task='15+27').stdout)['MEMORY_RETRIEVAL_TRIGGERED'])
        self.assertFalse(self.trace.exists())
    def test_native_and_other_stores_refused(self):
        for store in (self.store.with_name('codex-memory.json'),self.store.with_name('workbuddy-memory.json'),self.store.with_name('agnes-code-memory.json'),self.store.parent/'.hermes'/'hermes-memory.json',Path(os.environ.get('HERMES_HOME') or Path.home()/'AppData/Local/hermes')/'hermes-memory.json'):
            with patch.object(router,'STORE',store),self.assertRaises(ValueError):router.validate_paths()
    def test_readonly_diagnostics_and_native_access_audit(self):
        before=self.store.read_bytes();r=self.read(audited=True);paths=set()
        for line in r.stderr.splitlines():
            if line.startswith('AUDIT='):paths.update(Path(p).resolve() for p in json.loads(line[6:]) if p.endswith(('.json','.jsonl')))
        self.assertEqual(paths,{self.store.resolve(),self.trace.resolve()})
        self.assertEqual(before,self.store.read_bytes())
        event=json.loads(self.trace.read_text());self.assertNotIn('context',event)
        Path(str(self.store)+'.move-journal.json').write_text('{}')
        with self.assertRaises(subprocess.CalledProcessError):self.read()
