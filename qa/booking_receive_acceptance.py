"""Real source-order generation, pending reservations, receipts and reversals."""
import uuid,concurrent.futures,argparse,json,time
from decimal import Decimal
from booking_audit_acceptance import OrderAuditSuite
from acceptance import read_state,sql,literal,QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class ReceiveSuite(OrderAuditSuite):
    def source_state_cases(self):
        def corrupt(approval=1,state=0):
            sql(self.state,'UPDATE bor SET examine='+str(approval)+',state='+str(state)+' WHERE id='+literal(self.source)+';')
        def read():
            self.setup();corrupt(2)
            assert self.preview().get('code')!=10000,'Invalid approval2 allowed receiving preview'
            assert self.receive(self.receive_body()).get('code')!=10000 and self.count_receipts()==0
            assert self.request('GET','/purchase-order/document?id='+self.source,service='purchase')['data']['header']['examine']==2
            assert self.request('GET','/purchase-order/status?id='+self.source,service='purchase')['data']['examine']==2
            self.unchanged();return ['Approval2 is preserved numerically in actual document/status and rejected by preview and generation without new drafts']
        self.case('booking.source_invalid_approval_preview',read)
        def raw():
            self.setup();corrupt(2)
            assert self.request('POST','/purchase-note/add',self.direct_body(),service='purchase').get('code')!=10000,'Raw source add bypassed approval2'
            assert self.count_receipts()==0;self.unchanged();return ['Direct purchase add cannot bypass malformed source approval']
        self.case('booking.source_invalid_approval_raw_add',raw)
        def posting():
            self.setup();id=self.create_receipt(self.receive_body(1));assert self.check([id]).get('code')==10000;corrupt(2)
            assert self.post([id]).get('code')!=10000,'Existing receipt posted against invalid approval2'
            assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(id)+';')=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM psi_purchase_posting WHERE purchase_id='+literal(id)+';')=='0'
            self.unchanged();return ['Existing checked receipt rejects approval2 at actual posting and leaves no stock/funds/posting marker']
        self.case('booking.source_invalid_approval_posting',posting)
        def unknown():
            self.setup();corrupt(1,4)
            assert self.preview().get('code')!=10000,'Unknown source state4 allowed preview'
            assert self.receive(self.receive_body()).get('code')!=10000 and self.request('POST','/purchase-note/add',self.direct_body(),service='purchase').get('code')!=10000
            assert self.count_receipts()==0;self.unchanged();return ['Unknown execution4 rejects preview/generated and raw source receiving rather than normalizing damaged state']
        self.case('booking.source_unknown_execution_generation',unknown)
        def post_unknown():
            self.setup();id=self.create_receipt(self.receive_body(1));assert self.check([id]).get('code')==10000;corrupt(1,4)
            assert self.post([id]).get('code')!=10000,'Existing receipt overwrote unknown source state4'
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM bor WHERE id='+literal(self.source)+';')=='4';self.unchanged()
            return ['Unknown source execution state rejects existing-receipt posting and retains original enum and balances']
        self.case('booking.source_unknown_execution_posting',post_unknown)
        def reverse():
            self.setup();id=self.create_receipt(self.receive_body(1));assert self.check([id]).get('code')==10000 and self.post([id]).get('code')==10000;corrupt(2,1)
            assert self.post([id],0).get('code')!=10000,'Malformed source approval permitted reversal'
            assert self.inventory()==1 and self.balance('supplier',self.supplier)==113 and self.balance('account',self.account)==100
            assert sql(self.state,'SELECT handle FROM bor_info WHERE pid='+literal(self.source)+';')=='1.0000'
            assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(id)+';')=='1'
            corrupt(1,1);assert self.post([id],0).get('code')==10000;self.unchanged()
            return ['Malformed source approval refuses reversal without changing actual posted stock/payable/quantity; restoring only QA source allows original reversal']
        self.case('booking.source_invalid_approval_reverse',reverse)
        def audit_approval():
            self.setup();corrupt(2);before=self.records(self.source)
            assert self.audit([self.source]).get('code')!=10000,'Approval2 falsely reported as already approved1'
            assert self.state_of(self.source)=='2' and self.records(self.source)==before;self.unchanged()
            return ['Order audit rejects malformed approval instead of false idempotent success or historical rewrite']
        self.case('booking.source_invalid_order_audit_approval',audit_approval)
        def audit_execution():
            self.setup(False);corrupt(0,4);before=self.records(self.source)
            assert self.audit([self.source],0).get('code')!=10000,'Unknown state skipped validation on idempotent reversal'
            assert self.records(self.source)==before and self.state_of(self.source)=='0';self.unchanged()
            return ['Even same-target order audit refuses unknown execution state before idempotent shortcut']
        self.case('booking.source_invalid_order_audit_execution',audit_execution)
    def setup(self,approved=True,multi=False,discount=0):
        self.fixture();body=self.order_body();body['purchaseOrderInfoDTOList'][0]['discount']=discount
        if multi:body['purchaseOrderInfoDTOList'].append(dict(body['purchaseOrderInfoDTOList'][0]))
        self.source=self.create_order(body);self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+' ORDER BY id;').splitlines()
        if approved:assert self.audit([self.source]).get('code')==10000
    def preview(self):return self.request('GET','/purchase-order/receive-preview?id='+self.source,service='purchase')
    def receive_body(self,nums=2):return dict(id=self.source,number='QARECV'+uuid.uuid4().hex[:23],time='2026-11-15',items=[dict(id=line,nums=nums) for line in self.lines])
    def receive(self,body):return self.request('POST','/purchase-order/receive',body,service='purchase')
    def create_receipt(self,body):
        result=self.receive(body);assert result.get('code')==10000 and result.get('data',{}).get('id'),'Actual source generation rejected; code='+str(result.get('code'));return result['data']['id']
    def direct_body(self,nums=2):
        body=self.body();body['purchaseNoteBuyDTO']['source']=self.source;body['purchaseNoteInfoDTOS'][0].update(source=self.lines[0],nums=nums,discount=0,tax=13,batch='',mfd=None,serial='[]');return body
    def count_receipts(self):return int(sql(self.state,'SELECT COUNT(*) FROM buy WHERE source='+literal(self.source)+';'))
    def remove(self,id):return self.request('POST','/purchase-note/delete',[id],service='purchase')
    def available(self):return Decimal(str(self.preview()['data']['items'][0]['available']))
    def preview_race(self):
        self.setup();trigger='qa_receive_wait_'+uuid.uuid4().hex[:9]
        sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON buy FOR EACH ROW BEGIN IF NEW.source="+literal(self.source)+" THEN DO SLEEP(3); END IF; END$$\nDELIMITER ;")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                generation=pool.submit(self.receive,self.receive_body())
                observed=False
                for _ in range(20):
                    if int(sql(self.state,"SELECT COUNT(*) FROM information_schema.processlist WHERE DB="+literal(self.state['database'])+" AND STATE='User sleep';"))>0:observed=True;break
                    time.sleep(.05)
                assert observed,'Could not observe actual generation transaction while storage trigger held it'
                quote=pool.submit(self.preview);created=generation.result();actual=quote.result()
            assert created.get('code')==10000 and actual.get('code')==10000
            assert Decimal(str(actual['data']['items'][0]['reserved']))==2 and Decimal(str(actual['data']['items'][0]['available']))==0
            assert [draft['id'] for draft in actual['data']['drafts']]==[created['data']['id']],'Preview saw current reserved quantity but stale/missing pending draft'
            return ['Actual preview starts while generated receipt is uncommitted (observed MySQL sleep trigger); after lock wait, both reservation and pending-draft action use current committed data']
        finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
    def run(self,baseline=False):
        def legacy():
            self.setup();result=self.request('GET','/purchase-order/generate-purchaseData?id='+self.source,service='purchase')
            assert result.get('code')==10000 and result['data']['goods']==self.goods,'Legacy generator queried wrong source tables'
            assert Decimal(result['data']['purchaseNoteOtherGenerateDataDTO']['actual'])==226
            self.unchanged();return ['Legacy single-line preview reads actual approved bor/bor_info rather than purchase receiving tables']
        self.case('booking.receive_legacy_source_preview',legacy)
        def unapproved():
            self.setup(False);body=self.direct_body();result=self.request('POST','/purchase-note/add',body,service='purchase')
            assert result.get('code')!=10000 and self.count_receipts()==0,'Direct add persisted receipt from unapproved order';return ['Direct purchase add cannot bypass source-order approval validation']
        self.case('booking.receive_unapproved_source_denied',unapproved)
        def pending():
            self.setup();self.create(self.direct_body(1));body=self.direct_body(2);result=self.request('POST','/purchase-note/add',body,service='purchase')
            assert result.get('code')!=10000 and self.count_receipts()==1,'Pending draft quantities were not reserved';self.unchanged()
            return ['Actual unposted draft reserves quantity; a different-number add cannot exceed the remaining order quantity']
        self.case('booking.receive_pending_quantity_reserved',pending)
        if baseline:self.write_report();return
        def multi():
            self.setup(multi=True,discount=10);quote=self.preview();assert quote.get('code')==10000 and len(quote['data']['items'])==2
            body=self.receive_body();body.update(supplier='forged-supplier',frame='forged-frame',user='forged-user',actual=1)
            body['items'][0].update(goods='forged-goods',warehouse='forged-warehouse',price=1,discount=0,tax=0,total=1,tpt=1)
            id=self.create_receipt(body)
            assert sql(self.state,'SELECT CONCAT(source,\':\',total,\':\',actual,\':\',money,\':\',CAST(examine AS SIGNED)) FROM buy WHERE id='+literal(id)+';')==self.source+':360.0000:406.8000:0.0000:0'
            assert sql(self.state,'SELECT CONCAT(supplier,\':\',frame,\':\',`user`) FROM buy WHERE id='+literal(id)+';')==self.supplier+':'+self.state['frame_id']+':'+self.actor
            for line in self.lines:
                assert sql(self.state,'SELECT CONCAT(goods,\':\',warehouse,\':\',price,\':\',nums,\':\',discount,\':\',dsc,\':\',tax,\':\',tat) FROM buy_info WHERE pid='+literal(id)+' AND source='+literal(line)+';')==self.goods+':'+self.warehouse+':100.0000:2.0000:10.00:20.0000:13.00:23.4000'
            assert self.available()==0;self.unchanged();return ['Actual two-line generation ignores forged header/line prices, IDs and ownership; preserves real source IDs,10%discount/13%tax and authoritative360/406.8; draft reserves but does not post']
        self.case('booking.receive_all_lines_and_discount',multi)
        def partial():
            self.setup(discount=10);first=self.create_receipt(self.receive_body(1));assert self.available()==1
            assert self.check([first]).get('code')==10000 and self.post([first]).get('code')==10000
            assert self.inventory()==1 and self.balance('supplier',self.supplier)==Decimal('101.7') and self.available()==1
            second=self.create_receipt(self.receive_body(1));assert self.check([second]).get('code')==10000 and self.post([second]).get('code')==10000
            assert self.inventory()==2 and self.balance('supplier',self.supplier)==Decimal('203.4') and self.available()==0
            assert sql(self.state,'SELECT CONCAT(handle,\':\',CAST(b.state AS SIGNED)) FROM bor_info i JOIN bor b ON b.id=i.pid WHERE i.id='+literal(self.lines[0])+';')=='2.0000:2'
            assert self.post([second],0).get('code')==10000 and self.available()==0
            assert self.check([second],0).get('code')==10000 and self.remove(second).get('code')==10000 and self.available()==1
            assert self.post([first],0).get('code')==10000;self.unchanged()
            return ['Actual two partial receipts post stock/payable1/101.7 then2/203.4; reverse restores quantities, reversed draft still reserves, uncheck/delete releases reservation']
        self.case('booking.receive_partial_stock_payable_and_release',partial)
        def concurrent_requests():
            self.setup();bodies=[self.receive_body(),self.receive_body()]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(self.receive,bodies))
            assert sum(r.get('code')==10000 for r in results)==1 and self.count_receipts()==1 and self.available()==0
            assert self.receive(next(b for b,r in zip(bodies,results) if r.get('code')==10000)).get('code')!=10000 and self.count_receipts()==1
            self.unchanged();return ['Two real concurrent different-number full generation requests produce only one draft; duplicate request creates no extra receipt']
        self.case('booking.receive_concurrent_no_over_generation',concurrent_requests)
        def fault():
            self.setup(multi=True);body=self.receive_body();trigger='qa_receive_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON buy_info FOR EACH ROW BEGIN IF NEW.source="+literal(self.lines[1])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA generated second line failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.receive(body).get('code')!=10000 and self.count_receipts()==0 and self.available()==2
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            self.create_receipt(body);assert self.count_receipts()==1;self.unchanged();return ['Actual second receiving-line storage fault rolls back header/earlier line/reservation/history; same number and payload succeeds after removing fault']
        self.case('booking.receive_storage_failure_atomic_retry',fault)
        def access():
            self.setup();role=self.success('POST','/role/add-role',dict(name='QA Receive '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.preview().get('code')==403 and self.receive(self.receive_body()).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/generate-purchaseData'],[keyword]):assert self.preview().get('code')==10000 and self.receive(self.receive_body()).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/generate-purchaseData','/purchase-note/add'],[keyword]):
                    id=self.create_receipt(self.receive_body(1));assert sql(self.state,'SELECT `user` FROM buy WHERE id='+literal(id)+';')==actor
                    frame=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Receive Other');"+'UPDATE `user` SET frame='+literal(frame)+' WHERE id='+literal(actor)+';')
                    assert self.preview().get('code')==403 and self.receive(self.receive_body(1)).get('code')==403
                assert self.preview().get('code')==403
            finally:self.token=admin
            return ['Actual OAuth role needs generation resource and purchase-add separately, records actual actor and respects immediate organization change/revocation']
        self.case('booking.receive_actual_permissions_scope',access)
        def invalid():
            self.setup()
            for items in [[],[dict(id=self.lines[0],nums=0)],[dict(id=self.lines[0],nums=-1)],[dict(id=self.lines[0],nums='0.00001')],[dict(id=uuid.uuid4().hex,nums=1)],[dict(id=self.lines[0],nums=1)]*2]:
                body=self.receive_body();body['items']=items;assert self.receive(body).get('code')!=10000 and self.count_receipts()==0
            for date in ['2026-02-30','2026-11-14']:
                body=self.receive_body();body['time']=date;assert self.receive(body).get('code')!=10000 and self.count_receipts()==0
            for field,value in [('source',uuid.uuid4().hex),('source','0')]:
                body=self.direct_body();body['purchaseNoteBuyDTO'][field]=value;assert self.request('POST','/purchase-note/add',body,service='purchase').get('code')!=10000 and self.count_receipts()==0
            body=self.direct_body();body['purchaseNoteInfoDTOS'][0]['unit']='wrong-unit';assert self.request('POST','/purchase-note/add',body,service='purchase').get('code')!=10000 and self.count_receipts()==0
            period=uuid.uuid4().hex;sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+literal(period)+",'2026-11-15','2026-11-15',"+literal(self.actor)+');')
            try:assert self.receive(self.receive_body()).get('code')!=10000 and self.count_receipts()==0
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            return ['Empty/duplicate/foreign lines, invalid quantity/date/period, receipt before order, mismatched source/unit and missing source head all reject without persistence']
        self.case('booking.receive_invalid_requests_no_persistence',invalid)
        def legacy_rates():
            self.setup(False,discount=10);sql(self.state,'UPDATE bor_info SET discount=0.9,tax=0.13 WHERE pid='+literal(self.source)+';');assert self.audit([self.source]).get('code')==10000
            id=self.create_receipt(self.receive_body(1));assert sql(self.state,'SELECT CONCAT(discount,\':\',dsc,\':\',tax,\':\',tat,\':\',tpt) FROM buy_info WHERE pid='+literal(id)+';')=='10.00:10.0000:13.00:11.7000:101.7000'
            return ['Consistent historical fraction representation is normalized to effective10%discount/13%tax for partial receiving without losing discount or tax']
        self.case('booking.receive_legacy_percentage_preserved',legacy_rates)
        def revise_reservation():
            self.setup();first=self.create_receipt(self.receive_body(1));second=self.create_receipt(self.receive_body(1));body=self.revision(first);body['details'][0]['nums']=2;body['actual']=226
            assert self.revise(body).get('code')!=10000 and self.available()==0
            assert self.remove(second).get('code')==10000 and self.available()==1
            assert self.revise(body).get('code')==10000 and self.available()==0
            return ['Source draft revision excludes its own reservation but honors other drafts; removing only other free draft releases exactly its quantity and permits retry']
        self.case('booking.receive_revision_reservation_consistent',revise_reservation)
        def disabled():
            self.setup();assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=False),service='purchase').get('code')==10000
            assert self.receive(self.receive_body()).get('code')!=10000 and self.count_receipts()==0
            body=self.direct_body();assert self.request('POST','/purchase-note/add',body,service='purchase').get('code')!=10000 and self.count_receipts()==0
            return ['Current disabled supply relationship blocks new receiving generation and direct source-add bypass']
        self.case('booking.receive_disabled_supply_denied',disabled)
        def precision():
            self.fixture();body=self.order_body();body['purchaseOrderInfoDTOList'][0].update(price='1.0001',nums=1,discount=0,tax=0);self.source=self.create_order(body);self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+';').splitlines();assert self.audit([self.source]).get('code')==10000
            id=self.create_receipt(self.receive_body('0.5'));assert sql(self.state,'SELECT CONCAT(price,\':\',nums,\':\',total,\':\',tpt) FROM buy_info WHERE pid='+literal(id)+';')=='1.0001:0.5000:0.5001:0.5001';self.unchanged()
            return ['Actual fractional receiving1.0001x0.5 uses positive four-decimal HALF_UP .5001, matching the integer-based browser preview']
        self.case('booking.receive_four_decimal_half_up',precision)
        self.case('booking.receive_preview_current_after_lock_wait',self.preview_race)
        def closed_source():
            self.setup();receipt=self.create_receipt(self.receive_body(1));assert self.check([receipt]).get('code')==10000
            sql(self.state,'UPDATE bor SET state=3 WHERE id='+literal(self.source)+';')
            try:
                assert self.request('GET','/purchase-order/document?id='+self.source,service='purchase')['data']['header']['state']==3
                assert self.request('GET','/purchase-order/status?id='+self.source,service='purchase')['data']['state']==3
                assert self.preview().get('code')!=10000 and self.receive(self.receive_body(1)).get('code')!=10000
                assert self.post([receipt]).get('code')!=10000 and sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(receipt)+';')=='0';self.unchanged()
            finally:sql(self.state,'UPDATE bor SET state=0 WHERE id='+literal(self.source)+';')
            return ['Actual closed-state3 fixture stays numeric in document/status, blocks preview/new generation and existing-draft posting; no stock or payable movement']
        self.case('booking.receive_closed_order_state_not_boolean',closed_source)
        self.source_state_cases()
        self.write_report()

def prepare_browser():
    suite=ReceiveSuite(read_state());suite.setup(multi=True,discount=10)
    fixture=dict(database=suite.state['database'],source=suite.source,number=sql(suite.state,'SELECT number FROM bor WHERE id='+literal(suite.source)+';'),goods=suite.goods,warehouse=suite.warehouse,supplier=suite.supplier,account=suite.account,actor=suite.actor)
    (QA/'runtime/booking-receive-browser.json').write_text(json.dumps(fixture),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8');print('Prepared actual approved two-line receiving order '+fixture['number'])

def verify_browser(stage):
    state=read_state();f=json.loads((QA/'runtime/booking-receive-browser.json').read_text(encoding='utf-8'));assert f['database']==state['database']
    id=sql(state,'SELECT id FROM buy WHERE source='+literal(f['source'])+';');assert id and '\n' not in id
    assert sql(state,'SELECT CONCAT(total,\':\',actual,\':\',money,\':\',`user`) FROM buy WHERE id='+literal(id)+';')=='360.0000:406.8000:0.0000:'+f['actor']
    assert sql(state,'SELECT COUNT(*) FROM buy_info i JOIN bor_info o ON o.id=i.source WHERE i.pid='+literal(id)+' AND o.pid='+literal(f['source'])+' AND i.goods=o.goods AND i.unit=o.unit AND i.warehouse='+literal(f['warehouse'])+' AND i.nums=2 AND i.discount=10 AND i.tax=13;')=='2'
    posted=stage=='posted';assert sql(state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(id)+';')==('1' if posted else '0')
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';'))==(4 if posted else 0)
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==(Decimal('406.8') if posted else 0)
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    assert Decimal(sql(state,'SELECT SUM(handle) FROM bor_info WHERE pid='+literal(f['source'])+';'))==(4 if posted else 0)
    (QA/('reports/booking-receive-browser-'+stage+'.json')).write_text(json.dumps(dict(case='booking.browser_receive_'+stage,status='verified',all_system_features_accepted=False,production_business_writes=0)),encoding='utf-8')
    print('PASS browser generated real two-line source receipt '+sql(state,'SELECT number FROM buy WHERE id='+literal(id)+';')+'; stage='+stage+'; correct360/406.8, stock/payable/order quantities')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','baseline','source-state','preview-race','prepare','verify-generated','verify-posted','verify-reversed'],nargs='?',default='run');args=parser.parse_args()
    if args.action=='prepare':prepare_browser()
    elif args.action.startswith('verify-'):verify_browser(args.action.split('-')[1])
    elif args.action=='preview-race':
        suite=ReceiveSuite(read_state());suite.case('booking.receive_preview_current_after_lock_wait',suite.preview_race);suite.write_report()
    elif args.action=='source-state':
        suite=ReceiveSuite(read_state());suite.source_state_cases();suite.write_report()
    else:ReceiveSuite(read_state()).run(args.action=='baseline')
