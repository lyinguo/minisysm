"""Actual isolated receipt drafts, signed ownership and authoritative amount gates."""
import uuid,json,urllib.request,urllib.parse,concurrent.futures
from decimal import Decimal
from sale_posting_acceptance import SalePostingSuite
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants
from acceptance import read_state,sql,literal

class ReceiptDraftSuite(SalePostingSuite):
    def receipt_body(self):return dict(customer=self.customer,time='2026-11-16 14:00:00',number='QARCPT'+uuid.uuid4().hex[:24],total=999,people='',file=[],data='QA receipt draft',info=[dict(account=self.account,amount=25,settle='',data='QA receipt first')])
    def receipt(self,body):return self.request('POST','/fund/receipt',body,service='fund')
    def create_receipt(self,body):
        result=self.receipt(body);assert result.get('code')==10000,str(result)
        assert isinstance(result.get('data'),str) and result['data'] and result['data']==sql(self.state,'SELECT id FROM imy WHERE number='+literal(body['number'].strip())+';'),'Creation must return actual receipt ID'
        return result['data']
    def count_receipt(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM imy WHERE number='+literal(number)+';'))
    def unchanged_receipt(self):
        assert self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0 and self.inventory()==0
        assert sql(self.state,'SELECT COUNT(*) FROM account_info WHERE pid='+literal(self.account)+';')=='0'
    def run(self):
        def actual():
            self.fixture(stock=0);body=self.receipt_body();body.update(user='forged-user',frame='forged-frame',examine=1,nucleus=2)
            body['info'].append(dict(account=self.account,amount=15,settle='QA BANK',data='QA receipt second'))
            identifier=self.create_receipt(body)
            head=json.loads(sql(self.state,"SELECT JSON_OBJECT('frame',frame,'user',`user`,'total',total,'examine',CAST(examine AS SIGNED),'nucleus',CAST(nucleus AS SIGNED),'file',file) FROM imy WHERE id="+literal(identifier)+';'))
            assert head==dict(frame=self.state['frame_id'],user=self.actor,total=40,examine=0,nucleus=0,file='[]'),str(head)
            assert sql(self.state,'SELECT COUNT(*) FROM imy_info WHERE pid='+literal(identifier)+';')=='2'
            assert sql(self.state,'SELECT COUNT(*) FROM imy_bill WHERE pid='+literal(identifier)+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+' AND `user`='+literal(self.actor)+';')=='1'
            self.unchanged_receipt()
            return ['Actual two-account draft returns persisted ID, computes40 rather than client999, ignores forged creator/org/states, records signed operator; no cash/AR/inventory or source settlement changes']
        self.case('receipt.draft_authoritative_amount_actor_and_no_posting',actual)
        def money():
            self.fixture(stock=0)
            for amount in [-1,0,None,'0.00001','100000000']:
                body=self.receipt_body();body['info'].append(dict(account=self.account,amount=amount,settle='',data='QA invalid second'))
                assert self.receipt(body).get('code')!=10000 and self.count_receipt(body['number'])==0
            self.unchanged_receipt();return ['Invalid second-line amounts reject entire real draft before header/first row/history persistence']
        self.case('receipt.draft_invalid_money_atomic',money)
        def references():
            self.fixture(stock=0)
            for field in ['customer','people','account']:
                body=self.receipt_body()
                if field=='account':body['info'][0][field]=uuid.uuid4().hex
                else:body[field]=uuid.uuid4().hex
                assert self.receipt(body).get('code')!=10000 and self.count_receipt(body['number'])==0
            frame,account=[uuid.uuid4().hex for _ in range(2)]
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Receipt Foreign');INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES("+','.join(literal(v) for v in [account,'QA Receipt Foreign Account','QA'+account[:18],frame,'2026-11-15',0,0])+');')
            body=self.receipt_body();body['info'][0]['account']=account;assert self.receipt(body).get('code')!=10000 and self.count_receipt(body['number'])==0
            self.unchanged_receipt();return ['Actual missing customer/person/account and foreign-account references reject without draft or money effects']
        self.case('receipt.draft_references_and_account_organization',references)
        def duplicate():
            self.fixture(stock=0);body=self.receipt_body();self.create_receipt(body)
            assert self.receipt(body).get('code')!=10000 and self.count_receipt(body['number'])==1
            another=self.receipt_body()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.receipt(another),range(2)))
            assert sum(row.get('code')==10000 for row in results)==1 and self.count_receipt(another['number'])==1
            self.unchanged_receipt();return ['Repeated and concurrent same-number actual creates commit one draft, no duplicate receipt or funds']
        self.case('receipt.draft_duplicate_and_concurrent_number',duplicate)
        def storage():
            self.fixture(stock=0);body=self.receipt_body();marker='QARCPTFAIL'+uuid.uuid4().hex[:12];body['info'].append(dict(account=self.account,amount=1,settle='',data=marker));trigger='qa_rct_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON imy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA receipt draft storage fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.receipt(body).get('code')!=10000 and self.count_receipt(body['number'])==0
                assert sql(self.state,'SELECT COUNT(*) FROM imy_info WHERE data='+literal(marker)+';')=='0';self.unchanged_receipt()
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            self.create_receipt(body);self.unchanged_receipt();return ['Actual late detail insertion failure rolls back header/first row/history; exact original request succeeds after removing only test fault']
        self.case('receipt.draft_storage_rollback_and_retry',storage)
        def grants():
            self.fixture(stock=0);helper=PaymentDocumentScopeSuite(self.state);user,token,role=helper.role_user();admin=self.token;self.token=token
            try:
                assert self.receipt(self.receipt_body()).get('code')==403
                with qa_resource_grants(self.state,['/fund/receipt/add'],[role]):
                    identifier=self.create_receipt(self.receipt_body());assert sql(self.state,'SELECT `user` FROM imy WHERE id='+literal(identifier)+';')==user
                assert self.receipt(self.receipt_body()).get('code')==403
            finally:self.token=admin
            self.unchanged_receipt();return ['Actual ordinary OAuth creation requires separate live grant, records real operator, same token loses access immediately on revoke']
        self.case('receipt.draft_actual_live_creation_grant',grants)
        def forged():
            self.fixture(stock=0);body=self.receipt_body()
            request=urllib.request.Request('http://127.0.0.1:18026/fund/receipt',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','user':urllib.parse.quote(json.dumps(dict(id=self.actor,frameId=self.state['frame_id'],authorities=['ROLE_ADMIN'])))})
            with self.opener.open(request,timeout=20) as response:result=json.load(response)
            assert result.get('code')==401 and self.count_receipt(body['number'])==0
            self.unchanged_receipt();return ['Unsigned fabricated user header cannot create receipt without real signed OAuth bearer']
        self.case('receipt.draft_unsigned_header_denied',forged)
        def optional():
            self.fixture(stock=0);body=self.receipt_body();body.pop('people');body.pop('data');body['info'][0].pop('settle');body['info'][0].pop('data');body['info'][0]['amount']='0.0001'
            body['more']=json.dumps(dict(qaReference='QA customer request'));identifier=self.create_receipt(body)
            assert Decimal(sql(self.state,'SELECT total FROM imy WHERE id='+literal(identifier)+';'))==Decimal('0.0001')
            assert json.loads(sql(self.state,'SELECT more FROM imy WHERE id='+literal(identifier)+';'))==dict(qaReference='QA customer request'),'Receipt extension metadata was dropped'
            self.unchanged_receipt();return ['Actual omitted optional fields persist, four-decimal amount preserved and valid extension metadata retained']
        self.case('receipt.draft_optional_fields_precision_metadata',optional)
        self.write_report()

if __name__=='__main__':ReceiptDraftSuite(read_state()).run()
