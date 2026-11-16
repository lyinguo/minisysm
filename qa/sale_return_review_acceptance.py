"""Actual sales-return check/uncheck gates. Inventory/refund posting is a separate gate."""
import argparse
import concurrent.futures
import uuid
from sale_return_draft_acceptance import SaleReturnDraftSuite
from acceptance import read_state, sql, literal
from resource_fixture import qa_resource_grants


class SaleReturnReviewSuite(SaleReturnDraftSuite):
    def review(self, ids, status=1, versions=None, **extra):
        body = dict(ids=ids, status=status, **extra)
        if versions is not None: body['versions'] = versions
        return self.request('POST', '/sale/return/return/check', body, service='sale')

    def versions(self, ids):
        return {identifier: self.return_doc(identifier)['version'] for identifier in ids}

    def history(self, identifier):
        return int(sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sre' AND source=" + literal(identifier) + ';'))

    def run_baseline(self):
        def actual_uuid():
            _, identifier, _ = self.created()
            before = self.history(identifier)
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.return_doc(identifier)['header']['check'] == 1 and self.history(identifier) == before + 1
            self.unchanged()
            return ['Actual UUID draft check persists state/current operator history, no stock or refund movements']
        self.case('sale.return_review_actual_uuid_check', actual_uuid)

        def empty():
            assert self.review([], versions={}).get('code') != 10000, 'Empty return selection reported success'
            return ['Empty check request is refused instead of silently reporting success']
        self.case('sale.return_review_empty_selection_refused', empty)

        def invalid_status():
            assert self.review([], status=2, versions={}).get('code') != 10000, 'Unsupported status became uncheck success'
            return ['Unsupported status cannot fall through to an uncheck command']
        self.case('sale.return_review_invalid_target_refused', invalid_status)
        self.write_report()

    def run_extended(self):
        def roundtrip():
            _, identifier, _ = self.created()
            frozen = self.versions([identifier]); before = self.history(identifier)
            assert self.review([identifier], versions=frozen).get('data') == 1
            assert self.review([identifier], status=0, versions=frozen).get('code') != 10000
            checked = self.versions([identifier]); assert checked != frozen
            assert self.review([identifier], versions=checked).get('data') == 0
            assert self.history(identifier) == before + 1
            assert self.review([identifier], status=0, versions=checked).get('data') == 1
            assert self.return_doc(identifier)['header']['check'] == 0
            assert self.history(identifier) == before + 2
            self.unchanged()
            return ['Real check/uncheck changes versions and history; stale retry rejected; fresh same-target retry adds no history; funds and stock unchanged']
        self.case('sale.return_review_roundtrip_and_idempotence', roundtrip)

        def protocol():
            _, identifier, _ = self.created(); frozen = self.versions([identifier])
            before = self.history(identifier)
            for ids, versions in [([identifier], None), ([identifier], {}), ([identifier], {identifier: 'bad'}),
                                  ([identifier], dict(frozen, unknown='0'*64)), ([identifier, identifier], frozen),
                                  (['x'+str(i) for i in range(201)], {})]:
                assert self.review(ids, versions=versions).get('code') != 10000
            for status in [None, -1, 2]:
                assert self.review([identifier], status=status, versions=frozen).get('code') != 10000
            assert self.review([identifier], versions=frozen, version=frozen[identifier]).get('code') != 10000
            assert self.history(identifier) == before and self.return_doc(identifier)['header']['check'] == 0
            self.unchanged()
            return ['Actual HTTP rejects incomplete/extra/duplicate/oversized versions, mixed version protocols and invalid targets without writes']
        self.case('sale.return_review_complete_protocol_required', protocol)

        def edited():
            _, identifier, _ = self.created(); frozen = self.versions([identifier])
            assert self.revise_return(self.revision(identifier, .5)).get('code') == 10000
            assert self.review([identifier], versions=frozen).get('code') != 10000
            assert self.return_doc(identifier)['header']['check'] == 0
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            return ['Actual persisted draft edit invalidates frozen review; explicit fresh reread permits review']
        self.case('sale.return_review_actual_edit_conflict', edited)

        def late_missing():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); missing = 'z'*32
            frozen[missing] = '0'*64; before = self.history(identifier)
            assert self.review([identifier, missing], versions=frozen).get('code') != 10000
            assert self.return_doc(identifier)['header']['check'] == 0 and self.history(identifier) == before
            self.unchanged()
            return ['Later missing member rolls back earlier actual state/history in the same transaction']
        self.case('sale.return_review_late_member_atomic_rollback', late_missing)

        def concurrent_commands():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); before = self.history(identifier)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.review([identifier], versions=frozen), range(2)))
            assert sum(r.get('code') == 10000 for r in results) == 1
            assert self.return_doc(identifier)['header']['check'] == 1 and self.history(identifier) == before + 1
            self.unchanged()
            return ['Two concurrent actual HTTP commands with one frozen version produce exactly one successful state/history transition']
        self.case('sale.return_review_concurrent_single_winner', concurrent_commands)

        def storage_fault():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); before = self.history(identifier)
            trigger = 'qa_review_' + uuid.uuid4().hex[:12]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='sre' AND NEW.source="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.review([identifier], versions=frozen).get('code') != 10000
                assert self.return_doc(identifier)['header']['check'] == 0 and self.history(identifier) == before
                assert self.versions([identifier]) == frozen
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.review([identifier], versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Actual MySQL history failure rolls back header/version; identical command succeeds after owned fault removal']
        self.case('sale.return_review_database_failure_rollback_retry', storage_fault)

        def live_permission():
            source, identifier, _ = self.created(); frozen = self.versions([identifier])
            token, role = self.role_session(); admin = self.token
            try:
                self.token = token
                assert self.review([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/sale/return/return/check'], [role]):
                    assert self.request('GET','/sale/form/document/'+source,service='sale').get('code')==403
                    assert self.request('GET', '/sale/return/document/' + identifier + '/source-options', service='sale').get('code') == 403
                    assert self.review([identifier], versions=frozen).get('code') == 10000
                assert self.review([identifier], status=0, versions=frozen).get('code') == 403
            finally:
                self.token = admin
            assert self.return_doc(identifier)['header']['check'] == 1
            self.unchanged()
            return ['New actual OAuth role needs only its current check grant; unrelated source detail remains denied; same token loses access immediately after revoke']
        self.case('sale.return_review_live_oauth_permission', live_permission)

        def source_change():
            source, identifier, _ = self.created(); frozen = self.versions([identifier])
            # Explicit corruption fixture on this case's private source, not an allowed source edit.
            line = sql(self.state, 'SELECT id FROM sell_info WHERE pid=' + literal(source) + ' LIMIT 1;')
            old = sql(self.state, 'SELECT price FROM sell_info WHERE id=' + literal(line) + ';')
            try:
                sql(self.state, 'UPDATE sell_info SET price=price+1 WHERE id=' + literal(line) + ';')
                current = self.versions([identifier]); assert current != frozen, 'Source mutation did not invalidate return detail version'
                listing = self.request('GET', '/sale/return/saleReturnList?id=' + identifier + '&pageIndex=1&pageSize=20', service='sale')
                assert listing.get('code') == 10000 and listing['data']['rows'][0]['version'] == current[identifier], 'Return list and detail versions differ'
                assert self.review([identifier], versions=frozen).get('code') != 10000, 'Old source-bound version accepted'
                assert self.review([identifier], versions=current).get('code') != 10000, 'Return with source-inconsistent price accepted'
                assert self.return_doc(identifier)['header']['check'] == 0, 'Failed source review changed state'
            finally:
                sql(self.state, 'UPDATE sell_info SET price=' + literal(old) + ' WHERE id=' + literal(line) + ';')
            assert self.versions([identifier]) == frozen, 'Restored source does not restore original version'
            assert self.review([identifier], versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Explicit private source-price corruption changes both return detail/list hashes; stale and freshly read price-inconsistent commands refuse; restoring exact owned source permits original command']
        self.case('sale.return_review_source_snapshot_and_eligibility', source_change)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['baseline', 'extended'])
    action = parser.parse_args().action
    suite = SaleReturnReviewSuite(read_state())
    if action == 'baseline': suite.run_baseline()
    else: suite.run_extended()
