"""Procurement business/reference/cost gates. SQL references are explicitly fixtures, not lifecycle proof."""
import json
import uuid
from decimal import Decimal
from purchase_posting_extended import PurchasePostingExtended
from sale_draft_acceptance import SaleDraftSuite
from acceptance import QA,read_state,sql,literal


class PurchaseBusinessSuite(PurchasePostingExtended):
    def run(self):
        def source_order():
            self.fixture();order,line=uuid.uuid4().hex,uuid.uuid4().hex
            sql(self.state,'INSERT INTO bor(id,frame,supplier,time,number,total,actual,arrival,examine,state,`user`) VALUES('+','.join(literal(v) for v in [order,self.state['frame_id'],self.supplier,'2026-11-14','QA-BOR-'+order[:16],300,339,'2026-11-15',1,0,self.actor])+');'+
                'INSERT INTO bor_info(id,pid,goods,attr,unit,price,nums,total,tpt,handle) VALUES('+','.join(literal(v) for v in [line,order,self.goods,'','unit',100,3,300,339,0])+');')
            ids=[]
            for _ in range(2):
                body=self.body();body['purchaseNoteBuyDTO']['source']=order
                body['purchaseNoteInfoDTOS'][0].update(source=line,discount=0,tax=13,batch='',mfd=None,serial='[]')
                identifier=self.create(body);assert self.check([identifier]).get('code')==10000;ids.append(identifier)
            assert self.post([ids[0]]).get('code')==10000
            assert Decimal(sql(self.state,'SELECT handle FROM bor_info WHERE id='+literal(line)+';'))==2
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM bor WHERE id='+literal(order)+';')=='1'
            assert self.post([ids[1]]).get('code')!=10000,'Second receipt exceeded remaining order quantity'
            assert self.inventory()==2 and self.balance('supplier',self.supplier)==226 and self.status(ids[1])=='0'
            assert self.post([ids[0]],0).get('code')==10000
            assert Decimal(sql(self.state,'SELECT handle FROM bor_info WHERE id='+literal(line)+';'))==0
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM bor WHERE id='+literal(order)+';')=='0'
            return ['SQL source-order fixture; actual purchase updates linked received quantity/state, over-receipt rolls back, reversal restores quantity', 'This is not complete purchase-order lifecycle acceptance']
        self.case('purchase.posting_source_order_quantity',source_order)

        def service():
            self.fixture();sql(self.state,'UPDATE goods SET type=1 WHERE id='+literal(self.goods)+';')
            identifier=self.ready();assert self.post([identifier]).get('code')==10000
            assert self.inventory()==0 and self.ledger('room_info',identifier)==0 and self.balance('supplier',self.supplier)==226
            assert Decimal(sql(self.state,'SELECT nums FROM serve WHERE goods='+literal(self.goods)+';'))==2
            assert self.post([identifier],0).get('code')==10000
            assert Decimal(sql(self.state,'SELECT nums FROM serve WHERE goods='+literal(self.goods)+';'))==0 and self.balance('supplier',self.supplier)==0
            return ['Service purchase posts service cumulative quantity/payable without physical warehouse stock; reversal restores both']
        self.case('purchase.posting_service_no_physical_stock',service)

        def period():
            self.fixture();identifier=self.ready(50);period=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-15','2026-11-15',self.actor])+');')
                assert self.post([identifier]).get('code')!=10000;self.empty([identifier])
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            return ['Owned closed-period fixture blocks procurement posting without stock/cash/payable effects; fixture removed']
        self.case('purchase.posting_closed_period_denied',period)

        def legacy():
            self.fixture();identifier=self.ready(50)
            sql(self.state,'UPDATE buy SET examine=1 WHERE id='+literal(identifier)+';')
            assert self.post([identifier]).get('code')!=10000 and self.post([identifier],0).get('code')!=10000
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            return ['Owned legacy status-only fixture cannot be replayed or reversed into invented inventory/cash; no existing record changed']
        self.case('purchase.posting_legacy_missing_journal_denied',legacy)

        def full_payment():
            self.fixture();sql(self.state,'UPDATE account SET initial=300,balance=300 WHERE id='+literal(self.account)+';')
            identifier=self.ready(226);assert self.post([identifier]).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==74 and self.balance('supplier',self.supplier)==0
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')=='2'
            assert self.post([identifier],0).get('code')==10000
            assert self.inventory()==0 and self.balance('account',self.account)==300 and self.balance('supplier',self.supplier)==0
            return ['Fully paid purchase settles its own payable and remains reversible with original own-payment evidence']
        self.case('purchase.posting_full_payment_roundtrip',full_payment)

        def discount_cost():
            self.fixture();body=self.body()
            body['purchaseNoteBuyDTO'].update(total=180,actual=203.4)
            body['purchaseNoteInfoDTOS'][0].update(discount=10,dsc=20,total=180,tax=13,tat=23.4,tpt=203.4,batch='',mfd=None,serial='[]')
            identifier=self.create(body);assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')==10000
            assert Decimal(sql(self.state,"SELECT price FROM room_info WHERE type='buy' AND `class`="+literal(identifier)+';'))==90
            assert self.balance('supplier',self.supplier)==Decimal('203.4')
            return ['Actual discounted purchase uses net-of-discount, tax-exclusive unit stock cost, with tax-inclusive payable']
        self.case('purchase.posting_discounted_net_stock_cost',discount_cost)

        def inconsistent():
            self.fixture();body=self.body();body['purchaseNoteBuyDTO'].update(actual=999)
            body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
            identifier=self.create(body);assert self.check([identifier]).get('code')==10000
            assert self.post([identifier]).get('code')!=10000;self.empty([identifier])
            return ['Inconsistent saved header/detail money is rejected at posting instead of entering inventory/payables']
        self.case('purchase.posting_inconsistent_money_denied',inconsistent)

        def costing():
            assert not sql(self.state,"SELECT id FROM sys WHERE name='fun';"),'Use QA without an existing cost configuration'
            setting=uuid.uuid4().hex
            raw=sql(self.state,"SELECT JSON_OBJECT('name',TRIGGER_NAME,'event',EVENT_MANIPULATION,'body',ACTION_STATEMENT) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND TRIGGER_NAME IN ('psi_guard_fun_update','psi_guard_fun_delete');")
            guards=[json.loads(line) for line in raw.splitlines() if line];assert len(guards)==2
            (QA/'runtime/cost-setting-guard-recovery.json').write_text(json.dumps(guards),encoding='utf-8')
            try:
                for guard in guards:sql(self.state,'DROP TRIGGER `'+guard['name']+'`;')
                for mode,expected in [('base',300),('ma',60),('fifo',50)]:
                    sql(self.state,'DELETE FROM sys WHERE id='+literal(setting)+';INSERT INTO sys(id,name,info) VALUES('+','.join(literal(v) for v in [setting,'fun',json.dumps(dict(valuation=mode,rule='def',branch=True))])+');')
                    self.fixture()
                    for price in [10,30]:
                        body=self.body();body['purchaseNoteBuyDTO'].update(time='2026-11-15 10:00:00',total=price*2,actual=price*2)
                        body['purchaseNoteInfoDTOS'][0].update(price=price,discount=0,dsc=0,total=price*2,tax=0,tat=0,tpt=price*2,batch='',mfd=None,serial='[]')
                        identifier=self.create(body);assert self.check([identifier]).get('code')==10000
                        assert self.post([identifier]).get('code')==10000
                    sale=SaleDraftSuite(self.state);sale.goods=self.goods;sale.warehouse=self.warehouse
                    body=sale.body();body['time']='2026-11-15 11:00:00';body['items'][0].update(nums=3,discount=1)
                    sold=sale.create(body);sale.sale('POST','/sale/form/check?check=true',[sold]);sale.sale('POST','/sale/form/examine?examine=true',[sold])
                    assert sql(self.state,"SELECT DATE_FORMAT(time,'%H:%i:%s') FROM sell WHERE id="+literal(sold)+';')=='11:00:00','Actual sales timestamp was truncated before cost replay'
                    assert self.inventory()==1
                    assert Decimal(sql(self.state,"SELECT bct FROM summary WHERE type='sell' AND `class`="+literal(sold)+';'))==expected,'Purchase-to-sale cost incorrect for '+mode
                    if mode in ('ma','fifo'):
                        self.fixture()
                        sql(self.state,"UPDATE goods SET unit='-1',units="+literal(json.dumps([dict(source='unit',name='box',nums=3)]))+' WHERE id='+literal(self.goods)+';')
                        body=self.body();body['purchaseNoteBuyDTO'].update(time='2026-11-15 10:00:00',total=100,actual=100)
                        body['purchaseNoteInfoDTOS'][0].update(unit='box',price=100,nums=1,discount=0,dsc=0,total=100,tax=0,tat=0,tpt=100,batch='',mfd=None,serial='[]')
                        receipt=self.create(body);assert self.check([receipt]).get('code')==10000
                        assert self.post([receipt]).get('code')==10000
                        assert Decimal(sql(self.state,"SELECT bct FROM summary WHERE type='buy' AND `class`="+literal(receipt)+';'))==100,'Fractional base-unit receipt lost its original net value'
                        sale=SaleDraftSuite(self.state);sale.goods=self.goods;sale.warehouse=self.warehouse
                        total_cost=Decimal(0)
                        for quantity,hour in [(1,11),(2,12)]:
                            body=sale.body();body['time']='2026-11-15 '+str(hour)+':00:00';body['items'][0].update(nums=quantity,discount=1)
                            sold=sale.create(body);sale.sale('POST','/sale/form/check?check=true',[sold]);sale.sale('POST','/sale/form/examine?examine=true',[sold])
                            total_cost+=Decimal(sql(self.state,"SELECT bct FROM summary WHERE type='sell' AND `class`="+literal(sold)+';'))
                        assert total_cost==100 and self.inventory()==0,'Partial issues did not conserve the original receipt value for '+mode
            finally:
                try:sql(self.state,'DELETE FROM sys WHERE id='+literal(setting)+';')
                finally:
                    for guard in guards:sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+guard['name']+'` BEFORE '+guard['event']+' ON sys FOR EACH ROW '+guard['body']+'$$\nDELIMITER ;\n')
            return ['Two actual same-time purchase receipts then actual sale verify base, moving-average and FIFO costs; sequence preserves first receipt', 'Only isolated SQL cost configuration/guards changed and restored; system-parameter editing and all cost/rule combinations remain pending']
        self.case('purchase.posting_actual_purchase_to_sale_cost_modes',costing)
        self.write_report()


if __name__=='__main__':PurchaseBusinessSuite(read_state()).run()
