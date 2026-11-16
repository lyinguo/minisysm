"""Actual partial-payment continuation and ordinary finance operator posting."""
import uuid
from payment_settlement_posting_acceptance import PaymentPostingSuite
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal

class PaymentCompetingSuite(PaymentPostingSuite):
    def run(self):
        def partial():
            f=self.prepare_chain();old=self.command(f['payment'])
            body=dict(supplier=self.supplier,time='2026-11-16',number='QAPART'+uuid.uuid4().hex[:23],people='',file='[]',data='QA partial supplier payment',infoList=[dict(account=self.account,money=500,settle='',data1='QA first partial payment')])
            second=self.create_payment(body);first=self.command(second)
            assert self.post_payment(first).get('data')==1;self.balances(1625,454)
            assert self.post_payment(old).get('code')!=10000;self.balances(1625,454)
            document=self.document(f['payment']);line=document['items'][0]
            revised=dict(version=document['version'],details=[dict(id=line['id'],pid=f['payment'],account=line['account'],money=454,settle='',data1='QA corrected remaining net payment')])
            response=self.request('PUT','/payment-order/document/'+f['payment'],revised,service='payment');assert response.get('code')==10000,str(response)
            rest=self.command(f['payment']);assert sum(row['money'] for row in rest['allocations'])==454
            assert self.post_payment(rest).get('data')==1;self.balances(1171,0)
            assert all(sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(source)+';')=='2' for source in f['receipts'])
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM bre WHERE id='+literal(f['purchase_return'])+';')=='2'
            assert self.post_payment(dict(id=second,status=0,version=self.document(second)['version'])).get('data')==1;self.balances(1671,500)
            assert self.document(f['payment'])['header']['examine']==1
            assert self.post_payment(dict(id=f['payment'],status=0,version=self.document(f['payment'])['version'])).get('data')==1;self.balances(2125,954)
            return ['Actual competing500 payment consumes part of same source invoices/credits; old954 plan refuses with unchanged funds, correcting same draft to454 finishes every source; reversing500 while454 stays posted preserves its effects, then reversing454 restores complete original balances']
        self.case('payment.competing_partial_then_correct_remaining_and_reverse',partial)

        def ordinary():
            f=self.prepare_chain();command=self.command(f['payment']);helper=PaymentDocumentScopeSuite(self.state);user,token,role=helper.role_user();admin=self.token;self.token=token
            try:
                assert self.post_payment(command).get('code')==403
                with qa_resource_grants(self.state,['/payment-order/modify-examine-status','/payment-order/query-by-id'],[role]):
                    assert self.post_payment(command).get('data')==1;self.balances(1171,0)
                    assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(f['payment'])+' AND `user`='+literal(user)+';')=='1'
                    reverse=dict(id=f['payment'],status=0,version=self.document(f['payment'])['version'])
                assert self.post_payment(reverse).get('code')==403;self.balances(1171,0)
                with qa_resource_grants(self.state,['/payment-order/modify-examine-status'],[role]):
                    assert self.post_payment(reverse).get('data')==1;self.balances(2125,954)
                assert self.post_payment(command).get('code')==403
            finally:self.token=admin
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(f['payment'])+' AND `user`='+literal(user)+';')=='2'
            return ['Actual ordinary signed finance operator can post/reverse same-organization actual payment only with live grants; immediate revoke prevents reversal until regranted, actual operator persisted for both actions and full balances restored']
        self.case('payment.posting_actual_ordinary_operator_live_grants',ordinary)
        self.write_report()

if __name__=='__main__':PaymentCompetingSuite(read_state()).run()
