"""Actual scoped supplier/account chooser used by the payment workflow."""
import uuid,urllib.parse
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal

class PaymentOptionsSuite(PaymentDocumentScopeSuite):
    def options(self,kind,keyword='',document=None):
        query=dict(kind=kind,keyword=keyword)
        if document:query['document']=document
        return self.request('GET','/payment-order/options?'+urllib.parse.urlencode(query),service='payment')
    def run(self):
        def scoped():
            self.fixture();identifier=self.create_payment(self.body());_,token,role=self.role_user();admin=self.token
            foreign,account,foreign_doc=uuid.uuid4().hex,uuid.uuid4().hex,self.create_payment(self.body())
            code='QAOPT'+uuid.uuid4().hex[:14]
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA Options Other Org');"+'INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES('+','.join(literal(v) for v in [account,'QA Options Foreign',code,foreign,'2026-11-15',0,0])+');UPDATE omy SET frame='+literal(foreign)+' WHERE id='+literal(foreign_doc)+';')
            self.token=token
            try:
                assert self.options('account').get('code')==403
                with qa_resource_grants(self.state,['/payment-order/add'],[role]):
                    for kind,key in [('supplier',self.supplier),('account',self.account)]:
                        number=sql(self.state,'SELECT number FROM '+kind+' WHERE id='+literal(key)+';')
                        result=self.options(kind,number);assert result.get('code')==10000,str(result)
                        assert result['data']['rows']==[dict(id=key,name='QA Posting Supplier' if kind=='supplier' else 'QA Purchase Posting Account',number=number)]
                    assert self.options('account',code)['data']['rows']==[]
                    assert self.options('account',"' OR 1=1 -- ")['data']['rows']==[]
                    assert self.options('account',document=identifier).get('code')==403
                with qa_resource_grants(self.state,['/payment-order/modify'],[role]):
                    assert self.options('account',document=identifier).get('code')==10000
                    assert self.options('account',document=foreign_doc).get('code')==403
                assert self.options('account',document=identifier).get('code')==403
            finally:self.token=admin
            assert self.options('account',code,foreign_doc)['data']['rows']==[dict(id=account,name='QA Options Foreign',number=code)]
            assert self.options('account; DROP TABLE omy').get('code')!=10000;self.unchanged()
            return ['Actual creation/edit grants select only current or real document organization; foreign IDs and arbitrary query SQL cannot bypass scope, chooser returns names/codes/IDs without balances, admin foreign-document editing uses its actual organization']
        self.case('payment.options_actual_grants_scope_and_safe_fields',scoped)
        def cap():
            self.fixture();prefix='QAOPT'+uuid.uuid4().hex[:12];records=[]
            for index in range(51):records.append('('+','.join(literal(v) for v in [uuid.uuid4().hex,prefix+' name',prefix+str(index).zfill(2),self.state['frame_id'],'2026-11-15',0,0])+')')
            sql(self.state,'INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES'+','.join(records)+';')
            result=self.options('account',prefix);assert result.get('code')==10000
            assert len(result['data']['rows'])==50 and result['data']['hasMore'] is True
            result=self.options('account',prefix+'50');assert result['data']['hasMore'] is False and len(result['data']['rows'])==1
            self.unchanged()
            return ['Actual remote chooser caps at50 with explicit hasMore, narrowing by full code finds the51st account rather than silently hiding it']
        self.case('payment.options_search_beyond_first_page',cap)
        self.write_report()

if __name__=='__main__':PaymentOptionsSuite(read_state()).run()
