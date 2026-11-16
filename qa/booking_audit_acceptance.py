"""Actual order approval and reversal; approval must never itself post stock or money."""
import uuid,concurrent.futures,argparse,json,urllib.parse
from decimal import Decimal
from booking_draft_acceptance import BookingDraftSuite
from acceptance import read_state,sql,literal,QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class OrderAuditSuite(BookingDraftSuite):
    def audit(self,ids,target=1,versions=None):
        # Explicit real status reads prepare each command; no hidden request injection.
        if versions is None:
            versions={}
            for id in ids:
                response=self.request('GET','/purchase-order/status?id='+urllib.parse.quote(str(id),safe=''),service='purchase')
                versions[id]=(response.get('data') or {}).get('version','0'*64)
        return self.request('PUT','/purchase-order/audit',dict(ids=ids,type=target,versions=versions),service='purchase')
    def state_of(self,id):return sql(self.state,'SELECT CAST(examine AS SIGNED) FROM bor WHERE id='+literal(id)+';')
    def records(self,id):return int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+';'))
    def order(self):return self.create_order(self.order_body())
    def run(self):
        def ordinary():
            self.fixture();id=self.order();assert self.audit([id]).get('code')==10000 and self.state_of(id)=='1','Actual UUID order cannot be approved'
            assert self.audit([id],0).get('code')==10000 and self.state_of(id)=='0';self.unchanged()
            assert self.records(id)==3;return ['Actual UUID order approval/reversal changes only approval and writes actual operation history; inventory/cash/payable unchanged']
        self.case('booking.audit_uuid_roundtrip',ordinary)
        def batch():
            self.fixture();id=self.order();before=self.records(id)
            assert self.audit([id,uuid.uuid4().hex]).get('code')!=10000 and self.state_of(id)=='0' and self.records(id)==before
            assert self.audit([id]).get('code')==10000
            assert self.audit([id,uuid.uuid4().hex],0).get('code')!=10000 and self.state_of(id)=='1';return ['Missing batch member rolls back all approval/reversal changes and history']
        self.case('booking.audit_batch_atomic',batch)
        def invalid():
            self.fixture();id=self.order()
            for ids,target in [([id],2),([id],-1),([id,id],1),([],1),([''],1)]:assert self.audit(ids,target).get('code')!=10000 and self.state_of(id)=='0'
            assert self.audit([id]).get('code')==10000;return ['Invalid targets/duplicate or empty IDs are rejected; valid actual approval still works']
        self.case('booking.audit_strict_input',invalid)
        def supply():
            self.fixture();id=self.order();assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=False),service='purchase').get('code')==10000
            assert self.audit([id]).get('code')!=10000 and self.state_of(id)=='0'
            assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=True),service='purchase').get('code')==10000
            assert self.audit([id]).get('code')==10000;return ['Draft whose catalog relation was disabled cannot be approved; restored relationship permits approval']
        self.case('booking.audit_live_supply',supply)
        def fault():
            self.fixture();id=self.order();before=self.records(id);trigger='qa_bora_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bor' AND NEW.source="+literal(id)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA order audit history failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.audit([id]).get('code')!=10000 and self.state_of(id)=='0' and self.records(id)==before
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.audit([id]).get('code')==10000 and self.state_of(id)=='1';return ['Actual operation-history MySQL fault rolls back approval; removing fault permits same-request retry']
        self.case('booking.audit_storage_rollback_retry',fault)
        def repeat():
            self.fixture();id=self.order()
            versions={id:self.request('GET','/purchase-order/status?id='+id,service='purchase')['data']['version']}
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda _:self.audit([id],versions=versions),range(3)))
            assert sum(r.get('code')==10000 for r in results)==1 and self.state_of(id)=='1' and self.records(id)==2
            assert self.audit([id]).get('code')==10000 and self.records(id)==2;self.unchanged();return ['One same-version concurrent approval succeeds, stale contenders reject; a fresh-version repeat is idempotent with no duplicate history or posting']
        self.case('booking.audit_concurrent_idempotent',repeat)
        def auth():
            self.fixture();id=self.order();role=self.success('POST','/role/add-role',dict(name='QA Order Audit '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.audit([id]).get('code')==403 and self.state_of(id)=='0'
                with qa_resource_grants(self.state,['/purchase-order/audit'],[keyword]):
                    assert self.audit([id]).get('code')==10000
                    assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+' AND `user`='+literal(actor)+';')=='1'
                    other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Other Audit');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.audit([id],0).get('code')==403 and self.state_of(id)=='1'
                assert self.audit([id],0).get('code')==403
            finally:self.token=admin
            return ['Actual OAuth role requires audit grant, records real operator, immediately respects current organization and revoked grant']
        self.case('booking.audit_actual_role_scope',auth)
        def damaged():
            self.fixture();id=self.order();sql(self.state,'UPDATE bor SET actual=actual+1 WHERE id='+literal(id)+';')
            assert self.audit([id]).get('code')!=10000 and self.state_of(id)=='0'
            sql(self.state,'UPDATE bor SET actual=actual-1 WHERE id='+literal(id)+';');assert self.audit([id]).get('code')==10000
            return ['Old corrupted monetary totals refuse approval instead of silently changing historical amounts']
        self.case('booking.audit_corrupt_totals_denied',damaged)
        def receiving():
            self.fixture();id=self.order();assert self.audit([id]).get('code')==10000
            line=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(id)+';')
            body=self.body();body['purchaseNoteBuyDTO']['source']=id;body['purchaseNoteInfoDTOS'][0].update(source=line,discount=0,tax=13,batch='',mfd=None,serial='[]')
            receipt=self.create(body)
            assert self.audit([id],0).get('code')!=10000 and self.state_of(id)=='1'
            assert self.check([receipt]).get('code')==10000 and self.post([receipt]).get('code')==10000
            assert self.inventory()==2 and self.balance('supplier',self.supplier)==226 and self.balance('account',self.account)==100
            assert sql(self.state,'SELECT CONCAT(handle,\':\',CAST(b.state AS SIGNED)) FROM bor_info i JOIN bor b ON b.id=i.pid WHERE i.id='+literal(line)+';')=='2.0000:2'
            assert self.audit([id],0).get('code')!=10000
            assert self.post([receipt],0).get('code')==10000
            assert sql(self.state,'SELECT handle FROM bor_info WHERE id='+literal(line)+';')=='0.0000'
            assert self.audit([id],0).get('code')!=10000 and self.state_of(id)=='1';self.unchanged()
            return ['Actual created and approved UUID order feeds actual purchase create/check/post: stock2, payable226, received2; purchase reversal restores all quantities and balances; existing downstream draft continues to protect order approval']
        self.case('booking.audit_real_order_purchase_stock_payable',receiving)
        def full_read():
            self.fixture();body=self.order_body();body['purchaseOrderInfoDTOList'].append(dict(body['purchaseOrderInfoDTOList'][0]));id=self.create_order(body)
            result=self.request('GET','/purchase-order/document?id='+id,service='purchase');assert result.get('code')==10000 and len(result['data']['items'])==2
            assert Decimal(str(result['data']['header']['actual']))==452
            role=self.success('POST','/role/add-role',dict(name='QA Order Read '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                for path in ['/purchase-order/document?id='+id,'/purchase-order/detail?id='+id,'/purchase-order/list?pageIndex=1&pageSize=10']:
                    assert self.request('GET',path,service='purchase').get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/detail','/purchase-order/list'],[keyword]):
                    assert len(self.request('GET','/purchase-order/document?id='+id,service='purchase')['data']['items'])==2
                    other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Read Foreign');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.request('GET','/purchase-order/document?id='+id,service='purchase').get('code')==403
                    assert self.request('GET','/purchase-order/detail?id='+id,service='purchase').get('code')==403
                    listed=self.request('GET','/purchase-order/list?pageIndex=1&pageSize=10&number='+body['number'],service='purchase');assert listed.get('code')==10000 and listed['data']['total']==0
            finally:self.token=admin
            return ['Full document returns all actual lines; actual OAuth role needs detail/list resources; both legacy and full detail and list respect changed current organization']
        self.case('booking.audit_full_review_and_read_scope',full_read)
        def update_guard():
            self.fixture();body=self.order_body();id=self.create_order(body);body.update(id=id,total=200,actual=226);body['purchaseOrderInfoDTOList'][0].update(total=200,tat=26,tpt=226)
            body['version']=self.request('GET','/purchase-order/document?id='+id,service='purchase')['data']['version']
            assert self.request('PUT','/purchase-order/update',body,service='purchase').get('code')==10000
            assert sql(self.state,'SELECT `user` FROM bor WHERE id='+literal(id)+';')==self.actor
            assert self.audit([id]).get('code')==10000
            body['purchaseOrderInfoDTOList'][0]['nums']=3
            body['version']=self.request('GET','/purchase-order/document?id='+id,service='purchase')['data']['version']
            assert self.request('PUT','/purchase-order/update',body,service='purchase').get('code')!=10000 and self.state_of(id)=='1'
            assert sql(self.state,'SELECT nums FROM bor_info WHERE pid='+literal(id)+';')=='2.0000'
            assert self.audit([id],0).get('code')==10000
            body['version']=self.request('GET','/purchase-order/document?id='+id,service='purchase')['data']['version']
            assert self.request('PUT','/purchase-order/update',body,service='purchase').get('code')!=10000
            return ['Actual valid draft update preserves creator; approved order cannot be overwritten through legacy update and bad draft monetary totals reject without changing persisted quantities']
        self.case('booking.audit_legacy_update_cannot_bypass',update_guard)
        def closed():
            self.fixture();id=self.order();period=uuid.uuid4().hex
            sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+literal(period)+",'2026-11-15','2026-11-15',"+literal(self.actor)+');')
            try:assert self.audit([id]).get('code')!=10000 and self.state_of(id)=='0'
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            assert self.audit([id]).get('code')==10000
            return ['Actual isolated period fixture prevents approval and leaves state unchanged; removing only this fixture allows retry']
        self.case('booking.audit_closed_period_denied',closed)
        self.write_report()

def prepare_browser():
    suite=OrderAuditSuite(read_state());suite.fixture();body=suite.order_body();body['purchaseOrderInfoDTOList'].append(dict(body['purchaseOrderInfoDTOList'][0]));id=suite.create_order(body)
    (QA/'runtime/booking-audit-browser.json').write_text(json.dumps(dict(database=suite.state['database'],id=id,number=body['number'],goods=suite.goods,warehouse=suite.warehouse,supplier=suite.supplier,account=suite.account)),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8');print('Prepared actual two-line browser order '+body['number'])

def verify_browser(target):
    state=read_state();f=json.loads((QA/'runtime/booking-audit-browser.json').read_text(encoding='utf-8'));assert state['database']==f['database']
    assert sql(state,'SELECT CONCAT(CAST(examine AS SIGNED),\':\',total,\':\',actual) FROM bor WHERE id='+literal(f['id'])+';')==str(target)+':400.0000:452.0000'
    assert sql(state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(f['id'])+';')=='2'
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0 and Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    (QA/('reports/booking-audit-browser-'+str(target)+'.json')).write_text(json.dumps(dict(case='booking.browser_actual_audit_'+str(target),status='verified',all_system_features_accepted=False)),encoding='utf-8');print('PASS browser actual order approval='+str(target)+'; both real lines and400/452 preserved; stock/cash/payable unchanged')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify-audited','verify-reversed'],nargs='?',default='run');action=parser.parse_args().action
    if action=='prepare':prepare_browser()
    elif action.startswith('verify'):verify_browser(1 if action=='verify-audited' else 0)
    else:OrderAuditSuite(read_state()).run()
