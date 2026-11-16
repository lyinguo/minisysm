"""Real stock document HTTP acceptance against the isolated MySQL database."""
import argparse
import json
import urllib.parse
import urllib.request
import uuid
import concurrent.futures
import threading
from decimal import Decimal
from acceptance import Suite, QA, read_state, sql, literal, authenticate_registered_login


class WarehouseSuite(Suite):
    def __init__(self, state):
        super().__init__(state)
        self.actor, payload, _ = self.new_user()
        # Fixture authorization is isolated: never grant roles to existing users.
        sql(state, 'UPDATE `user` SET role=\'0\' WHERE id=' + literal(self.actor) + ';')
        self.actor_login = payload['user']
        client = json.loads((QA / 'runtime/oauth-client.json').read_text(encoding='utf-8'))
        parameters = {'grant_type': 'password', 'client_id': client['mgr-id'], 'client_secret': client['mgr-password'],
                      'username': payload['user'], 'password': payload['pwd']}
        if getattr(self,'through_gateway',False):
            self.token=authenticate_registered_login(state,payload['user'],payload['pwd'],self.opener)
        else:
            request = urllib.request.Request('http://127.0.0.1:18002/oauth/token',
                                            data=urllib.parse.urlencode(parameters).encode())
            with self.opener.open(request, timeout=20) as response:
                result = json.load(response)
            self.token = result.get('token') or result.get('access_token')
        assert self.token, 'Isolated stock actor could not actually authenticate'
        self.goods = uuid.uuid4().hex
        self.warehouse = uuid.uuid4().hex
        sql(state, 'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES(' +
            ','.join(literal(value) for value in [self.goods, 'QA Stock Goods', 'qa', 'QG' + self.goods[:16], '0', 'unit', 2, 3, 0, 0, '{}']) + ');')
        sql(state, 'INSERT INTO warehouse(id,name,number,frame) VALUES(' +
            ','.join(literal(value) for value in [self.warehouse, 'QA Stock Warehouse', 'QW' + self.warehouse[:16], state['frame_id']]) + ');')

    def store(self, method, path, body=None):
        result = self.request(method, path, body, service='store')
        if result.get('code') != 10000:
            (QA / 'runtime/warehouse-last-error.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        assert result.get('code') == 10000, 'Stock request failed at ' + path.split('?')[0] + '; code=' + str(result.get('code'))
        return result.get('data')

    def inbound(self, quantity=4):
        return {'supplier': '', 'frame': self.state['frame_id'], 'time': '2026-11-14 10:00:00',
                'number': 'QAIN' + uuid.uuid4().hex[:24], 'type': 0, 'total': quantity * 2, 'cost': 0,
                'examine': 0, 'cse': 3, 'check': 0, 'user': self.actor_login, 'data': 'QA real stock acceptance',
                'file': [], 'more': {}, 'costDTOList': [],
                'otherInListDetailInfoDTOList': [{'goods': self.goods, 'attr': '', 'unit': 'unit',
                    'warehouse': self.warehouse, 'price': 2, 'nums': quantity, 'total': quantity * 2, 'data': ''}]}

    def baseline(self):
        def forged_header():
            forged = urllib.parse.quote(json.dumps({'id': self.actor, 'user_name': self.actor_login,
                'frameId': self.state['frame_id'], 'authorities': ['ROLE_ADMIN']}))
            request = urllib.request.Request('http://127.0.0.1:18020/transfer/report-documents/entry', headers={'user': forged})
            try:
                with self.opener.open(request, timeout=20) as response:
                    result = json.load(response)
                assert result.get('code') in (401, 403), 'Forged user header bypassed authentication or returned an unrelated server error'
            except urllib.error.HTTPError as error:
                assert error.code in (401, 403)
            return ['Unsigned identity header cannot read protected warehouse documents']
        self.case('stock.forged_identity_header_cannot_authenticate', forged_header)
        def empty_rollback():
            body = self.inbound()
            body['otherInListDetailInfoDTOList'] = []
            result = self.request('POST', '/otherin/add', body, service='store')
            assert result.get('code') != 10000, 'Empty document was accepted'
            count = sql(self.state, 'SELECT COUNT(*) FROM entry WHERE number=' + literal(body['number']) + ';')
            assert count == '0', 'Rejected empty document left ' + count + ' committed header rows'
            return ['Actual invalid create rejected; no header persisted']
        self.case('stock.invalid_empty_create_has_no_partial_header', empty_rollback)

        def normal_create():
            body = self.inbound()
            self.store('POST', '/otherin/add', body)
            rows = sql(self.state, 'SELECT COUNT(*) FROM entry e JOIN entry_info i ON i.pid=e.id WHERE e.number=' + literal(body['number']) + ';')
            assert rows == '1', 'Header and detail did not persist together'
            assert sql(self.state, 'SELECT COUNT(*) FROM room WHERE goods=' + literal(self.goods) + ';') == '0', 'Draft creation changed actual stock'
            return ['Actual document create persists header/detail atomically', 'Draft does not change stock']
        self.case('stock.actual_inbound_create', normal_create)
        self.write_report()

    def create_inbound(self, quantity=4):
        payload = self.inbound(quantity)
        identifier = self.store('POST', '/otherin/add', payload)
        assert isinstance(identifier, str) and len(identifier) == 32, 'Create must return the persisted document ID'
        return identifier, payload

    def detail(self, identifier):
        return self.store('GET', '/transfer/report-documents/entry/' + identifier)

    def audit(self, identifier, target, version=None):
        version = version or self.detail(identifier)['version']
        return self.store('POST', '/transfer/report-documents/entry/' + identifier + '/audit', {'target': target, 'version': version})

    def inventory(self):
        return Decimal(sql(self.state, 'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods=' + literal(self.goods) + ' AND warehouse=' + literal(self.warehouse) + ';'))

    def lifecycle(self):
        def full_draft_edit():
            identifier, payload = self.create_inbound()
            before = self.inventory()
            original = self.detail(identifier)
            payload.update(id=identifier, version=original['version'], user='forged-creator')
            payload['otherInListDetailInfoDTOList'].append(dict(payload['otherInListDetailInfoDTOList'][0], nums=2, total=4))
            self.store('PUT', '/otherin/update', payload)
            changed = self.detail(identifier)
            assert len(changed['items']) == 2 and Decimal(str(changed['header']['total'])) == 12
            assert changed['header']['user'] == self.actor and self.inventory() == before
            rejected = self.request('PUT', '/otherin/update', payload, service='store')
            assert rejected.get('code') != 10000 and self.detail(identifier) == changed
            payload['version'] = changed['version']
            payload['otherInListDetailInfoDTOList'] = payload['otherInListDetailInfoDTOList'][:1]
            self.store('PUT', '/otherin/update', payload)
            assert len(self.detail(identifier)['items']) == 1
            self.audit(identifier, 1)
            payload['version'] = self.detail(identifier)['version']
            assert self.request('PUT', '/otherin/update', payload, service='store').get('code') != 10000
            self.audit(identifier, 0)
            assert self.inventory() == before
            return ['Actual full draft update adds/removes lines, preserves creator and stock', 'Stale and audited full updates rejected']
        self.case('stock.inbound_full_draft_edit', full_draft_edit)

        def actual_chain():
            before = self.inventory()
            identifier, payload = self.create_inbound()
            assert self.inventory() == before
            detail = self.detail(identifier)
            assert detail['header']['number'] == payload['number'] and len(detail['items']) == 1
            assert detail['header']['user'] == self.actor, 'Client-provided creator was trusted'
            detail['items'][0]['nums'] = 5
            saved = self.store('PUT', '/transfer/report-documents/entry/' + identifier,
                               {key: detail[key] for key in ['version', 'header', 'items']})
            assert Decimal(str(saved['header']['total'])) == 10 and self.inventory() == before
            assert sql(self.state, "SELECT DATE_FORMAT(time,'%Y-%m-%d %H:%i:%s') FROM entry WHERE id=" + literal(identifier) + ';') == payload['time'], 'Date round-trip changed business time'
            audited = self.audit(identifier, 1, saved['version'])
            assert audited['header']['examine'] == 1 and self.inventory() == before + 5
            for table in ['room_info', 'summary']:
                assert sql(self.state, 'SELECT COUNT(*) FROM ' + table + ' WHERE `class`=' + literal(identifier) + ';') == '1'
            self.audit(identifier, 0, audited['version'])
            assert self.inventory() == before and self.detail(identifier)['header']['examine'] == 0
            for table in ['room_info', 'summary']:
                assert sql(self.state, 'SELECT COUNT(*) FROM ' + table + ' WHERE `class`=' + literal(identifier) + ';') == '0'
            assert int(sql(self.state, 'SELECT COUNT(*) FROM record WHERE source=' + literal(identifier) + ';')) >= 4
            return ['Actual create -> detail -> edit -> audit -> reverse HTTP chain', 'Independent MySQL quantities and stock/summary ledgers match',
                    'Draft does not change inventory; reverse restores original quantities', 'Creator comes from authenticated identity and operation records persist']
        self.case('stock.inbound_actual_full_lifecycle', actual_chain)

        def concurrent_audit():
            before = self.inventory()
            identifier, _ = self.create_inbound()
            version = self.detail(identifier)['version']
            barrier = threading.Barrier(4)
            def execute(_):
                barrier.wait(timeout=10)
                return self.audit(identifier, 1, version)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(execute, range(4)))
            assert self.inventory() == before + 4, 'Concurrent audit applied stock more than once'
            assert sql(self.state, 'SELECT COUNT(*) FROM room_info WHERE `class`=' + literal(identifier) + ';') == '1'
            self.audit(identifier, 1, version)
            assert self.inventory() == before + 4
            self.audit(identifier, 0)
            assert self.inventory() == before
            return ['Four real concurrent audit requests add inventory exactly once', 'Repeated stale-target audit is idempotent', 'Exactly one stock ledger remains before reversal']
        self.case('stock.inbound_repeated_and_concurrent_audit', concurrent_audit)

        def duplicate_number():
            number = self.inbound()['number']
            barrier = threading.Barrier(4)
            def execute(_):
                body = self.inbound()
                body['number'] = number
                barrier.wait(timeout=10)
                return self.request('POST', '/otherin/add', body, service='store').get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                codes = list(pool.map(execute, range(4)))
            count = sql(self.state, 'SELECT COUNT(*) FROM entry WHERE number=' + literal(number) + ';')
            assert count == '1' and codes.count(10000) == 1, 'Concurrent document numbers were not unique'
            return ['Four concurrent creates with one business number persist exactly one document']
        self.case('stock.inbound_concurrent_document_number', duplicate_number)

        def later_failure():
            payload = self.inbound()
            bad = dict(payload['otherInListDetailInfoDTOList'][0])
            bad['goods'] = uuid.uuid4().hex
            payload['otherInListDetailInfoDTOList'].append(bad)
            before = self.inventory()
            result = self.request('POST', '/otherin/add', payload, service='store')
            assert result.get('code') != 10000
            assert sql(self.state, 'SELECT COUNT(*) FROM entry WHERE number=' + literal(payload['number']) + ';') == '0'
            assert self.inventory() == before
            return ['Invalid second detail rejects entire HTTP create; no header or stock changes persist']
        self.case('stock.inbound_invalid_second_line_atomic', later_failure)

        def persistence_failure():
            payload = self.inbound()
            first_marker = 'QA first ' + uuid.uuid4().hex[:16]
            reject_marker = 'QA reject ' + uuid.uuid4().hex[:16]
            payload['otherInListDetailInfoDTOList'][0]['data'] = first_marker
            second = dict(payload['otherInListDetailInfoDTOList'][0])
            second['data'] = reject_marker
            payload['otherInListDetailInfoDTOList'].append(second)
            trigger = 'qa_fail_entry_' + uuid.uuid4().hex[:12]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER " + trigger + " BEFORE INSERT ON entry_info FOR EACH ROW BEGIN IF NEW.data=" +
                literal(reject_marker) + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA controlled persistence failure'; END IF; END$$\nDELIMITER ;")
            try:
                result = self.request('POST', '/otherin/add', payload, service='store')
                assert result.get('code') != 10000
                assert sql(self.state, 'SELECT COUNT(*) FROM entry WHERE number=' + literal(payload['number']) + ';') == '0'
                assert sql(self.state, 'SELECT COUNT(*) FROM entry_info WHERE data=' + literal(first_marker) + ';') == '0'
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS ' + trigger + ';')
            return ['Real MySQL rejects second insert after first insert', 'Transaction rolls back both the header and the first persisted detail']
        self.case('stock.inbound_storage_failure_rolls_back_first_insert', persistence_failure)

        def stale_and_audited_edit():
            identifier, _ = self.create_inbound()
            original = self.detail(identifier)
            changed = json.loads(json.dumps(original))
            changed['header']['data'] = 'QA newer edit'
            self.store('PUT', '/transfer/report-documents/entry/' + identifier, {key: changed[key] for key in ['version', 'header', 'items']})
            current = self.detail(identifier)
            rejected = self.request('PUT', '/transfer/report-documents/entry/' + identifier,
                                    {key: original[key] for key in ['version', 'header', 'items']}, service='store')
            assert rejected.get('code') != 10000 and self.detail(identifier) == current, 'Stale save overwrote newer data'
            self.audit(identifier, 1, current['version'])
            audited = self.detail(identifier)
            rejected = self.request('PUT', '/transfer/report-documents/entry/' + identifier,
                                    {key: audited[key] for key in ['version', 'header', 'items']}, service='store')
            assert rejected.get('code') != 10000 and self.detail(identifier) == audited, 'Audited document was edited'
            self.audit(identifier, 0)
            return ['Old version cannot overwrite a committed edit', 'Audited document cannot be edited; rejected requests leave data unchanged']
        self.case('stock.inbound_stale_and_audited_edits_rejected', stale_and_audited_edit)

        def save_second_line_rollback():
            payload = self.inbound()
            payload['otherInListDetailInfoDTOList'].append(dict(payload['otherInListDetailInfoDTOList'][0]))
            identifier = self.store('POST', '/otherin/add', payload)
            original = self.detail(identifier)
            changed = json.loads(json.dumps(original))
            changed['items'][0]['nums'] = 8
            changed['items'][1]['nums'] = 0
            rejected = self.request('PUT', '/transfer/report-documents/entry/' + identifier,
                                    {key: changed[key] for key in ['version', 'header', 'items']}, service='store')
            assert rejected.get('code') != 10000 and self.detail(identifier) == original, 'Partial line update survived a failed save'
            return ['Second invalid line fails actual save; earlier SQL line updates are rolled back']
        self.case('stock.inbound_edit_failure_rolls_back_previous_line', save_second_line_rollback)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['baseline', 'lifecycle'])
    arguments = parser.parse_args()
    suite = WarehouseSuite(read_state())
    if arguments.action == 'baseline': suite.baseline()
    else: suite.lifecycle()
