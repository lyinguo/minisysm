"""Real source sale -> return draft -> check -> inventory/refund posting acceptance.

All new fixtures use the dedicated QA database; financial success must be proved
by stock, customer, account and supporting journal queries, never HTTP alone.
"""
import argparse
import concurrent.futures
import uuid
import json
from decimal import Decimal
from sale_return_review_acceptance import SaleReturnReviewSuite
from acceptance import read_state, sql, literal
from resource_fixture import qa_resource_grants


class SaleReturnPostingSuite(SaleReturnReviewSuite):
    def post_return(self, ids, status=1, versions=None):
        body = dict(ids=ids, status=status)
        if versions is not None: body['versions'] = versions
        return self.request('POST', '/sale/return/return/examine', body, service='sale')

    def checked_return(self, quantity=1, refund=25):
        source, identifier, _ = self.created(quantity)
        body = self.revision(identifier, quantity)
        body.update(money=refund, account=self.account if refund else '')
        assert self.revise_return(body).get('code') == 10000
        assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
        return source, identifier

    def baseline(self):
        def actual_posting():
            source, identifier = self.checked_return()
            result = self.post_return([identifier], versions=self.versions([identifier]))
            assert result.get('code') == 10000, 'Checked real UUID return cannot be financially posted'
            document = self.return_doc(identifier)
            assert document['header']['examine'] == 1
            assert self.inventory() == 9, 'Return did not restore exactly one original stock unit'
            assert self.balance('account', self.account) == 125, 'Refund must deduct planned25 rather than return net100 or gross113'
            assert self.balance('customer', self.customer) == 88, 'Return must reduce receivable by gross113 minus actual refund25'
            assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 1
            for table in ['room_info', 'summary', 'account_info']:
                assert sql(self.state, "SELECT COUNT(*) FROM " + table + " WHERE type='sre' AND `class`=" + literal(identifier) + ';') == '1'
            assert sql(self.state, "SELECT COUNT(*) FROM sre_bill WHERE pid=" + literal(identifier) + " AND money=25;") == '1'
            assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='sre' AND `class`=" + literal(identifier) + ';')) == 2, 'Returned stock cost must equal original issue cost, not selling price'
            return ['Actual checked UUID return restores one unit at original cost2, refunds25 with journals, reduces receivable88, updates source returned quantity1']
        self.case('sale.return_posting_actual_uuid_stock_refund_receivable', actual_posting)

        def empty():
            assert self.post_return([], versions={}).get('code') != 10000, 'Empty return audit silently reported financial success'
            return ['Empty posting selection rejects before any transaction effects']
        self.case('sale.return_posting_empty_selection_refused', empty)
        self.write_report()

    def extended(self):
        def reverse():
            source, identifier = self.checked_return()
            frozen = self.versions([identifier]); history = self.history(identifier)
            assert self.post_return([identifier], versions=frozen).get('code') == 10000
            assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('data') == 0
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            assert self.history(identifier) == history + 2
            assert self.return_doc(identifier)['header']['examine'] == 0
            assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 0
            for table in ['room_info', 'summary', 'account_info']:
                assert sql(self.state, "SELECT COUNT(*) FROM " + table + " WHERE type='sre' AND `class`=" + literal(identifier) + ';') == '0'
            assert sql(self.state, 'SELECT COUNT(*) FROM psi_sale_return_posting WHERE return_id=' + literal(identifier) + ';') == '0'
            return ['Actual return post verified before reverse; stale reversal refused; fresh same-target no-op; reversal restores exact stock/cash/receivable/source quantity and removes own active journals']
        self.case('sale.return_posting_verified_reverse_and_idempotence', reverse)

        def refund_boundaries():
            for refund, expected_account, expected_credit in [(0, 150, 63), (113, 37, 176)]:
                _, identifier = self.checked_return(refund=refund)
                assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
                assert self.inventory() == 9 and self.balance('account', self.account) == expected_account and self.balance('customer', self.customer) == expected_credit
                count = '0' if refund == 0 else '1'
                assert sql(self.state, "SELECT COUNT(*) FROM account_info WHERE type='sre' AND `class`=" + literal(identifier) + ';') == count
                assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
                self.unchanged()
            return ['Actual zero refund uses receivable credit only; full refund deducts gross113 only; both reverse back to verified original sale balances']
        self.case('sale.return_posting_zero_and_full_refunds', refund_boundaries)

        def cash_fault():
            source, identifier = self.checked_return(); frozen = self.versions([identifier]); history = self.history(identifier)
            trigger = 'qa_sre_cash_' + uuid.uuid4().hex[:12]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON account_info FOR EACH ROW BEGIN IF NEW.type='sre' AND NEW.`class`="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return refund failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_return([identifier], versions=frozen).get('code') != 10000
                self.unchanged(); assert self.versions([identifier]) == frozen and self.history(identifier) == history
                assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 0
                for table in ['room_info', 'summary', 'account_info']:
                    assert sql(self.state, "SELECT COUNT(*) FROM " + table + " WHERE type='sre' AND `class`=" + literal(identifier) + ';') == '0'
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_return([identifier], versions=frozen).get('code') == 10000
            return ['Real refund-journal MySQL failure rolls back stock/cost/source quantity/account/customer/history/version; exact frozen command retries after owned fault removal']
        self.case('sale.return_posting_refund_failure_rolls_back_inventory', cash_fault)

        def shared_source():
            source = self.posted(); identifiers = []
            for _ in range(2):
                result = self.add_return(self.return_body(source, .5)); assert result.get('code') == 10000
                identifiers.append(result['data'])
            assert self.review(identifiers, versions=self.versions(identifiers)).get('code') == 10000
            assert self.post_return(identifiers, versions=self.versions(identifiers)).get('data') == 2
            assert self.inventory() == 9 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 63
            assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 1
            assert self.post_return(identifiers, status=0, versions=self.versions(identifiers)).get('data') == 2
            self.unchanged()
            return ['Two actual checked returns sharing one sale post and reverse atomically using the complete pre-write displayed-version map']
        self.case('sale.return_posting_shared_source_batch_roundtrip', shared_source)

        def concurrent_commands():
            _, identifier = self.checked_return(); frozen = self.versions([identifier])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.post_return([identifier], versions=frozen), range(2)))
            assert sum(result.get('code') == 10000 for result in results) == 1
            assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            assert sql(self.state, "SELECT COUNT(*) FROM account_info WHERE type='sre' AND `class`=" + literal(identifier) + ';') == '1'
            return ['Concurrent same-version actual return posting has one winner and one set of stock/refund effects']
        self.case('sale.return_posting_concurrent_single_financial_effect', concurrent_commands)
        self.write_report()

    def post_source(self, body):
        identifier = self.create(body)
        assert self.request('POST', '/sale/form/check?check=true', [identifier], service='sale').get('code') == 10000
        assert self.post([identifier]).get('code') == 10000
        return identifier

    def check_from_source(self, source, quantity, serial=None):
        body = self.return_body(source, quantity)
        if serial is not None: body['salesReturnOrderInfos'][0]['serial'] = json.dumps(serial)
        result = self.add_return(body); assert result.get('code') == 10000
        identifier = result['data']
        assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
        return identifier

    def variants(self):
        def batch_serial():
            self.fixture(stock=0)
            sql(self.state, 'UPDATE goods SET batch=1,serial=1 WHERE id=' + literal(self.goods) + ';')
            incoming = self.inbound(3)
            incoming['otherInListDetailInfoDTOList'][0].update(batch='QA-SRE-BATCH', mfd='2026-11-01', serial=json.dumps(['QA-SRE-SN1', 'QA-SRE-SN2', 'QA-SRE-SN3']))
            entry = self.store('POST', '/otherin/add', incoming); self.audit(entry, 1)
            body = self.body(); body.update(money=50, account=self.account)
            body['items'][0].update(discount=1, batch='QA-SRE-BATCH', mfd='2026-11-01', serial=json.dumps(['QA-SRE-SN1', 'QA-SRE-SN2']))
            source = self.post_source(body)
            identifier = self.check_from_source(source, 1, ['QA-SRE-SN1'])
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 2 and Decimal(sql(self.state, 'SELECT nums FROM batch WHERE goods=' + literal(self.goods) + ';')) == 2
            assert sql(self.state, 'SELECT CAST(state AS SIGNED) FROM serial WHERE goods=' + literal(self.goods) + " AND number='QA-SRE-SN1';") == '0'
            assert self.balance('customer', self.customer) == 63
            assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='sre' AND `class`=" + literal(identifier) + ';')) == 2
            wrong = self.return_body(source, 1); wrong['salesReturnOrderInfos'][0]['serial'] = json.dumps(['QA-SRE-SN3'])
            assert self.add_return(wrong).get('code') != 10000
            assert self.inventory() == 2 and self.balance('customer', self.customer) == 63
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 1 and Decimal(sql(self.state, 'SELECT nums FROM batch WHERE goods=' + literal(self.goods) + ';')) == 1
            assert sql(self.state, 'SELECT CAST(state AS SIGNED) FROM serial WHERE goods=' + literal(self.goods) + " AND number='QA-SRE-SN1';") == '1'
            assert self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176
            return ['Actual batch/serial inbound and sale precede return; selected originally sold serial restores stock at source cost; unsold serial cannot return; reverse restores batch/serial/source balances']
        self.case('sale.return_posting_actual_batch_serial_roundtrip', batch_serial)

        def multiunit():
            self.fixture()
            sql(self.state, "UPDATE goods SET unit='-1',units=" + literal(json.dumps([dict(source='unit', name='box', nums=5)])) + ' WHERE id=' + literal(self.goods) + ';')
            body = self.body(); body.update(money=50, account=self.account); body['items'][0].update(unit='box', nums=1, discount=1)
            source = self.post_source(body); assert self.inventory() == 5
            identifier = self.check_from_source(source, .5)
            # Explicit new-fixture configuration change; the original sale issue remains five base units.
            sql(self.state, 'UPDATE goods SET units=' + literal(json.dumps([dict(source='unit', name='box', nums=10)])) + ' WHERE id=' + literal(self.goods) + ';')
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == Decimal('7.5')
            assert Decimal(sql(self.state, "SELECT nums FROM room_info WHERE type='sre' AND `class`=" + literal(identifier) + ';')) == Decimal('2.5')
            assert Decimal(sql(self.state, "SELECT bct FROM summary WHERE type='sre' AND `class`=" + literal(identifier) + ';')) == 5
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 5
            return ['Actual original issue five base units per box controls half-box return2.5 at cost5 despite later owned configuration change to ten per box; reverse removes exactly2.5']
        self.case('sale.return_posting_original_unit_conversion', multiunit)

        def service():
            self.fixture(stock=0); sql(self.state, 'UPDATE goods SET type=1 WHERE id=' + literal(self.goods) + ';')
            body = self.body(); body.update(money=50, account=self.account); body['items'][0]['discount'] = 1
            source = self.post_source(body)
            identifier = self.check_from_source(source, 1)
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 0 and Decimal(sql(self.state, 'SELECT nums FROM serve WHERE goods=' + literal(self.goods) + ';')) == 1
            assert self.balance('customer', self.customer) == 63
            for table in ['room_info', 'summary']:
                assert sql(self.state, "SELECT COUNT(*) FROM " + table + " WHERE type='sre' AND `class`=" + literal(identifier) + ';') == '0'
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            assert Decimal(sql(self.state, 'SELECT nums FROM serve WHERE goods=' + literal(self.goods) + ';')) == 2
            assert self.inventory() == 0 and self.balance('customer', self.customer) == 176
            return ['Actual service sale then return adjusts original service cumulative2->1->2 and receivable; never creates warehouse stock or physical summaries']
        self.case('sale.return_posting_actual_service_roundtrip', service)

        def tampered_journal():
            _, identifier = self.checked_return()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier])
            try:
                sql(self.state, "UPDATE account_info SET money=money+1 WHERE type='sre' AND `class`=" + literal(identifier) + ';')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            finally:
                sql(self.state, "UPDATE account_info SET money=25 WHERE type='sre' AND `class`=" + literal(identifier) + ';')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Explicit owned refund journal corruption cannot be hidden behind unchanged document version; marker refuses reversal with no effects; restoring exact journal permits original command']
        self.case('sale.return_posting_journal_fingerprint_protection', tampered_journal)
        self.write_report()

    def guards(self):
        def batch_insufficient_cash():
            source = self.posted(); identifiers = []
            for _ in range(2):
                body = self.return_body(source, 1); body.update(money=100, account=self.account)
                result = self.add_return(body); assert result.get('code') == 10000
                identifiers.append(result['data'])
            assert self.review(identifiers, versions=self.versions(identifiers)).get('code') == 10000
            frozen = self.versions(identifiers); history = {i: self.history(i) for i in identifiers}
            assert self.post_return(identifiers, versions=frozen).get('code') != 10000
            self.unchanged(); assert self.versions(identifiers) == frozen
            assert all(self.history(i) == history[i] and self.return_doc(i)['header']['examine'] == 0 for i in identifiers)
            assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 0
            assert self.review(identifiers, status=0, versions=frozen).get('code') == 10000
            for identifier in identifiers:
                revision = self.revision(identifier, 1); revision.update(money=25, account=self.account)
                assert self.revise_return(revision).get('code') == 10000
            assert self.review(identifiers, versions=self.versions(identifiers)).get('code') == 10000
            assert self.post_return(identifiers, versions=self.versions(identifiers)).get('data') == 2
            assert self.inventory() == 10 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
            return ['Second actual refund exceeds remaining account balance and rolls back the whole first return; actual uncheck/edit/recheck to affordable refunds permits complete batch posting']
        self.case('sale.return_posting_later_refund_insufficient_batch_atomic', batch_insufficient_cash)

        def closed_period():
            _, identifier = self.checked_return(); period = uuid.uuid4().hex; frozen = self.versions([identifier])
            try:
                sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-16', '2026-11-16', self.actor]) + ');')
                assert self.post_return([identifier], versions=frozen).get('code') != 10000
                self.unchanged(); assert self.versions([identifier]) == frozen
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.post_return([identifier], versions=frozen).get('code') == 10000
            frozen = self.versions([identifier])
            try:
                sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-16', '2026-11-16', self.actor]) + ');')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Explicit owned closed-period fixture blocks both real posting and verified reversal atomically; exact commands retry only after reopening the QA period']
        self.case('sale.return_posting_closed_period_both_directions', closed_period)

        def invoice_reference():
            _, identifier = self.checked_return()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); invoice = uuid.uuid4().hex
            try:
                sql(self.state, 'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES(' + ','.join(literal(v) for v in [invoice, 'sre', identifier, '2026-11-16', 'QA-SRE-'+invoice[:16], 'QA Return Invoice', 1]) + ');')
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            finally: sql(self.state, 'DELETE FROM invoice WHERE id=' + literal(invoice) + ';')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Explicit owned downstream invoice reference protects real return reversal; removing only that fixture permits exact original command and restores balances']
        self.case('sale.return_posting_downstream_invoice_protection', invoice_reference)

        def actual_role():
            source, identifier = self.checked_return(); frozen = self.versions([identifier]); token, role = self.role_session(); admin = self.token
            try:
                self.token = token
                assert self.post_return([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/sale/return/return/examine'], [role]):
                    assert self.request('GET','/sale/form/document/'+source,service='sale').get('code')==403
                    assert self.post_return([identifier], versions=frozen).get('code') == 10000
                assert self.post_return([identifier], status=0, versions=frozen).get('code') == 403
            finally: self.token = admin
            assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
            assert self.post_return([identifier], status=0, versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            return ['Actual new OAuth user needs its current audit grant without unrelated source-detail authorization; same token immediately loses audit after grant restoration; authorized admin can reverse verified posting']
        self.case('sale.return_posting_live_role_and_revocation', actual_role)
        self.write_report()

    def serial_options(self):
        def actual_reservations():
            self.fixture(stock=0)
            sql(self.state, 'UPDATE goods SET serial=1 WHERE id=' + literal(self.goods) + ';')
            incoming = self.inbound(3); incoming['otherInListDetailInfoDTOList'][0]['serial'] = json.dumps(['QA-OPTION-A', 'QA-OPTION-B', 'QA-OPTION-C'])
            self.audit(self.store('POST', '/otherin/add', incoming), 1)
            body = self.body(); body.update(money=50, account=self.account); body['items'][0].update(discount=1, serial=json.dumps(['QA-OPTION-A', 'QA-OPTION-B']))
            source = self.post_source(body)
            preview = self.preview(source)['data']['items'][0]
            assert preview['serialRequired'] is True and preview['availableSerials'] == ['QA-OPTION-A', 'QA-OPTION-B'] and Decimal(str(preview['serialBaseQuantity'])) == 2
            bodies = [self.return_body(source, 1) for _ in range(2)]
            for payload in bodies: payload['salesReturnOrderInfos'][0]['serial'] = json.dumps(['QA-OPTION-A'])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(self.add_return, bodies))
            assert sum(result.get('code') == 10000 for result in results) == 1
            identifier = next(result['data'] for result in results if result.get('code') == 10000)
            assert self.preview(source)['data']['items'][0]['availableSerials'] == ['QA-OPTION-B']
            duplicate = self.return_body(source, 1); duplicate['salesReturnOrderInfos'][0]['serial'] = json.dumps(['QA-OPTION-A'])
            assert self.add_return(duplicate).get('code') != 10000
            options = self.sale('GET', '/sale/return/document/' + identifier + '/source-options')
            document = self.return_doc(identifier)
            assert options['version'] == document['version'] and options['sourceVersion'] == document['sourceVersion']
            assert options['items'][0]['availableSerials'] == ['QA-OPTION-A', 'QA-OPTION-B']
            duplicate['salesReturnOrderInfos'][0]['serial'] = json.dumps(['QA-OPTION-B'])
            assert self.add_return(duplicate).get('code') == 10000
            assert self.sale('GET', '/sale/return/document/' + identifier + '/source-options')['items'][0]['availableSerials'] == ['QA-OPTION-A']
            assert self.inventory() == 1 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176
            return ['Actual source serial options exclude unsold numbers; same serial concurrent drafts have one winner even while quantity remains; own draft edit excludes only itself, preserving other draft reservations; stock/refunds unchanged']
        self.case('sale.return_serial_options_actual_reservation_and_edit', actual_reservations)
        self.write_report()

    def edges(self):
        def serial_resold():
            self.fixture(stock=0);sql(self.state,'UPDATE goods SET serial=1 WHERE id='+literal(self.goods)+';')
            incoming=self.inbound(3);incoming['otherInListDetailInfoDTOList'][0]['serial']=json.dumps(['QA-CYCLE-A','QA-CYCLE-B','QA-CYCLE-C'])
            self.audit(self.store('POST','/otherin/add',incoming),1)
            body=self.body();body.update(money=50,account=self.account);body['items'][0].update(discount=1,serial=json.dumps(['QA-CYCLE-A','QA-CYCLE-B']))
            source=self.post_source(body);identifier=self.check_from_source(source,1,['QA-CYCLE-A'])
            assert self.post_return([identifier],versions=self.versions([identifier])).get('code')==10000
            later=self.body();later['time']='2026-11-16 13:00:00';later['items'][0].update(nums=1,discount=1,serial=json.dumps(['QA-CYCLE-A']))
            sold_again=self.post_source(later)
            retry=self.return_body(source,1);retry['salesReturnOrderInfos'][0]['serial']=json.dumps(['QA-CYCLE-A'])
            assert self.add_return(retry).get('code')!=10000
            frozen=self.versions([identifier]);assert self.post_return([identifier],status=0,versions=frozen).get('code')!=10000
            assert self.inventory()==1 and self.balance('account',self.account)==150 and self.balance('customer',self.customer)==176
            assert self.post([sold_again],False).get('code')==10000
            assert self.post_return([identifier],status=0,versions=self.versions([identifier])).get('code')==10000
            assert self.inventory()==1 and self.balance('account',self.account)==150 and self.balance('customer',self.customer)==176
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM serial WHERE goods='+literal(self.goods)+" AND number='QA-CYCLE-A';")=='1'
            return ['Actual serial return then later resale cannot be returned again against old source or reversed through original return; reversing dependent resale first permits original return reversal with exact stock/serial/balance restoration']
        self.case('sale.return_posting_resold_serial_source_and_reverse_guards',serial_resold)

        def reverse_storage_failure():
            source, identifier = self.checked_return()
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            frozen = self.versions([identifier]); history = self.history(identifier); trigger = 'qa_sre_reverse_' + uuid.uuid4().hex[:12]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='sre' AND NEW.source="+literal(identifier)+" AND NEW.info='反审核销售退货单' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return reverse history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_return([identifier], status=0, versions=frozen).get('code') != 10000
                assert self.inventory() == 9 and self.balance('account', self.account) == 125 and self.balance('customer', self.customer) == 88
                assert self.versions([identifier]) == frozen and self.history(identifier) == history
                assert Decimal(sql(self.state, 'SELECT retreat FROM sell_info WHERE pid=' + literal(source) + ';')) == 1
                assert sql(self.state, 'SELECT COUNT(*) FROM psi_sale_return_posting WHERE return_id=' + literal(identifier) + ';') == '1'
            finally: sql(self.state, 'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_return([identifier], status=0, versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Actual reverse history write failure after stock/refund/source changes rolls everything back, preserving exact original version and posting proof; same command retries after owned fault removal']
        self.case('sale.return_posting_reverse_storage_failure_atomic', reverse_storage_failure)

        def reviewed_protocol():
            _, identifier, _ = self.created(); frozen = self.versions([identifier])
            for ids, versions in [([identifier], None), ([identifier], {}), ([identifier], dict(frozen, extra='0'*64)), ([identifier, identifier], frozen), (['x'+str(i) for i in range(201)], {})]:
                assert self.post_return(ids, versions=versions).get('code') != 10000
            for status in [None, -1, 2]: assert self.post_return([identifier], status=status, versions=frozen).get('code') != 10000
            assert self.post_return([identifier], versions=frozen).get('code') != 10000
            self.unchanged()
            assert self.review([identifier], versions=frozen).get('code') == 10000
            assert self.post_return([identifier], versions=frozen).get('code') != 10000
            assert self.post_return([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.inventory() == 9 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 63
            return ['Real financial endpoint requires complete unique current versions and target0/1; unchecked and pre-check frozen versions reject without effects; explicit reread after actual check permits posting']
        self.case('sale.return_posting_reviewed_protocol_and_check_required', reviewed_protocol)

        def mixed_organization():
            sources=[]; identifiers=[]; scopes=[]
            for foreign in [False, True]:
                frame=None
                if foreign:
                    frame=uuid.uuid4().hex;sql(self.state,"INSERT INTO frame(id,pid,name,sort) VALUES("+literal(frame)+",'0','QA Return Posting Foreign',0);")
                source=self.posted(frame); result=self.add_return(self.return_body(source,1));assert result.get('code')==10000
                identifier=result['data']; assert self.review([identifier],versions=self.versions([identifier])).get('code')==10000
                sources.append(source);identifiers.append(identifier);scopes.append((self.goods,self.warehouse,self.account,self.customer))
            frozen=self.versions(identifiers);histories={i:self.history(i) for i in identifiers};token,role=self.role_session();admin=self.token
            try:
                self.token=token
                with qa_resource_grants(self.state,['/sale/return/return/examine','/sale/form/getSaleDetail'],[role]):
                    assert self.post_return(identifiers,versions=frozen).get('code')==403
                    assert self.post_return([identifiers[1]],versions={identifiers[1]:'0'*64}).get('code')==403
            finally:self.token=admin
            assert self.versions(identifiers)==frozen and all(self.history(i)==histories[i] and self.return_doc(i)['header']['examine']==0 for i in identifiers)
            for goods,warehouse,account,customer in scopes:
                assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(goods)+' AND warehouse='+literal(warehouse)+';'))==8
                assert self.balance('account',account)==150 and self.balance('customer',customer)==176
            assert all(Decimal(sql(self.state,'SELECT retreat FROM sell_info WHERE pid='+literal(source)+';'))==0 for source in sources)
            return ['Real OAuth own-organization user with audit/source grants cannot post mixed or foreign batches; organization refusal precedes stale-version details; all own/foreign stock/cash/customer/history remain unchanged']
        self.case('sale.return_posting_cross_organization_batch_atomic', mixed_organization)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['baseline', 'extended', 'variants', 'guards', 'serial-options', 'edges'])
    action = parser.parse_args().action; suite = SaleReturnPostingSuite(read_state())
    if action == 'baseline': suite.baseline()
    elif action == 'extended': suite.extended()
    elif action == 'variants': suite.variants()
    elif action == 'guards': suite.guards()
    elif action == 'serial-options': suite.serial_options()
    else: suite.edges()
