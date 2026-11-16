"""Actual procurement-return posting gate; private QA DB only, never normal business data."""
import argparse
import concurrent.futures
import uuid
import json
from decimal import Decimal
from purchase_return_review_acceptance import PurchaseReturnReviewSuite
from acceptance import read_state, sql, literal
from resource_fixture import qa_resource_grants, authority
from purchase_ui_acceptance import PurchaseUiSuite


class PurchaseReturnPostingSuite(PurchaseReturnReviewSuite):
    def post_return(self, ids, status=1, versions=None):
        return self.request('PUT', '/purchase-return-form/approve', dict(ids=ids, status=status, versions=versions), service='purchase')

    def ready(self):
        source, identifier, body = self.created()
        body = self.revision_return(identifier)
        body.update(money=25, account=self.account)
        assert self.revise_return(identifier, body).get('code') == 10000
        assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
        self.unchanged()
        return source, identifier

    def run_baseline(self):
        def actual_post():
            source, identifier = self.ready()
            frozen = self.versions([identifier])
            response = self.post_return([identifier], versions=frozen)
            assert response.get('code') == 10000, 'Actual checked UUID procurement return cannot post stock/refund/payable'
            assert self.inventory() == 1, 'Return must actually issue one base unit'
            assert self.balance('account', self.account) == 100, 'Supplier refund25 must credit original account75'
            assert self.balance('supplier', self.supplier) == 113, 'Return113 less refund25 must reduce payable201 by88'
            assert Decimal(sql(self.state, 'SELECT retreat FROM buy_info WHERE pid=' + literal(source) + ';')) == 1
            assert self.return_doc(identifier)['header']['examine'] == 1
            assert sql(self.state, "SELECT COUNT(*) FROM account_info WHERE type='bre' AND `class`=" + literal(identifier) + ' AND direction=1 AND money=25;') == '1'
            assert sql(self.state, 'SELECT COUNT(*) FROM psi_purchase_return_posting WHERE return_id=' + literal(identifier) + ';') == '1'
            return ['Actual checked UUID issues inventory2→1, credits supplier refund account75→100, reduces payable201→113, increments original returned quantity and stores actual stock/funds proof']
        self.case('purchase.return_posting_actual_stock_refund_payable', actual_post)
        def no_selection():
            assert self.post_return([], versions={}).get('code') != 10000
            return ['Empty actual posting request must refuse']
        self.case('purchase.return_posting_empty_selection_refused', no_selection)
        self.write_report()


    def run_extended(self):
        def roundtrip():
            source, identifier = self.ready(); before = self.history(identifier)
            assert self.post_return([identifier], versions=self.versions([identifier])).get('data') == 1
            assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
            current = self.versions([identifier]); assert self.post_return([identifier], versions=current).get('data') == 0
            assert self.history(identifier) == before + 1
            assert self.post_return([identifier], status=0, versions=current).get('data') == 1
            self.unchanged(); doc = self.return_doc(identifier)
            assert doc['header']['examine'] == 0 and doc['header']['check'] == 1 and self.history(identifier) == before + 2
            for table, condition in [('room_info', "type='bre' AND `class`="), ('account_info', "type='bre' AND `class`="), ('summary', "type='bre' AND `class`="), ('bre_bill', 'pid=')]:
                assert sql(self.state, 'SELECT COUNT(*) FROM ' + table + ' WHERE ' + condition + literal(identifier) + ';') == '0'
            assert Decimal(sql(self.state, 'SELECT retreat FROM buy_info WHERE pid=' + literal(source) + ';')) == 0
            return ['Actual forward effects verified before reversal; reverse restores source counter, stock/account/payable and removes only active posting evidence; fresh same-target is idempotent']
        self.case('purchase.return_posting_actual_roundtrip_and_idempotence', roundtrip)
        def concurrency():
            _, identifier = self.ready(); frozen = self.versions([identifier]); before = self.history(identifier)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.post_return([identifier], versions=frozen), range(2)))
            assert sum(r.get('code') == 10000 for r in results) == 1
            assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
            assert self.history(identifier) == before + 1
            return ['Concurrent frozen actual posting commands produce one inventory/refund/payable effect and one operator history']
        self.case('purchase.return_posting_concurrent_single_effect', concurrency)
        def fault():
            _, identifier = self.ready(); frozen = self.versions([identifier]); trigger = 'qa_bre_refund_' + uuid.uuid4().hex[:10]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `" + trigger + "` BEFORE INSERT ON account_info FOR EACH ROW BEGIN IF NEW.type='bre' AND NEW.class=" + literal(identifier) + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA supplier refund write failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_return([identifier], versions=frozen).get('code') != 10000
                self.unchanged(); assert self.versions([identifier]) == frozen
                assert sql(self.state, "SELECT COUNT(*) FROM room_info WHERE type='bre' AND `class`=" + literal(identifier) + ';') == '0'
            finally: sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            assert self.post_return([identifier], versions=frozen).get('code') == 10000
            assert self.inventory() == 1 and self.balance('account', self.account) == 100
            return ['Actual supplier-refund storage failure rolls back earlier stock, source quantity, balance, version and history; exact original command retries after owned trigger removal']
        self.case('purchase.return_posting_refund_failure_atomic_retry', fault)
        self.write_report()

    def run_variants(self):
        def serial_roundtrip():
            self.fixture(); sql(self.state, 'UPDATE goods SET serial=1 WHERE id=' + literal(self.goods) + ';')
            body = self.body(); body['purchaseNoteBuyDTO'].update(money=25, account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(discount=0, tax=13, batch='', mfd=None, serial=json.dumps(['QA-BRE-A', 'QA-BRE-B']))
            source = self.create(body); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
            payload = self.body_return(source); payload['details'][0]['serial'] = json.dumps(['QA-BRE-B'])
            result = self.add_return(payload); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 1
            assert sql(self.state, "SELECT CAST(state AS SIGNED) FROM serial WHERE goods=" + literal(self.goods) + " AND number='QA-BRE-B';") == '1'
            assert sql(self.state, "SELECT CAST(state AS SIGNED) FROM serial WHERE goods=" + literal(self.goods) + " AND number='QA-BRE-A';") == '0'
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            assert sql(self.state, "SELECT CAST(state AS SIGNED) FROM serial WHERE goods=" + literal(self.goods) + " AND number='QA-BRE-B';") == '0'
            return ['Actual original serialB is issued and restored; unselected serialA stays in stock; source-specific serial and room journals agree']
        self.case('purchase.return_posting_original_serial_roundtrip', serial_roundtrip)
        def service_roundtrip():
            self.fixture(); sql(self.state, 'UPDATE goods SET type=1 WHERE id=' + literal(self.goods) + ';')
            source = self.create_document(paid=25); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
            result = self.add_return(self.body_return(source)); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert sql(self.state, 'SELECT nums FROM serve WHERE goods=' + literal(self.goods) + ';') in ['1.0000', '1']
            assert self.inventory() == 0 and self.balance('supplier', self.supplier) == 88
            assert sql(self.state, "SELECT COUNT(*) FROM summary WHERE type='bre' AND `class`=" + literal(identifier) + ';') == '0'
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert Decimal(sql(self.state, 'SELECT nums FROM serve WHERE goods=' + literal(self.goods) + ';')) == 2
            assert self.balance('supplier', self.supplier) == 201
            return ['Actual service return decreases and restores original service total without creating warehouse or stock-cost records; payable reverses']
        self.case('purchase.return_posting_service_roundtrip', service_roundtrip)
        def stock_shortage():
            source = self.posted(); self.sale_from_receipt(1)
            result = self.add_return(self.body_return(source, 2)); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); assert self.post_return([identifier], versions=frozen).get('code') != 10000
            assert self.inventory() == 1 and self.balance('account', self.account) == 75 and self.balance('supplier', self.supplier) == 201
            assert self.versions([identifier]) == frozen
            assert Decimal(sql(self.state, 'SELECT retreat FROM buy_info WHERE pid=' + literal(source) + ';')) == 0
            return ['Actual later sale leaves physical stock1 despite original source allowance2; return2 saves as plan but actual posting refuses atomically without source/funds effects']
        self.case('purchase.return_posting_actual_consumption_shortage', stock_shortage)
        self.write_report()

    def run_quantity_gates(self):
        def shared_batch():
            source = self.posted(); ids = []
            for _ in range(2):
                result = self.add_return(self.body_return(source, .5)); assert result.get('code') == 10000; ids.append(result['data'])
            assert self.review(ids, versions=self.versions(ids)).get('data') == 2
            assert self.post_return(ids, versions=self.versions(ids)).get('data') == 2
            assert self.inventory() == 1 and self.balance('supplier', self.supplier) == 88
            assert Decimal(sql(self.state, 'SELECT retreat FROM buy_info WHERE pid=' + literal(source) + ';')) == 1
            assert self.post_return(ids, status=0, versions=self.versions(ids)).get('data') == 2
            self.unchanged()
            assert Decimal(sql(self.state, 'SELECT retreat FROM buy_info WHERE pid=' + literal(source) + ';')) == 0
            return ['Two actual returns sharing a source check/post/reverse as one batch; all displayed source-bound versions validated before first source counter change']
        self.case('purchase.return_posting_shared_source_batch_roundtrip', shared_batch)
        def original_units():
            self.fixture(); sql(self.state, "UPDATE goods SET unit='-1',units=" + literal(json.dumps([dict(source='unit', name='box', nums=5)])) + ' WHERE id=' + literal(self.goods) + ';')
            body = self.body(); body['purchaseNoteBuyDTO'].update(total=100, actual=113, money=25, account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(unit='box', nums=1, discount=0, tax=13, total=100, tat=13, tpt=113, batch='', mfd=None, serial='[]')
            source = self.create(body); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
            sql(self.state, 'UPDATE goods SET units=' + literal(json.dumps([dict(source='unit', name='box', nums=10)])) + ' WHERE id=' + literal(self.goods) + ';')
            result = self.add_return(self.body_return(source, .5)); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == Decimal('2.5')
            assert Decimal(sql(self.state, "SELECT nums FROM room_info WHERE type='bre' AND `class`=" + literal(identifier) + ';')) == Decimal('2.5')
            assert self.balance('supplier', self.supplier) == Decimal('31.5')
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 5 and self.balance('supplier', self.supplier) == 88
            return ['Actual original five-unit box receipt returns half-box2.5 base units despite current conversion10; reverse restores5, source amounts and payable']
        self.case('purchase.return_posting_original_unit_conversion', original_units)
        def batch_roundtrip():
            self.fixture(); sql(self.state, 'UPDATE goods SET batch=1 WHERE id=' + literal(self.goods) + ';')
            body = self.body(); body['purchaseNoteBuyDTO'].update(money=25, account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(discount=0, tax=13, batch='QA-RETURN-BATCH', mfd='2026-11-01', serial='[]')
            source = self.create(body); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
            result = self.add_return(self.body_return(source)); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 1
            assert Decimal(sql(self.state, 'SELECT b.nums FROM batch b JOIN room r ON r.id=b.room WHERE r.goods=' + literal(self.goods) + ';')) == 1
            assert sql(self.state, "SELECT COUNT(*) FROM batch_info WHERE type='bre' AND `class`=" + literal(identifier) + ' AND direction=0 AND nums=1;') == '1'
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            assert Decimal(sql(self.state, 'SELECT b.nums FROM batch b JOIN room r ON r.id=b.room WHERE r.goods=' + literal(self.goods) + ';')) == 2
            return ['Actual original batch and manufacturing date persist into return; batch and room quantities2→1→2 with actual outgoing and reversed batch journals']
        self.case('purchase.return_posting_original_batch_roundtrip', batch_roundtrip)
        self.write_report()

    def run_cost_precision(self, mode=None):
        def exact_net():
            self.fixture(); body = self.body()
            sql(self.state, "UPDATE goods SET unit='-1',units=" + literal(json.dumps([dict(source='unit', name='box', nums=3)])) + ' WHERE id=' + literal(self.goods) + ';')
            body['purchaseNoteBuyDTO'].update(total=100, actual=113, money=25, account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(unit='box', nums=1, price=100, discount=0, tax=13, total=100, tat=13, tpt=113, batch='', mfd=None, serial='[]')
            source = self.create(body); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
            assert Decimal(sql(self.state, 'SELECT total FROM buy_info WHERE pid=' + literal(source) + ';')) == 100
            result = self.add_return(self.body_return(source, 1)); assert result.get('code') == 10000; identifier = result['data']
            assert Decimal(sql(self.state, 'SELECT total FROM bre_info WHERE pid=' + literal(identifier) + ';')) == 100
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            net = Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='bre' AND `class`=" + literal(identifier) + ';'))
            assert net == 100, 'Procurement return net100 became rounded unit-price multiplication ' + str(net)
            replenishment = self.create_document()
            assert self.check([replenishment]).get('code') == 10000 and self.post([replenishment]).get('code') == 10000
            sale, sold = self.sale_from_receipt(1, time='2026-11-16 13:00:00')
            replayed = Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='bre' AND `class`=" + literal(identifier) + ';'))
            assert replayed == 100, 'Sales cost replay changed exact procurement return cost to ' + str(replayed)
            assert sale.post([sold], 0).get('code') == 10000
            assert self.post([replenishment], 0).get('code') == 10000
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 3 and self.balance('supplier', self.supplier) == 88
            return ['Actual three-unit net100 receipt/full return preserves inventory value100 rather than33.3333×3=99.9999; later actual purchase and sale cost replay retain100; dependent reversals then restore original receipt and payable']
        self.case('purchase.return_posting_exact_net_cost_precision' + ('_' + mode if mode else ''), exact_net)
        self.write_report()

    def run_finance_guards(self):
        def refund_limits():
            for refund in [0, 113]:
                _, identifier, _ = self.created(); body = self.revision_return(identifier)
                body.update(money=refund, account=self.account if refund else '')
                assert self.revise_return(identifier, body).get('code') == 10000
                assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
                assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
                assert self.balance('account', self.account) == 75 + refund
                assert self.balance('supplier', self.supplier) == 88 + refund
                assert self.return_doc(identifier)['header']['nucleus'] == (2 if refund else 0)
                assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
                self.unchanged()
            return ['Zero refund reduces payable by full113 with no account movement; full113 credits account and leaves payable unchanged; settlement enums and actual reverse both agree']
        self.case('purchase.return_posting_zero_full_refund_roundtrip', refund_limits)
        def spent_refund():
            _, identifier = self.ready()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            body = self.body(); body['purchaseNoteBuyDTO'].update(money=100, account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(discount=0, tax=13, batch='', mfd=None, serial='[]')
            spend = self.create(body); assert self.check([spend]).get('code') == 10000 and self.post([spend]).get('code') == 10000
            assert self.balance('account', self.account) == 0
            frozen = self.versions([identifier]); stock = self.inventory(); payable = self.balance('supplier', self.supplier)
            assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
            assert self.versions([identifier]) == frozen and self.inventory() == stock and self.balance('supplier', self.supplier) == payable
            assert self.post([spend], 0).get('code') == 10000
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Actual later purchase spends refund account to0; return reversal refuses and rolls back prior attempted stock restoration; reversing owned spending allows original frozen command']
        self.case('purchase.return_posting_spent_refund_reverse_guard', spent_refund)
        def live_permission():
            _, identifier = self.ready(); frozen = self.versions([identifier])
            role = self.success('POST', '/role/add-role', dict(name='QA Return Post ' + uuid.uuid4().hex[:8], data='', root='[]', auth='{}'))
            keyword = sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(role) + ';')
            actor, user, _ = self.new_user(role=role); token = PurchaseUiSuite.login(self, user); admin = self.token
            try:
                self.token = token
                assert self.post_return([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/purchase-return-form/approve'], [authority(role, keyword)]):
                    assert self.post_return([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/purchase-return-form/approve', '/purchase-note/getBuildBre'], [authority(role, keyword)]):
                    assert self.post_return([identifier], versions=frozen).get('code') == 10000
                assert self.post_return([identifier], status=0, versions=frozen).get('code') == 403
            finally: self.token = admin
            assert self.inventory() == 1 and self.balance('account', self.account) == 100
            assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='bre' AND source=" + literal(identifier) + ' AND `user`=' + literal(actor) + ';') == '1'
            return ['Actual new OAuth actor needs both live approve and original-source grants; stock/refund and actor history persist once; same token immediately denied after revoke']
        self.case('purchase.return_posting_live_oauth_permission', live_permission)
        self.write_report()

    def run_state_guards(self):
        def versions_and_check():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); history = self.history(identifier)
            assert self.post_return([identifier], versions=frozen).get('code') != 10000
            assert self.review([identifier], versions=frozen).get('code') == 10000
            checked = self.versions([identifier])
            for versions in [None, {}, {identifier: 'bad'}, dict(checked, extra='a'*64), frozen]:
                assert self.post_return([identifier], versions=versions).get('code') != 10000
            assert self.versions([identifier]) == checked and self.history(identifier) == history + 1
            self.unchanged()
            assert self.post_return([identifier], versions=checked).get('code') == 10000
            return ['Unreviewed actual draft cannot post; absent/malformed/extra/stale complete versions refuse without stock/funds/history writes; exact checked version succeeds']
        self.case('purchase.return_posting_review_and_frozen_versions_required', versions_and_check)
        def closed_period():
            _, identifier = self.ready(); period = uuid.uuid4().hex; frozen = self.versions([identifier])
            def close(): sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-16', '2026-11-16', self.actor]) + ');')
            close()
            try:
                assert self.post_return([identifier], versions=frozen).get('code') != 10000
                assert self.versions([identifier]) == frozen; self.unchanged()
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.post_return([identifier], versions=frozen).get('code') == 10000
            posted = self.versions([identifier]); close()
            try:
                assert self.post_return([identifier], status=0, versions=posted).get('code') != 10000
                assert self.versions([identifier]) == posted
                assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.post_return([identifier], status=0, versions=posted).get('code') == 10000
            self.unchanged()
            return ['Owned QA closed-period fixture refuses actual posting and reversal atomically; removing only owned fixture allows original commands']
        self.case('purchase.return_posting_closed_period_both_directions', closed_period)
        def invoice_reference():
            _, identifier = self.ready()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); invoice = uuid.uuid4().hex
            try:
                sql(self.state, 'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES(' + ','.join(literal(v) for v in [invoice, 'bre', identifier, '2026-11-16', 'QA-BRE-'+invoice[:16], 'QA Return Invoice', 1]) + ');')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
                assert self.versions([identifier]) == frozen
            finally: sql(self.state, 'DELETE FROM invoice WHERE id=' + literal(invoice) + ';')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Owned downstream invoice fixture blocks actual reverse without stock/funds effects; remove owned reference then exact reverse restores balances']
        self.case('purchase.return_posting_downstream_invoice_protection', invoice_reference)
        self.write_report()

    def run_scope_guard(self):
        def actual_foreign_batch():
            _, own = self.ready(); own_version = self.versions([own])[own]
            own_account = self.account; own_supplier = self.supplier; own_goods = self.goods
            foreign = uuid.uuid4().hex; self.fixture()
            sql(self.state, "INSERT INTO frame(id,pid,name,sort) VALUES(" + literal(foreign) + ",'0','QA Procurement Return Scope',0);")
            for table, identifier in [('warehouse', self.warehouse), ('supplier', self.supplier), ('account', self.account)]:
                sql(self.state, 'UPDATE ' + table + ' SET frame=' + literal(foreign) + ' WHERE id=' + literal(identifier) + ';')
            self.success('PUT', '/user/mod-user', dict(id=self.actor, frame=foreign))
            try:
                source = self.create_document(paid=25); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
                result = self.add_return(self.body_return(source)); assert result.get('code') == 10000; other = result['data']
                assert self.review([other], versions=self.versions([other])).get('code') == 10000
                other_version = self.versions([other])[other]
            finally: self.success('PUT', '/user/mod-user', dict(id=self.actor, frame=self.state['frame_id']))
            histories = [self.history(i) for i in [own, other]]
            role = self.success('POST', '/role/add-role', dict(name='QA Return Scope '+uuid.uuid4().hex[:8], data='', root='[]', auth='{}'))
            keyword = sql(self.state, 'SELECT keyword FROM role WHERE id='+literal(role)+';')
            _, username, _ = self.new_user(role=role); token = PurchaseUiSuite.login(self, username); admin = self.token
            with qa_resource_grants(self.state, ['/purchase-return-form/approve', '/purchase-note/getBuildBre'], [authority(role, keyword)]):
                try:
                    self.token = token
                    assert self.post_return([own, other], versions={own: own_version, other: other_version}).get('code') == 403
                finally: self.token = admin
            assert [self.history(i) for i in [own, other]] == histories
            for identifier in [own, other]:
                assert sql(self.state, 'SELECT CAST(examine AS SIGNED) FROM bre WHERE id=' + literal(identifier) + ';') == '0'
                assert sql(self.state, 'SELECT COUNT(*) FROM psi_purchase_return_posting WHERE return_id=' + literal(identifier) + ';') == '0'
            assert self.balance('account', own_account) == 75 and self.balance('supplier', own_supplier) == 201
            assert Decimal(sql(self.state, 'SELECT SUM(nums) FROM room WHERE goods=' + literal(own_goods) + ';')) == 2
            self.unchanged()
            with qa_resource_grants(self.state, ['/purchase-return-form/approve', '/purchase-note/getBuildBre'], [authority(role, keyword)]):
                try:
                    self.token = token
                    assert self.post_return([own], versions={own: own_version}).get('code') == 10000
                finally: self.token = admin
            assert self.balance('account', own_account) == 100
            return ['Actual foreign-organization source and checked return are prepared through real APIs; new ordinary own-organization OAuth actor with explicit grants cannot include foreign return in batch; neither organization gets partial stock/funds/history effects and own original command still succeeds']
        self.case('purchase.return_posting_cross_organization_batch_refused', actual_foreign_batch)
        self.write_report()

    def run_backdated_fifo(self):
        from sale_return_cost_acceptance import owned_cost_mode
        def legitimate_replay():
            with owned_cost_mode(self.state, 'fifo'):
                self.fixture(); sql(self.state, "UPDATE goods SET unit='-1',units=" + literal(json.dumps([dict(source='unit', name='box', nums=3)])) + ' WHERE id=' + literal(self.goods) + ';')
                body = self.body(); body['purchaseNoteBuyDTO'].update(total=100, actual=113, money=25, account=self.account)
                body['purchaseNoteInfoDTOS'][0].update(unit='box', nums=1, price=100, discount=0, tax=13, total=100, tat=13, tpt=113, batch='', mfd=None, serial='[]')
                source = self.create(body); assert self.check([source]).get('code') == 10000 and self.post([source]).get('code') == 10000
                extra = self.create_document(); assert self.check([extra]).get('code') == 10000 and self.post([extra]).get('code') == 10000
                result = self.add_return(self.body_return(source)); assert result.get('code') == 10000; identifier = result['data']
                assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
                assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
                assert self.inventory() == 2
                assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='bre' AND `class`=" + literal(identifier) + ';')) == 100
                sale, sold = self.sale_from_receipt(1, time='2026-11-16 10:00:00')
                assert self.inventory() == 1
                assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='bre' AND `class`=" + literal(identifier) + ';')) == Decimal('166.6667')
                response = self.post_return([identifier], status=0, versions=self.versions([identifier]))
                assert response.get('code') == 10000, 'Legitimate FIFO replay changed derived cost and incorrectly blocked return reversal as damaged journal'
                assert self.inventory() == 4 and self.balance('supplier', self.supplier) == 314
                assert sale.post([sold], 0).get('code') == 10000
                assert self.post([extra], 0).get('code') == 10000
                assert self.inventory() == 3 and self.balance('supplier', self.supplier) == 88
                return ['Actual backdated sale legally reallocates FIFO return cost100→166.6667; immutable posting evidence remains valid and return reverses while sale is active; remaining actual reversals restore original source']
        self.case('purchase.return_posting_legitimate_backdated_fifo_reversal', legitimate_replay)
        self.write_report()

    def run_edges(self):
        def historical_stock():
            source = self.posted(); self.sale_from_receipt(2, time='2026-11-16 10:00:00')
            assert self.inventory() == 0
            body = self.body(); body['purchaseNoteBuyDTO'].update(time='2026-11-16 14:00:00', money=0, account='')
            body['purchaseNoteInfoDTOS'][0].update(discount=0, tax=13, batch='', mfd=None, serial='[]')
            replenishment = self.create(body)
            assert self.check([replenishment]).get('code') == 10000 and self.post([replenishment]).get('code') == 10000
            result = self.add_return(self.body_return(source)); assert result.get('code') == 10000; identifier = result['data']
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); payable = self.balance('supplier', self.supplier)
            assert self.post_return([identifier], versions=frozen).get('code') != 10000
            assert self.inventory() == 2 and self.balance('supplier', self.supplier) == payable and self.versions([identifier]) == frozen
            assert self.review([identifier], status=0, versions=frozen).get('code') == 10000
            body = self.revision_return(identifier); body['time'] = '2026-11-16 15:00:00'
            assert self.revise_return(identifier, body).get('code') == 10000
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 1
            return ['Actual sale10:00 drains stock, replenishment14:00 restores current2; return12:00 refuses historical negative inventory atomically, explicit persisted edit15:00 then check/post succeeds']
        self.case('purchase.return_posting_actual_historical_stock_guard', historical_stock)
        def reverse_history_fault():
            _, identifier = self.ready()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); trigger = 'qa_bre_reverse_' + uuid.uuid4().hex[:10]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `" + trigger + "` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bre' AND NEW.source=" + literal(identifier) + " AND NEW.info='反审核采购退货单' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return reverse history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
                assert self.versions([identifier]) == frozen
                assert sql(self.state, 'SELECT COUNT(*) FROM psi_purchase_return_posting WHERE return_id=' + literal(identifier) + ';') == '1'
            finally: sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Actual reverse history insertion fails after stock/source/funds/proof changes; whole transaction rolls back and original frozen command retries after owned trigger removal']
        self.case('purchase.return_posting_reverse_history_failure_atomic', reverse_history_fault)
        def damaged_refund():
            _, identifier = self.ready()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier])
            try:
                sql(self.state, "UPDATE account_info SET money=money+1 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
                for status in [0, 1]: assert self.post_return([identifier], status=status, versions=frozen).get('code') != 10000
                assert self.inventory() == 1 and self.balance('account', self.account) == 100 and self.balance('supplier', self.supplier) == 113
            finally: sql(self.state, "UPDATE account_info SET money=25 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
            try:
                sql(self.state, "UPDATE room_info SET nums=nums+1 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 1 and self.balance('account', self.account) == 100
            finally: sql(self.state, "UPDATE room_info SET nums=1 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
            try:
                sql(self.state, "UPDATE summary SET nums=nums+1 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 1 and self.balance('account', self.account) == 100
            finally: sql(self.state, "UPDATE summary SET nums=1 WHERE type='bre' AND `class`=" + literal(identifier) + ';')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Owned QA refund-ledger corruption refuses duplicate posting/reversal; physical-journal and summary immutable quantity corruption also refuses; restoring each exact owned evidence allows original reverse despite legitimate derived cost replay being allowed']
        self.case('purchase.return_posting_refund_fingerprint_guard', damaged_refund)
        self.write_report()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['baseline', 'extended', 'variants', 'quantity', 'finance', 'cost', 'states', 'modes', 'scope', 'edges', 'backdated-fifo']); action = parser.parse_args().action
    suite = PurchaseReturnPostingSuite(read_state())
    if action == 'baseline': suite.run_baseline()
    elif action == 'extended': suite.run_extended()
    elif action == 'variants': suite.run_variants()
    elif action == 'quantity': suite.run_quantity_gates()
    elif action == 'finance': suite.run_finance_guards()
    elif action == 'cost': suite.run_cost_precision()
    elif action == 'states': suite.run_state_guards()
    elif action == 'scope': suite.run_scope_guard()
    elif action == 'edges': suite.run_edges()
    elif action == 'backdated-fifo': suite.run_backdated_fifo()
    else:
        from sale_return_cost_acceptance import owned_cost_mode
        for mode in ['base', 'ma', 'fifo']:
            with owned_cost_mode(suite.state, mode): suite.run_cost_precision(mode)
