"""Real complete trade settlement, atomic original-document allocations and reversal."""
import uuid,copy,concurrent.futures,argparse
from decimal import Decimal
from payment_settlement_acceptance import SettlementPreviewSuite
from trade_flow_acceptance import TradeFlowSuite
from acceptance import read_state,sql,literal,QA
import json

class PaymentPostingSuite(SettlementPreviewSuite):
    def command(self,identifier):
        response=self.preview(identifier);assert response.get('code')==10000
        return dict(id=identifier,status=1,version=response['data']['version'],allocations=response['data']['allocations'])
    def post_payment(self,body):return self.request('POST','/payment-order/settle',body,service='payment')
    def document(self,identifier):
        response=self.request('GET','/payment-order/settlement-document/'+identifier,service='payment');assert response.get('code')==10000;return response['data']
    def balances(self,cash,payable):assert self.inventory()==6 and self.balance('account',self.account)==cash and self.balance('supplier',self.supplier)==payable
    def run(self):
        def complete():
            flow=TradeFlowSuite(self.state);flow.run('settle')
            return ['Same actual order→partial receipts→sales→both returns→payment chain confirms cash954 journal, purchase allocations1130, return offset176, both original purchases and return fully settled, proof and actual operator history; customer receipt151 remains separate pending gate']
        self.case('payment.posting_complete_trade_original_settlement',complete)
        def roundtrip():
            f=self.prepare_chain();command=self.command(f['payment']);assert self.post_payment(command).get('data')==1
            self.balances(1171,0);posted=self.document(f['payment']);assert posted['header']['examine']==1 and posted['header']['nucleus']==2
            assert self.post_payment(dict(id=f['payment'],version=posted['version'],status=1)).get('data')==0
            assert self.post_payment(dict(id=f['payment'],version=command['version'],status=0)).get('code')!=10000
            assert self.post_payment(dict(id=f['payment'],version=posted['version'],status=0)).get('data')==1
            self.balances(2125,954);draft=self.document(f['payment']);assert draft['header']['examine']==0 and draft['header']['nucleus']==0 and draft['version']!=command['version']
            for source in f['receipts']:assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(source)+';')=='0'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM bre WHERE id='+literal(f['purchase_return'])+';')=='1'
            for table,where in [('account_info',"type='omy' AND `class`="),('omy_bill','pid='),('buy_bill',"type='omy' AND source="),('bre_bill',"type='omy' AND source="),('psi_payment_posting','payment_id=')]:assert sql(self.state,'SELECT COUNT(*) FROM '+table+' WHERE '+where+literal(f['payment'])+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(f['payment'])+';')=='3'
            return ['Verified forward cash/original-source effects before reverse; fresh same-target retry idempotent, stale reverse refused; reverse restores cash, payable, original buy0/return1 settlement and removes active evidence while preserving3 histories and changing version']
        self.case('payment.posting_actual_roundtrip_and_versions',roundtrip)
        def concurrent_commands():
            f=self.prepare_chain();command=self.command(f['payment'])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.post_payment(command),range(2)))
            assert sum(r.get('code')==10000 for r in results)==1;self.balances(1171,0)
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(f['payment'])+';')=='1'
            return ['Two actual concurrent commands with identical frozen payment/source versions produce one debit and one set of source allocations']
        self.case('payment.posting_concurrent_single_effect',concurrent_commands)
        def source_storage_fault():
            f=self.prepare_chain();command=self.command(f['payment']);trigger='qa_omy_credit_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bre_bill FOR EACH ROW BEGIN IF NEW.type='omy' AND NEW.source="+literal(f['payment'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return offset failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_payment(command).get('code')!=10000;self.balances(2125,954)
                assert self.document(f['payment'])['version']==command['version']
                for source in f['receipts']:assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(source)+';')=='0'
                assert sql(self.state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(f['payment'])+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_payment(command).get('data')==1;self.balances(1171,0)
            return ['Actual late return-offset MySQL storage failure rolls back prior account debit, supplier reduction, purchase bills/statuses and payment version; exact original reviewed command retries successfully']
        self.case('payment.posting_original_credit_failure_atomic_retry',source_storage_fault)
        def protocol():
            f=self.prepare_chain();command=self.command(f['payment'])
            invalid=[]
            for key,value in [('version',None),('status',2),('allocations',[]),('allocations',command['allocations']*2)]:
                body=copy.deepcopy(command);body[key]=value;invalid.append(body)
            body=copy.deepcopy(command);body['allocations'][0]['version']='0'*64;invalid.append(body)
            body=copy.deepcopy(command);body['allocations'][0]['money']=-1;invalid.append(body)
            body=copy.deepcopy(command);body['allocations'][0]['money']=1;invalid.append(body)
            for body in invalid:assert self.post_payment(body).get('code')!=10000
            assert self.request('PUT','/payment-order/modify-examine-status',[f['payment']],service='payment').get('code')!=10000
            self.balances(2125,954);assert self.document(f['payment'])['version']==command['version']
            assert self.post_payment(command).get('data')==1
            return ['Actual missing/current-source version, invalid targets, duplicate/empty allocations, wrong signs and unbalanced amounts refuse atomically; old toggle cannot bypass protocol, exact valid reviewed plan succeeds']
        self.case('payment.posting_complete_reviewed_allocation_protocol',protocol)
        self.write_report()

    def residual_credit(self):
        def cannot_strand_offset():
            f=self.prepare_chain();reviewed=self.command(f['payment']);cash_only=copy.deepcopy(reviewed);left=Decimal('954');allocations=[]
            for row in reviewed['allocations']:
                if row['type']!='buy':continue
                money=min(Decimal(str(row['remaining'])),left)
                if money>0:
                    item=dict(row);item['money']=float(money);allocations.append(item);left-=money
            assert left==0;cash_only['allocations']=allocations
            result=self.post_payment(cash_only)
            if result.get('code')==10000:
                self.balances(1171,0)
                unpaid=Decimal(sql(self.state,'SELECT SUM(h.actual-COALESCE((SELECT SUM(money) FROM buy_bill WHERE pid=h.id),0)) FROM buy h WHERE h.id IN ('+','.join(literal(i) for i in f['receipts'])+');'))
                credit=Decimal(sql(self.state,'SELECT actual-COALESCE((SELECT SUM(money) FROM bre_bill WHERE pid=h.id),0) FROM bre h WHERE id='+literal(f['purchase_return'])+';'))
                assert unpaid==credit==176
                raise AssertionError('Payment cleared supplier balance0 while leaving original invoices176 and return credit176 unsettled with no cash remaining to close them')
            self.balances(2125,954);assert self.document(f['payment'])['version']==reviewed['version']
            assert self.post_payment(reviewed).get('data')==1;self.balances(1171,0)
            assert all(sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(i)+';')=='2' for i in f['receipts'])
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM bre WHERE id='+literal(f['purchase_return'])+';')=='2'
            return ['Actual final supplier payment cannot omit return credits and strand equal unpaid invoices/credit; refusal preserves input versions and funds, explicitly reviewed netting plan closes every original source']
        self.case('payment.posting_final_payment_cannot_strand_return_credit',cannot_strand_offset)
        self.write_report()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','residual'],nargs='?',default='run')
    suite=PaymentPostingSuite(read_state())
    if parser.parse_args().action=='residual':suite.residual_credit()
    else:suite.run()
