"""Actual procurement deletion gates; only owned disposable QA documents are removed."""
import concurrent.futures
import threading
import uuid
import json
import subprocess
import urllib.parse
import urllib.request
import argparse
from purchase_posting_extended import PurchasePostingExtended
from acceptance import QA,read_state,sql,literal


class PurchaseDeleteSuite(PurchasePostingExtended):
    def delete(self,ids):
        return self.request('POST','/purchase-note/delete',ids,service='purchase')

    def exists(self,identifier):
        return int(sql(self.state,'SELECT COUNT(*) FROM buy WHERE id='+literal(identifier)+';'))

    def details(self,identifier):
        return int(sql(self.state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(identifier)+';'))

    def legacy_free(self,identifier):
        # Only this owned draft is normalized to legacy zero flags so a wrong early
        # rejection of cse=3 cannot mask the reference/scope/storage checks below.
        sql(self.state,'UPDATE buy SET cse=0,invoice=0 WHERE id='+literal(identifier)+';')

    def run(self):
        def ordinary():
            self.fixture();identifier=self.create_document()
            assert self.delete([identifier]).get('code')==10000,'Unreferenced zero-fee draft cannot be deleted'
            assert self.exists(identifier)==0 and self.details(identifier)==0
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            return ['Actual disposable free draft deletion removes header/details, never stock, cash or payable']
        self.case('purchase.delete_actual_free_draft',ordinary)

        def states():
            self.fixture();identifier=self.ready(50)
            assert self.delete([identifier]).get('code')!=10000 and self.exists(identifier)==1 and self.details(identifier)==1
            assert self.post([identifier]).get('code')==10000
            assert self.delete([identifier]).get('code')!=10000 and self.exists(identifier)==1 and self.inventory()==2
            assert self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            return ['Actual checked and actually posted purchases reject deletion with persisted details/stock/cash/payable retained']
        self.case('purchase.delete_checked_and_posted_denied',states)

        def reference():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier)
            free=self.create_document()
            sql(self.state,'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [uuid.uuid4().hex,'buy',identifier,'2026-11-15','QA-DEL-'+identifier[:16],'QA deletion reference fixture',1])+');')
            assert self.delete([identifier]).get('code')!=10000,'Actual invoice reference ignored because flags remained zero'
            assert self.exists(identifier)==1 and self.details(identifier)==1
            assert self.delete([free,identifier]).get('code')!=10000
            assert self.exists(free)==1 and self.details(free)==1,'Referenced second member did not protect whole batch'
            return ['SQL invoice-reference fixture protects a legacy zero-flag draft; this is not invoice lifecycle acceptance']
        self.case('purchase.delete_actual_reference_denied',reference)

        def scope():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier);other=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,name,pid) VALUES('+literal(other)+",'QA Foreign Delete','0');"+
                'UPDATE `user` SET role='+literal(self.state['role_id'])+',frame='+literal(other)+' WHERE id='+literal(self.actor)+';')
            try:
                assert self.delete([identifier]).get('code')!=10000,'Cross-organization user deleted a purchase'
                assert self.exists(identifier)==1 and self.details(identifier)==1
            finally:
                sql(self.state,"UPDATE `user` SET role='0',frame="+literal(self.state['frame_id'])+' WHERE id='+literal(self.actor)+';')
            return ['Only a newly created QA actor changes organization; foreign deletion is denied with existing token']
        self.case('purchase.delete_foreign_scope_denied',scope)

        def missing_batch():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier)
            assert self.delete([identifier,'zz'+uuid.uuid4().hex[:30]]).get('code')!=10000
            assert self.exists(identifier)==1 and self.details(identifier)==1
            return ['Missing second batch member leaves first owned document and all details intact']
        self.case('purchase.delete_batch_missing_atomic',missing_batch)

        def storage():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier);trigger='qa_buy_del_'+uuid.uuid4().hex[:12]
            before=int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+';'))
            try:
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE DELETE ON buy FOR EACH ROW BEGIN IF OLD.id='+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA purchase header delete failure'; END IF; END;$$\nDELIMITER ;\n")
                assert self.delete([identifier]).get('code')!=10000
                assert self.exists(identifier)==1 and self.details(identifier)==1
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.delete([identifier]).get('code')==10000
            assert self.exists(identifier)==0 and self.details(identifier)==0
            assert int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+';'))==before+1,'Deleting a draft removed its action history or failed to add deletion evidence'
            return ['Actual header-delete storage fault rolls back prior detail deletion; retry succeeds and retains action history plus deletion record']
        self.case('purchase.delete_storage_failure_and_audit_history',storage)

        def same_id():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier);barrier=threading.Barrier(2)
            def worker():barrier.wait();return self.delete([identifier])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:worker(),range(2)))
            assert sum(row.get('code')==10000 for row in results)==1
            assert self.exists(identifier)==0 and self.details(identifier)==0
            return ['Concurrent same-ID deletes commit once, with no partial header/detail state']
        self.case('purchase.delete_concurrent_once',same_id)

        def posting_race():
            self.fixture();identifier=self.create_document();self.legacy_free(identifier);barrier=threading.Barrier(2)
            def delete_worker():barrier.wait();return self.delete([identifier])
            def post_worker():
                barrier.wait()
                checked=self.check([identifier])
                return self.post([identifier]) if checked.get('code')==10000 else checked
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                deletion,posting=pool.submit(delete_worker),pool.submit(post_worker)
                deleted,posted=deletion.result(),posting.result()
            if deleted.get('code')==10000:
                assert posted.get('code')!=10000 and self.exists(identifier)==0 and self.details(identifier)==0 and self.inventory()==0
                assert self.balance('supplier',self.supplier)==0
            else:
                assert posted.get('code')==10000 and self.exists(identifier)==1 and self.details(identifier)==1 and self.inventory()==2
                assert self.balance('supplier',self.supplier)==226
            return ['Real delete versus check/audit race ends either deleted without posting or posted with intact header/details; no orphan stock']
        self.case('purchase.delete_races_actual_posting',posting_race)

        def period():
            self.fixture();identifier=self.create_document();period=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-15','2026-11-15',self.actor])+');')
                assert self.delete([identifier]).get('code')!=10000 and self.exists(identifier)==1 and self.details(identifier)==1
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            return ['Owned closed-period fixture rejects draft deletion and retains every detail; period fixture removed']
        self.case('purchase.delete_closed_period_denied',period)

        def journal_guard():
            self.fixture();identifier=self.ready(50)
            assert self.post([identifier]).get('code')==10000
            # This owned corrupt-flag fixture proves that the marker/actual movements,
            # rather than just UI flags, protect posted business evidence.
            sql(self.state,'UPDATE buy SET examine=0,`check`=0,nucleus=0 WHERE id='+literal(identifier)+';')
            assert self.delete([identifier]).get('code')!=10000
            assert self.exists(identifier)==1 and self.details(identifier)==1 and self.inventory()==2
            assert self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            return ['Actual posted stock/cash journals prevent deletion even when only owned QA status flags are corrupted to zero']
        self.case('purchase.delete_actual_posting_marker_guard',journal_guard)

        def permissions():
            self.fixture();first,second=self.create_document(),self.create_document()
            role=self.success('POST','/role/add-role',dict(name='QA Purchase Delete '+uuid.uuid4().hex[:7],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role)
            client=json.loads((QA/'runtime/oauth-client.json').read_text(encoding='utf-8'))
            request=urllib.request.Request('http://127.0.0.1:18002/oauth/token',data=urllib.parse.urlencode(dict(grant_type='password',client_id=client['mgr-id'],client_secret=client['mgr-password'],username=user['user'],password=user['pwd'])).encode())
            with self.opener.open(request,timeout=20) as response:login=json.load(response)
            token=login.get('access_token') or login.get('token');assert token
            container='psi-qa-redis-'+self.state['database'][len('psi_qa_'):]
            actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
            assert actual==container,'Refusing to alter unverified Redis'
            def redis(*args):return subprocess.run(['docker','exec',container,'redis-cli','--raw']+list(args),capture_output=True,text=True,check=True).stdout.rstrip('\r\n')
            resource='/purchase-note/delete';existed,value=redis('HEXISTS','AUTH:RESOURCE_ROLES',resource),redis('HGET','AUTH:RESOURCE_ROLES',resource)
            admin=self.token
            try:
                self.token=token;redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.delete([first]).get('code')==403 and self.exists(first)==1
                grant=json.dumps(['java.util.ArrayList',[keyword]]);redis('HSET','AUTH:RESOURCE_ROLES',resource,grant)
                assert self.delete([first]).get('code')==10000 and self.exists(first)==0 and self.details(first)==0
                assert int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(first)+' AND `user`='+literal(user_id)+';'))==1
                redis('HDEL','AUTH:RESOURCE_ROLES',resource)
                assert self.delete([second]).get('code')==403 and self.exists(second)==1
                redis('HSET','AUTH:RESOURCE_ROLES',resource,grant)
                other=uuid.uuid4().hex
                sql(self.state,'INSERT INTO frame(id,name,pid) VALUES('+literal(other)+",'QA Foreign Granted Delete','0');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(user_id)+';')
                assert self.delete([second]).get('code')==403 and self.exists(second)==1
            finally:
                self.token=admin
                if existed=='1':redis('HSET','AUTH:RESOURCE_ROLES',resource,value)
                else:redis('HDEL','AUTH:RESOURCE_ROLES',resource)
            return ['Actual new role/user OAuth login: ungranted denied, granted delete persists with real actor, revoked and foreign-organization operations denied', 'Only verified QA Redis touched, original resource grant restored']
        self.case('purchase.delete_actual_role_and_scope',permissions)
        self.write_report()


def prepare_browser():
    suite=PurchaseDeleteSuite(read_state());suite.fixture();prefix='QADEL'+uuid.uuid4().hex[:12]
    identifiers=[];before={}
    for suffix in ['A','B','C','D']:
        body=suite.body();body['purchaseNoteBuyDTO']['number']=prefix+'-'+suffix
        body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
        identifier=suite.create(body);identifiers.append(identifier)
        before[identifier]=int(sql(suite.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+';'))
    assert suite.check([identifiers[1]]).get('code')==10000
    fixture={key:getattr(suite,key) for key in ['goods','warehouse','supplier','account','actor']}
    fixture.update(database=suite.state['database'],prefix=prefix,free=identifiers[0],checked=identifiers[1],batch=identifiers[2:],before=before)
    (QA/'runtime/purchase-delete-browser.json').write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated browser deletion prefix: '+prefix+'; A=free, B=checked, C/D=batch free')


def verify_browser(batch):
    state=read_state();fixture=json.loads((QA/'runtime/purchase-delete-browser.json').read_text(encoding='utf-8'))
    assert fixture['database']==state['database'] and state['purchase_port']==18023
    gone=[fixture['free']]+(fixture['batch'] if batch else [])
    for identifier in gone:
        assert sql(state,'SELECT COUNT(*) FROM buy WHERE id='+literal(identifier)+';')=='0'
        assert sql(state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(identifier)+';')=='0'
        assert int(sql(state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+';'))==fixture['before'][identifier]+1
    retained=[fixture['checked']]+([] if batch else fixture['batch'])
    for identifier in retained:
        assert sql(state,'SELECT COUNT(*) FROM buy WHERE id='+literal(identifier)+';')=='1'
        assert sql(state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(identifier)+';')=='1'
    assert sql(state,'SELECT CAST(`check` AS SIGNED) FROM buy WHERE id='+literal(fixture['checked'])+';')=='1'
    assert sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+';') in ('0','0.0000')
    assert sql(state,'SELECT balance FROM account WHERE id='+literal(fixture['account'])+';') in ('100','100.0000')
    assert sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';') in ('0','0.0000')
    report=dict(case='purchase.browser_batch_delete' if batch else 'purchase.browser_single_delete',status='verified',removed_count=len(gone),history_retained=True,checked_document_retained=True,production_business_writes=0,all_system_features_accepted=False)
    (QA/('reports/purchase-delete-browser-'+('batch' if batch else 'single')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS browser deletion: '+str(len(gone))+' free draft(s) removed with history retained; checked document retained; stock/cash/payable unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify-single','verify-batch'],nargs='?',default='run')
    action=parser.parse_args().action
    if action=='prepare':prepare_browser()
    elif action.startswith('verify-'):verify_browser(action=='verify-batch')
    else:PurchaseDeleteSuite(read_state()).run()
