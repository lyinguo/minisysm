"""Actual payment draft API and MySQL gates; no business writes on main services."""
import uuid
import json
import concurrent.futures
import urllib.request
import urllib.parse
from decimal import Decimal
from purchase_posting_acceptance import PurchasePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal


class PaymentDraftSuite(PurchasePostingSuite):
    def body(self):
        return dict(supplier=self.supplier,time='2026-11-15',number='QAPAY'+uuid.uuid4().hex[:24],total=999,people='',file='[]',data='QA Payment Draft',infoList=[dict(account=self.account,money=25,settle='',data1='QA first')])

    def payment(self,body):return self.request('POST','/payment-order/add',body,service='payment')

    def create_payment(self,body):
        result=self.payment(body)
        assert result.get('code')==10000 and result.get('data'),'Valid actual payment draft rejected; code='+str(result.get('code'))
        return result['data']

    def count_payment(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM omy WHERE number='+literal(number)+';'))

    def unchanged(self):
        assert self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
        assert sql(self.state,'SELECT COUNT(*) FROM account_info WHERE pid='+literal(self.account)+';')=='0'

    def run(self):
        def actual():
            self.fixture();body=self.body();body['infoList'].append(dict(account=self.account,money=15,settle='QA-SETTLE',data1='QA second'))
            identifier=self.create_payment(body)
            head=json.loads(sql(self.state,"SELECT JSON_OBJECT('frame',frame,'user',`user`,'total',total,'audit',examine,'nucleus',nucleus,'file',file) FROM omy WHERE id="+literal(identifier)+';'))
            assert head['frame']==self.state['frame_id'] and head['user']==self.actor,'Fabricated organization or creator'
            assert Decimal(str(head['total']))==40 and head['audit']==0 and head['nucleus']==0 and head['file']=='[]'
            assert sql(self.state,'SELECT COUNT(*) FROM omy_info WHERE pid='+literal(identifier)+';')=='2'
            assert sql(self.state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(identifier)+';')=='0','Draft fabricated a settlement relationship'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(identifier)+' AND `user`='+literal(self.actor)+';')=='1'
            self.unchanged()
            return ['Real two-line draft uses signed current actor/organization, authoritative total, actual metadata/history; no settlement/stock/funds side effects']
        self.case('payment.draft_real_actor_amounts_and_no_posting',actual)

        def invalid_money():
            self.fixture()
            for value in [-1,0,None,'0.00001','100000000']:
                body=self.body();body['infoList'].append(dict(account=self.account,money=value,settle='',data1='QA invalid'))
                assert self.payment(body).get('code')!=10000,'Invalid individual payment line accepted'
                assert self.count_payment(body['number'])==0
            self.unchanged()
            return ['Negative/zero/missing/overprecision/oversized second-line amounts reject the whole draft']
        self.case('payment.draft_invalid_money_atomic',invalid_money)

        def references():
            self.fixture()
            for field in ['supplier','people','account']:
                body=self.body()
                if field=='account':body['infoList'][0][field]=uuid.uuid4().hex
                else:body[field]=uuid.uuid4().hex
                assert self.payment(body).get('code')!=10000 and self.count_payment(body['number'])==0
            self.unchanged()
            return ['Unknown supplier/person/account rejected without persisted header or movements']
        self.case('payment.draft_unknown_references',references)

        def duplicate():
            self.fixture();body=self.body();identifier=self.create_payment(body)
            assert self.payment(body).get('code')!=10000 and self.count_payment(body['number'])==1
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                another=self.body();results=list(pool.map(lambda _:self.payment(another),range(2)))
            assert sum(result.get('code')==10000 for result in results)==1 and self.count_payment(another['number'])==1
            self.unchanged()
            return ['Actual repeated and simultaneous same-number creates persist only one draft each']
        self.case('payment.draft_number_duplicate_and_concurrency',duplicate)

        def storage():
            self.fixture();body=self.body();marker='QAFAIL'+uuid.uuid4().hex[:12]
            body['infoList'].append(dict(account=self.account,money=1,settle='',data1=marker))
            trigger='qa_pay_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON omy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA payment storage failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.payment(body).get('code')!=10000 and self.count_payment(body['number'])==0
                assert sql(self.state,'SELECT COUNT(*) FROM omy_info WHERE data='+literal(marker)+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.create_payment(body)
            self.unchanged()
            return ['Actual second-detail insert failure rolls back header/first line; same request succeeds after removing fault']
        self.case('payment.draft_storage_failure_atomic_retry',storage)

        def scope():
            self.fixture();role=self.success('POST','/role/add-role',dict(name='QA Payment '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,user);admin=self.token
            body=self.body();self.token=token
            try:
                assert self.payment(body).get('code')==403,'Payment create did not enforce explicit function grant'
                with qa_resource_grants(self.state,['/payment-order/add'],[keyword]):
                    foreign=uuid.uuid4().hex;foreign_account=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA Payment Other Org');"+
                        'INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES('+','.join(literal(v) for v in [foreign_account,'QA Payment Other Account','QA'+foreign_account[:16],foreign,'2026-11-15',100,100])+');')
                    bad=self.body();bad['infoList'][0]['account']=foreign_account
                    assert self.payment(bad).get('code')!=10000 and self.count_payment(bad['number'])==0
                    identifier=self.create_payment(body)
                    assert sql(self.state,'SELECT `user` FROM omy WHERE id='+literal(identifier)+';')==user_id
                assert self.payment(self.body()).get('code')==403,'Grant revocation ignored with same token'
            finally:self.token=admin
            self.unchanged()
            return ['Actual OAuth role grant/revocation enforced, foreign account refused, creator is actual non-admin actor']
        self.case('payment.draft_actual_grants_and_scope',scope)

        def forged_identity():
            self.fixture();body=self.body()
            request=urllib.request.Request('http://127.0.0.1:18024/payment-order/add',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','user':urllib.parse.quote(json.dumps(dict(id=self.actor,frameId=self.state['frame_id'],authorities=['ROLE_ADMIN'])))})
            with self.opener.open(request,timeout=20) as response:result=json.load(response)
            assert result.get('code')==401 and self.count_payment(body['number'])==0,'Unsigned identity was trusted'
            self.unchanged()
            return ['Forged user header without a signed OAuth bearer is rejected before creating a draft']
        self.case('payment.draft_unsigned_identity_denied',forged_identity)

        def precision_metadata():
            self.fixture();body=self.body();body['infoList'][0].update(money='0.0001',data1='QA 备注',settle=None)
            body['file']=json.dumps([dict(name='qa-proof.txt',url='/qa-proof.txt')]);body['number']='  '+body['number']+'  '
            body.update(examine=1,nucleus=2,frame='forged-frame',user='forged-user')
            identifier=self.create_payment(body)
            head=json.loads(sql(self.state,"SELECT JSON_OBJECT('total',total,'user',`user`,'frame',frame,'audit',examine,'nucleus',nucleus,'number',number) FROM omy WHERE id="+literal(identifier)+';'))
            assert Decimal(str(head['total']))==Decimal('0.0001') and head['number']==body['number'].strip()
            assert head['user']==self.actor and head['frame']==self.state['frame_id'] and head['audit']==0 and head['nucleus']==0
            assert json.loads(sql(self.state,'SELECT file FROM omy WHERE id='+literal(identifier)+';'))==json.loads(body['file'])
            assert sql(self.state,'SELECT data FROM omy_info WHERE pid='+literal(identifier)+';')=='QA 备注'
            assert sql(self.state,'SELECT LENGTH(settle) FROM omy_info WHERE pid='+literal(identifier)+';')=='0'
            self.unchanged()
            return ['Four-decimal payment and attachment metadata persist; omitted settlement number remains empty; forged ownership/state ignored and real creator retained']
        self.case('payment.draft_precision_metadata_and_state',precision_metadata)
        self.write_report()


if __name__=='__main__':PaymentDraftSuite(read_state()).run()
