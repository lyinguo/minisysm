"""Actual legacy procurement revise endpoint gates, including storage failure rollback."""
import uuid
from decimal import Decimal
from purchase_draft_acceptance import PurchaseDraftSuite
from warehouse_acceptance import WarehouseSuite
from acceptance import QA,read_state,sql,literal
import json
import concurrent.futures
import threading


class PurchaseRevisionSuite(PurchaseDraftSuite):
    def draft(self):
        body=self.body()
        body['purchaseNoteInfoDTOS'][0].update(tax=13,discount=0,batch='',mfd=None,serial='[]')
        return self.create(body)

    def revision(self,identifier):
        document=self.document(identifier)
        line=document['items'][0]['id']
        return dict(id=identifier,version=document['version'],supplier=self.supplier,time='2026-11-15 13:47:00',number=document['header']['number'],actual=339,money=0,account='',people='',file='',data='QA revised purchase',examine=0,checkStatus=0,
                    details=[dict(id=line,goods=self.goods,unit='unit',warehouse=self.warehouse,price=100,nums=3,discount=0,tax=13,data='QA revised line',retreat=0)])

    def document(self,identifier):
        result=self.request('GET','/purchase-note/document/'+identifier,service='purchase')
        assert result.get('code')==10000,'Complete purchase document read failed'
        return result['data']

    def revise(self,body):
        result=self.request('POST','/purchase-note/revise',body,service='purchase')
        if result.get('code')!=10000: (QA/'runtime/purchase-revise-last-error.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        return result

    def run(self):
        def ordinary():
            identifier=self.draft();body=self.revision(identifier)
            result=self.revise(body)
            assert result.get('code')==10000,'Ordinary real purchase revise failed; code='+str(result.get('code'))
            actual=sql(self.state,"SELECT CONCAT(total,',',actual,',',money) FROM buy WHERE id="+literal(identifier)+';')
            assert list(map(Decimal,actual.split(',')))==list(map(Decimal,['300','339','0']))
            assert sql(self.state,'SELECT `user` FROM buy WHERE id='+literal(identifier)+';')==self.actor
            assert sql(self.state,'SELECT COUNT(*) FROM room WHERE goods='+literal(self.goods)+';')=='0'
            return ['Real create then revise quantity; header and detail amounts agree, original creator preserved and stock unchanged']
        self.case('purchase.revise_actual_draft',ordinary)

        def add_remove():
            identifier=self.draft();body=self.revision(identifier)
            body['details'].append(dict(body['details'][0],id=None,nums=1,data='QA new revision line'))
            body['actual']=452
            assert self.revise(body).get('code')==10000
            rows=sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(identifier)+' ORDER BY id;').splitlines()
            assert len(rows)==2 and body['details'][0]['id'] in rows,'New line was deleted again or original ID was replaced'
            assert len(self.document(identifier)['items'])==2
            body['version']=self.document(identifier)['version']
            body['details']=body['details'][:1];body['actual']=339
            assert self.revise(body).get('code')==10000
            assert sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(identifier)+';')==body['details'][0]['id']
            return ['Actual full-draft replacement keeps retained IDs, inserts new rows and removes only omitted rows']
        self.case('purchase.revise_add_remove_line_identity',add_remove)

        def rollback():
            identifier=self.draft();body=self.revision(identifier)
            original=sql(self.state,'SELECT CONCAT(data,\':\',actual) FROM buy WHERE id='+literal(identifier)+';')
            marker=uuid.uuid4().hex;trigger='qa_buy_revise_'+marker[:12]
            body['details'].append(dict(body['details'][0],id=None,data=marker,nums=1));body['actual']=452
            try:
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON buy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA revise second line failure'; END IF; END;$$\nDELIMITER ;\n")
                assert self.revise(body).get('code')!=10000
                assert sql(self.state,'SELECT CONCAT(data,\':\',actual) FROM buy WHERE id='+literal(identifier)+';')==original
                assert Decimal(sql(self.state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';'))==2
            finally:
                sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.revise(body).get('code')==10000,'Retry failed after removing the actual storage fault'
            return ['Injected second-line storage error leaves header and first line unchanged; real retry succeeds after trigger cleanup']
        self.case('purchase.revise_storage_failure_atomic',rollback)

        def foreign_line():
            first,second=self.draft(),self.draft();body=self.revision(first)
            foreign=sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(second)+';')
            body['details'][0]['id']=foreign
            result=self.revise(body)
            assert result.get('code')!=10000
            assert sql(self.state,'SELECT pid FROM buy_info WHERE id='+literal(foreign)+';')==second
            assert Decimal(sql(self.state,'SELECT actual FROM buy WHERE id='+literal(first)+';'))==226
            return ['A detail ID belonging to another real draft cannot be moved or overwritten']
        self.case('purchase.revise_foreign_line_rejected',foreign_line)

        def missing_flags():
            identifier=self.draft();body=self.revision(identifier)
            del body['examine'];del body['checkStatus']
            assert self.revise(body).get('code')==10000
            assert sql(self.state,'SELECT CONCAT(CAST(examine AS SIGNED),\',\',CAST(`check` AS SIGNED)) FROM buy WHERE id='+literal(identifier)+';')=='0,0'
            return ['Draft modification does not require the client to resubmit authoritative business status flags']
        self.case('purchase.revise_omitted_status_supported',missing_flags)

        def status_protection():
            identifier=self.draft();body=self.revision(identifier)
            body['examine']=1
            assert self.revise(body).get('code')!=10000
            assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM room WHERE goods='+literal(self.goods)+';')=='0'
            assert self.request('POST','/purchase-note/verification',dict(ids=[identifier],type=1,version=self.document(identifier)['version']),service='purchase').get('code')==10000
            body['examine']=0
            assert self.revise(body).get('code')!=10000
            assert Decimal(sql(self.state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';'))==2
            return ['Revise cannot impersonate audit; actually checked documents reject direct edits and leave physical inventory untouched']
        self.case('purchase.revise_status_changes_and_checked_edits_rejected',status_protection)

        def original_rates():
            original=self.body();identifier=self.create(original)
            body=self.revision(identifier)
            body['details'][0].update(tax=.13,discount=1)
            assert self.revise(body).get('code')==10000
            amounts=sql(self.state,"SELECT CONCAT(total,',',actual) FROM buy WHERE id="+literal(identifier)+';')
            assert list(map(Decimal,amounts.split(',')))==list(map(Decimal,['300','339'])),'Unchanged legacy rate representation changed the effective discount/tax'
            return ['Original monetary evidence determines unchanged effective rates; old fractional representation is not reinterpreted as percentage points']
        self.case('purchase.revise_retains_unchanged_legacy_effective_rates',original_rates)

        def stale_version():
            identifier=self.draft();body=self.revision(identifier)
            assert self.revise(body).get('code')==10000
            body['details'][0]['nums']=4
            assert self.revise(body).get('code')!=10000
            assert Decimal(sql(self.state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';'))==3
            return ['Real full document read supplies a version; stale editor cannot overwrite a committed newer revision']
        self.case('purchase.revise_stale_version_rejected',stale_version)
        def concurrent_version():
            identifier=self.draft();first=self.revision(identifier)
            second=dict(first,details=[dict(first['details'][0],nums=4)])
            barrier=threading.Barrier(2)
            def worker(body):
                barrier.wait(timeout=10)
                return self.revise(body).get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                codes=list(executor.map(worker,[first,second]))
            assert codes.count(10000)==1,'Same-version editors both overwrote the document or neither succeeded: '+str(codes)
            assert Decimal(sql(self.state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';')) in [3,4]
            return ['Two actual HTTP editors with the same read version produce one committed revision and one conflict']
        self.case('purchase.revise_concurrent_same_version',concurrent_version)
        def missing_version():
            identifier=self.draft();body=self.revision(identifier)
            del body['version']
            assert self.revise(body).get('code')!=10000
            assert Decimal(sql(self.state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';'))==2
            return ['An editor without a read version cannot bypass conflict protection or replace unseen document lines']
        self.case('purchase.revise_missing_version_rejected',missing_version)
        def omitted_metadata():
            original=self.body();identifier=self.create(original)
            before=self.document(identifier)
            body=self.revision(identifier)
            for field in ['file','account','people']: del body[field]
            body['details'][0].update(tax=.13,discount=1,nums=2)
            assert self.revise(body).get('code')==10000
            after=self.document(identifier)
            assert after['header']['file']==before['header']['file']
            for field in ['account','people','logistics']:
                assert after['header'].get(field) is None and before['header'].get(field) is None,'Omitted SQL NULL metadata changed'
            assert sql(self.state,'SELECT IF(account IS NULL AND people IS NULL AND logistics IS NULL,1,0) FROM buy WHERE id='+literal(identifier)+';')=='1'
            for field in ['source','attr','batch','mfd','serial']:
                assert after['items'][0][field]==before['items'][0][field],'Existing detail metadata lost: '+field
            return ['Omitted optional fields retain attachments and SQL NULL values; original source/attribute/batch/date/serial metadata survives revision']
        self.case('purchase.revise_omitted_metadata_preserved',omitted_metadata)
        def different_editor():
            identifier=self.draft();body=self.revision(identifier)
            editor=WarehouseSuite(self.state)
            original_token=self.token
            try:
                self.token=editor.token
                assert self.revise(body).get('code')==10000
            finally:
                self.token=original_token
            assert sql(self.state,'SELECT `user` FROM buy WHERE id='+literal(identifier)+';')==self.actor
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(identifier)+' AND `user`='+literal(editor.actor)+' AND info='+literal('修改采购草稿')+';')=='1'
            return ['Another newly created, actually authenticated QA user edits the draft; original creator stays unchanged and the event identifies the real editor']
        self.case('purchase.revise_distinct_editor_preserves_creator',different_editor)
        self.write_report()


if __name__=='__main__':
    PurchaseRevisionSuite(read_state()).run()
