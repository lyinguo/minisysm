"""One real business chain across order, partial receipts, sales, returns and settlement.

Opening account balance and master records are explicit private QA fixtures. Every
business document and approval below uses actual HTTP, with independent SQL checks.
"""
import json,uuid,argparse
from decimal import Decimal
from booking_receive_acceptance import ReceiveSuite
from sale_return_posting_acceptance import SaleReturnPostingSuite
from purchase_return_posting_acceptance import PurchaseReturnPostingSuite
from acceptance import read_state,sql,literal,QA


class TradeFlowSuite(ReceiveSuite):
    def run(self,stage='settle'):
        def integrated_chain():
            self.fixture();self.flow=[]
            sql(self.state,'UPDATE account SET initial=2000,balance=2000 WHERE id='+literal(self.account)+';')
            def checkpoint(stage,stock,cash,payable):
                assert self.inventory()==Decimal(str(stock)),stage+' inventory mismatch'
                assert self.balance('account',self.account)==Decimal(str(cash)),stage+' cash mismatch'
                assert self.balance('supplier',self.supplier)==Decimal(str(payable)),stage+' payable mismatch'
                self.flow.append(dict(stage=stage,stock=str(stock),cash=str(cash),supplier_payable=str(payable)))
                (QA/'runtime/trade-flow-checkpoints.json').write_text(json.dumps(self.flow,ensure_ascii=False,indent=2),encoding='utf-8')
            body=self.order_body();body['purchaseOrderInfoDTOList'][0]['nums']=10
            self.source=self.create_order(body)
            self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+' ORDER BY id;').splitlines()
            assert self.audit([self.source]).get('code')==10000
            checkpoint('approved order10',0,2000,0)
            receipts=[]
            for quantity,stock,payable in [(6,6,678),(4,10,1130)]:
                receipt=self.create_receipt(self.receive_body(quantity));receipts.append(receipt)
                assert self.check([receipt]).get('code')==10000 and self.post([receipt]).get('code')==10000
                checkpoint('actual partial receipt'+str(quantity),stock,2000,payable)
                assert Decimal(sql(self.state,'SELECT handle FROM bor_info WHERE pid='+literal(self.source)+';'))==stock
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM bor WHERE id='+literal(self.source)+';')=='2'
            sale=SaleReturnPostingSuite(self.state)
            for name in ['goods','warehouse','account','actor','token']:setattr(sale,name,getattr(self,name))
            body=sale.body();body.update(time='2026-11-16 10:00:00',money=100,account=self.account)
            body['items'][0].update(nums=3,discount=1,tax=.13)
            sold=sale.create(body)
            assert sale.request('POST','/sale/form/check?check=true',[sold],service='sale').get('code')==10000
            assert sale.post([sold]).get('code')==10000
            checkpoint('sold3 received100',7,2100,1130)
            assert sale.balance('customer',sale.customer)==239
            purchase=PurchaseReturnPostingSuite(self.state)
            for name in ['goods','warehouse','supplier','account','actor','token']:setattr(purchase,name,getattr(self,name))
            body=purchase.body_return(receipts[0],2);body.update(money=50,account=self.account)
            returned=purchase.add_return(body);assert returned.get('code')==10000;bre=returned['data']
            assert purchase.review([bre],versions=purchase.versions([bre])).get('code')==10000
            assert purchase.post_return([bre],versions=purchase.versions([bre])).get('code')==10000
            checkpoint('supplier return2 refund50',5,2150,954)
            body=sale.return_body(sold,1);body.update(money=25,account=self.account)
            returned=sale.add_return(body);assert returned.get('code')==10000;sre=returned['data']
            assert sale.review([sre],versions=sale.versions([sre])).get('code')==10000
            assert sale.post_return([sre],versions=sale.versions([sre])).get('code')==10000
            checkpoint('customer return1 refund25',6,2125,954)
            assert sale.balance('customer',sale.customer)==151
            # Gross received quantity stays10; purchase return2 is a separate credit,
            # not an implicit instruction to buy replacement stock from the supplier.
            assert Decimal(sql(self.state,'SELECT handle FROM bor_info WHERE pid='+literal(self.source)+';'))==10
            payment=dict(supplier=self.supplier,time='2026-11-16',number='QAFLOWPAY'+uuid.uuid4().hex[:20],people='',file='[]',data='QA complete trade settlement',infoList=[dict(account=self.account,money=954,settle='',data1='QA supplier net settlement')])
            result=self.request('POST','/payment-order/add',payment,service='payment');assert result.get('code')==10000,'Actual net supplier-payment draft failed'
            voucher=result['data']
            fixture=dict(database=self.state['database'],order=self.source,receipts=receipts,sale=sold,purchase_return=bre,sales_return=sre,payment=voucher,supplier=self.supplier,customer=sale.customer,account=self.account,goods=self.goods,warehouse=self.warehouse,actor=self.actor)
            (QA/'runtime/trade-flow-fixture.json').write_text(json.dumps(fixture),encoding='utf-8')
            if stage=='prepare':return ['Actual order10→partial receipts6+4→sale3→supplier return2→customer return1 reaches real payment954 draft; stock6/cash2125/payable954/customer151; payment posting and final settlement explicitly not yet accepted']
            plan=self.request('GET','/payment-order/settlement-preview?id='+voucher,service='payment')
            assert plan.get('code')==10000,'Actual original-document settlement preparation failed'
            result=self.request('POST','/payment-order/settle',dict(id=voucher,status=1,version=plan['data']['version'],allocations=plan['data']['allocations']),service='payment')
            assert result.get('code')==10000,'Actual net supplier-payment posting failed'
            checkpoint('supplier payment954',6,1171,0)
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(voucher)+' AND direction=0 AND money=954;')=='1','Supplier balance became zero without actual payment journal'
            assert sql(self.state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(voucher)+';')!='0','Payment has no allocation to original purchase/return documents'
            assert all(sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(i)+';')=='2' for i in receipts),'Supplier paid but original purchases remain unsettled'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM bre WHERE id='+literal(bre)+';')=='2','Return credit was not fully applied to original purchases'
            assert Decimal(sql(self.state,'SELECT SUM(money) FROM omy_bill WHERE pid='+literal(voucher)+';'))==954
            assert Decimal(sql(self.state,"SELECT SUM(money) FROM buy_bill WHERE type='omy' AND source="+literal(voucher)+';'))==1130
            assert Decimal(sql(self.state,"SELECT SUM(money) FROM bre_bill WHERE type='omy' AND source="+literal(voucher)+';'))==176
            assert sql(self.state,'SELECT COUNT(*) FROM psi_payment_posting WHERE payment_id='+literal(voucher)+';')=='1'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(voucher)+' AND `user`='+literal(self.actor)+';')=='2'
            return ['Actual order10 → receipts6+4 → sale3/receipt100 → supplier return2/refund50 → customer return1/refund25 → supplier net payment954; stock6, cash1171, payable0 and all original settlement journals/statuses agree; customer remaining151 still requires receipt gate']
        self.case('trade.actual_partial_receipts_sales_returns_'+('payment_draft' if stage=='prepare' else 'supplier_settlement'),integrated_chain)
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['settle','prepare'],nargs='?',default='settle')
    TradeFlowSuite(read_state()).run(parser.parse_args().stage)
