"""Actual list-snapshot bulk approval: no stale or partial selection may commit."""
import copy,uuid,concurrent.futures,json,argparse,time
from decimal import Decimal
from booking_conflict_acceptance import OrderConflictSuite
from acceptance import read_state,sql,literal,QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class BatchAuditSuite(OrderConflictSuite):
    def setup_batch(self,count=2):
        self.fixture();self.prefix='QABA'+uuid.uuid4().hex[:20];self.ids=[]
        for index in range(count):
            body=self.order_body();body['number']=self.prefix+str(index);self.ids.append(self.create_order(body))
        self.ids.sort();return self.snapshot()
    def snapshot(self):return {id:self.document(id)['data']['version'] for id in self.ids}
    def listing(self):return self.request('GET','/purchase-order/list?pageIndex=1&pageSize=10&number='+self.prefix,service='purchase')
    def bulk(self,ids,versions,target=1):return self.request('PUT','/purchase-order/audit',dict(ids=ids,type=target,versions=versions),service='purchase')
    def states(self):return [self.state_of(id) for id in self.ids]
    def read_race(self):
        from read_gate import list_read_gate
        old=self.setup_batch()
        with list_read_gate(self.state) as gate:
            (gate/'armed').write_text('once',encoding='ascii')
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                listing=pool.submit(self.listing);deadline=time.monotonic()+6
                while not (gate/'entered').exists() and time.monotonic()<deadline and not listing.done():time.sleep(.025)
                assert (gate/'entered').exists() and not listing.done(),'Actual QA list did not reach the post-page scheduling gate'
                sql(self.state,"UPDATE bor_info SET data='QA list race line' WHERE pid="+literal(self.ids[0])+';')
                assert not (gate/'timed-out').exists() and not listing.done(),'The actual list was no longer paused when the fixture change committed'
                (gate/'resume').write_text('resume',encoding='ascii');response=listing.result(timeout=20)
                assert not (gate/'timed-out').exists()
        assert response.get('code')==10000
        assert {r['id']:r.get('version') for r in response['data']['rows']}==old,'List versions mixed committed detail changes into an earlier page snapshot'
        current=self.snapshot();assert current[self.ids[0]]!=old[self.ids[0]] and current[self.ids[1]]==old[self.ids[1]]
        shown={r['id']:r['version'] for r in response['data']['rows']}
        assert self.bulk(self.ids,shown).get('code')==9999 and self.states()==['0','0'] and [self.records(id) for id in self.ids]==[1,1]
        assert self.bulk(self.ids,current).get('code')==10000 and self.states()==['1','1'] and [self.records(id) for id in self.ids]==[2,2]
        self.unchanged();return ['Actual QA HTTP list paused after its page read; dedicated SQL changed its own detail before version queries; returned versions remain the old consistent snapshot; stale response cannot approve either order, a new read can approve both without stock/funds changes; the temporary local JVM scheduling gate was removed']
    def run_batch(self):
        def listed():
            versions=self.setup_batch();rows=self.listing()['data']['rows']
            assert len(rows)==2 and {r['id']:r.get('version') for r in rows}==versions,'Actual list omits reviewed versions or disagrees with full document'
            assert self.snapshot()==versions;self.unchanged();return ['Real authorized list and full documents expose the same stable versions for all selected orders']
        self.case('booking.batch_list_versions',listed)
        def stale():
            versions=self.setup_batch();id=self.ids[-1];data=self.document(id)['data'];head=data['header'];line=data['items'][0];body=self.order_body()
            body.update(id=id,version=data['version'],number=head['number'],total=head['total'],actual=head['actual'],data='QA changed after list')
            body['purchaseOrderInfoDTOList'][0].update({key:line[key] for key in ['price','nums','discount','dsc','total','tax','tat','tpt']})
            assert self.update(body).get('code')==10000
            rejected=self.bulk(self.ids,versions)
            assert rejected.get('code')==9999 and '已变化' in rejected.get('message',''),'Stale list batch was not rejected as a real version conflict'
            assert self.states()==['0','0'] and [self.records(id) for id in self.ids]==[1,2]
            assert sql(self.state,'SELECT data FROM bor WHERE id='+literal(id)+';')=='QA changed after list';self.unchanged()
            return ['Last sorted member changed after listing: entire actual batch rejects and earlier member/history rolls back']
        self.case('booking.batch_stale_member_atomic',stale)
        def ordinary():
            versions=self.setup_batch();assert self.bulk(self.ids,versions).get('code')==10000 and self.states()==['1','1']
            rows=self.listing()['data']['rows'];fresh={r['id']:r.get('version') for r in rows}
            assert all(fresh[id] and fresh[id]!=versions[id] for id in self.ids)
            assert self.bulk(self.ids,fresh,0).get('code')==10000 and self.states()==['0','0']
            assert [self.records(id) for id in self.ids]==[3,3];self.unchanged()
            return ['Actual current-list batch approval/reversal affects all selected UUIDs exactly once without posting stock or funds']
        self.case('booking.batch_fresh_roundtrip',ordinary)
        def shape():
            versions=self.setup_batch()
            for wrong in [None,{}, {self.ids[0]:versions[self.ids[0]]},dict(versions,unknown='0'*64),{id:'x' for id in self.ids}]:
                assert self.bulk(self.ids,wrong).get('code')!=10000,'Missing/incomplete/extra/malformed batch version accepted'
            assert self.request('PUT','/purchase-order/audit',dict(ids=self.ids,type=1),service='purchase').get('code')!=10000
            assert self.request('PUT','/purchase-order/audit',dict(ids=[self.ids[0]],type=1,version=versions[self.ids[0]],versions={self.ids[0]:versions[self.ids[0]]}),service='purchase').get('code')!=10000
            assert self.states()==['0','0'] and [self.records(id) for id in self.ids]==[1,1];self.unchanged()
            return ['No omitted version mode; exact ID/version membership required, with single and batch protocols mutually exclusive']
        self.case('booking.batch_complete_versions_required',shape)
        def missing():
            versions=self.setup_batch();missing='z'*32;versions[missing]='0'*64
            assert self.bulk(self.ids+[missing],versions).get('code')!=10000
            assert self.states()==['0','0'] and [self.records(id) for id in self.ids]==[1,1];self.unchanged()
            return ['Complete-shaped request with a genuinely missing final UUID rejects and rolls back earlier selected orders']
        self.case('booking.batch_missing_document_atomic',missing)
        def fault():
            versions=self.setup_batch();trigger='qa_bulk_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bor' AND NEW.source="+literal(self.ids[-1])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA second bulk history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.bulk(self.ids,versions).get('code')!=10000 and self.states()==['0','0']
                assert self.snapshot()==versions and [self.records(id) for id in self.ids]==[1,1]
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.bulk(self.ids,versions).get('code')==10000 and self.states()==['1','1'];self.unchanged()
            return ['Actual second-member history storage failure rolls back the entire transaction and same snapshot can retry after removing the fault']
        self.case('booking.batch_storage_fault_atomic_retry',fault)
        def overlap():
            versions=self.setup_batch(3);groups=[self.ids[:2],self.ids[1:]]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda ids:self.bulk(ids,{id:versions[id] for id in ids}),groups))
            assert sum(r.get('code')==10000 for r in results)==1,'Overlapping stale batches both succeeded'
            winner=next(i for i,r in enumerate(results) if r.get('code')==10000)
            loser=results[1-winner];assert loser.get('code')==9999 and '已变化' in loser.get('message','')
            assert self.states()==(['1','1','0'] if winner==0 else ['0','1','1'])
            assert [self.records(id) for id in self.ids]==([2,2,1] if winner==0 else [1,2,2]);self.unchanged()
            return ['Two overlapping real HTTP batches from one snapshot commit one complete winner; losing batch does not partly approve its non-overlap member']
        self.case('booking.batch_overlap_one_complete_winner',overlap)
        def scope():
            versions=self.setup_batch();role=self.success('POST','/role/add-role',dict(name='QA Bulk '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.bulk(self.ids,versions).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/audit'],[keyword]):
                    assert self.bulk(self.ids,versions).get('code')==10000
                    self.token=admin;versions=self.snapshot();self.token=PurchaseUiSuite.login(self,user)
                    other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Other Bulk');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.bulk(self.ids,versions,0).get('code')==403 and self.states()==['1','1']
                    sql(self.state,'UPDATE `user` SET frame='+literal(self.state['frame_id'])+' WHERE id='+literal(actor)+';')
                assert self.bulk(self.ids,versions,0).get('code')==403
            finally:self.token=admin
            self.unchanged();return ['Correct batch versions do not bypass real OAuth grant, current organization or immediate revocation']
        self.case('booking.batch_live_role_and_frame',scope)
        def aba():
            old=self.setup_batch();assert self.bulk(self.ids,old).get('code')==10000
            assert self.bulk(self.ids,self.snapshot(),0).get('code')==10000
            assert self.bulk(self.ids,old).get('code')!=10000 and self.states()==['0','0']
            assert [self.records(id) for id in self.ids]==[3,3];self.unchanged()
            return ['Returning both orders to unaudited does not make their old list snapshots valid again']
        self.case('booking.batch_old_snapshot_after_roundtrip',aba)
        self.case('booking.batch_consistent_list_read_race',self.read_race)
        self.write_report()

FIXTURE=QA/'runtime/booking-batch-browser.json'
def prepare():
    s=BatchAuditSuite(read_state());s.setup_batch(3)
    numbers=[sql(s.state,'SELECT number FROM bor WHERE id='+literal(id)+';') for id in s.ids]
    FIXTURE.write_text(json.dumps(dict(database=s.state['database'],ids=s.ids,numbers=numbers,prefix=s.prefix,goods=s.goods,supplier=s.supplier,account=s.account)),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared disposable batch prefix '+s.prefix+'; select '+numbers[0]+' and '+numbers[1]+'; leave '+numbers[2]+' unchecked')
def external_edit():
    state=read_state();f=json.loads(FIXTURE.read_text());assert f['database']==state['database']
    s=BatchAuditSuite(state);s.token=json.loads((QA/'runtime/browser-session.json').read_text())['token'];id=f['ids'][1]
    data=s.document(id)['data'];head=data['header'];line=data['items'][0]
    body=dict(id=id,version=data['version'],supplier=head['supplier'],people=head['people'],number=head['number'],time='2026-11-15',arrival='2026-11-16',total=head['total'],actual=head['actual'],data='QA batch newer',file=head['file'],purchaseOrderInfoDTOList=[{key:line[key] for key in ['goods','warehouse','unit','attr','price','nums','discount','dsc','total','tax','tat','tpt']}])
    assert s.update(body).get('code')==10000
    print('Actual second writer changed the second selected QA order after the list was read')
def verify(stage):
    state=read_state();f=json.loads(FIXTURE.read_text());assert f['database']==state['database']
    expected,counts={'stale':(['0','0','0'],[1,2,1]),'approved':(['1','1','0'],[2,3,1]),'mixed':(['1','1','0'],[2,3,1]),'reversed':(['0','0','0'],[3,4,1])}[stage]
    for index,id in enumerate(f['ids']):
        assert sql(state,'SELECT CAST(examine AS SIGNED) FROM bor WHERE id='+literal(id)+';')==expected[index]
        assert int(sql(state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+';'))==counts[index]
        assert sql(state,'SELECT CONCAT(total,\':\',actual) FROM bor WHERE id='+literal(id)+';')=='200.0000:226.0000'
    assert sql(state,'SELECT data FROM bor WHERE id='+literal(f['ids'][1])+';')=='QA batch newer'
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0 and Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    (QA/('reports/booking-batch-browser-'+stage+'.json')).write_text(json.dumps(dict(status='verified',case='booking.browser_batch_'+stage,fixture_ids=f['ids'],production_business_writes=0,all_system_features_accepted=False)))
    print('PASS actual browser batch '+stage+'; all selected and unselected states/history plus stock/funds independently verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='run');a=p.parse_args().action
    if a=='prepare':prepare()
    elif a=='external-edit':external_edit()
    elif a.startswith('verify-'):verify(a[7:])
    elif a=='read-race':
        s=BatchAuditSuite(read_state());s.case('booking.batch_consistent_list_read_race',s.read_race);s.write_report()
    elif a=='run':BatchAuditSuite(read_state()).run_batch()
    else:raise SystemExit('Unknown acceptance action')
