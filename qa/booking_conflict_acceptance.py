"""Actual optimistic editing and reviewed-document approval, isolated QA only."""
import copy,concurrent.futures,uuid,json,argparse
from decimal import Decimal
from booking_detail_acceptance import OrderDetailSuite
from acceptance import read_state,sql,literal,QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class OrderConflictSuite(OrderDetailSuite):
    def setup_edit(self):
        self.fixture();body=self.order_body();id=self.create_order(body);data=self.document(id)['data'];head=data['header'];item=data['items'][0]
        body.update(id=id,total=head['total'],actual=head['actual'],version=data.get('version','0'*64))
        body['purchaseOrderInfoDTOList'][0].update({key:item[key] for key in ['price','nums','discount','dsc','total','tax','tat','tpt']})
        return id,body
    def update(self,body):return self.request('PUT','/purchase-order/update',body,service='purchase')
    def reviewed_audit(self,id,version,target=1):return self.request('PUT','/purchase-order/audit',dict(ids=[id],type=target,version=version),service='purchase')
    def run_conflicts(self):
        def metadata():
            id,body=self.setup_edit();version=self.document(id)['data'].get('version')
            assert isinstance(version,str) and len(version)==64 and version==body['version'],'Full document lacks a stable review version'
            assert self.document(id)['data']['version']==version;self.unchanged()
            return ['Repeated real read returns same opaque version without business mutations']
        self.case('booking.edit_actual_version',metadata)
        def stale():
            id,body=self.setup_edit();other=copy.deepcopy(body);body['data']='QA first writer';other['data']='QA stale writer'
            assert self.update(body).get('code')==10000
            line=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(id)+';')
            assert self.update(other).get('code')!=10000,'A stale full-order update overwrote the first writer'
            assert sql(self.state,'SELECT data FROM bor WHERE id='+literal(id)+';')=='QA first writer' and self.records(id)==2
            assert sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(id)+';')==line;self.unchanged()
            return ['Second actual writer is rejected; first data, line identity, history and balances remain intact']
        self.case('booking.edit_stale_writer_rejected',stale)
        def concurrent_edits():
            id,body=self.setup_edit();requests=[dict(copy.deepcopy(body),data='QA concurrent '+str(i)) for i in range(2)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(self.update,requests))
            assert sum(r.get('code')==10000 for r in results)==1,'Same-version concurrent edits both persisted'
            winner=next(i for i,r in enumerate(results) if r.get('code')==10000)
            assert sql(self.state,'SELECT data FROM bor WHERE id='+literal(id)+';')==requests[winner]['data'] and self.records(id)==2;self.unchanged()
            return ['Two simultaneous actual HTTP saves from one version persist exactly one winner and one operation record']
        self.case('booking.edit_concurrent_one_winner',concurrent_edits)
        def approval():
            id,body=self.setup_edit();old=body['version'];body['data']='QA edited after review';assert self.update(body).get('code')==10000
            assert self.reviewed_audit(id,old).get('code')!=10000 and self.state_of(id)=='0','Stale reviewed content was approved'
            fresh=self.document(id)['data'].get('version','0'*64);assert self.reviewed_audit(id,fresh).get('code')==10000
            assert self.reviewed_audit(id,fresh,0).get('code')!=10000 and self.state_of(id)=='1'
            approved=self.document(id)['data']['version'];assert self.reviewed_audit(id,approved,0).get('code')==10000
            reversed=self.document(id)['data']['version'];assert len({old,fresh,approved,reversed})==4
            assert self.records(id)==4;self.unchanged()
            return ['Actual reviewed audit/reversal rejects stale content; versions change through edit/audit/reversal including return to unaudited state']
        self.case('booking.edit_reviewed_audit_version',approval)
        def required():
            id,body=self.setup_edit()
            for version in [None,'','x','0'*64]:
                request=copy.deepcopy(body)
                if version is None:request.pop('version',None)
                else:request['version']=version
                assert self.update(request).get('code')!=10000,'Missing/invalid/stale edit version accepted'
            assert self.records(id)==1 and self.update(body).get('code')==10000;self.unchanged()
            return ['Omitted, empty, malformed and invented versions cannot bypass update protection']
        self.case('booking.edit_version_required',required)
        def rollback():
            id,body=self.setup_edit();trigger='qa_bor_edit_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bor_info FOR EACH ROW BEGIN IF NEW.pid="+literal(id)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA edit line failure'; END IF; END$$\nDELIMITER ;")
            try:
                body['data']='QA retry edit';assert self.update(body).get('code')!=10000
                assert self.records(id)==1 and self.document(id)['data']['version']==body['version']
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.update(body).get('code')==10000 and self.records(id)==2;self.unchanged()
            return ['Real storage fault rolls back replaced lines, header and history; unchanged version permits same-request retry']
        self.case('booking.edit_failure_rollback_same_version_retry',rollback)
        def rename():
            id,body=self.setup_edit();sql(self.state,"UPDATE people SET name='QA renamed person' WHERE id="+literal(self.person)+';')
            data=self.document(id)['data'];assert data.get('version')==body['version'] and data['header']['peopleName']=='QA renamed person'
            assert self.update(body).get('code')==10000;self.unchanged()
            return ['Presentation-only master name changes do not create false document conflicts; actual references remain validated']
        self.case('booking.edit_version_excludes_display_names',rename)
        def scope():
            id,body=self.setup_edit();creator=self.actor
            role=self.success('POST','/role/add-role',dict(name='QA Edit Version '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.document(id).get('code')==403 and self.update(body).get('code')==403 and self.records(id)==1
                with qa_resource_grants(self.state,['/purchase-order/detail','/purchase-order/update'],[keyword]):
                    body['version']=self.document(id)['data']['version'];body['data']='QA authorized editor'
                    assert self.update(body).get('code')==10000
                    assert sql(self.state,'SELECT `user` FROM bor WHERE id='+literal(id)+';')==creator
                    assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+' AND `user`='+literal(actor)+';')=='1'
                    body['version']=self.document(id)['data']['version'];other=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Other Edit');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.document(id).get('code')==403 and self.update(body).get('code')==403 and self.records(id)==2
                    sql(self.state,'UPDATE `user` SET frame='+literal(self.state['frame_id'])+' WHERE id='+literal(actor)+';')
                    assert self.document(id).get('code')==10000
                assert self.update(body).get('code')==403 and self.records(id)==2
            finally:self.token=admin
            self.unchanged();return ['Actual OAuth editor needs live detail/update grants, preserves original creator, records real operator, rejects changed organization and immediate grant revocation despite a correct version']
        self.case('booking.edit_actual_role_scope',scope)
        self.write_report()

FIXTURE=QA/'runtime/booking-conflict-browser.json'
def prepare():
    s=OrderConflictSuite(read_state());id,body=s.setup_edit()
    FIXTURE.write_text(json.dumps(dict(database=s.state['database'],id=id,number=body['number'],body=body,goods=s.goods,warehouse=s.warehouse,supplier=s.supplier,account=s.account)),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared disposable versioned browser order '+body['number'])
def external_edit():
    state=read_state();f=json.loads(FIXTURE.read_text());assert state['database']==f['database']
    s=OrderConflictSuite(state);s.token=json.loads((QA/'runtime/browser-session.json').read_text())['token']
    body=f['body'];body.update(version=s.document(f['id'])['data']['version'],data='QA external newer')
    assert s.update(body).get('code')==10000
    print('Actual second writer saved a newer version in the dedicated QA order')
def verify(stage):
    state=read_state();f=json.loads(FIXTURE.read_text());assert state['database']==f['database']
    target,count,remark={'dirty':(0,1,'QA Booking'),'saved':(0,2,'QA local unsaved'),'stale-audit':(0,3,'QA external newer'),'stale-save':(0,3,'QA external newer'),'resolved':(0,4,'QA resolved after review'),'approved':(1,5,'QA resolved after review'),'reversed':(0,6,'QA resolved after review')}[stage]
    id=f['id'];head=json.loads(sql(state,"SELECT JSON_OBJECT('state',CAST(examine AS SIGNED),'data',data,'total',total,'actual',actual) FROM bor WHERE id="+literal(id)+';'))
    assert head['state']==target and head['data']==remark and Decimal(str(head['total']))==200 and Decimal(str(head['actual']))==226
    assert int(sql(state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+';'))==count
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0 and Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    (QA/('reports/booking-conflict-browser-'+stage+'.json')).write_text(json.dumps(dict(status='verified',case='booking.browser_conflict_'+stage,fixture_id=f['id'],production_business_writes=0,all_system_features_accepted=False)))
    print('PASS actual browser conflict checkpoint '+stage+'; actual status/history/content and stock/funds verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='run');a=p.parse_args().action
    if a=='prepare':prepare()
    elif a=='external-edit':external_edit()
    elif a.startswith('verify-'):verify(a[7:])
    elif a=='run':OrderConflictSuite(read_state()).run_conflicts()
    else:raise SystemExit('Unknown acceptance action')
