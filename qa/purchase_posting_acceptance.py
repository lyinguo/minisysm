"""Procurement check/posting gates using actual dedicated HTTP and independent MySQL."""
import argparse
import uuid
import json
import subprocess
import urllib.request
import urllib.parse
from decimal import Decimal
from purchase_revision_acceptance import PurchaseRevisionSuite
from acceptance import QA, read_state, sql, literal


class PurchasePostingSuite(PurchaseRevisionSuite):
    def fixture(self):
        self.goods, self.warehouse, self.supplier, self.account = [uuid.uuid4().hex for _ in range(4)]
        sql(self.state, 'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES(' +
            ','.join(literal(v) for v in [self.goods,'QA Purchase Posting Goods','qa','QG'+self.goods[:16],'0','unit',100,120,0,0,'{}']) + ');' +
            'INSERT INTO warehouse(id,name,number,frame) VALUES(' + ','.join(literal(v) for v in [self.warehouse,'QA Purchase Posting Warehouse','QW'+self.warehouse[:16],self.state['frame_id']]) + ');' +
            'INSERT INTO supplier(id,name,py,number,frame,`user`,category) VALUES(' + ','.join(literal(v) for v in [self.supplier,'QA Posting Supplier','qa','QS'+self.supplier[:16],self.state['frame_id'],self.actor,'0']) + ');' +
            'INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES(' + ','.join(literal(v) for v in [self.account,'QA Purchase Posting Account','QA'+self.account[:16],self.state['frame_id'],'2026-11-15',100,100]) + ');')

    def create_document(self, paid=0):
        body=self.body()
        body['purchaseNoteBuyDTO'].update(money=paid,account=self.account if paid else None)
        body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
        return self.create(body)

    def check(self, ids, target=1):
        return self.request('POST','/purchase-note/verification',dict(ids=ids,type=target),service='purchase')

    def post(self, ids, target=1):
        return self.request('POST','/purchase-note/audit',dict(ids=ids,type=target),service='purchase')

    def inventory(self):
        return Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(self.warehouse)+';'))

    def balance(self, table, identifier):
        assert table in ('account','supplier')
        return Decimal(sql(self.state,'SELECT COALESCE(balance,0) FROM '+table+' WHERE id='+literal(identifier)+';'))

    def checked(self, identifier):
        return sql(self.state,'SELECT CAST(`check` AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')

    def ledger(self, table, identifier):
        assert table in ('room_info','account_info','summary')
        return int(sql(self.state,"SELECT COUNT(*) FROM "+table+" WHERE type='buy' AND `class`="+literal(identifier)+';'))

    def run_checks(self):
        def ordinary():
            self.fixture();identifier=self.create_document()
            assert self.check([identifier]).get('code')==10000
            assert self.checked(identifier)=='1'
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            assert self.check([identifier],0).get('code')==10000 and self.checked(identifier)=='0'
            return ['Actual check/uncheck changes only state; inventory, cash and supplier balance unchanged']
        self.case('purchase.check_actual_draft',ordinary)

        def batch_atomic():
            self.fixture();identifier=self.create_document()
            result=self.check([identifier,uuid.uuid4().hex])
            assert result.get('code')!=10000,'Missing batch member was accepted'
            assert self.checked(identifier)=='0','Failed batch check partially committed its first document'
            return ['Missing second document rejects whole batch without changing first document']
        self.case('purchase.check_batch_failure_atomic',batch_atomic)

        def invalid_target():
            self.fixture();identifier=self.create_document()
            result=self.check([identifier],7)
            assert result.get('code')!=10000,'Invalid check status was accepted'
            assert self.checked(identifier)=='0','Invalid request changed persisted state'
            return ['Invalid target is rejected without changing check state']
        self.case('purchase.check_invalid_target',invalid_target)

        def foreign():
            self.fixture();identifier=self.create_document()
            other=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,name,pid) VALUES('+literal(other)+",'QA Foreign Check','0');")
            # Change only this newly created QA actor; its existing signed token must not retain admin access.
            sql(self.state,'UPDATE `user` SET role='+literal(self.state['role_id'])+',frame='+literal(other)+' WHERE id='+literal(self.actor)+';')
            try:
                assert self.check([identifier]).get('code')!=10000,'Foreign document check allowed'
                assert self.checked(identifier)=='0','Cross-organization request changed state'
            finally:
                sql(self.state,"UPDATE `user` SET role='0',frame="+literal(self.state['frame_id'])+' WHERE id='+literal(self.actor)+';')
            return ['Actual non-admin identity cannot check another organization; scope reloads from database']
        self.case('purchase.check_cross_organization_denied',foreign)

        def write_failure():
            self.fixture();identifier=self.create_document();trigger='qa_buy_check_'+uuid.uuid4().hex[:12]
            records="SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+';'
            previous=int(sql(self.state,records))
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='buy' AND NEW.source="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA purchase check record failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.check([identifier]).get('code')!=10000,'Actual audit-trail storage failure was swallowed'
                assert self.checked(identifier)=='0','Record storage failure left committed check state'
                assert int(sql(self.state,records))==previous,'Failed action left a persisted record'
            finally:
                sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.check([identifier]).get('code')==10000 and self.checked(identifier)=='1'
            assert int(sql(self.state,records))==previous+1,'Retry did not create exactly one successful action record'
            assert self.check([identifier]).get('code')==10000
            assert int(sql(self.state,records))==previous+1,'Repeated check duplicated action records'
            return ['Actual MySQL action-record failure rolls back state; removing fault permits retry; repeat is idempotent']
        self.case('purchase.check_storage_failure_rollback_retry',write_failure)

        def authorization():
            self.fixture();identifier=self.create_document()
            role=self.success('POST','/role/add-role',dict(name='QA Purchase Check '+uuid.uuid4().hex[:7],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role)
            client=json.loads((QA/'runtime/oauth-client.json').read_text(encoding='utf-8'))
            request=urllib.request.Request('http://127.0.0.1:18002/oauth/token',data=urllib.parse.urlencode(dict(grant_type='password',client_id=client['mgr-id'],client_secret=client['mgr-password'],username=user['user'],password=user['pwd'])).encode())
            with self.opener.open(request,timeout=20) as response: login=json.load(response)
            token=login.get('access_token') or login.get('token');assert token
            container='psi-qa-redis-'+self.state['database'][len('psi_qa_'):]
            actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
            assert actual==container,'Refusing to change unverified Redis'
            def redis(*args):
                return subprocess.run(['docker','exec',container,'redis-cli','--raw']+list(args),capture_output=True,text=True,check=True).stdout.rstrip('\r\n')
            resource='/purchase-note/verification'
            existed,value=redis('HEXISTS','AUTH:RESOURCE_ROLES',resource),redis('HGET','AUTH:RESOURCE_ROLES',resource)
            admin=self.token
            try:
                self.token=token
                redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.check([identifier]).get('code')==403 and self.checked(identifier)=='0'
                redis('HSET','AUTH:RESOURCE_ROLES',resource,json.dumps(['java.util.ArrayList',[keyword]]))
                assert self.check([identifier]).get('code')==10000 and self.checked(identifier)=='1'
                redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.check([identifier],0).get('code')==403 and self.checked(identifier)=='1','Revoked grant remained effective'
                redis('HSET','AUTH:RESOURCE_ROLES',resource,json.dumps(['java.util.ArrayList',[keyword]]))
                other=uuid.uuid4().hex
                sql(self.state,'INSERT INTO frame(id,name,pid) VALUES('+literal(other)+",'QA Foreign Granted Check','0');")
                sql(self.state,'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(user_id)+';')
                assert self.check([identifier],0).get('code')==403 and self.checked(identifier)=='1','Granted role bypassed organization restriction'
            finally:
                self.token=admin
                if existed=='1': redis('HSET','AUTH:RESOURCE_ROLES',resource,value)
                else: redis('HDEL','AUTH:RESOURCE_ROLES',resource)
            return ['Actual new role/user OAuth login: denied before grant, allowed after grant, denied immediately after revoke', 'Same signed token with a granted role still cannot check another organization; only QA Redis changed and restored']
        self.case('purchase.check_real_permission_and_scope',authorization)

    def run_posting(self):
        def stock():
            self.fixture();identifier=self.create_document()
            assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000,'Actual purchase audit rejected'
            assert self.inventory()==2,'Purchase audit did not add two real warehouse units'
            assert self.ledger('room_info',identifier)==1 and self.ledger('summary',identifier)==1,'Missing supporting stock/report movements'
            assert self.balance('supplier',self.supplier)==226,'Unpaid purchase payable missing'
            assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')=='1'
            return ['Actual create/check/audit adds stock and supplier payable, backed by persisted movements']
        self.case('purchase.posting_stock_and_payable',stock)

        def cash():
            self.fixture();identifier=self.create_document(50)
            assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000
            assert self.balance('account',self.account)==50,'Purchase payment did not deduct cash'
            assert self.balance('supplier',self.supplier)==176,'Payable must equal actual 226 less payment 50'
            assert self.ledger('account_info',identifier)==1,'Payment has no supporting cash movement'
            assert Decimal(sql(self.state,'SELECT COALESCE(SUM(money),0) FROM buy_bill WHERE pid='+literal(identifier)+';'))==50
            return ['Partial payment deducts account cash and posts remaining payable with settlement evidence']
        self.case('purchase.posting_cash_and_settlement',cash)

        def unchecked():
            self.fixture();identifier=self.create_document()
            assert self.post([identifier]).get('code')!=10000,'Unchecked purchase was audited successfully'
            assert self.inventory()==0 and self.balance('supplier',self.supplier)==0
            return ['Unchecked purchase audit denied without stock or payable effects']
        self.case('purchase.posting_unchecked_denied',unchecked)

        def reverse():
            self.fixture();identifier=self.create_document(50)
            assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==50,'Forward posting must exist before reversal can count'
            assert self.post([identifier],0).get('code')==10000
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            for table in ['room_info','account_info','summary']: assert self.ledger(table,identifier)==0
            return ['Verified forward stock/cash/payable posting is exactly reversed with no active ledger left']
        self.case('purchase.posting_reverse_actual_movements',reverse)

    def run(self, action):
        if action in ('all','check'): self.run_checks()
        if action in ('all','posting'): self.run_posting()
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['all','check','posting','verify-checked','verify-unchecked'],nargs='?',default='all')
    action=parser.parse_args().action
    if action.startswith('verify-'):
        from purchase_ui_acceptance import verify
        state=read_state();fixture=json.loads((QA/'runtime/purchase-browser-document.json').read_text(encoding='utf-8'))
        assert fixture['database']==state['database']
        expected='1' if action=='verify-checked' else '0'
        assert sql(state,'SELECT CAST(`check` AS SIGNED) FROM buy WHERE id='+literal(fixture['id'])+';')==expected
        verify(3)
        print('PASS browser procurement check='+expected+'; persisted draft, stock, cash and payable unchanged')
    else:
        PurchasePostingSuite(read_state()).run(action)
