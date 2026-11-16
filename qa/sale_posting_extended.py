"""Additional real sales posting gates; fixtures never leave the dedicated QA database."""
import json
import uuid
from decimal import Decimal
from sale_posting_acceptance import SalePostingSuite
from acceptance import QA, read_state, sql, literal


class ExtendedPostingSuite(SalePostingSuite):
    def source_state_cases(self):
        def linked(state=0,approved=1):
            self.fixture();order,line=uuid.uuid4().hex,uuid.uuid4().hex
            sql(self.state,'INSERT INTO sor(id,frame,customer,time,number,total,actual,arrival,examine,state,`user`) VALUES('+','.join(literal(v) for v in [order,self.state['frame_id'],self.customer,'2026-11-14','QA-SOR-'+order[:16],500,565,'2026-11-15',approved,state,self.actor])+');'+'INSERT INTO sor_info(id,pid,goods,attr,unit,price,nums,total,tpt,handle) VALUES('+','.join(literal(v) for v in [line,order,self.goods,'','unit',100,5,500,565,0])+');')
            body=self.body();body.update(source=order,money=50,account=self.account);body['items'][0].update(source=line,discount=1)
            return order,line,self.save_checked(body)
        def closed():
            order,line,id=linked(3)
            assert self.post([id]).get('code')!=10000,'Closed source order incorrectly allowed sales posting'
            self.assert_empty_posting(id,10)
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='3'
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==0
            sql(self.state,'UPDATE sor SET state=0 WHERE id='+literal(order)+';')
            assert self.post([id]).get('code')==10000 and self.inventory()==8
            assert self.balance('account',self.account)==150 and self.balance('customer',self.customer)==176
            assert self.post([id],False).get('code')==10000;self.assert_empty_posting(id,10)
            return ['SQL closed source state3 blocks actual sale posting and all stock/cash/receivable/handled changes; reopening only owned fixture permits original draft posting and reversal']
        self.case('sale.source_closed_order_atomic',closed)
        def approval():
            order,line,id=linked(0,2)
            assert self.post([id]).get('code')!=10000,'Invalid approval2 was treated as approved boolean1'
            self.assert_empty_posting(id,10)
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==0
            return ['Owned malformed approval2 cannot masquerade as approved1; source quantity and all posting effects unchanged']
        self.case('sale.source_nonbinary_approval_denied',approval)
        def corrupt():
            order,line,id=linked(4)
            assert self.post([id]).get('code')!=10000,'Unknown execution state accepted'
            self.assert_empty_posting(id,10)
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='4'
            return ['Unknown source execution enum is rejected instead of silently normalized while posting']
        self.case('sale.source_unknown_state_denied',corrupt)
        def reverse_closed():
            order,line,id=linked()
            assert self.post([id]).get('code')==10000
            sql(self.state,'UPDATE sor SET state=3 WHERE id='+literal(order)+';')
            assert self.post([id],False).get('code')!=10000,'Reversal silently reopened closed order'
            assert self.inventory()==8 and self.balance('account',self.account)==150 and self.balance('customer',self.customer)==176
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='3'
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==2
            assert self.ledger_count('room_info',id)==self.ledger_count('account_info',id)==1
            sql(self.state,'UPDATE sor SET state=1 WHERE id='+literal(order)+';')
            assert self.post([id],False).get('code')==10000;self.assert_empty_posting(id,10)
            return ['Actual posted sale cannot silently reopen a closed source on reversal; original movements remain intact; reopening owned SQL fixture permits reversal']
        self.case('sale.source_closed_reverse_preserves_posting',reverse_closed)
        def full_quantity():
            order,line,first=linked()
            assert self.post([first]).get('code')==10000
            body=self.body();body.update(source=order);body['items'][0].update(source=line,nums=3,discount=1)
            second=self.save_checked(body);assert self.post([second]).get('code')==10000
            assert self.inventory()==5 and self.balance('customer',self.customer)==515 and self.balance('account',self.account)==150
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='2'
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==5
            body=self.body();body.update(source=order);body['items'][0].update(source=line,nums=1,discount=1)
            excess=self.save_checked(body);assert self.post([excess]).get('code')!=10000
            assert self.inventory()==5 and self.balance('customer',self.customer)==515 and self.ledger_count('room_info',excess)==0
            assert self.post([second],False).get('code')==10000
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='1'
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==2
            assert self.post([first],False).get('code')==10000;self.assert_empty_posting(first,10)
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';')=='0'
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';'))==0
            return ['Actual two shipments2+3 advance source0->1->2, extra shipment rejected atomically; reversals restore2->1->0 and original stock/cash/receivable']
        self.case('sale.source_partial_full_quantity_roundtrip',full_quantity)
    def save_checked(self, body):
        identifier = self.create(body)
        self.sale('POST', '/sale/form/check?check=true', [identifier])
        return identifier

    def assert_empty_posting(self, identifier, stock):
        assert self.inventory() == stock
        assert self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
        assert self.scalar('SELECT CAST(examine AS SIGNED) FROM sell WHERE id='+literal(identifier)+';') == '0'
        for table in ('room_info', 'summary', 'account_info'):
            assert self.ledger_count(table, identifier) == 0
        assert self.scalar('SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id='+literal(identifier)+';') == '0'

    def run(self):
        self.source_state_cases()
        def retry():
            self.fixture()
            identifier = self.draft(received=50)
            assert self.post([identifier]).get('code') == 10000
            assert self.post([identifier]).get('code') == 10000
            assert self.inventory() == 8 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176
            assert self.ledger_count('room_info', identifier) == self.ledger_count('account_info', identifier) == 1
            assert self.post([identifier], False).get('code') == 10000
            assert self.post([identifier], False).get('code') == 10000
            self.assert_empty_posting(identifier, 10)
            return ['Repeated audit/reverse requests have no duplicate stock, balance or movement effects']
        self.case('sale.posting_retry_has_no_duplicate_effects', retry)

        def full_receipt():
            self.fixture()
            identifier = self.draft(received=226)
            assert self.post([identifier]).get('code') == 10000
            assert self.balance('account', self.account) == 326 and self.balance('customer', self.customer) == 0
            assert self.scalar('SELECT CAST(nucleus AS SIGNED) FROM sell WHERE id='+literal(identifier)+';') == '2'
            assert self.post([identifier], False).get('code') == 10000
            self.assert_empty_posting(identifier, 10)
            return ['Full own receipt settles the sale and remains reversible without external settlement references']
        self.case('sale.posting_full_receipt_and_reverse', full_receipt)

        def rollback():
            self.fixture()
            identifier = self.draft(received=50)
            trigger = 'qa_sale_cash_' + uuid.uuid4().hex[:12]
            try:
                sql(self.state, 'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON account_info FOR EACH ROW BEGIN IF NEW.class="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA cash journal failure'; END IF; END;$$\nDELIMITER ;\n")
                assert self.post([identifier]).get('code') != 10000, 'Injected cash journal failure did not reject audit'
                self.assert_empty_posting(identifier, 10)
                assert self.scalar("SELECT COUNT(*) FROM record WHERE type='sell' AND source="+literal(identifier)+" AND info="+literal('审核销售单')+';') == '0'
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post([identifier]).get('code') == 10000 and self.inventory() == 8
            return ['Real MySQL trigger fails after stock/report work and account update; transaction rolls back all effects; retry succeeds']
        self.case('sale.posting_injected_cash_failure_rolls_back_stock', rollback)

        def batch_serial():
            self.fixture(stock=0)
            sql(self.state, 'UPDATE goods SET batch=1,serial=1 WHERE id='+literal(self.goods)+';')
            incoming = self.inbound(3)
            incoming['otherInListDetailInfoDTOList'][0].update(batch='QA-BATCH', mfd='2026-11-01', serial=json.dumps(['QA-SN1','QA-SN2','QA-SN3']))
            entry = self.store('POST', '/otherin/add', incoming)
            self.audit(entry, 1)
            body = self.body()
            body['items'][0].update(batch='QA-BATCH', mfd='2026-11-01', serial=json.dumps(['QA-SN1','QA-SN2']), discount=1)
            identifier = self.save_checked(body)
            assert self.post([identifier]).get('code') == 10000
            assert self.inventory() == 1
            assert Decimal(self.scalar('SELECT nums FROM batch WHERE goods='+literal(self.goods)+';')) == 1
            assert self.scalar('SELECT SUM(CAST(state AS SIGNED)) FROM serial WHERE goods='+literal(self.goods)+';') == '2'
            assert self.post([identifier], False).get('code') == 10000
            assert self.inventory() == 3 and Decimal(self.scalar('SELECT nums FROM batch WHERE goods='+literal(self.goods)+';')) == 3
            assert self.scalar('SELECT SUM(CAST(state AS SIGNED)) FROM serial WHERE goods='+literal(self.goods)+';') == '0'
            return ['Actual batch/serial inbound followed by sales audit and reverse; physical quantities and individual serial states restored']
        self.case('sale.posting_batch_and_serial_round_trip', batch_serial)

        def multiunit():
            self.fixture()
            units=json.dumps([dict(source='unit', name='box', nums=5)])
            sql(self.state, 'UPDATE goods SET unit=\'-1\',units='+literal(units)+' WHERE id='+literal(self.goods)+';')
            body=self.body(); body['items'][0].update(unit='box', nums=1, discount=1)
            identifier=self.save_checked(body)
            assert self.post([identifier]).get('code') == 10000 and self.inventory() == 5
            assert Decimal(self.scalar("SELECT nums FROM room_info WHERE type='sell' AND `class`="+literal(identifier)+';')) == 5
            units=json.dumps([dict(source='unit', name='box', nums=10)])
            sql(self.state, 'UPDATE goods SET units='+literal(units)+' WHERE id='+literal(self.goods)+';')
            assert self.post([identifier],False).get('code') == 10000 and self.inventory() == 10
            return ['One box deducts five base units; changing the new fixture conversion afterwards cannot alter original reversal quantity']
        self.case('sale.posting_unit_conversion_uses_original_reverse', multiunit)

        def service():
            self.fixture(stock=0)
            sql(self.state,'UPDATE goods SET type=1 WHERE id='+literal(self.goods)+';')
            identifier=self.draft()
            assert self.post([identifier]).get('code') == 10000 and self.inventory() == 0
            assert Decimal(self.scalar('SELECT nums FROM serve WHERE goods='+literal(self.goods)+';')) == 2
            assert self.ledger_count('room_info', identifier) == 0
            assert self.post([identifier],False).get('code') == 10000
            assert Decimal(self.scalar('SELECT nums FROM serve WHERE goods='+literal(self.goods)+';')) == 0
            return ['Service sale changes service cumulative movement and receivable, never physical warehouse stock; reverse restores both']
        self.case('sale.posting_service_has_no_physical_stock', service)

        def source_order():
            self.fixture()
            order,line=uuid.uuid4().hex,uuid.uuid4().hex
            sql(self.state,'INSERT INTO sor(id,frame,customer,time,number,total,actual,arrival,examine,state,`user`) VALUES('+','.join(literal(v) for v in [order,self.state['frame_id'],self.customer,'2026-11-14','QA-SOR-'+order[:16],500,565,'2026-11-15',1,0,self.actor])+');'+
                'INSERT INTO sor_info(id,pid,goods,attr,unit,price,nums,total,tpt,handle) VALUES('+','.join(literal(v) for v in [line,order,self.goods,'','unit',100,5,500,565,0])+');')
            body=self.body(); body.update(source=order); body['items'][0].update(source=line,discount=1)
            identifier=self.save_checked(body)
            assert self.post([identifier]).get('code') == 10000
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';')) == 2
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';') == '1'
            assert self.post([identifier],False).get('code') == 10000
            assert Decimal(self.scalar('SELECT handle FROM sor_info WHERE id='+literal(line)+';')) == 0
            assert self.scalar('SELECT CAST(state AS SIGNED) FROM sor WHERE id='+literal(order)+';') == '0'
            return ['SQL-only source-order fixture; actual sale posting/reverse updates linked quantity and order state; not full order lifecycle acceptance']
        self.case('sale.posting_linked_order_quantity', source_order)

        def period():
            self.fixture()
            identifier=self.draft()
            period=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-15','2026-11-15',self.actor])+');')
                assert self.post([identifier]).get('code') != 10000
                self.assert_empty_posting(identifier,10)
            finally:
                sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            return ['Owned period fixture blocks posting for the whole closed business day without side effects; fixture removed']
        self.case('sale.posting_closed_period_rejected', period)

        def legacy():
            self.fixture()
            identifier=self.draft()
            sql(self.state,'UPDATE sell SET examine=1 WHERE id='+literal(identifier)+';')
            assert self.post([identifier]).get('code') != 10000 and self.post([identifier],False).get('code') != 10000
            assert self.inventory() == 10 and self.balance('customer',self.customer) == 0
            return ['Owned legacy-state fixture without movements cannot cause duplicate posting or an invented stock/funds reversal']
        self.case('sale.posting_legacy_state_without_journal_not_replayed', legacy)

        def downstream():
            self.fixture()
            identifier=self.draft(received=50)
            assert self.post([identifier]).get('code') == 10000
            invoice=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'sell',identifier,'2026-11-15','QA-'+invoice[:16],'QA Invoice',1])+');')
                assert self.post([identifier],False).get('code') != 10000
                assert self.inventory() == 8 and self.balance('account',self.account) == 150 and self.balance('customer',self.customer) == 176
                assert self.ledger_count('room_info',identifier) == 1
            finally:
                sql(self.state,'DELETE FROM invoice WHERE id='+literal(invoice)+';')
            assert self.post([identifier],False).get('code') == 10000
            return ['Owned SQL invoice reference blocks real reverse audit without partial effects; reverse succeeds only after removing that fixture']
        self.case('sale.posting_downstream_invoice_protects_reverse', downstream)

        def deletion():
            self.fixture()
            free=self.create(self.body())
            assert self.request('DELETE','/sale/form/deleteSales',[free],service='sale').get('code')==10000
            assert self.scalar('SELECT COUNT(*) FROM sell WHERE id='+literal(free)+';')=='0'
            assert self.scalar('SELECT COUNT(*) FROM sell_info WHERE pid='+literal(free)+';')=='0'
            checked=self.draft()
            assert self.request('DELETE','/sale/form/deleteSales',[checked],service='sale').get('code')!=10000
            referenced=self.create(self.body());invoice=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'sell',referenced,'2026-11-15','QA-'+invoice[:16],'QA Invoice',1])+');')
                assert self.request('DELETE','/sale/form/deleteSales',[referenced],service='sale').get('code')!=10000
                assert self.scalar('SELECT COUNT(*) FROM sell WHERE id='+literal(referenced)+';')=='1'
            finally:
                sql(self.state,'DELETE FROM invoice WHERE id='+literal(invoice)+';')
            assert self.inventory()==10
            return ['Real DELETE array removes a free draft and its lines; checked or referenced drafts are rejected without changing stock']
        self.case('sale.posting_draft_delete_and_reference_guards', deletion)

        def report_scopes():
            self.fixture()
            other=uuid.uuid4().hex
            sql(self.state,'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [other,'QA Other Posting Warehouse','QW'+other[:16],self.state['frame_id']])+');')
            incoming=self.inbound(5);incoming['total']=20
            incoming['otherInListDetailInfoDTOList'][0].update(warehouse=other,price=4,total=20)
            entry=self.store('POST','/otherin/add',incoming); self.audit(entry,1)
            identifier=self.draft()
            assert self.post([identifier]).get('code') == 10000
            row=json.loads(self.scalar("SELECT JSON_OBJECT('qty',exist,'value',balance) FROM summary WHERE type='sell' AND `class`="+literal(identifier)+';'))
            assert list(map(Decimal,map(str,json.loads(row['qty'])))) == list(map(Decimal,['13','8','13','8']))
            assert list(map(Decimal,map(str,json.loads(row['value'])))) == list(map(Decimal,['36','16','36','16']))
            return ['Different warehouses and inbound prices produce distinct whole-product and per-warehouse stock/value scopes']
        self.case('sale.posting_report_whole_and_warehouse_balances', report_scopes)

        def closed_costs():
            self.fixture()
            body=self.body(); body['time']='2026-11-14 12:00:00'
            identifier=self.save_checked(body)
            assert self.post([identifier]).get('code') == 10000
            query="SELECT CONCAT(uct,':',bct,':',exist,':',balance) FROM summary WHERE type='sell' AND `class`="+literal(identifier)+';'
            original=self.scalar(query)
            period=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-14','2026-11-15',self.actor])+');'+
                    'UPDATE goods SET buy=9 WHERE id='+literal(self.goods)+';')
                current=self.draft()
                assert self.post([current]).get('code') == 10000
                assert self.scalar(query) == original, 'Current posting rewrote closed-period cost or stock report balances'
            finally:
                sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            return ['Current-day sale posts after closing yesterday; changing the owned goods cost cannot rewrite closed-period report amounts']
        self.case('sale.posting_preserves_closed_period_costs', closed_costs)

        def costing():
            rows=sql(self.state,"SELECT CONCAT(id,':',HEX(info)) FROM sys WHERE name='fun';")
            assert not rows, 'Use a fresh QA configuration for isolated cost-mode acceptance'
            setting=uuid.uuid4().hex
            # The existing function-settings write API is still pending: its readonly
            # guards are not the subject of this costing fixture. Preserve exact QA
            # definitions and restore them even when a cost assertion fails.
            raw=sql(self.state,"SELECT JSON_OBJECT('name',TRIGGER_NAME,'event',EVENT_MANIPULATION,'body',ACTION_STATEMENT) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND TRIGGER_NAME IN ('psi_guard_fun_update','psi_guard_fun_delete');")
            guards=[json.loads(line) for line in raw.splitlines() if line]
            assert len(guards)==2, 'Expected both known QA-only function-setting guards'
            (QA / 'runtime/cost-setting-guard-recovery.json').write_text(json.dumps(guards),encoding='utf-8')
            try:
                for guard in guards:
                    sql(self.state,'DROP TRIGGER `'+guard['name']+'`;')
                for mode,cost,value in [('base','2','8'),('ma','4.4','17.6'),('fifo','3.5','14')]:
                    self.fixture(stock=0)
                    config=json.dumps(dict(valuation=mode,rule='def',branch=True))
                    sql(self.state,"DELETE FROM sys WHERE id="+literal(setting)+";INSERT INTO sys(id,name,info) VALUES("+','.join(literal(v) for v in [setting,'fun',config])+');')
                    for qty,price in [(3,2),(2,8)]:
                        incoming=self.inbound(qty); incoming['total']=qty*price
                        incoming['otherInListDetailInfoDTOList'][0].update(price=price,total=qty*price)
                        entry=self.store('POST','/otherin/add',incoming); self.audit(entry,1)
                    identifier=self.draft(qty=4)
                    assert self.post([identifier]).get('code') == 10000
                    actual=self.scalar("SELECT CONCAT(uct,',',bct) FROM summary WHERE type='sell' AND `class`="+literal(identifier)+';')
                    assert list(map(Decimal,actual.split(','))) == list(map(Decimal,[cost,value])), mode+' cost mismatch: '+actual
                    assert self.inventory() == 1
                    assert self.post([identifier],False).get('code') == 10000 and self.inventory() == 5
                    assert self.scalar('SELECT COUNT(*) FROM fifo WHERE `out` NOT IN (SELECT id FROM summary) OR `in` NOT IN (SELECT id FROM summary);') == '0'
            finally:
                try:
                    sql(self.state,'DELETE FROM sys WHERE id='+literal(setting)+';')
                finally:
                    for guard in guards:
                        sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+guard['name']+'` BEFORE '+guard['event']+' ON sys FOR EACH ROW '+guard['body']+'$$\nDELIMITER ;\n')
            return ['Actual differently priced inbound lots; base, moving average and FIFO cost assertions plus reversal and no orphan FIFO relations']
        self.case('sale.posting_real_cost_modes', costing)
        self.write_report()


if __name__ == '__main__':
    import sys
    suite=ExtendedPostingSuite(read_state())
    if len(sys.argv)>1 and sys.argv[1]=='source-state':suite.source_state_cases();suite.write_report()
    elif len(sys.argv)>1 and sys.argv[1]=='closed-cost':
        actual_case=suite.case
        suite.case=lambda name,action: actual_case(name,action) if name=='sale.posting_preserves_closed_period_costs' else None
        suite.run()
    else:suite.run()
