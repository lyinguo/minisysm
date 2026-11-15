"""Real procurement draft gates against dedicated purchase HTTP and MySQL only."""
import json
import uuid
import concurrent.futures
import threading
import urllib.request
from decimal import Decimal
from warehouse_acceptance import WarehouseSuite
from acceptance import QA,read_state,sql,literal


class PurchaseDraftSuite(WarehouseSuite):
    def __init__(self,state):
        super().__init__(state)
        self.supplier=uuid.uuid4().hex
        self.numeric_supplier=str(int(uuid.uuid4().hex[:15],16))
        for identifier in [self.supplier,self.numeric_supplier]:
            sql(state,'INSERT INTO supplier(id,name,py,number,frame,`user`,category) VALUES('+','.join(literal(v) for v in [identifier,'QA Purchase Supplier','qa','QS'+identifier[:24],state['frame_id'],self.actor,'0'])+');')

    def body(self,numeric=False):
        return dict(purchaseNoteBuyDTO=dict(supplier=self.numeric_supplier if numeric else self.supplier,time='2026-11-15',number='QAP'+uuid.uuid4().hex[:24],total=200,actual=226,money=0,cost=0,account=None,people=None,source='0',file=json.dumps([dict(name='qa-proof.txt',url='/qa-proof.txt')]),data='QA actual purchase draft'),
                    purchaseNoteInfoDTOS=[dict(source='0',goods=self.goods,attr='',unit='unit',warehouse=self.warehouse,batch='QA-LOT',mfd='2026-11-01',price=100,nums=2,discount=1,dsc=0,total=200,tax=.13,tat=26,tpt=226,data='QA line',serial='["QA-SN-A","QA-SN-B"]')])

    def create(self,body):
        result=self.request('POST','/purchase-note/add',body,service='purchase')
        if result.get('code')!=10000: (QA/'runtime/purchase-last-error.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        assert result.get('code')==10000,'Actual purchase create rejected; code='+str(result.get('code'))
        assert isinstance(result.get('data'),str) and result['data']
        return result['data']

    def run(self):
        def uuid_ids():
            body=self.body();identifier=self.create(body)
            assert sql(self.state,'SELECT supplier FROM buy WHERE id='+literal(identifier)+';')==self.supplier
            return ['Actual create accepts persisted UUID supplier and goods identifiers']
        self.case('purchase.draft_accepts_real_uuid_supplier',uuid_ids)

        def optional_batch():
            body=self.body(True);body['purchaseNoteInfoDTOS'][0].update(batch='',mfd=None,serial='[]')
            identifier=self.create(body)
            assert sql(self.state,'SELECT IF(mfd IS NULL,\'NULL\',\'NOT_NULL\') FROM buy_info WHERE pid='+literal(identifier)+';')=='NULL'
            return ['Ordinary goods do not require an invented batch or manufacturing date']
        self.case('purchase.draft_nonbatch_goods_need_no_batch_date',optional_batch)

        def metadata():
            body=self.body(True);identifier=self.create(body)
            assert sql(self.state,'SELECT file FROM buy WHERE id='+literal(identifier)+';')==body['purchaseNoteBuyDTO']['file'],'Attachment metadata overwritten with placeholder'
            assert json.loads(sql(self.state,'SELECT serial FROM buy_info WHERE pid='+literal(identifier)+';'))==['QA-SN-A','QA-SN-B'],'Serial metadata lost'
            assert sql(self.state,'SELECT `user` FROM buy WHERE id='+literal(identifier)+';')==self.actor
            assert sql(self.state,'SELECT CAST(cse AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')=='3','Zero-fee draft should not require expense settlement'
            assert Decimal(sql(self.state,'SELECT money FROM buy WHERE id='+literal(identifier)+';'))==0
            assert sql(self.state,'SELECT COUNT(*) FROM room WHERE goods='+literal(self.goods)+';')=='0'
            return ['Persisted attachments/serial metadata/creator match real request; draft leaves physical stock untouched']
        self.case('purchase.draft_preserves_metadata_and_stock',metadata)

        def duplicate():
            body=self.body(True);self.create(body)
            result=self.request('POST','/purchase-note/add',body,service='purchase')
            assert result.get('code')!=10000,'Repeated business number accepted'
            assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='1'
            return ['Actual repeated create cannot duplicate the procurement number']
        self.case('purchase.draft_number_unique',duplicate)

        def invalid_date():
            for date in ['not-a-date','2026-02-30','2026-02-30 10:00:00']:
                body=self.body(True);body['purchaseNoteBuyDTO']['time']=date
                result=self.request('POST','/purchase-note/add',body,service='purchase')
                assert result.get('code')!=10000,'Invalid business date silently changed to another date'
                assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
            return ['Invalid date is rejected atomically instead of recording a different business date']
        self.case('purchase.draft_invalid_business_date_rejected',invalid_date)

        def concurrent_number():
            body=self.body();barrier=threading.Barrier(2)
            def worker(_):
                barrier.wait(timeout=10)
                return self.request('POST','/purchase-note/add',body,service='purchase').get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                codes=list(executor.map(worker,range(2)))
            assert codes.count(10000)==1,'Concurrent number reservation did not produce exactly one committed draft; codes='+str(codes)
            assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='1'
            return ['Two real concurrent creates of the same number commit exactly one header and detail set']
        self.case('purchase.draft_concurrent_number_unique',concurrent_number)

        def storage_failure():
            body=self.body();marker=uuid.uuid4().hex
            body['purchaseNoteInfoDTOS'][0]['data']='QA-FIRST-'+marker
            body['purchaseNoteInfoDTOS'].append(dict(body['purchaseNoteInfoDTOS'][0],data='QA-FAIL-'+marker))
            body['purchaseNoteBuyDTO'].update(total=400,actual=452)
            trigger='qa_buy_line_'+marker[:12]
            try:
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON buy_info FOR EACH ROW BEGIN IF NEW.data="+literal('QA-FAIL-'+marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA purchase second line failure'; END IF; END;$$\nDELIMITER ;\n")
                result=self.request('POST','/purchase-note/add',body,service='purchase')
                assert result.get('code')!=10000
                assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
                assert sql(self.state,'SELECT COUNT(*) FROM buy_info WHERE data='+literal('QA-FIRST-'+marker)+';')=='0'
            finally:
                sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            identifier=self.create(body)
            assert sql(self.state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(identifier)+';')=='2'
            return ['Real second-detail insert failure rolls back header and first detail; removing injected failure permits retry']
        self.case('purchase.draft_second_detail_failure_atomic',storage_failure)

        def foreign_warehouse():
            frame,warehouse=uuid.uuid4().hex,uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name,sort) VALUES('+','.join(literal(v) for v in [frame,'0','QA Other Purchase Org',0])+');'+
                'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [warehouse,'QA Foreign Purchase Warehouse','QW'+warehouse[:16],frame])+');')
            body=self.body();body['purchaseNoteInfoDTOS'][0]['warehouse']=warehouse
            assert self.request('POST','/purchase-note/add',body,service='purchase').get('code')!=10000
            assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
            return ['Foreign-organization warehouse rejected before committing the draft; not complete role permission acceptance']
        self.case('purchase.draft_warehouse_organization_checked',foreign_warehouse)

        def forged_identity():
            body=self.body()
            request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/add',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','user':json.dumps(dict(id=self.actor,authorities=['ROLE_ADMIN']))})
            with self.opener.open(request,timeout=20) as response:result=json.load(response)
            assert result.get('code') in (401,403),'Unsigned identity header accepted or produced an unrelated error'
            assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
            return ['Forged identity header without signed credentials cannot create a purchase draft']
        self.case('purchase.draft_unsigned_identity_rejected',forged_identity)
        self.write_report()


if __name__=='__main__':
    PurchaseDraftSuite(read_state()).run()
