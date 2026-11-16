"""Actual OAuth grant changes, organization boundaries and posted draft protections."""
import uuid
import concurrent.futures
from payment_document_acceptance import PaymentDocumentSuite
from payment_settlement_posting_acceptance import PaymentPostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants,authority
from acceptance import read_state,sql,literal

class PaymentDocumentScopeSuite(PaymentDocumentSuite):
    def role_user(self):
        role=self.success('POST','/role/add-role',dict(name='QA Pay Docs '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
        keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
        identifier,payload,_=self.new_user(role=role)
        return identifier,PurchaseUiSuite.login(self,payload),authority(role,keyword)

    def run(self):
        def grants():
            self.fixture();identifier=self.create_payment(self.body());initial=self.document(identifier)
            user,token,role=self.role_user();admin=self.token
            def read():return self.request('GET','/payment-order/document/'+identifier,service='payment')
            self.token=token
            try:
                assert read().get('code')==403
                assert self.edit(identifier,self.revision(initial)).get('code')==403
                assert self.remove(identifier,initial['version']).get('code')==403
                with qa_resource_grants(self.state,['/payment-order/query-by-id','/payment-order/query-all'],[role]):
                    current=self.document(identifier)
                    assert self.request('GET','/payment-order/documents?number='+initial['header']['number'],service='payment').get('code')==10000
                    assert self.edit(identifier,self.revision(current)).get('code')==403
                    with qa_resource_grants(self.state,['/payment-order/modify'],[role]):
                        assert self.edit(identifier,self.revision(current)).get('code')==10000
                        changed=self.document(identifier)
                    assert self.edit(identifier,self.revision(changed)).get('code')==403
                    assert self.remove(identifier,changed['version']).get('code')==403
                    with qa_resource_grants(self.state,['/payment-order/remove'],[role]):
                        assert self.remove(identifier,changed['version']).get('code')==10000
                assert read().get('code')==403
            finally:self.token=admin
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(identifier)+' AND `user`='+literal(user)+';')=='2'
            self.unchanged()
            return ['Actual ordinary OAuth separately needs read/edit/delete grants; read alone cannot mutate, same token immediately loses revoked grant, edit/delete history records actual operator without add grant']
        self.case('payment.document_live_function_grants',grants)

        def organization():
            self.fixture();own=self.create_payment(self.body());foreign=self.create_payment(self.body());before=self.document(foreign)
            frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Foreign Payment');UPDATE omy SET frame="+literal(frame)+' WHERE id='+literal(foreign)+';')
            foreign_document=self.document(foreign);user,token,role=self.role_user();admin=self.token
            resources=['/payment-order/query-by-id','/payment-order/query-all','/payment-order/modify','/payment-order/remove']
            try:
                with qa_resource_grants(self.state,resources,[role]):
                    self.token=token
                    assert self.document(own)['header']['frame']==self.state['frame_id'],'Own document frame mismatch'
                    for path in ['/document/','/query-by-id/','/settlement-document/']:
                        response=self.request('GET','/payment-order'+path+foreign,service='payment')
                        assert response.get('code')==403,path+str(response)
                    for path in ['/documents','/query-all']:
                        result=self.request('GET','/payment-order'+path+'?pageIndex=1&pageSize=10&number='+before['header']['number'],service='payment')
                        assert result.get('code')==10000 and result['data']['total']==0,str(result)
                    response=self.edit(foreign,self.revision(foreign_document));assert response.get('code')==403,'Foreign edit '+str(response)
                    response=self.remove(foreign,foreign_document['version']);assert response.get('code')==403,'Foreign remove '+str(response)
            finally:self.token=admin
            assert self.document(foreign)['version']==foreign_document['version'],'Foreign version changed';self.unchanged()
            return ['Actual privileged ordinary role cannot read/edit/delete foreign draft; both new and legacy lists exclude it, administrator still reads unchanged foreign document']
        self.case('payment.document_cross_organization_all_paths',organization)

        def concurrency():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda value:self.edit(identifier,self.revision(before,value)),[30,35]))
            assert sum(result.get('code')==10000 for result in results)==1
            assert sql(self.state,'SELECT COUNT(*) FROM omy_info WHERE pid='+literal(identifier)+';')=='1'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(identifier)+';')=='2'
            self.unchanged()
            return ['Two actual simultaneous revisions from one reviewed version produce exactly one corrected draft and one modification history, no cash changes']
        self.case('payment.document_concurrent_revision_single_winner',concurrency)

        def posted():
            flow=PaymentPostingSuite(self.state);fixture=flow.prepare_chain();identifier=fixture['payment']
            assert flow.post_payment(flow.command(identifier)).get('data')==1
            current=self.document(identifier)
            assert self.edit(identifier,self.revision(current,454)).get('code')!=10000
            assert self.remove(identifier,current['version']).get('code')!=10000
            assert self.document(identifier)['version']==current['version'];flow.balances(1171,0)
            assert flow.post_payment(dict(id=identifier,version=current['version'],status=0)).get('data')==1
            reversed=self.document(identifier)
            assert self.edit(identifier,self.revision(reversed,454)).get('code')==10000
            flow.balances(2125,954)
            assert self.remove(identifier,self.document(identifier)['version']).get('code')==10000
            flow.balances(2125,954)
            return ['Actual posted payment rejects fresh-version edit/delete without moving funds; explicit real reversal restores funds/AP and permits correction and removal while preserving original purchases/return balances']
        self.case('payment.document_posted_requires_explicit_reversal',posted)
        self.write_report()

if __name__=='__main__':PaymentDocumentScopeSuite(read_state()).run()
