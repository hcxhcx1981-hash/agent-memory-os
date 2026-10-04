import unittest,tempfile,json,subprocess,sys
from pathlib import Path
from core.engine import Memory
from adapters.hermes.adapter import HermesAdapter
ROOT=Path(__file__).resolve().parents[1]
def candidate(content,**kw): return dict(content=content,confirmed=True,source_type='user',**kw)
class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'memory.json';self.m=Memory(self.path)
    def test_preference_and_temporary(self):
        self.assertEqual(self.m.add(candidate('用户长期偏好深色UI'))['record']['type'],'USER')
        r=self.m.add(candidate('今天先不开发这个项目',type='USER'))['record']
        self.assertEqual(r['type'],'EPISODIC');self.assertIsNotNone(r['expires_at'])
    def test_duplicate_and_conflict_chain(self):
        c=candidate('默认模型=A',project='X');a=self.m.add(c)['record']
        self.assertEqual(self.m.add(c)['decision'],'DUPLICATE')
        b=candidate('默认模型=B',project='X')
        self.assertEqual(self.m.add(b)['decision'],'CONFLICT')
        n=self.m.supersede(a['id'],b,'Confirmed model change')['record']
        self.assertEqual(self.m.get(a['id'])['status'],'SUPERSEDED')
        self.assertEqual(self.m.get(a['id'])['superseded_by'],n['id'])
        self.assertEqual(n['supersedes'],[a['id']])
        self.assertEqual([r['id'] for r in self.m.search(project='X')],[n['id']])
    def test_path_duplicate_and_change(self):
        a=self.m.add(candidate('项目路径=D:/fictional/x',project='X'))['record']
        self.assertEqual(self.m.add(candidate(a['content'],project='X'))['decision'],'DUPLICATE')
        self.assertEqual(self.m.evaluate(candidate('项目路径=D:/fictional/y',project='X'))['decision'],'CONFLICT')
    def test_scope_retire_budget(self):
        a=self.m.add(candidate('Build workflow X',project='X',type='WORKFLOW'))['record']
        self.m.add(candidate('Build workflow Y',project='Y'))
        self.m.add(candidate('Build workflow private',project='X',agent_scope=['other']))
        result=self.m.inject('Build',project='X',agent='hermes',budget=80)
        self.assertEqual(result['memory_ids'],[a['id']]);self.assertLessEqual(result['characters'],80)
        self.assertEqual(self.m.inject('Build',project='X',budget=1)['context'],'')
        self.m.retire(a['id'],'Obsolete');self.assertEqual(self.m.search(project='X',agent='hermes'),[])
    def test_sensitive_unconfirmed_no_leak(self):
        # Synthetic fixture is generated at runtime and never committed as a credential.
        secret='sk-'+'fictionalcredential12345'
        for c in (candidate('API Key='+secret),candidate('这个项目以后大概会部署到云端'),{'content':'Cloud deployment','confirmed':True,'source_type':'model'},candidate('Harmless',metadata={'token':'fictional-value'}),dict(content='Unconfirmed')):
            self.assertEqual(self.m.add(c)['decision'],'REJECT')
        self.assertNotIn(secret,self.path.read_text());self.assertEqual(self.m.load()['records'],[])
    def test_expiry_and_audit(self):
        r=self.m.add(candidate('Old event',type='EPISODIC',expires_at='2000-01-01T00:00:00+00:00'))['record']
        self.assertEqual(self.m.search(),[]);self.assertEqual(self.m.expire(),[r['id']])
        self.assertEqual(self.m.get(r['id'])['status'],'EXPIRED')
        self.assertEqual([e['event'] for e in self.m.load()['audit']],['CREATE','EXPIRE'])
    def test_supplement(self):
        r=self.m.add(candidate('User prefers dark UI'))['record']
        v=self.m.add(candidate('User prefers dark UI and large fonts',metadata={'supplements':r['id']}))
        self.assertEqual(v['decision'],'UPDATE');self.assertEqual(len(self.m.load()['records']),1)
        self.assertEqual(self.m.load()['audit'][-1]['event'],'UPDATE')
    def test_invalid_candidate(self):
        for c in ([],candidate('Fact',tags='bad'),candidate('Fact',metadata=[]),candidate('Fact',expires_at='bad'),candidate('Fact',confidence=0.1)):
            self.assertEqual(self.m.evaluate(c)['decision'],'REJECT')
    def test_hermes_public_interface(self):
        f=Path(self.temp.name)/'candidate.json';f.write_text(json.dumps(candidate('Build instructions',project='X')),encoding='utf-8')
        a=HermesAdapter(ROOT,self.path)
        self.assertEqual(a.remember(f)['decision'],'ACCEPT');self.assertTrue(a.context('Build','X')['memory_ids'])
    def test_real_cli_chain(self):
        def run(*args):
            p=subprocess.run([sys.executable,'-m','cli','--store',str(self.path),*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);return json.loads(p.stdout)
        f=Path(self.temp.name)/'candidate.json'
        def write(c): f.write_text(json.dumps(c),encoding='utf-8')
        write(candidate('默认模型=A',project='X'))
        self.assertEqual(run('evaluate','--candidate',str(f))['decision'],'ACCEPT')
        old=run('add','--candidate',str(f))['record']
        self.assertEqual(run('add','--candidate',str(f))['decision'],'DUPLICATE')
        write(candidate('默认模型=B',project='X'))
        self.assertEqual(run('add','--candidate',str(f))['decision'],'CONFLICT')
        self.assertTrue(run('conflicts'))
        new=run('supersede',old['id'],'--candidate',str(f),'--reason','Confirmed replacement')['record']
        self.assertEqual(run('get',old['id'])['superseded_by'],new['id'])
        self.assertEqual(len(run('search','默认模型','--project','X')),1)
        self.assertEqual(len(run('retrieve','默认模型','--project','X')),1)
        self.assertEqual(run('inject','默认模型','--project','X')['memory_ids'],[new['id']])
        self.assertEqual(run('inject','默认模型','--project','Y')['memory_ids'],[])
        run('retire',new['id'],'--reason','Obsolete')
        self.assertEqual(run('retrieve','默认模型','--project','X'),[])
        write(candidate('token='+'fictional-sensitive-value'))
        self.assertEqual(run('add','--candidate',str(f))['decision'],'REJECT')
        self.assertEqual(len(run('export')['records']),2)
if __name__=='__main__': unittest.main()
