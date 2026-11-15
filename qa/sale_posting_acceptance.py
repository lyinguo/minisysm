"""Real sales posting gates. Every fixture and write belongs to the dedicated QA DB."""
import concurrent.futures
import threading
import uuid
from decimal import Decimal
from sale_draft_acceptance import SaleDraftSuite
from acceptance import read_state, sql, literal


class SalePostingSuite(SaleDraftSuite):
    def fixture(self, stock=10):
        # A fresh scope per case prevents one failed audit from masking another case.
        self.goods, self.warehouse, self.customer, self.account = [uuid.uuid4().hex for _ in range(4)]
        sql(self.state, 'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES(' +
            ','.join(literal(v) for v in [self.goods, 'QA Posting Goods', 'qa', 'QG'+self.goods[:16], '0', 'unit', 2, 100, 0, 0, '{}']) + ');' +
            'INSERT INTO warehouse(id,name,number,frame) VALUES(' + ','.join(literal(v) for v in [self.warehouse, 'QA Posting Warehouse', 'QW'+self.warehouse[:16], self.state['frame_id']]) + ');' +
            'INSERT INTO customer(id,name,py,number,frame,`user`,category,grade) VALUES(' + ','.join(literal(v) for v in [self.customer, 'QA Posting Customer', 'qa', 'QC'+self.customer[:16], self.state['frame_id'], self.actor, '0', '0']) + ');' +
            'INSERT INTO account(id,name,number,frame,time,initial,balance) VALUES(' + ','.join(literal(v) for v in [self.account, 'QA Posting Account', 'QA'+self.account[:16], self.state['frame_id'], '2026-11-15', 100, 100]) + ');')
        if stock:
            entry_id, _ = self.create_inbound(stock)
            self.audit(entry_id, 1)
        assert self.inventory() == Decimal(stock), 'Actual inbound fixture did not establish expected stock'

    def draft(self, qty=2, received=0):
        body = self.body()
        body['items'][0].update(nums=qty, discount=1)
        body.update(money=received, account=self.account if received else '')
        identifier = self.create(body)
        self.sale('POST', '/sale/form/check?check=true', [identifier])
        return identifier

    def post(self, ids, target=True):
        return self.request('POST', '/sale/form/examine?examine=' + str(target).lower(), ids, service='sale')

    def scalar(self, statement):
        return sql(self.state, statement)

    def balance(self, table, identifier):
        assert table in ('customer', 'account')
        return Decimal(self.scalar('SELECT COALESCE(balance,0) FROM '+table+' WHERE id='+literal(identifier)+';'))

    def ledger_count(self, table, identifier):
        assert table in ('room_info', 'summary', 'account_info')
        return int(self.scalar('SELECT COUNT(*) FROM '+table+' WHERE type=\'sell\' AND `class`='+literal(identifier)+';'))

    def run(self):
        def physical_posting():
            self.fixture()
            identifier = self.draft(qty=3)
            assert self.inventory() == 10, 'Draft/check changed stock before audit'
            assert self.post([identifier]).get('code') == 10000
            assert self.inventory() == 7, 'Audit changed status without deducting three actual stock units'
            assert self.ledger_count('room_info', identifier) == 1, 'Missing actual stock movement'
            assert self.ledger_count('summary', identifier) == 1, 'Missing sales stock report movement'
            assert self.balance('customer', self.customer) == Decimal('339'), 'Unpaid sales receivable not posted'
            return ['Real HTTP inbound -> sales create -> check -> audit; independent stock, ledger and receivable assertions']
        self.case('sale.posting_actual_stock_and_receivable', physical_posting)

        def received_posting():
            self.fixture()
            identifier = self.draft(received=50)
            assert self.post([identifier]).get('code') == 10000
            assert self.balance('account', self.account) == 150, 'Received cash did not reach the settlement account'
            assert self.balance('customer', self.customer) == 176, 'Receivable must equal 226 actual minus 50 received'
            assert self.ledger_count('account_info', identifier) == 1, 'Cash balance has no supporting movement'
            assert self.scalar('SELECT CAST(nucleus AS SIGNED) FROM sell WHERE id='+literal(identifier)+';') == '1', 'Partial receipt has wrong settlement state'
            assert Decimal(self.scalar('SELECT COALESCE(SUM(money),0) FROM sell_bill WHERE pid='+literal(identifier)+';')) == 50
            return ['Real partial-receipt sale posts account +50, receivable +176 and supporting settlement records']
        self.case('sale.posting_received_cash_and_settlement', received_posting)

        def insufficient():
            self.fixture(stock=1)
            identifier = self.draft(qty=2, received=50)
            result = self.post([identifier])
            assert result.get('code') != 10000, 'Insufficient inventory was audited successfully'
            assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
            assert self.scalar('SELECT CAST(examine AS SIGNED) FROM sell WHERE id='+literal(identifier)+';') == '0'
            assert not self.ledger_count('room_info', identifier) and not self.ledger_count('account_info', identifier)
            return ['Insufficient inventory rejects audit with no state, stock, cash or receivable side effects']
        self.case('sale.posting_insufficient_stock_atomic', insufficient)

        def reverse():
            self.fixture()
            identifier = self.draft(received=50)
            assert self.post([identifier]).get('code') == 10000
            assert self.inventory() == 8 and self.balance('account', self.account) == 150, 'Forward movement must exist before reversal can be accepted'
            assert self.post([identifier], False).get('code') == 10000, 'Own partial receipt incorrectly prevents reverse audit'
            assert self.inventory() == 10 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
            for table in ('room_info', 'summary', 'account_info'):
                assert self.ledger_count(table, identifier) == 0, 'Reverse audit left an active posting'
            return ['Forward posting verified first; reverse restores original stock/account/receivable and removes active movements']
        self.case('sale.posting_reverse_restores_verified_forward', reverse)

        def batch_atomic():
            self.fixture(stock=3)
            first, second = self.draft(qty=2, received=50), self.draft(qty=2, received=50)
            assert self.post([first, second]).get('code') != 10000, 'Batch overdraw was accepted'
            assert self.inventory() == 3 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
            for identifier in (first, second):
                assert self.scalar('SELECT CAST(examine AS SIGNED) FROM sell WHERE id='+literal(identifier)+';') == '0'
                assert self.ledger_count('room_info', identifier) == 0
            return ['Batch with combined demand beyond stock rolls back every member and every balance']
        self.case('sale.posting_batch_failure_rolls_back_all', batch_atomic)

        def race():
            self.fixture(stock=3)
            identifiers = [self.draft(qty=2, received=50) for _ in range(2)]
            barrier = threading.Barrier(2)
            def worker(identifier):
                barrier.wait(timeout=10)
                return self.post([identifier]).get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                codes = list(executor.map(worker, identifiers))
            assert codes.count(10000) == 1, 'Concurrent sales both consumed the same final stock, or neither succeeded'
            assert self.inventory() == 1 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176
            return ['Two concurrent actual HTTP audits compete for three units; exactly one quantity-two sale can post']
        self.case('sale.posting_concurrent_last_stock', race)

        def unchecked():
            self.fixture()
            identifier = self.create(self.body())
            assert self.post([identifier]).get('code') != 10000, 'Unchecked sale was audited'
            assert self.inventory() == 10 and self.balance('customer', self.customer) == 0
            return ['Unchecked document rejected through actual HTTP with unchanged inventory/receivable']
        self.case('sale.posting_requires_check', unchecked)
        self.write_report()


if __name__ == '__main__':
    SalePostingSuite(read_state()).run()
