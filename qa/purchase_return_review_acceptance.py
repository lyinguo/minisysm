"""Actual procurement-return check/uncheck gates. Inventory/refund posting is a separate gate."""
import argparse
import concurrent.futures
import uuid
from purchase_return_draft_acceptance import PurchaseReturnDraftSuite
from acceptance import read_state, sql, literal
from resource_fixture import qa_resource_grants, authority
from purchase_ui_acceptance import PurchaseUiSuite


class PurchaseReturnReviewSuite(PurchaseReturnDraftSuite):
    def review(self, ids, status=1, versions=None, **extra):
        body = dict(ids=ids, status=status, **extra)
        if versions is not None: body['versions'] = versions
        return self.request('POST', '/purchase-return-form/checkout', body, service='purchase')

    def versions(self, ids):
        return {identifier: self.return_doc(identifier)['version'] for identifier in ids}

    def history(self, identifier):
        return int(sql(self.state, "SELECT COUNT(*) FROM record WHERE type='bre' AND source=" + literal(identifier) + ';'))

    def run_baseline(self):
        def actual_uuid():
            _, identifier, _ = self.created()
            before = self.history(identifier)
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            assert self.return_doc(identifier)['header']['check'] == 1 and self.history(identifier) == before + 1
            self.unchanged()
            return ['Actual UUID draft check persists state/current operator history, no stock or refund movements']
        self.case('purchase.return_review_actual_uuid_check', actual_uuid)

        def empty():
            assert self.review([], versions={}).get('code') != 10000, 'Empty return selection reported success'
            return ['Empty check request is refused instead of silently reporting success']
        self.case('purchase.return_review_empty_selection_refused', empty)

        def invalid_status():
            assert self.review([], status=2, versions={}).get('code') != 10000, 'Unsupported status became uncheck success'
            return ['Unsupported status cannot fall through to an uncheck command']
        self.case('purchase.return_review_invalid_target_refused', invalid_status)
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
        self.case('purchase.return_review_roundtrip_and_idempotence', roundtrip)

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
        self.case('purchase.return_review_complete_protocol_required', protocol)

        def edited():
            _, identifier, _ = self.created(); frozen = self.versions([identifier])
            assert self.revise_return(identifier, self.revision_return(identifier, .5)).get('code') == 10000
            assert self.review([identifier], versions=frozen).get('code') != 10000
            assert self.return_doc(identifier)['header']['check'] == 0
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            self.unchanged()
            return ['Actual persisted draft edit invalidates frozen review; explicit fresh reread permits review']
        self.case('purchase.return_review_actual_edit_conflict', edited)

        def late_missing():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); missing = 'z'*32
            frozen[missing] = '0'*64; before = self.history(identifier)
            assert self.review([identifier, missing], versions=frozen).get('code') != 10000
            assert self.return_doc(identifier)['header']['check'] == 0 and self.history(identifier) == before
            self.unchanged()
            return ['Later missing member rolls back earlier actual state/history in the same transaction']
        self.case('purchase.return_review_late_member_atomic_rollback', late_missing)

        def concurrent_commands():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); before = self.history(identifier)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.review([identifier], versions=frozen), range(2)))
            assert sum(r.get('code') == 10000 for r in results) == 1
            assert self.return_doc(identifier)['header']['check'] == 1 and self.history(identifier) == before + 1
            self.unchanged()
            return ['Two concurrent actual HTTP commands with one frozen version produce exactly one successful state/history transition']
        self.case('purchase.return_review_concurrent_single_winner', concurrent_commands)

        def storage_fault():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); before = self.history(identifier)
            trigger = 'qa_review_' + uuid.uuid4().hex[:12]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bre' AND NEW.source="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.review([identifier], versions=frozen).get('code') != 10000
                assert self.return_doc(identifier)['header']['check'] == 0 and self.history(identifier) == before
                assert self.versions([identifier]) == frozen
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.review([identifier], versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Actual MySQL history failure rolls back header/version; identical command succeeds after owned fault removal']
        self.case('purchase.return_review_database_failure_rollback_retry', storage_fault)

        def live_permission():
            _, identifier, _ = self.created(); frozen = self.versions([identifier])
            role = self.success('POST', '/role/add-role', dict(name='QA Return Review ' + uuid.uuid4().hex[:8], data='', root='[]', auth='{}'))
            keyword = sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(role) + ';')
            actor, user, _ = self.new_user(role=role); token = PurchaseUiSuite.login(self, user); admin = self.token
            try:
                self.token = token
                assert self.review([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/purchase-return-form/checkout'], [authority(role, keyword)]):
                    assert self.review([identifier], versions=frozen).get('code') == 403
                with qa_resource_grants(self.state, ['/purchase-return-form/checkout', '/purchase-note/getBuildBre'], [authority(role, keyword)]):
                    assert self.review([identifier], versions=frozen).get('code') == 10000
                assert self.review([identifier], status=0, versions=frozen).get('code') == 403
            finally:
                self.token = admin
            assert self.return_doc(identifier)['header']['check'] == 1
            assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='bre' AND source=" + literal(identifier) + ' AND `user`=' + literal(actor) + ';') == '1'
            self.unchanged()
            return ['Actual new OAuth actor needs current check and original purchase detail grants; current operator persists; same token denied after revoke']
        self.case('purchase.return_review_live_oauth_permission', live_permission)

        def source_change():
            source, identifier, _ = self.created(); frozen = self.versions([identifier])
            # Explicit corruption fixture on this case's private source, not an allowed source edit.
            line = sql(self.state, 'SELECT id FROM buy_info WHERE pid=' + literal(source) + ' LIMIT 1;')
            old = sql(self.state, 'SELECT price FROM buy_info WHERE id=' + literal(line) + ';')
            try:
                sql(self.state, 'UPDATE buy_info SET price=price+1 WHERE id=' + literal(line) + ';')
                current = self.versions([identifier]); assert current != frozen, 'Source mutation did not invalidate return detail version'
                listing = self.request('GET', '/purchase-return-form/list?number=' + self.return_doc(identifier)['header']['number'] + '&pageIndex=1&pageSize=20', service='purchase')
                assert listing.get('code') == 10000 and listing['data']['rows'][0]['version'] == current[identifier], 'Return list and detail versions differ'
                assert self.review([identifier], versions=frozen).get('code') != 10000, 'Old source-bound version accepted'
                assert self.review([identifier], versions=current).get('code') != 10000, 'Return with source-inconsistent price accepted'
                assert self.return_doc(identifier)['header']['check'] == 0, 'Failed source review changed state'
            finally:
                sql(self.state, 'UPDATE buy_info SET price=' + literal(old) + ' WHERE id=' + literal(line) + ';')
            assert self.versions([identifier]) == frozen, 'Restored source does not restore original version'
            assert self.review([identifier], versions=frozen).get('code') == 10000
            self.unchanged()
            return ['Explicit private source-price corruption changes both return detail/list hashes; stale and freshly read price-inconsistent commands refuse; restoring exact owned source permits original command']
        self.case('purchase.return_review_source_snapshot_and_eligibility', source_change)
        self.write_report()


    def run_guards(self):
        def closed_period():
            _, identifier, _ = self.created(); frozen = self.versions([identifier]); period = uuid.uuid4().hex
            def close():
                sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-16', '2026-11-16', self.actor]) + ');')
            close()
            try:
                assert self.review([identifier], versions=frozen).get('code') != 10000
                assert self.versions([identifier]) == frozen
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.review([identifier], versions=frozen).get('code') == 10000
            checked = self.versions([identifier]); close()
            try:
                assert self.review([identifier], status=0, versions=checked).get('code') != 10000
                assert self.versions([identifier]) == checked
            finally: sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.review([identifier], status=0, versions=checked).get('code') == 10000
            self.unchanged()
            return ['Owned QA closed-period fixture blocks actual check and uncheck without state/version writes; original commands succeed after owned period removal']
        self.case('purchase.return_review_closed_period_both_directions', closed_period)
        def checked_protection():
            _, identifier, _ = self.created(); body = self.revision_return(identifier, .5)
            assert self.review([identifier], versions=self.versions([identifier])).get('code') == 10000
            checked = self.versions([identifier]); body['version'] = checked[identifier]
            assert self.revise_return(identifier, body).get('code') != 10000
            assert self.remove_return(identifier, checked[identifier]).get('code') != 10000
            assert self.versions([identifier]) == checked
            assert self.review([identifier], status=0, versions=checked).get('code') == 10000
            assert self.revise_return(identifier, self.revision_return(identifier, .5)).get('code') == 10000
            self.unchanged()
            return ['Actually checked draft cannot edit or delete even with current version; explicit uncheck releases editing without stock or funds movements']
        self.case('purchase.return_review_checked_edit_delete_guard', checked_protection)
        self.write_report()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['baseline', 'extended', 'guards'])
    action = parser.parse_args().action
    suite = PurchaseReturnReviewSuite(read_state())
    if action == 'baseline': suite.run_baseline()
    elif action == 'extended': suite.run_extended()
    else: suite.run_guards()
