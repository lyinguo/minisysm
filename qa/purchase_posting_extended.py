"""Extended real procurement posting gates; no business inventory is inserted by fixtures."""
import concurrent.futures
import threading
import uuid
import json
import subprocess
import urllib.request
import urllib.parse
from decimal import Decimal
from purchase_posting_acceptance import PurchasePostingSuite
from sale_draft_acceptance import SaleDraftSuite
from acceptance import QA, read_state, sql, literal


class PurchasePostingExtended(PurchasePostingSuite):
    def ready(self,paid=0):
        identifier=self.create_document(paid)
        assert self.check([identifier]).get('code')==10000
        return identifier

    def status(self,identifier):
        return sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')

    def empty(self,ids):
        assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
        for identifier in ids:
            assert self.status(identifier)=='0'
            for table in ['room_info','summary','account_info']: assert self.ledger(table,identifier)==0
            assert sql(self.state,'SELECT COUNT(*) FROM psi_purchase_posting WHERE purchase_id='+literal(identifier)+';')=='0'

    def run(self):
        def repeats():
            self.fixture();identifier=self.ready(50)
            barrier=threading.Barrier(2)
            def worker():
                barrier.wait();return self.post([identifier])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:worker(),range(2)))
            assert all(row.get('code')==10000 for row in results),'Repeated audit should be idempotent'
            assert self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            for table in ['room_info','summary','account_info']: assert self.ledger(table,identifier)==1
            assert self.post([identifier],0).get('code')==10000
            assert self.post([identifier],0).get('code')==10000
            self.empty([identifier])
            return ['Concurrent same-document audit creates one receipt/payment/payable; repeated reversal has no extra effects']
        self.case('purchase.posting_concurrent_idempotence',repeats)

        def funds():
            self.fixture();identifier=self.ready(150)
            assert self.post([identifier]).get('code')!=10000,'Payment exceeded actual account balance'
            self.empty([identifier])
            return ['Insufficient funds roll back earlier inventory/report work and all financial/state effects']
        self.case('purchase.posting_insufficient_cash_atomic',funds)

        def batch():
            self.fixture();ids=[self.ready(60),self.ready(60)]
            assert self.post(ids).get('code')!=10000,'Batch spent 120 from an account containing 100'
            self.empty(ids)
            return ['Second-document insufficient funds roll back the entire batch, including first receipt and payment']
        self.case('purchase.posting_batch_failure_atomic',batch)

        def concurrent_cash():
            self.fixture();ids=[self.ready(60),self.ready(60)];barrier=threading.Barrier(2)
            def worker(identifier):
                barrier.wait();return self.post([identifier])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(worker,ids))
            assert sum(row.get('code')==10000 for row in results)==1,'Concurrent purchases overspent one account'
            assert self.inventory()==2 and self.balance('account',self.account)==40 and self.balance('supplier',self.supplier)==166
            assert sum(self.ledger('room_info',identifier) for identifier in ids)==1
            assert sum(self.ledger('account_info',identifier) for identifier in ids)==1
            return ['Two real concurrent purchases compete for cash: one commits, one fails without partial inventory']
        self.case('purchase.posting_concurrent_cash_limit',concurrent_cash)

        def storage():
            self.fixture();identifier=self.ready(50);trigger='qa_purchase_post_'+uuid.uuid4().hex[:12]
            try:
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON account_info FOR EACH ROW BEGIN IF NEW.type='buy' AND NEW.`class`="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA purchase cash movement failure'; END IF; END;$$\nDELIMITER ;\n")
                assert self.post([identifier]).get('code')!=10000
                self.empty([identifier])
            finally:
                sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post([identifier]).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            return ['Actual MySQL cash-ledger fault rolls back stock/report/account/state; removing fault permits real retry']
        self.case('purchase.posting_storage_failure_retry',storage)

        def consumed():
            self.fixture();identifier=self.ready(50)
            assert self.post([identifier]).get('code')==10000
            sale=SaleDraftSuite(self.state);sale.goods=self.goods;sale.warehouse=self.warehouse
            body=sale.body();body['items'][0]['discount']=1
            sold=sale.create(body)
            sale.sale('POST','/sale/form/check?check=true',[sold])
            sale.sale('POST','/sale/form/examine?examine=true',[sold])
            assert self.inventory()==0,'Real sale did not consume the purchase receipt'
            assert self.post([identifier],0).get('code')!=10000,'Consumed receipt was reversed into negative stock'
            assert self.status(identifier)=='1' and self.inventory()==0 and self.balance('account',self.account)==50
            assert self.balance('supplier',self.supplier)==176 and self.ledger('room_info',identifier)==1
            return ['Actual purchase -> actual sale consumes receipt; reverse purchase rejects atomically instead of creating negative stock']
        self.case('purchase.posting_consumed_receipt_reverse_denied',consumed)

        def serial_batch():
            self.fixture()
            sql(self.state,'UPDATE goods SET batch=1,serial=1 WHERE id='+literal(self.goods)+';')
            body=self.body();body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='QA-PURCHASE-LOT',mfd='2026-11-01',serial=json.dumps(['QA-P1-'+self.goods,'QA-P2-'+self.goods]))
            identifier=self.create(body);assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000
            assert self.inventory()==2
            assert Decimal(sql(self.state,'SELECT nums FROM batch WHERE goods='+literal(self.goods)+';'))==2
            assert sql(self.state,'SELECT COUNT(*) FROM serial WHERE goods='+literal(self.goods)+' AND state=0;')=='2'
            assert self.post([identifier],0).get('code')==10000
            assert self.inventory()==0
            assert Decimal(sql(self.state,'SELECT nums FROM batch WHERE goods='+literal(self.goods)+';'))==0
            assert sql(self.state,'SELECT COUNT(*) FROM serial WHERE goods='+literal(self.goods)+';')=='0'
            return ['Actual purchase creates batch and two serials; reversal restores batch/room counts and removes original unused serials']
        self.case('purchase.posting_batch_serial_roundtrip',serial_batch)

        def units():
            self.fixture();units=json.dumps([dict(source='unit',name='box',nums=10)])
            sql(self.state,"UPDATE goods SET unit='-1',units="+literal(units)+' WHERE id='+literal(self.goods)+';')
            body=self.body();body['purchaseNoteInfoDTOS'][0].update(unit='box',discount=0,tax=13,batch='',mfd=None,serial='[]')
            identifier=self.create(body);assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000
            assert self.inventory()==20
            assert Decimal(sql(self.state,"SELECT price FROM room_info WHERE type='buy' AND `class`="+literal(identifier)+';'))==10
            sql(self.state,'UPDATE goods SET units='+literal(json.dumps([dict(source='unit',name='box',nums=100)]))+' WHERE id='+literal(self.goods)+';')
            assert self.post([identifier],0).get('code')==10000 and self.inventory()==0
            return ['Two boxes receive twenty base units at net cost ten; reversal uses original twenty after conversion changes to one hundred']
        self.case('purchase.posting_original_unit_quantity_on_reverse',units)

        def required_target():
            self.fixture();identifier=self.ready()
            for path in ['verification','audit']:
                result=self.request('POST','/purchase-note/'+path,dict(ids=[identifier]),service='purchase')
                assert result.get('code')!=10000,'Omitted target was interpreted as a reverse request'
            assert self.checked(identifier)=='1';self.empty([identifier])
            return ['Omitting check/audit target rejects the request instead of defaulting to reverse operation']
        self.case('purchase.posting_explicit_target_required',required_target)

        def invoice_reference():
            self.fixture();identifier=self.ready(50)
            assert self.post([identifier]).get('code')==10000
            # Query/reference fixture only; this does not prove invoice issuance.
            sql(self.state,"INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES("+','.join(literal(v) for v in [uuid.uuid4().hex,'buy',identifier,'2026-11-15','QA-INV-'+identifier[:16],'QA reference fixture',226])+');')
            assert self.post([identifier],0).get('code')!=10000,'Referenced purchase was reversed'
            assert self.status(identifier)=='1' and self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            return ['Existing invoice reference rejects reversal atomically; fixture does not imply invoice workflow acceptance']
        self.case('purchase.posting_invoice_reference_reverse_denied',invoice_reference)

        def permissions():
            self.fixture();identifier=self.ready(50)
            role=self.success('POST','/role/add-role',dict(name='QA Purchase Audit '+uuid.uuid4().hex[:7],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role)
            client=json.loads((QA/'runtime/oauth-client.json').read_text(encoding='utf-8'))
            request=urllib.request.Request('http://127.0.0.1:18002/oauth/token',data=urllib.parse.urlencode(dict(grant_type='password',client_id=client['mgr-id'],client_secret=client['mgr-password'],username=user['user'],password=user['pwd'])).encode())
            with self.opener.open(request,timeout=20) as response: login=json.load(response)
            token=login.get('access_token') or login.get('token');assert token
            container='psi-qa-redis-'+self.state['database'][len('psi_qa_'):]
            actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
            assert actual==container,'Refusing to alter unverified Redis'
            def redis(*args):
                return subprocess.run(['docker','exec',container,'redis-cli','--raw']+list(args),capture_output=True,text=True,check=True).stdout.rstrip('\r\n')
            resource='/purchase-note/audit'
            existed,value=redis('HEXISTS','AUTH:RESOURCE_ROLES',resource),redis('HGET','AUTH:RESOURCE_ROLES',resource)
            admin=self.token
            try:
                self.token=token;redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.post([identifier]).get('code')==403;self.empty([identifier])
                grant=json.dumps(['java.util.ArrayList',[keyword]])
                redis('HSET','AUTH:RESOURCE_ROLES',resource,grant)
                assert self.post([identifier]).get('code')==10000 and self.inventory()==2
                assert int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+' AND `user`='+literal(user_id)+';'))>0
                redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.post([identifier],0).get('code')==403 and self.inventory()==2
                redis('HSET','AUTH:RESOURCE_ROLES',resource,grant)
                assert self.post([identifier],0).get('code')==10000;self.empty([identifier])
                other=uuid.uuid4().hex
                sql(self.state,'INSERT INTO frame(id,name,pid) VALUES('+literal(other)+",'QA Foreign Audit','0');")
                sql(self.state,'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(user_id)+';')
                assert self.post([identifier]).get('code')==403;self.empty([identifier])
            finally:
                self.token=admin
                if existed=='1': redis('HSET','AUTH:RESOURCE_ROLES',resource,value)
                else: redis('HDEL','AUTH:RESOURCE_ROLES',resource)
            return ['Actual new role/user OAuth login: no grant denied, grant permits posting, revoked grant denies reversal, restored grant permits reversal', 'Same token with granted role still denies another organization; new actor recorded, QA Redis restored']
        self.case('purchase.posting_actual_role_and_scope',permissions)
        self.write_report()


if __name__=='__main__': PurchasePostingExtended(read_state()).run()
