"""Reviewed purchase check/posting commands: actual HTTP, MySQL, no production writes."""
import argparse,concurrent.futures,uuid,time
from purchase_posting_acceptance import PurchasePostingSuite
from acceptance import read_state,sql,literal,QA
import json

class PurchaseSnapshotSuite(PurchasePostingSuite):
    def versions(self,ids):return {id:self.document(id)['version'] for id in ids}
    def command(self,ids,target=1,versions=None,audit=False,**extra):
        body=dict(ids=ids,type=target,**extra)
        if versions is not None:body['versions']=versions
        return self.request('POST','/purchase-note/'+('audit' if audit else 'verification'),body,service='purchase')
    def history(self,id):return int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(id)+';'))
    def fresh(self,paid=0):self.fixture();return self.create_document(paid)
    def unchanged(self):assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
    def run_snapshot(self):
        def listing():
            id=self.fresh();version=self.document(id)['version'];assert len(version)==64
            result=self.request('GET','/purchase-note/list?pageIndex=1&pageSize=10&number='+self.document(id)['header']['number'],service='purchase')
            assert result.get('code')==10000 and len(result['data']['rows'])==1 and result['data']['rows'][0].get('version')==version
            self.unchanged();return ['Actual list and complete detail expose identical stable canonical reviewed versions']
        self.case('purchase.snapshot_list_matches_detail',listing)
        def required():
            id=self.fresh();v=self.versions([id]);before=self.history(id)
            for versions,extra in [(None,{}),({},{}),({id:'bad'},{}),({id:v[id],uuid.uuid4().hex:'0'*64},{}),(v,dict(version=v[id]))]:
                assert self.command([id],versions=versions,**extra).get('code')!=10000
            assert self.checked(id)=='0' and self.history(id)==before
            assert self.command([id],versions=v).get('code')==10000
            assert self.command([id],audit=True).get('code')!=10000;self.unchanged()
            return ['Missing/incomplete/extra/invalid/mixed versions reject; actual check/audit cannot use a no-version bypass']
        self.case('purchase.snapshot_complete_versions_required',required)
        def stale_check():
            id=self.fresh();old=self.versions([id]);body=self.revision(id);assert self.revise(body).get('code')==10000
            assert self.command([id],versions=old).get('code')!=10000 and self.checked(id)=='0'
            assert self.command([id],versions=self.versions([id])).get('code')==10000;self.unchanged()
            return ['An actual newer saved quantity cannot be checked from the older displayed version']
        self.case('purchase.snapshot_stale_check_rejected',stale_check)
        def stale_audit():
            id=self.fresh();assert self.command([id],versions=self.versions([id])).get('code')==10000;old=self.versions([id])
            assert self.command([id],0,self.versions([id])).get('code')==10000;assert self.revise(self.revision(id)).get('code')==10000
            assert self.command([id],versions=self.versions([id])).get('code')==10000
            before=self.history(id);assert self.command([id],versions=old,audit=True).get('code')!=10000
            assert self.history(id)==before;self.unchanged()
            return ['Old checked snapshot cannot post newer saved/checked quantities; no stock, cash or payable movement']
        self.case('purchase.snapshot_stale_audit_no_posting',stale_audit)
        def batch():
            first=self.fresh();second=self.create_document();ids=[first,second];old=self.versions(ids)
            assert self.revise(self.revision(second)).get('code')==10000;before=[self.history(i) for i in ids]
            assert self.command(ids,versions=old).get('code')!=10000
            assert [self.checked(i) for i in ids]==['0','0'] and [self.history(i) for i in ids]==before
            assert self.command(ids,versions=self.versions(ids)).get('code')==10000;self.unchanged()
            return ['A stale member cancels the full actual check batch with no partial history; fresh batch retries']
        self.case('purchase.snapshot_stale_batch_atomic',batch)
        def audit_batch():
            first=self.fresh(50);second=self.create_document(50);ids=sorted([first,second]);first,second=ids
            assert self.command(ids,versions=self.versions(ids)).get('code')==10000;old=self.versions(ids)
            assert self.command([second],0,self.versions([second])).get('code')==10000
            body=self.revision(second);body.update(money=50,account=self.account,actual=226);body['details'][0]['nums']=2
            assert self.revise(body).get('code')==10000 and self.command([second],versions=self.versions([second])).get('code')==10000
            before=[self.history(i) for i in ids]
            assert self.command(ids,versions=old,audit=True).get('code')!=10000
            assert [self.history(i) for i in ids]==before
            for id in ids:
                assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(id)+';')=='0'
                for table in ['room_info','account_info','summary']:assert self.ledger(table,id)==0
            self.unchanged()
            assert self.command(ids,versions=self.versions(ids),audit=True).get('code')==10000
            assert self.inventory()==4 and self.balance('account',self.account)==0 and self.balance('supplier',self.supplier)==352
            assert self.command(ids,0,self.versions(ids),audit=True).get('code')==10000;self.unchanged()
            return ['Stale audit batch rolls back earlier member stock/payment/payable/history; fresh two-document audit and reversal persist exactly4 units/100 cash/352 payable and restore originals']
        self.case('purchase.snapshot_stale_audit_batch_financial_rollback',audit_batch)
        def aba():
            id=self.fresh();old=self.versions([id]);assert self.command([id],versions=old).get('code')==10000
            assert self.command([id],0,self.versions([id])).get('code')==10000
            assert self.versions([id])!=old and self.command([id],versions=old).get('code')!=10000;self.unchanged()
            return ['Check/uncheck round trip cannot resurrect an old page version; history participates in digest']
        self.case('purchase.snapshot_roundtrip_invalidates_old_page',aba)
        def race():
            id=self.fresh();versions=self.versions([id]);before=self.history(id)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.command([id],versions=versions),range(2)))
            assert sum(r.get('code')==10000 for r in results)==1 and self.history(id)==before+1 and self.checked(id)=='1'
            fresh=self.versions([id]);assert self.command([id],versions=fresh).get('code')==10000 and self.history(id)==before+1;self.unchanged()
            return ['Same reviewed version has one actual winner; explicitly reread same-target retry remains idempotent']
        self.case('purchase.snapshot_concurrent_same_version',race)
        def fault():
            id=self.fresh();versions=self.versions([id]);before=self.history(id);trigger='qa_snapshot_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source="+literal(id)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA snapshot history failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.command([id],versions=versions).get('code')!=10000 and self.versions([id])==versions and self.history(id)==before
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.command([id],versions=versions).get('code')==10000;self.unchanged()
            return ['Real history write failure rolls back state/version; exact reviewed command retries after removing fault']
        self.case('purchase.snapshot_failure_atomic_retry',fault)
        def lifecycle():
            id=self.fresh(50);versions=self.versions([id]);assert self.command([id],versions=versions).get('code')==10000
            checked=self.versions([id]);assert self.command([id],versions=checked,audit=True).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            assert self.command([id],0,self.versions([id]),audit=True).get('code')==10000;self.unchanged()
            assert self.command([id],versions=checked,audit=True).get('code')!=10000;self.unchanged()
            assert self.command([id],0,self.versions([id])).get('code')==10000
            return ['Actual versioned check/post/reversal/uncheck preserves2 units,50 cash,176 payable and exact reversal; pre-post snapshot stays invalid']
        self.case('purchase.snapshot_actual_post_reverse_lifecycle',lifecycle)
        self.case('purchase.snapshot_consistent_list_read_race',self.read_race)
        self.write_report()

    def read_race(self):
        from read_gate import list_read_gate
        first=self.fresh();second=self.create_document();ids=[first,second];prefix='QASNAPSHOT'+uuid.uuid4().hex[:12]
        for index,id in enumerate(ids):sql(self.state,'UPDATE buy SET number='+literal(prefix+str(index))+' WHERE id='+literal(id)+';')
        old=self.versions(ids)
        with list_read_gate(self.state,'purchase') as gate:
            (gate/'armed').write_text('armed')
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                request=pool.submit(self.request,'GET','/purchase-note/list?pageIndex=1&pageSize=10&number='+prefix,service='purchase')
                try:
                    deadline=time.monotonic()+10
                    while not (gate/'entered').exists() and time.monotonic()<deadline:time.sleep(.025)
                    assert (gate/'entered').exists(),'Actual purchase list did not reach the bounded QA scheduling window'
                    sql(self.state,'UPDATE buy SET data='+literal('QA changed after page read')+' WHERE id='+literal(second)+';')
                finally:(gate/'resume').write_text('resume')
                result=request.result(timeout=25)
            assert not (gate/'timed-out').exists()
        assert result.get('code')==10000 and {row['id']:row.get('version') for row in result['data']['rows']}==old
        current=self.versions(ids);assert current[first]==old[first] and current[second]!=old[second]
        assert self.command(ids,versions=old).get('code')!=10000 and [self.checked(i) for i in ids]==['0','0']
        assert self.command(ids,versions=current).get('code')==10000;self.unchanged()
        return ['Observed actual page read paused before version queries; committed owned SQL mutation; response kept old snapshot, old command refused atomically, fresh command succeeded; scheduling code removed in finally']

FIXTURE=QA/'runtime/purchase-snapshot-browser.json'
def prepare():
    s=PurchaseSnapshotSuite(read_state());s.fixture();prefix='QASNAPUI'+uuid.uuid4().hex[:12];ids=[]
    for suffix in ['A','B','C']:
        body=s.body();body['purchaseNoteBuyDTO'].update(number=prefix+'-'+suffix,time='2026-11-15 13:47:00',money=50,account=s.account)
        body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]');ids.append(s.create(body))
    f=dict(database=s.state['database'],prefix=prefix,ids=ids,goods=s.goods,warehouse=s.warehouse,supplier=s.supplier,account=s.account,actor=s.actor,history={i:s.history(i) for i in ids},originalData={i:s.document(i)['header']['data'] for i in ids})
    FIXTURE.write_text(json.dumps(f),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared actual reviewed purchase browser orders '+prefix+'-A / -B / -C')
def external(batch=False):
    f=json.loads(FIXTURE.read_text());s=PurchaseSnapshotSuite(read_state());assert f['database']==s.state['database']
    s.goods=f['goods'];s.warehouse=f['warehouse'];s.supplier=f['supplier'];s.account=f['account'];id=f['ids'][2 if batch else 0]
    body=s.revision(id);body['details'][0]['nums']=2;body['actual']=226;body['data']='QA external batch newer' if batch else 'QA external detail newer';body['money']=50;body['account']=f['account']
    assert s.revise(body).get('code')==10000
    print('Actual versioned external edit persisted; old browser version must be rejected')
def verify(stage):
    state=read_state();f=json.loads(FIXTURE.read_text());assert state['database']==f['database'];s=PurchaseSnapshotSuite(state)
    head=[]
    for id in f['ids']:head.append(json.loads(sql(state,"SELECT JSON_OBJECT('check',CAST(`check` AS SIGNED),'audit',CAST(examine AS SIGNED),'data',data,'user',`user`,'total',total,'actual',actual) FROM buy WHERE id="+literal(id)+';')))
    transitions={'dirty':(0,0,0),'stale':(0,0,1),'checked':(1,0,2),'audited':(1,1,3),'reversed':(1,0,4),'unchecked':(0,0,5),'batch-stale':(0,0,5),'batch-checked':(0,0,5)}
    check,audit,extra=transitions[stage];assert head[0]['check']==check and head[0]['audit']==audit and s.history(f['ids'][0])==f['history'][f['ids'][0]]+extra
    assert head[0]['data']==(f['originalData'][f['ids'][0]] if stage=='dirty' else 'QA external detail newer')
    for index in [1,2]:
        changed=index==2 and stage.startswith('batch-');target=1 if stage=='batch-checked' else 0
        assert head[index]['check']==target and head[index]['audit']==0
        assert s.history(f['ids'][index])==f['history'][f['ids'][index]]+int(changed)+target
        assert head[index]['data']==('QA external batch newer' if changed else f['originalData'][f['ids'][index]])
    for row in head:assert row['user']==f['actor'] and float(row['total'])==200 and float(row['actual'])==226
    assert float(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==(2 if audit else 0)
    assert float(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==(50 if audit else 100)
    assert float(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==(176 if audit else 0)
    (QA/('reports/purchase-snapshot-browser-'+stage+'.json')).write_text(json.dumps(dict(status='verified',stage=stage,fixture_ids=f['ids'],production_business_writes=0,all_system_features_accepted=False)))
    print('PASS actual browser '+stage+': all three documents/history/amounts/operator and stock/cash/payable independently verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='run');a=p.parse_args().action
    if a=='run':PurchaseSnapshotSuite(read_state()).run_snapshot()
    elif a=='prepare':prepare()
    elif a in ['external-edit','external-batch']:external(a=='external-batch')
    elif a.startswith('verify-'):verify(a[7:])
    else:raise SystemExit('Unknown action')
