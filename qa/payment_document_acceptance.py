"""Actual scoped payment draft lifecycle; isolated API writes and independent SQL."""
import copy
import uuid
import urllib.parse
from decimal import Decimal
from payment_draft_acceptance import PaymentDraftSuite
from acceptance import read_state,sql,literal

class PaymentDocumentSuite(PaymentDraftSuite):
    def document(self,identifier):
        result=self.request('GET','/payment-order/document/'+identifier,service='payment')
        assert result.get('code')==10000,str(result)
        return result['data']

    def revision(self,document,money=30):
        row=document['items'][0]
        return dict(version=document['version'],data='QA corrected',details=[dict(id=row['id'],pid=row['pid'],account=row['account'],money=money,settle='',data1='QA revised')])

    def edit(self,identifier,body):return self.request('PUT','/payment-order/document/'+identifier,body,service='payment')
    def remove(self,identifier,version):return self.request('DELETE','/payment-order/document/'+identifier,dict(version=version),service='payment')

    def run(self):
        def lifecycle():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier)
            listing=self.request('GET','/payment-order/documents?number='+before['header']['number'],service='payment')
            assert listing.get('code')==10000,str(listing)
            row=next(row for row in listing['data']['rows'] if row['id']==identifier)
            assert row['version']==before['version'] and type(row['examine']) is int and type(row['nucleus']) is int
            assert self.edit(identifier,self.revision(before)).get('code')==10000
            after=self.document(identifier)
            assert after['version']!=before['version'] and Decimal(str(after['header']['total']))==30
            for key in ['frame','user','file','more','number','supplier']:
                assert after['header'].get(key)==before['header'].get(key),key
            assert after['items'][0]['id']==before['items'][0]['id']
            assert self.edit(identifier,self.revision(before,35)).get('code')!=10000
            assert self.remove(identifier,before['version']).get('code')!=10000
            assert self.document(identifier)['version']==after['version'];self.unchanged()
            assert self.remove(identifier,after['version']).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM omy WHERE id='+literal(identifier)+';')=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM omy_info WHERE pid='+literal(identifier)+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(identifier)+';')=='3'
            self.unchanged()
            return ['Actual list/detail version identity, corrected draft preserves ownership/line IDs, stale edit/delete refuse, physical draft removal retains actor history; no cash/AP posting']
        self.case('payment.document_draft_correct_then_delete',lifecycle)

        def invalid():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier)
            variants=[]
            for field,value in [('id',uuid.uuid4().hex),('pid',uuid.uuid4().hex),('money',-1),('money','0.00001'),('account',uuid.uuid4().hex)]:
                body=self.revision(before);body['details'][0][field]=value;variants.append(body)
            duplicate=self.revision(before);duplicate['details'].append(copy.deepcopy(duplicate['details'][0]));variants.append(duplicate)
            empty=self.revision(before);empty['details']=[];variants.append(empty)
            for body in variants:
                assert self.edit(identifier,body).get('code')!=10000
                assert self.document(identifier)['version']==before['version']
            self.unchanged()
            return ['Wrong/duplicate detail ownership, invalid amounts/accounts and empty rows reject atomically without changing reviewed version']
        self.case('payment.document_invalid_revision_atomic',invalid)

        def storage():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier);body=self.revision(before)
            marker='QAREV'+uuid.uuid4().hex[:12];body['details'][0]['data1']=marker;trigger='qa_rev_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON omy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA revision insert fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.edit(identifier,body).get('code')!=10000
                assert self.document(identifier)['version']==before['version']
                assert self.document(identifier)['items']==before['items'];self.unchanged()
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.edit(identifier,body).get('code')==10000;self.unchanged()
            return ['Actual insert failure after header update and line deletion rolls back all facts/history/version; exact same reviewed command retries']
        self.case('payment.document_storage_rollback_retry',storage)

        def filtered():
            self.fixture();identifier=self.create_payment(self.body());document=self.document(identifier)
            base=dict(number=document['header']['number'],startTime='2026-11-15',endTime='2026-11-15',pageIndex=1,pageSize=10)
            for suffix in ['/documents','/query-all']:
                result=self.request('GET','/payment-order'+suffix+'?'+urllib.parse.urlencode(base),service='payment')
                assert result.get('code')==10000,str(result)
                assert result['data']['total']==1,str(result)
            for field in ['account','data1']:
                for text in ["' OR 1=1 -- ","QA first' ) OR 1=1 -- "]:
                    query=dict(base);query[field]=text
                    result=self.request('GET','/payment-order/query-all?'+urllib.parse.urlencode(query),service='payment')
                    assert result.get('code')==10000,str(result)
                    assert result['data']['total']==0,'Filter text changed query meaning'
            assert self.document(identifier)['version']==document['version'];self.unchanged()
            return ['Actual legacy/new inclusive same-day filters find the real draft; quoted account/remark strings remain literal filters and cannot alter query meaning']
        self.case('payment.document_legacy_parameterized_filters',filtered)

        def associations():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier);kind,expense,invoice=[uuid.uuid4().hex for _ in range(3)]
            sql(self.state,'INSERT INTO iet(id,name,type,sort) VALUES('+','.join(literal(v) for v in [kind,'QA Visible Payment Expense',1,0])+');INSERT INTO cost(id,type,`class`,time,iet,money,settle,state,data) VALUES('+','.join(literal(v) for v in [expense,'omy',identifier,'2026-11-15',kind,1,0,0,'QA linked expense'])+');INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'omy',identifier,'2026-11-15','QA'+invoice[:12],'QA Visible Invoice',1])+');')
            try:
                current=self.document(identifier)
                assert len(current['expenses'])==len(current['invoices'])==1
                assert current['expenses'][0]['id']==expense and current['expenses'][0]['expenseName']=='QA Visible Payment Expense' and current['expenses'][0]['data']=='QA linked expense'
                assert current['invoices'][0]['id']==invoice and current['invoices'][0]['title']=='QA Visible Invoice'
                assert self.edit(identifier,self.revision(current)).get('code')!=10000
                assert self.remove(identifier,current['version']).get('code')!=10000
                self.unchanged()
            finally:sql(self.state,'DELETE FROM cost WHERE id='+literal(expense)+';DELETE FROM invoice WHERE id='+literal(invoice)+';DELETE FROM iet WHERE id='+literal(kind)+';')
            assert self.document(identifier)['version']==before['version']
            assert self.edit(identifier,self.revision(before)).get('code')==10000;self.unchanged()
            return ['Explicit SQL association fixtures shown by actual payment detail with real IDs/business names/amounts; linked draft cannot be altered/deleted, removing test associations permits reviewed correction without money changes']
        self.case('payment.document_visible_association_blockers',associations)
        self.write_report()

if __name__=='__main__':PaymentDocumentSuite(read_state()).run()
