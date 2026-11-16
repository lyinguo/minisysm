"""Actual signed OAuth identity is revalidated against current organization and role."""
import uuid
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants
from acceptance import read_state,sql,literal

class PaymentIdentitySuite(PaymentDocumentScopeSuite):
    def run(self):
        def missing_frame():
            self.fixture();identifier=self.create_payment(self.body());before=self.document(identifier)
            user,token,role=self.role_user();admin=self.token
            paths=['/payment-order/query-all','/payment-order/query-by-id/{id}','/payment-order/modify','/payment-order/remove']
            with qa_resource_grants(self.state,paths,[role]):
                self.token=token
                try:
                    assert self.document(identifier)['version']==before['version']
                    rejected=False
                    try:sql(self.state,'UPDATE `user` SET frame='+literal(uuid.uuid4().hex)+' WHERE id='+literal(user)+';')
                    except RuntimeError as failure:
                        assert 'PSI_INTEGRITY:missing:frame' in str(failure),str(failure);rejected=True
                    assert rejected,'Storage allowed a dangling user organization'
                    assert self.document(identifier)['version']==before['version']
                    sql(self.state,"UPDATE `user` SET frame='0' WHERE id="+literal(user)+';')
                    try:
                        for path in ['/payment-order/documents?pageIndex=1&pageSize=10','/payment-order/query-all?pageIndex=1&pageSize=10','/payment-order/document/'+identifier]:
                            response=self.request('GET',path,service='payment')
                            assert response.get('code')==403,'Invalid root organization accepted: '+path+' code='+str(response.get('code'))
                        assert self.edit(identifier,self.revision(before)).get('code')==403
                        assert self.remove(identifier,before['version']).get('code')==403
                    finally:sql(self.state,'UPDATE `user` SET frame='+literal(self.state['frame_id'])+' WHERE id='+literal(user)+';')
                    assert self.document(identifier)['version']==before['version']
                finally:self.token=admin
            self.unchanged()
            return ['Actual storage integrity refuses nonexistent organization; same ordinary OAuth token loses all list/read/write access with root0 organization, restoring only QA identity permits original document read without money/document changes']
        self.case('payment.identity_live_organization_required',missing_frame)
        self.write_report()

if __name__=='__main__':PaymentIdentitySuite(read_state()).run()
