"""Actual sales review-snapshot baseline; isolated OAuth/HTTP/MySQL only.

Failing cases are recorded as gaps, never as completed business acceptance.
"""
import argparse
import uuid
import concurrent.futures
import time
from sale_posting_acceptance import SalePostingSuite
from acceptance import Suite, read_state, sql, literal


class SaleSnapshotSuite(SalePostingSuite):
    def edit(self, identifier, qty=3, received=0):
        document = self.document(identifier)
        body = dict(document['header'])
        if 'timeEpoch' in body:
            body['time'] = body.pop('timeEpoch')
        body.update(version=document['version'], items=document['items'], money=received,
                    account=self.account if received else '')
        body['items'][0].update(nums=qty, discount=1)
        return self.request('PUT', '/sale/form/updateSale', body, service='sale')

    def batch(self, ids, versions, target=True, audit=False, **extra):
        return self.request('POST', '/sale/form/' + ('examine?examine=' if audit else 'check?check=') + str(target).lower(),
                            dict(ids=ids, versions=versions, **extra), service='sale')

    def versions(self, ids):
        return {identifier: self.document(identifier)['version'] for identifier in ids}

    def document(self, identifier):
        return self.sale('GET', '/sale/form/document/' + identifier)

    def command(self, identifier, target=True, audit=False, version=None, unversioned=False):
        body = dict(ids=[identifier])
        if not unversioned:
            body['version'] = version or self.document(identifier)['version']
        return self.request('POST', '/sale/form/' + ('examine?examine=' if audit else 'check?check=') + str(target).lower(), body, service='sale')

    def fresh(self):
        self.fixture()
        return self.create(self.body())

    def history(self, identifier):
        return int(sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sell' AND source=" + literal(identifier) + ';'))

    def unchanged(self):
        assert self.inventory() == 10
        assert self.balance('account', self.account) == 100
        assert self.balance('customer', self.customer) == 0

    def baseline(self):
        def check_requires_review():
            identifier = self.fresh()
            assert self.command(identifier, unversioned=True).get('code') != 10000, 'Unversioned request checked a real sales document'
            assert self.document(identifier)['header']['check'] == 0
            self.unchanged()
            return ['Unversioned check refused without state, inventory or funds changes']
        self.case('sale.snapshot_check_requires_review', check_requires_review)

        def audit_requires_review():
            identifier = self.fresh()
            assert self.command(identifier).get('code') == 10000
            assert self.command(identifier, audit=True, unversioned=True).get('code') != 10000, 'Unversioned request actually posted inventory and receivable'
            self.unchanged()
            return ['Unversioned posting refused with actual inventory and receivable unchanged']
        self.case('sale.snapshot_audit_requires_review', audit_requires_review)

        def roundtrip():
            identifier = self.fresh()
            before = self.document(identifier)['version']
            assert self.command(identifier).get('code') == 10000
            assert self.command(identifier, False).get('code') == 10000
            assert self.document(identifier)['version'] != before, 'Check/uncheck resurrected the old page version'
            self.unchanged()
            return ['Actual check/uncheck invalidates previously read drafts']
        self.case('sale.snapshot_roundtrip_invalidates_old_page', roundtrip)

        def history():
            identifier = self.fresh()
            before = self.history(identifier)
            assert self.command(identifier).get('code') == 10000
            assert self.history(identifier) == before + 1, 'Successful check has no persisted operator history'
            assert self.command(identifier, False).get('code') == 10000
            assert self.history(identifier) == before + 2
            assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sell' AND source=" + literal(identifier) + ' AND `user`=' + literal(self.actor) + ';') == str(before + 2)
            self.unchanged()
            return ['Check and uncheck each persist actual current-operator history']
        self.case('sale.snapshot_check_operator_history', history)

        def old_edit():
            identifier = self.fresh()
            document = self.document(identifier)
            assert self.command(identifier).get('code') == 10000
            assert self.command(identifier, False).get('code') == 10000
            body = dict(document['header'])
            if 'timeEpoch' in body:
                body['time'] = body.pop('timeEpoch')
            body.update(version=document['version'], items=document['items'], data='QA stale snapshot edit')
            assert self.request('PUT', '/sale/form/updateSale', body, service='sale').get('code') != 10000, 'Old editor saved after an intervening check/uncheck'
            self.unchanged()
            return ['Old editor cannot save after actual review-state roundtrip']
        self.case('sale.snapshot_roundtrip_rejects_old_editor', old_edit)

        def closed_period():
            identifier = self.fresh()
            period = uuid.uuid4().hex
            sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-15', '2026-11-15', self.actor]) + ');')
            try:
                assert self.command(identifier).get('code') != 10000, 'Closed-period document was checked'
                self.unchanged()
            finally:
                sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            return ['Closed-period check refused; only the self-created QA period is removed']
        self.case('sale.snapshot_closed_period_check', closed_period)
        self.write_report()

    def extended(self):
        def listing():
            identifier = self.fresh()
            document = self.document(identifier)
            result = self.sale('GET', '/sale/form/getSaleList?pageIndex=1&pageSize=10&number=' + document['header']['number'])
            assert len(result['rows']) == 1 and result['rows'][0]['version'] == document['version']
            assert len(document['version']) == 64
            self.unchanged()
            return ['Actual list and detail expose the same canonical SHA256 review snapshot']
        self.case('sale.snapshot_list_matches_detail', listing)

        def exact_versions():
            identifier = self.fresh()
            versions = self.versions([identifier])
            before = self.history(identifier)
            for malformed in [{}, {identifier: 'bad'}, {identifier: None}, dict(versions, **{uuid.uuid4().hex: '0' * 64})]:
                assert self.batch([identifier], malformed).get('code') != 10000
            assert self.batch([identifier], versions, version=versions[identifier]).get('code') != 10000
            # The former JSON-array endpoint must be refused too, not just a missing object property.
            try:
                result = Suite.request(self, 'POST', '/sale/form/check?check=true', [identifier], service='sale')
            except AssertionError as error:
                assert str(error) == 'HTTP 400 at /sale/form/check'
            else:
                assert result.get('code') != 10000
            assert self.history(identifier) == before and self.document(identifier)['header']['check'] == 0
            self.unchanged()
            return ['Missing, malformed, extra or mixed versions and the old array endpoint cannot bypass review']
        self.case('sale.snapshot_exact_versions_and_legacy_refused', exact_versions)

        def stale_check():
            identifier = self.fresh()
            old = self.document(identifier)['version']
            assert self.edit(identifier).get('code') == 10000
            assert self.command(identifier, version=old).get('code') != 10000
            assert self.document(identifier)['header']['check'] == 0
            assert self.command(identifier).get('code') == 10000
            self.unchanged()
            return ['Actual newer saved quantities reject the older check snapshot; fresh review succeeds']
        self.case('sale.snapshot_stale_check_rejected', stale_check)

        def stale_audit():
            identifier = self.fresh()
            assert self.command(identifier).get('code') == 10000
            old = self.document(identifier)['version']
            assert self.command(identifier, False).get('code') == 10000
            assert self.edit(identifier).get('code') == 10000 and self.command(identifier).get('code') == 10000
            before = self.history(identifier)
            assert self.command(identifier, audit=True, version=old).get('code') != 10000
            assert self.history(identifier) == before
            self.unchanged()
            return ['Old checked page cannot post newer saved and checked quantities; no stock/cash/receivable movements']
        self.case('sale.snapshot_stale_audit_rejected', stale_audit)

        def check_batch():
            first = self.fresh()
            second = self.create(self.body())
            ids = sorted([first, second])
            versions = self.versions(ids)
            assert self.edit(ids[1]).get('code') == 10000
            before = [self.history(i) for i in ids]
            assert self.batch(ids, versions).get('code') != 10000
            assert [self.history(i) for i in ids] == before
            assert all(self.document(i)['header']['check'] == 0 for i in ids)
            assert self.batch(ids, self.versions(ids)).get('code') == 10000
            self.unchanged()
            return ['Stale later member rolls back the whole check batch including earlier operator history; fresh retry works']
        self.case('sale.snapshot_stale_check_batch_atomic', check_batch)

        def audit_batch():
            self.fixture()
            body = self.body(); body.update(money=50, account=self.account); body['items'][0]['discount'] = 1
            ids = sorted([self.create(body), self.create(dict(body, number='QAS' + uuid.uuid4().hex[:24]))])
            assert self.batch(ids, self.versions(ids)).get('code') == 10000
            versions = self.versions(ids)
            assert self.command(ids[1], False).get('code') == 10000
            assert self.edit(ids[1], qty=2, received=50).get('code') == 10000
            assert self.command(ids[1]).get('code') == 10000
            before = [self.history(i) for i in ids]
            assert self.batch(ids, versions, audit=True).get('code') != 10000
            assert [self.history(i) for i in ids] == before
            for i in ids:
                assert self.document(i)['header']['examine'] == 0
                assert all(self.ledger_count(table, i) == 0 for table in ['room_info', 'account_info', 'summary'])
            self.unchanged()
            assert self.batch(ids, self.versions(ids), audit=True).get('code') == 10000
            assert self.inventory() == 6 and self.balance('account', self.account) == 200 and self.balance('customer', self.customer) == 352
            assert self.batch(ids, self.versions(ids), False, audit=True).get('code') == 10000
            self.unchanged()
            return ['Stale later audit member rolls back earlier stock/cash/receivable/history; fresh batch posts4/100/352 and reverses exactly']
        self.case('sale.snapshot_stale_audit_batch_financial_rollback', audit_batch)

        def race():
            identifier = self.fresh()
            version = self.document(identifier)['version']
            before = self.history(identifier)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.command(identifier, version=version), range(2)))
            assert sum(r.get('code') == 10000 for r in results) == 1
            assert self.history(identifier) == before + 1
            assert self.command(identifier).get('code') == 10000 and self.history(identifier) == before + 1
            self.unchanged()
            return ['Same reviewed version has one concurrent winner; explicit fresh same-target retry is idempotent']
        self.case('sale.snapshot_concurrent_same_review', race)

        def failure():
            identifier = self.fresh()
            version = self.document(identifier)['version']
            before = self.history(identifier)
            trigger = 'qa_sale_review_' + uuid.uuid4().hex[:10]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `" + trigger + "` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source=" + literal(identifier) + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA sale review history fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.command(identifier, version=version).get('code') != 10000
                assert self.document(identifier)['version'] == version and self.history(identifier) == before
                assert self.document(identifier)['header']['check'] == 0
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            assert self.command(identifier, version=version).get('code') == 10000
            self.unchanged()
            return ['Actual MySQL history-write fault rolls back check and version; exact old command retries after removing fault']
        self.case('sale.snapshot_history_failure_atomic_retry', failure)

        def lifecycle():
            self.fixture()
            body = self.body(); body.update(money=50, account=self.account); body['items'][0]['discount'] = 1
            identifier = self.create(body)
            assert self.command(identifier).get('code') == 10000
            checked = self.document(identifier)['version']
            assert self.command(identifier, audit=True, version=checked).get('code') == 10000
            assert self.inventory() == 8 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176
            assert self.command(identifier, False, audit=True).get('code') == 10000
            self.unchanged()
            assert self.command(identifier, audit=True, version=checked).get('code') != 10000
            assert self.command(identifier, False).get('code') == 10000
            self.unchanged()
            return ['Actual check/post/reverse/uncheck posts2 units/50 cash/176 receivable and restores all; pre-post snapshot cannot post again']
        self.case('sale.snapshot_reviewed_real_lifecycle', lifecycle)

        def list_read_race():
            from read_gate import list_read_gate
            identifier = self.fresh()
            document = self.document(identifier)
            path = '/sale/form/getSaleList?pageIndex=1&pageSize=10&number=' + document['header']['number']
            with list_read_gate(self.state, 'sale') as gate:
                (gate / 'armed').write_text('armed', encoding='ascii')
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(self.sale, 'GET', path)
                    deadline = time.monotonic() + 8
                    while not (gate / 'entered').exists() and time.monotonic() < deadline:
                        time.sleep(.025)
                    assert (gate / 'entered').exists(), 'Actual list did not reach bounded scheduling gate'
                    try:
                        assert self.edit(identifier).get('code') == 10000
                    finally:
                        (gate / 'resume').write_text('resume', encoding='ascii')
                    result = pending.result(timeout=15)
                    assert not (gate / 'timed-out').exists()
                    assert len(result['rows']) == 1
                    row = result['rows'][0]
                    assert row['version'] == document['version'] and row['actual'] == document['header']['actual']
            latest = self.document(identifier)
            assert latest['version'] != document['version']
            assert self.sale('GET', path)['rows'][0]['version'] == latest['version']
            self.unchanged()
            return ['Actual list paused after header read; concurrent HTTP save cannot mix old displayed amounts with a new review version; temporary QA agent removed in finally']
        self.case('sale.snapshot_actual_list_read_race', list_read_race)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['baseline', 'run'])
    args = parser.parse_args()
    suite = SaleSnapshotSuite(read_state())
    suite.baseline()
    if args.action == 'run':
        suite.extended()
