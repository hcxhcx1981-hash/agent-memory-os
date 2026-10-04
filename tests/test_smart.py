import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from smart.layer import SmartMemory, SemanticJudge
from core.engine import Memory
ROOT=Path(__file__).resolve().parents[1]
def c(text,**kwargs):return dict(content=text,source_type='user',**kwargs)
class SmartTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'memory.json';self.s=SmartMemory(self.path);self.m=Memory(self.path)
    def add(self,text,**kwargs):
        return self.m.add(c(text,confirmed=True,**kwargs))['record']
    def test_judge_required_examples(self):
        j=SemanticJudge()
        alias=j.judge(c('以后 AC 就是 Agnes Code'))
        self.assertTrue(alias['should_remember']);self.assertGreater(alias['stability_score'],0.8)
        self.assertGreater(alias['future_value_score'],0.8);self.assertEqual(alias['suggested_fact_key'],'alias.ac')
        self.assertIn(alias['memory_type'],('USER','WORKFLOW'))
        self.assertEqual(j.judge(c('今天先别搞这个项目'))['memory_type'],'EPISODIC')
        self.assertFalse(j.judge(c('这个项目以后可能部署到云端'))['should_remember'])
        project=j.judge(c(r'Win10 上 D:\fictional\agent-memory-os 是 Memory OS 项目'))
        self.assertEqual(project['memory_type'],'PROJECT');self.assertEqual(project['suggested_scope']['machine'],'win10')
        self.assertFalse(j.judge(c('我今天心情不好'))['should_remember'])
    def test_repeat_recommends_but_requires_user(self):
        for _ in range(3):result=self.s.observe(c('用户偏好黑紫配色',type='USER'))
        id=result['observation_id'];promotions=self.s.promotion_candidates()
        self.assertEqual(len(promotions),1);self.assertEqual(promotions[0]['repeat_count'],3)
        self.assertIn('time_span_seconds',promotions[0]);self.assertEqual(self.m.load()['records'],[])
        self.assertEqual(self.s.promote(id)['decision'],'NEEDS_CONFIRMATION')
        promoted=self.s.promote(id,True)
        self.assertEqual(promoted['decision'],'ACCEPT');self.assertEqual(promoted['record']['status'],'ACTIVE')
        self.assertEqual(self.s.explain(id)['status'],'ACTIVE')
    def test_single_temporary_cannot_promote(self):
        result=self.s.observe(c('今天先不开发'))
        self.assertEqual(result['decision'],'OBSERVED');self.assertEqual(self.s.promotion_candidates(),[])
        self.assertEqual(self.s.promote(result['observation_id'],True)['decision'],'OBSERVED')
        self.assertEqual(self.m.load()['records'],[])
    def test_explicit_confirmation_and_core_conflict(self):
        result=self.s.observe(c('以后 AC 就是 Agnes Code',confirmed=True),True)
        self.assertEqual(result['decision'],'ACCEPT')
        old=result['record']['id']
        change=self.s.observe(c('以后 AC 就是 Another Code',confirmed=True),True)
        self.assertEqual(change['decision'],'CONFLICT');self.assertEqual(self.m.get(old)['status'],'ACTIVE')
        self.assertEqual(len(self.m.load()['records']),1)
    def test_model_and_sensitive_never_staged(self):
        secret='fictional-'+str(123456)
        for candidate in (c('token='+secret),c('Harmless',metadata={'token':secret}),{'content':'以后默认部署到云端','source_type':'model','confirmed':True},c('以后可能上云',confirmed=True)):
            self.assertEqual(self.s.observe(candidate,True)['decision'],'REJECT')
        self.assertNotIn(secret,self.s.path.read_text());self.assertEqual(self.m.load()['records'],[])
        rejected=self.s.load()['observations'][0]
        self.assertEqual(self.s.explain(rejected['id'])['status'],'REJECTED')
    def test_machine_inference_and_expired_explain(self):
        r=self.s.observe(c(r'Win10 上 D:\fictional-memory 是 Memory OS 项目',confirmed=True,machine=None),True)
        self.assertEqual(r['record']['machine'],'win10')
        self.m.retire(r['record']['id'],'Obsolete')
        self.assertEqual(self.s.explain(r['observation_id'])['status'],'RETIRED')
        self.assertEqual(SemanticJudge().judge(c('以后都用深色UI',metadata=[]))['risk_flags'],['invalid'])
    def test_trusted_explicit_intent_survives_factual_text_extraction(self):
        result=self.s.observe(c('Project-Aurora UI 使用深色背景。',project='Project-Aurora',confirmed=True),True)
        self.assertEqual(result['decision'],'ACCEPT')
        self.assertEqual(result['record']['content'],'Project-Aurora UI 使用深色背景。')
        self.assertEqual(self.s.observe(c('Project-Aurora UI 可能使用深色背景。',project='Project-Aurora',confirmed=True),True)['decision'],'REJECT')
    def test_optional_judge_cannot_override_safety(self):
        class UnsafeJudge:
            def judge(self,candidate):
                r=SemanticJudge().judge(candidate);r.update(stability_score=1,should_remember=True,risk_flags=[]);return r
        self.s.judge=UnsafeJudge()
        r=self.s.observe(c('今天先不开发',confirmed=True),True)
        self.assertEqual(r['decision'],'OBSERVED')
        self.assertEqual(self.s.observe(c('以后可能上云',confirmed=True),True)['decision'],'REJECT')
    def test_consolidation_lossless_and_traceable(self):
        texts=['用户喜欢深色 UI','用户偏好黑紫配色','绿色只用于成功状态','不喜欢浅蓝白 SaaS 风']
        sources=[self.add(text,type='USER') for text in texts]
        ids=[r['id'] for r in sources];before=copy.deepcopy(self.m.load()['records'])
        proposal=self.s.consolidate(ids)
        self.assertEqual(proposal['decision'],'CANDIDATE');self.assertEqual(proposal['source_memory_ids'],ids)
        for text in texts:self.assertIn(text,proposal['candidate']['content'])
        self.assertEqual(self.m.load()['records'],before)
        promoted=self.s.promote(proposal['observation_id'],True)
        self.assertEqual(promoted['decision'],'ACCEPT');self.assertEqual(len(self.m.load()['records']),5)
        self.assertEqual(self.s.load()['relationships'][0]['derived_from'],ids)
        self.assertEqual(self.s.load()['relationships'][0]['source_disposition'],'retained')
        self.assertEqual(self.s.explain(promoted['record']['id'])['relationships'][0]['consolidates'],ids)
    def test_conflicting_consolidation_refused(self):
        a=self.add('default_theme=purple',project='X',metadata={'fact_key':'theme'})
        b=self.add('default_theme=green',project='X',agent_scope=['other'],metadata={'fact_key':'theme'})
        with self.assertRaises(ValueError):self.s.consolidate([a['id'],b['id']])
        # Imported historic conflicts must also be refused even if both were marked ACTIVE.
        d=self.m.load();d['records'][1]['agent_scope']=[];self.m.save(d)
        with self.assertRaises(ValueError):self.s.consolidate([a['id'],b['id']])
        self.assertEqual(self.s.load()['observations'],[])
    def test_negation_consolidation_refused(self):
        a=self.add('用户喜欢深色 UI',type='USER')
        b=copy.deepcopy(a);b['id']='synthetic-negated-source';b['content']='用户不喜欢深色 UI'
        data=self.m.load();data['records'].append(b);self.m.save(data)
        with self.assertRaises(ValueError):self.s.consolidate([a['id'],b['id']])
    def test_changed_sources_block_promotion_and_derived_recall(self):
        a=self.add('用户喜欢深色 UI',type='USER');b=self.add('用户偏好黑紫配色',type='USER')
        proposal=self.s.consolidate([a['id'],b['id']]);promoted=self.s.promote(proposal['observation_id'],True)['record']
        self.m.retire(a['id'],'Changed preference')
        result=self.s.retrieval('UI 配色')
        self.assertIn(promoted['id'],[r['memory_id'] for r in result['excluded'] if r['excluded_reason']=='derived_source_changed'])
        self.assertNotIn(promoted['id'],self.s.inject('UI 配色')['memory_ids'])
        # Another proposal with a subsequently retired source cannot write.
        x=self.add('用户偏好大字体',type='USER');y=self.add('用户喜欢宽间距',type='USER')
        p=self.s.consolidate([x['id'],y['id']]);self.m.retire(x['id'],'Obsolete')
        with self.assertRaises(ValueError):self.s.promote(p['observation_id'],True)
    def test_source_update_invalidates_proposal_and_derived_context(self):
        a=self.add('用户喜欢深色 UI',type='USER');b=self.add('用户偏好黑紫配色',type='USER')
        proposal=self.s.consolidate([a['id'],b['id']])
        accepted=self.s.promote(proposal['observation_id'],True)['record']
        pending=self.s.consolidate([a['id'],b['id']])
        self.m.add(c('用户喜欢深色 UI 和大字体',confirmed=True,type='USER',metadata={'supplements':a['id']}))
        with self.assertRaises(ValueError):self.s.promote(pending['observation_id'],True)
        self.assertNotIn(accepted['id'],self.s.inject('UI 配色')['memory_ids'])
    def test_primary_color_change_and_conflicting_sources_blocked(self):
        purple=self.add('Project-Aurora UI 紫色为主交互色',project='Project-Aurora',type='PROJECT')
        result=self.s.observe(c('Project-Aurora UI 主交互色改为蓝色',project='Project-Aurora',confirmed=True),True)
        self.assertEqual(result['decision'],'CONFLICT')
        self.assertIn(purple['id'],result['conflicts_with'])
        # Reproduce legacy data produced by the pre-fix host: two ACTIVE color assertions.
        blue=copy.deepcopy(purple);blue['id']='synthetic-blue-fixture';blue['content']='Project-Aurora UI 主交互色改为蓝色'
        d=self.m.load();d['records'].append(blue);self.m.save(d)
        with self.assertRaisesRegex(ValueError,'consolidation blocked'):self.s.consolidate([purple['id'],blue['id']])
        r=subprocess.run([sys.executable,'-m','cli','--store',str(self.path),'consolidate',purple['id'],blue['id']],cwd=ROOT,capture_output=True,encoding='utf-8')
        self.assertEqual(r.returncode,2);response=json.loads(r.stdout)
        self.assertEqual(response['decision'],'BLOCKED');self.assertIn('primary-interaction color',response['error'])
    def test_scope_weighted_retrieval_and_why(self):
        a=self.add('Memory OS Hermes Adapter 修复规则',type='WORKFLOW',project='X',machine='Win10',agent_scope=['hermes'],priority=90)
        b=self.add('Memory OS Hermes Adapter 修复路径',project='X',machine='Win11')
        y=self.add('Memory OS Hermes Adapter 修复规则',project='Y')
        mbti=self.add('MBTI personality',type='USER')
        task='修复 Win10 Hermes Memory OS Adapter'
        result=self.s.retrieval(task,'X','hermes','Win10')
        self.assertEqual(result['results'][0]['memory_id'],a['id'])
        factors=result['results'][0]['matched_factors']
        for key in ('task_relevance','project_scope','agent_scope','machine_scope','memory_type','priority','recency','confidence','stability','relationship','active_lifecycle_state'):self.assertIn(key,factors)
        excluded={r['memory_id']:r['excluded_reason'] for r in result['excluded']}
        self.assertEqual(excluded[b['id']],'machine_scope_mismatch');self.assertEqual(excluded[y['id']],'project_scope_mismatch');self.assertEqual(excluded[mbti['id']],'no_task_relevance')
        self.assertEqual(self.s.inject(task,'X','hermes','Win10',budget=500)['memory_ids'],[a['id']])
        self.assertEqual(self.s.inject('帮我分析今天 A 股')['memory_ids'],[])
        self.assertIn('Core Gate',self.s.explain(a['id'])['reason'])
    def test_smart_contradiction_blocks_core_near_duplicate(self):
        old=self.s.observe(c('以后用户喜欢深色 UI',confirmed=True),True)['record']
        result=self.s.observe(c('以后用户不喜欢深色 UI',confirmed=True),True)
        self.assertEqual(result['decision'],'CONFLICT')
        self.assertEqual(self.m.get(old['id'])['status'],'ACTIVE')
    def test_low_source_quality_and_expired_observation(self):
        for _ in range(3):r=self.s.observe({'content':'用户喜欢深色 UI','source_type':'import'})
        self.assertEqual(self.s.promotion_candidates(),[])
        self.assertEqual(self.s.promote(r['observation_id'],True)['decision'],'REJECT')
        temp=self.s.observe(c('今天先不开发'))
        d=self.s.load();d['observations'][-1]['expires_at']='2000-01-01T00:00:00+00:00';self.s.save(d)
        with self.assertRaises(ValueError):self.s.promote(temp['observation_id'],True)
    def test_real_cli_smart_chain(self):
        f=Path(self.tmp.name)/'candidate.json';f.write_text(json.dumps(c('用户偏好黑紫配色')),encoding='utf-8')
        def run(*args):
            r=subprocess.run([sys.executable,'-m','cli','--store',str(self.path),*args],cwd=ROOT,capture_output=True,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stdout+r.stderr);return json.loads(r.stdout)
        self.assertTrue(run('judge','--candidate',str(f))['should_remember'])
        for _ in range(3):r=run('observe','--candidate',str(f))
        self.assertEqual(len(run('promotion-candidates')),1)
        self.assertEqual(run('promote',r['observation_id'])['decision'],'NEEDS_CONFIRMATION')
        active=run('promote',r['observation_id'],'--user-confirmed')['record']
        self.assertEqual(run('smart-retrieve','黑紫配色')['results'][0]['memory_id'],active['id'])
        self.assertEqual(run('smart-inject','黑紫配色')['memory_ids'],[active['id']])
        self.assertTrue(run('why','股票')['excluded'])
        self.assertEqual(run('explain',active['id'])['status'],'ACTIVE')
        other=self.add('用户喜欢深色 UI',type='USER')
        proposal=run('consolidate',active['id'],other['id'])
        self.assertEqual(proposal['decision'],'CANDIDATE')
        derived=run('promote',proposal['observation_id'],'--user-confirmed')['record']
        self.assertEqual(run('explain',derived['id'])['relationships'][0]['source_disposition'],'retained')
if __name__=='__main__':unittest.main()
