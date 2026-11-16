"""Cross-service return costing: real inbound -> sale -> return -> later purchase -> both reversals."""
import json
import uuid
import argparse
from contextlib import contextmanager
from decimal import Decimal
from acceptance import QA, read_state, sql, literal
from sale_return_posting_acceptance import SaleReturnPostingSuite
from purchase_posting_acceptance import PurchasePostingSuite


@contextmanager
def owned_cost_mode(state, mode):
    assert not sql(state, "SELECT id FROM sys WHERE name='fun';"), 'Cost-mode acceptance requires no existing QA function setting'
    raw = sql(state, "SELECT JSON_OBJECT('name',TRIGGER_NAME,'event',EVENT_MANIPULATION,'body',ACTION_STATEMENT) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND TRIGGER_NAME IN ('psi_guard_fun_update','psi_guard_fun_delete');")
    guards = [json.loads(line) for line in raw.splitlines() if line]
    assert len(guards) == 2
    (QA/'runtime/sale-return-cost-guard-recovery.json').write_text(json.dumps(guards), encoding='utf-8')
    setting = uuid.uuid4().hex
    try:
        for guard in guards: sql(state, 'DROP TRIGGER `'+guard['name']+'`;')
        sql(state, 'INSERT INTO sys(id,name,info) VALUES('+','.join(literal(v) for v in [setting,'fun',json.dumps(dict(valuation=mode,rule='def',branch=True))])+');')
        yield
    finally:
        try: sql(state, 'DELETE FROM sys WHERE id='+literal(setting)+';')
        finally:
            for guard in guards:
                sql(state, 'DELIMITER $$\nCREATE TRIGGER `'+guard['name']+'` BEFORE '+guard['event']+' ON sys FOR EACH ROW '+guard['body']+'$$\nDELIMITER ;\n')


class ReturnCostSuite(SaleReturnPostingSuite):
    def consumed(self):
        def fifo_consumed_layer():
            with owned_cost_mode(self.state, 'fifo'):
                self.fixture(stock=0)
                self.audit(self.store('POST','/otherin/add',self.inbound(1)),1)
                body=self.body();body['items'][0].update(nums=1,discount=1)
                source=self.post_source(body)
                identifier=self.check_from_source(source,1)
                assert self.post_return([identifier],versions=self.versions([identifier])).get('code')==10000
                following=self.body();following['time']='2026-11-16 13:00:00';following['items'][0].update(nums=1,discount=1)
                later=self.post_source(following);assert self.inventory()==0
                restock=self.inbound(1);restock['time']='2026-11-16 14:00:00'
                self.audit(self.store('POST','/otherin/add',restock),1)
                assert self.inventory()==1
                assert int(sql(self.state,"SELECT COUNT(*) FROM fifo WHERE `in` IN (SELECT id FROM summary WHERE type='sre' AND `class`="+literal(identifier)+');'))>0
                frozen=self.versions([identifier]);history=self.history(identifier)
                assert self.post_return([identifier],status=0,versions=frozen).get('code')!=10000
                assert self.inventory()==1 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==113
                assert self.versions([identifier])==frozen and self.history(identifier)==history
                assert self.post([later],False).get('code')==10000
                assert self.post_return([identifier],status=0,versions=self.versions([identifier])).get('code')==10000
                assert self.inventory()==1 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==113
                assert sql(self.state,'SELECT COUNT(*) FROM fifo WHERE `out` NOT IN (SELECT id FROM summary) OR `in` NOT IN (SELECT id FROM summary);')=='0'
                return ['Actual FIFO returned layer is consumed by later sale; actual restock makes physical stock sufficient but cannot bypass consumed-layer protection; reversing real dependent sale then allows return reversal without orphan cost links']
        self.case('sale.return_cost_consumed_fifo_layer_protection',fifo_consumed_layer)
        self.write_report()

    def run(self):
        for mode, source_value, return_value in [('base', '8', '2'), ('ma', '17.6', '4.4'), ('fifo', '14', '3.5')]:
            def scenario(mode=mode, source_value=source_value, return_value=return_value):
                with owned_cost_mode(self.state, mode):
                    self.fixture(stock=0)
                    for quantity, price in [(3, 2), (2, 8)]:
                        body = self.inbound(quantity); body['total'] = quantity*price
                        body['otherInListDetailInfoDTOList'][0].update(price=price,total=quantity*price)
                        self.audit(self.store('POST', '/otherin/add', body), 1)
                    body = self.body(); body.update(money=50,account=self.account); body['items'][0].update(nums=4,discount=1)
                    source = self.post_source(body)
                    assert self.inventory() == 1
                    assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='sell' AND `class`="+literal(source)+';')) == Decimal(source_value)
                    identifier = self.check_from_source(source, 1)
                    assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
                    def value(): return Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='sre' AND `class`="+literal(identifier)+';'))
                    assert self.inventory() == 2 and value() == Decimal(return_value), mode+' source-return cost mismatch'
                    procurement = PurchasePostingSuite(self.state)
                    procurement.goods=self.goods; procurement.warehouse=self.warehouse; procurement.account=self.account
                    purchase = procurement.body(); purchase['purchaseNoteBuyDTO'].update(time='2026-11-17',total=7,actual=7,money=0,file='[]')
                    purchase['purchaseNoteInfoDTOS'][0].update(price=7,nums=1,discount=0,dsc=0,total=7,tax=0,tat=0,tpt=7,batch='',mfd=None,serial='[]')
                    purchased = procurement.create(purchase)
                    assert procurement.check([purchased]).get('code') == 10000
                    assert procurement.post([purchased]).get('code') == 10000
                    assert self.inventory() == 3 and value() == Decimal(return_value), mode+' later purchase changed frozen return cost'
                    assert procurement.post([purchased],0).get('code') == 10000
                    assert self.inventory() == 2 and value() == Decimal(return_value), mode+' purchase reversal changed frozen return cost'
                    assert self.post_return([identifier],status=0,versions=self.versions([identifier])).get('code') == 10000
                    assert self.inventory() == 1 and self.balance('account',self.account)==150 and self.balance('customer',self.customer)==402
                    assert sql(self.state,'SELECT COUNT(*) FROM fifo WHERE `out` NOT IN (SELECT id FROM summary) OR `in` NOT IN (SELECT id FROM summary);')=='0'
                    return ['Actual differently priced inbound -> sale -> original-cost return -> later purchase -> purchase reverse -> return reverse; '+mode+' return value remains '+return_value+' with no orphan FIFO rows']
            self.case('sale.return_cost_cross_purchase_'+mode,scenario)
        self.write_report()


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['modes','consumed'],nargs='?',default='modes')
    suite=ReturnCostSuite(read_state())
    if parser.parse_args().action=='consumed':suite.consumed()
    else:suite.run()
