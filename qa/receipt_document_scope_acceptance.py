"""Actual receipt function grants, legacy reads and concurrent correction/posting."""
import uuid,concurrent.futures
from receipt_document_acceptance import ReceiptDocumentSuite
from receipt_settlement_acceptance import ReceiptSettlementSuite
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants
from acceptance import read_state,sql,literal

class ReceiptDocumentScopeSuite(ReceiptDocumentSuite):
    role_user=PaymentDocumentScopeSuite.role_user
    def legacy_list(self,query):return self.request('POST','/fund/receipt/fundReceiptList',dict(pageIndex=1,pageSize=10,**query),service='fund')
    def run(self):
        def grants():
            self.fixture(stock=0);identifier=self.create_receipt(self.receipt_body());before=self.document(identifier);user,token,role=self.role_user();admin=self.token;self.token=token
            try:
                assert self.request('GET','/fund/receipt/document/'+identifier,service='fund').get('code')==403
                assert self.edit(identifier,self.revision(before)).get('code')==403
                with qa_resource_grants(self.state,['/fund/receipt/fundReceiptDetail','/fund/receipt/fundReceiptList'],[role]):
                    assert self.document(identifier)['version']==before['version']
                    assert self.legacy_list(dict(number=before['header']['number'])).get('code')==10000
                    assert self.edit(identifier,self.revision(before)).get('code')==403
                    with qa_resource_grants(self.state,['/fund/receipt/update'],[role]):assert self.edit(identifier,self.revision(before)).get('code')==10000
                    current=self.document(identifier);assert self.edit(identifier,self.revision(current)).get('code')==403
                    assert self.remove(identifier,current['version']).get('code')==403
                    with qa_resource_grants(self.state,['/fund/receipt/remove'],[role]):assert self.remove(identifier,current['version']).get('code')==10000
                assert self.request('GET','/fund/receipt/document/'+identifier,service='fund').get('code')==403
            finally:self.token=admin
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+' AND `user`='+literal(user)+';')=='2';self.unchanged_receipt()
            return ['Actual ordinary OAuth separately needs read/update/remove grants; read alone cannot mutate, revoke takes effect with same token, actual modifying/deleting operator recorded without creation grant']
        self.case('receipt.document_live_separate_function_grants',grants)
        def organization():
            self.fixture(stock=0);own=self.create_receipt(self.receipt_body());foreign=self.create_receipt(self.receipt_body());number=self.document(foreign)['header']['number'];frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Receipt Foreign Read');UPDATE imy SET frame="+literal(frame)+' WHERE id='+literal(foreign)+';')
            document=self.document(foreign);_,token,role=self.role_user();admin=self.token
            try:
                with qa_resource_grants(self.state,['/fund/receipt/fundReceiptDetail','/fund/receipt/fundReceiptList','/fund/receipt/update','/fund/receipt/remove'],[role]):
                    self.token=token;assert self.document(own)['header']['frame']==self.state['frame_id']
                    assert self.request('GET','/fund/receipt/document/'+foreign,service='fund').get('code')==403
                    assert self.request('POST','/fund/receipt/fundReceiptDetail?id='+foreign,service='fund').get('code')==403
                    page=self.request('GET','/fund/receipt/documents?number='+number,service='fund');assert page.get('code')==10000 and page['data']['total']==0,str(page)
                    page=self.legacy_list(dict(number=number));assert page.get('code')==10000 and page['data']['total']==0,str(page)
                    assert self.edit(foreign,self.revision(document)).get('code')==403
                    assert self.remove(foreign,document['version']).get('code')==403
            finally:self.token=admin
            assert self.document(foreign)['version']==document['version'];self.unchanged_receipt()
            return ['Actual authorized ordinary role cannot read foreign header/details through new or legacy endpoints, both lists exclude foreign parent, current-version update/remove refuse before mutation']
        self.case('receipt.document_cross_organization_new_and_legacy',organization)
        def legacy_filters():
            flow=ReceiptSettlementSuite(self.state);f=flow.prepare_trade();document=self.document(f['receipt']);line=document['items'][0]
            revision=self.revision(document,50);revision['details'].append(dict(account=line['account'],amount=101,settle='',data='QA second actual account'))
            assert self.edit(f['receipt'],revision).get('code')==10000
            assert flow.post_receipt(flow.command(f['receipt'])).get('data')==1;flow.balances(f,1322,0)
            query=dict(number=f['receipt_number'],account=f['account'],beginTime='2026-11-16',endTime='2026-11-16')
            result=self.legacy_list(query);assert result.get('code')==10000,str(result)
            assert result['data']['total']==1 and len(result['data']['rows'])==1,str(result)
            row=result['data']['rows'][0];assert row['money']==151 and row['customer']=='QA Sale Customer' and row['nucleus']==2,str(row)
            assert self.legacy_list(dict(query,account=uuid.uuid4().hex))['data']['total']==0
            assert self.legacy_list(dict(query,data="' OR 1=1 -- "))['data']['total']==0
            legacy=self.request('POST','/fund/receipt/fundReceiptDetail?id='+f['receipt'],service='fund');assert legacy.get('code')!=10000,'Legacy one-row DTO silently discarded a real second account'
            assert len(self.document(f['receipt'])['items'])==2
            return ['Actual receipt with2 account rows and2 source allocations returns one legacy parent and net151, correct customer name/integer settled2, account filter uses account rather than remark, quoted text remains literal; obsolete single-line detail refuses truncation, complete document returns both actual rows']
        self.case('receipt.document_legacy_filter_aggregation_and_complete_rows',legacy_filters)
        def competing():
            flow=ReceiptSettlementSuite(self.state);f=flow.prepare_trade();document=self.document(f['receipt']);revision=self.revision(document,91);command=flow.command(f['receipt'])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                edit=pool.submit(self.edit,f['receipt'],revision);post=pool.submit(flow.post_receipt,command);results=[edit.result(),post.result()]
            assert sum(result.get('code')==10000 for result in results)==1,str(results)
            after=self.document(f['receipt'])
            if after['header']['examine']==1:
                assert after['header']['total']==151;flow.balances(f,1322,0)
            else:
                assert after['header']['total']==91 and not after['allocations'];flow.balances(f,1171,151)
            return ['Actual concurrent correction91 versus reviewed posting151 shares receipt lock and version checks: exactly one wins, final cash/customer/source journals match the winning complete operation']
        self.case('receipt.document_revision_vs_posting_single_winner',competing)
        self.write_report()

if __name__=='__main__':ReceiptDocumentScopeSuite(read_state()).run()
