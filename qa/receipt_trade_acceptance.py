"""Actual customer receipt closes the same procurement/sale/return trade chain."""
import json,uuid,argparse
from decimal import Decimal
from trade_flow_acceptance import TradeFlowSuite
from acceptance import read_state,sql,literal,QA

class ReceiptTradeSuite(TradeFlowSuite):
    def run(self,mode='baseline'):
        def final_customer_receipt():
            flow=TradeFlowSuite(self.state);flow.run('settle')
            f=json.loads((QA/'runtime/trade-flow-fixture.json').read_text(encoding='utf-8'));self.token=flow.token;self.actor=flow.actor
            number='QARECEIPT'+uuid.uuid4().hex[:20]
            body=dict(customer=f['customer'],time='2026-11-16 14:00:00',number=number,total=151,people='',file=[],data='QA integrated final customer collection',info=[dict(account=f['account'],amount=151,settle='',data='QA customer remaining151')])
            response=self.request('POST','/fund/receipt',body,service='fund')
            assert response.get('code')==10000,'Actual customer receipt draft rejected: '+str(response)
            identifier=sql(self.state,'SELECT id FROM imy WHERE number='+literal(number)+';');assert identifier and len(identifier.splitlines())==1
            f.update(receipt=identifier,receipt_number=number)
            (QA/'runtime/receipt-trade-fixture.json').write_text(json.dumps(f),encoding='utf-8')
            assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==1171
            assert Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==151
            if mode=='prepare':return ['Actual whole trade chain including supplier settlement reaches customer receipt151 draft without moving receipt cash or receivable; stock6/cash1171/supplier0/customer151']
            if mode=='baseline':response=self.request('PATCH','/fund/receipt/audit',dict(ids=[identifier]),service='fund')
            else:
                plan=self.request('GET','/fund/receipt/settlement-preview?id='+identifier,service='fund');assert plan.get('code')==10000,str(plan)
                response=self.request('POST','/fund/receipt/settle',dict(id=identifier,status=1,version=plan['data']['version'],allocations=plan['data']['allocations']),service='fund')
            assert response.get('code')==10000,'Actual final customer receipt approval rejected: '+str(response)
            assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM imy WHERE id='+literal(identifier)+';')=='1'
            assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==1322,'Receipt approval flag changed without actual customer cash151 entering account'
            assert Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0,'Customer final receivable151 was not closed'
            assert Decimal(sql(self.state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0
            assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';'))==6
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='imy' AND `class`="+literal(identifier)+' AND direction=1 AND money=151;')=='1'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM sell WHERE id='+literal(f['sale'])+';')=='2'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM sre WHERE id='+literal(f['sales_return'])+';')=='2'
            assert Decimal(sql(self.state,"SELECT SUM(money) FROM sell_bill WHERE type='imy' AND source="+literal(identifier)+';'))==239
            assert Decimal(sql(self.state,"SELECT SUM(money) FROM sre_bill WHERE type='imy' AND source="+literal(identifier)+';'))==88
            assert Decimal(sql(self.state,'SELECT SUM(money) FROM imy_bill WHERE pid='+literal(identifier)+';'))==151
            assert sql(self.state,'SELECT COUNT(*) FROM psi_receipt_posting WHERE receipt_id='+literal(identifier)+';')=='1'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+' AND `user`='+literal(f['actor'])+';')=='2'
            return ['Actual order10→receipts6+4→sale3/receipt100→supplier return2/refund50→customer return1/refund25→supplier payment954→customer receipt151 closes both parties at0, cash1322/stock6; original sell239 minus return credit88 settled with actual journals/proof/operator']
        self.case('trade.actual_customer_final_receipt_draft' if mode=='prepare' else 'trade.actual_both_parties_final_settlement',final_customer_receipt)
        self.write_report()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['baseline','settle','prepare'],nargs='?',default='baseline')
    ReceiptTradeSuite(read_state()).run(parser.parse_args().mode)
