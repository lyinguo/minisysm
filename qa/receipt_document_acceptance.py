"""Actual complete receipt document revision/deletion with stable ownership."""
import uuid,copy,urllib.parse
from decimal import Decimal
from receipt_draft_acceptance import ReceiptDraftSuite
from receipt_settlement_acceptance import ReceiptSettlementSuite
from acceptance import read_state,sql,literal

class ReceiptDocumentSuite(ReceiptDraftSuite):
    def document(self,identifier):
        response=self.request('GET','/fund/receipt/document/'+identifier,service='fund');assert response.get('code')==10000,str(response);return response['data']
    def revision(self,document,money=30):
        row=document['items'][0]
        return dict(version=document['version'],data='QA corrected receipt',details=[dict(id=row['id'],pid=row['pid'],account=row['account'],amount=money,settle='',data='QA revised receipt line')])
    def edit(self,identifier,body):return self.request('PUT','/fund/receipt/document/'+identifier,body,service='fund')
    def remove(self,identifier,version):return self.request('DELETE','/fund/receipt/document/'+identifier,dict(version=version),service='fund')
    def run(self):
        def lifecycle():
            self.fixture(stock=0);body=self.receipt_body();body['more']='{"qaReference":"keep extension"}';identifier=self.create_receipt(body);before=self.document(identifier)
            page=self.request('GET','/fund/receipt/documents?number='+body['number'],service='fund');assert page.get('code')==10000,str(page)
            assert page['data']['total']==1 and page['data']['rows'][0]['version']==before['version']
            assert type(before['header']['examine']) is int and type(before['header']['nucleus']) is int
            assert before['header']['timeText']=='2026-11-16 14:00:00'
            assert self.edit(identifier,self.revision(before)).get('code')==10000
            after=self.document(identifier);assert after['version']!=before['version'] and Decimal(str(after['header']['total']))==30
            for field in ['frame','user','file','more','number','customer','time']:assert after['header'][field]==before['header'][field],field
            assert after['items'][0]['id']==before['items'][0]['id']
            assert self.edit(identifier,self.revision(before,35)).get('code')!=10000
            assert self.remove(identifier,before['version']).get('code')!=10000
            assert self.document(identifier)['version']==after['version'];self.unchanged_receipt()
            assert self.remove(identifier,after['version']).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM imy WHERE id='+literal(identifier)+';')=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM imy_info WHERE pid='+literal(identifier)+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+';')=='3'
            self.unchanged_receipt();return ['Actual canonical list/detail version identity, full timestamp preserved; reviewed correction keeps original line/creator/org/file/extensions, stale commands refuse; physical draft removal keeps3 audit histories without funds/AR/inventory changes']
        self.case('receipt.document_correct_then_remove_stable_identity',lifecycle)
        def invalid():
            self.fixture(stock=0);identifier=self.create_receipt(self.receipt_body());before=self.document(identifier);variants=[]
            for key,value in [('id',uuid.uuid4().hex),('pid',uuid.uuid4().hex),('amount',-1),('amount','0.00001'),('account',uuid.uuid4().hex)]:
                body=self.revision(before);body['details'][0][key]=value;variants.append(body)
            body=self.revision(before);body['details']*=2;variants.append(body)
            body=self.revision(before);body['details']=[];variants.append(body)
            body=self.revision(before);body['more']='[]';variants.append(body)
            for body in variants:
                assert self.edit(identifier,body).get('code')!=10000
                assert self.document(identifier)['version']==before['version']
            self.unchanged_receipt();return ['Invalid/foreign/duplicate stable line ownership, amount/precision/account/empty rows and invalid extension shape reject entire revision without replacing prior rows or version']
        self.case('receipt.document_invalid_revision_atomic',invalid)
        def storage():
            self.fixture(stock=0);identifier=self.create_receipt(self.receipt_body());before=self.document(identifier);body=self.revision(before);marker='QAREV'+uuid.uuid4().hex[:12];body['details'][0]['data']=marker;trigger='qa_rct_rev_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON imy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA receipt revision fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.edit(identifier,body).get('code')!=10000
                assert self.document(identifier)==before;self.unchanged_receipt()
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.edit(identifier,body).get('code')==10000;self.unchanged_receipt()
            return ['Actual detail insert failure after header update and old-row deletion restores complete original document/history/version; same reviewed revision succeeds after fault removal']
        self.case('receipt.document_storage_rollback_retry',storage)
        def filters():
            self.fixture(stock=0);body=self.receipt_body();body['info'].append(dict(body['info'][0],amount=10));identifier=self.create_receipt(body)
            query=dict(number=body['number'],startTime='2026-11-16',endTime='2026-11-16',pageIndex=1,pageSize=10)
            response=self.request('GET','/fund/receipt/documents?'+urllib.parse.urlencode(query),service='fund');assert response.get('code')==10000,str(response)
            assert response['data']['total']==1 and len(response['data']['rows'])==1
            for key in ['number','customer']:
                changed=dict(query);changed[key]="' OR 1=1 -- "
                response=self.request('GET','/fund/receipt/documents?'+urllib.parse.urlencode(changed),service='fund');assert response.get('code')==10000 and response['data']['total']==0,str(response)
            self.unchanged_receipt();return ['Actual same-day receipt search includes full timestamp and returns one parent for two account lines; quoted number/customer text remains literal filtering']
        self.case('receipt.document_filters_single_parent_and_literal_text',filters)
        def posted():
            flow=ReceiptSettlementSuite(self.state);f=flow.prepare_trade();assert flow.post_receipt(flow.command(f['receipt'])).get('data')==1
            current=self.document(f['receipt'])
            assert self.edit(f['receipt'],self.revision(current,91)).get('code')!=10000
            assert self.remove(f['receipt'],current['version']).get('code')!=10000
            flow.balances(f,1322,0);assert self.document(f['receipt'])['version']==current['version']
            assert flow.post_receipt(dict(id=f['receipt'],status=0,version=current['version'])).get('data')==1
            assert self.edit(f['receipt'],self.revision(self.document(f['receipt']),91)).get('code')==10000
            flow.balances(f,1171,151)
            assert self.remove(f['receipt'],self.document(f['receipt'])['version']).get('code')==10000;flow.balances(f,1171,151)
            return ['Actual credited receipt rejects direct fresh-version edit/delete; explicit cash/source reversal permits corrected91 draft and removal, leaving original customer AR151 and supplier0 unchanged']
        self.case('receipt.document_posted_requires_explicit_reverse',posted)
        self.write_report()

if __name__=='__main__':ReceiptDocumentSuite(read_state()).run()
