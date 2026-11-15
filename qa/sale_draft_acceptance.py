"""Actual sale draft HTTP/MySQL acceptance; stock/funds/audit remain separate gates."""
import argparse
import json
import uuid
import concurrent.futures
import threading
import urllib.request
import urllib.parse
import subprocess
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from warehouse_acceptance import WarehouseSuite
from acceptance import QA, read_state, sql, literal


class SaleDraftSuite(WarehouseSuite):
    def __init__(self, state):
        super().__init__(state)
        self.customer = uuid.uuid4().hex
        sql(state, 'INSERT INTO customer(id,name,py,number,frame,`user`,category,grade) VALUES(' +
            ','.join(literal(value) for value in [self.customer, 'QA Sale Customer', 'qa', 'QC' + self.customer[:20], state['frame_id'], self.actor, '0', '0']) + ');')

    def body(self):
        return dict(frame=self.state['frame_id'], customer=self.customer, time='2026-11-15',
                    number='QAS' + uuid.uuid4().hex[:24], total=200, actual=226, money=0, cost=0,
                    account='', people='', logistics='', file='', data='QA actual sale draft', more='{}',
                    user=self.actor, examine=False, check=False, nucleus=0, cse=3, invoice=3,
                    items=[dict(goods=self.goods, unit='unit', warehouse=self.warehouse, price=100, nums=2, tax=.13, discount=0, attr='', serial='[]', retreat=0)])

    def sale(self, method, path, body=None):
        result = self.request(method, path, body, service='sale')
        if result.get('code') != 10000:
            (QA / 'runtime/sale-last-error.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        assert result.get('code') == 10000, 'Sale request failed; code=' + str(result.get('code'))
        return result.get('data')

    def create(self, body):
        result = self.sale('POST', '/sale/form/addSale', body)
        assert result.get('id'), 'Actual sale create did not return its persisted ID'
        return result['id']

    def baseline(self):
        def unpaid_money():
            body = self.body()
            identifier = self.create(body)
            actual = sql(self.state, 'SELECT CONCAT(total,\',\',actual,\',\',money) FROM sell WHERE id=' + literal(identifier) + ';').split(',')
            assert list(map(Decimal, actual)) == list(map(Decimal, ['200', '226', '0'])), 'Unpaid sale was recorded as received, or totals are wrong'
            return ['Actual create persists tax/amount and preserves zero received money']
        self.case('sale.draft_preserves_unpaid_money', unpaid_money)

        def omitted_discount():
            body = self.body()
            del body['items'][0]['discount']
            identifier = self.create(body)
            assert sql(self.state, 'SELECT COUNT(*) FROM sell_info WHERE pid=' + literal(identifier) + ';') == '1'
            return ['Normal frontend payload without discount can persist a real draft']
        self.case('sale.draft_omitted_discount_supported', omitted_discount)

        def reject_zero():
            body = self.body()
            body['items'][0]['nums'] = 0
            result = self.request('POST', '/sale/form/addSale', body, service='sale')
            assert result.get('code') != 10000, 'Zero-quantity sales draft accepted'
            assert sql(self.state, 'SELECT COUNT(*) FROM sell WHERE number=' + literal(body['number']) + ';') == '0', 'Rejected draft left a header'
            return ['Invalid quantity rejected without committed header/details']
        self.case('sale.draft_invalid_quantity_atomic', reject_zero)

        def duplicate_number():
            body = self.body()
            self.create(body)
            result = self.request('POST', '/sale/form/addSale', body, service='sale')
            assert result.get('code') != 10000, 'Duplicate sale number accepted'
            assert sql(self.state, 'SELECT COUNT(*) FROM sell WHERE number=' + literal(body['number']) + ';') == '1'
            return ['Actual repeated create cannot duplicate the same business number']
        self.case('sale.draft_number_unique', duplicate_number)
        self.write_report()

    def lifecycle(self):
        def detail(identifier):
            return self.sale('GET', '/sale/form/document/' + identifier)
        def edit(document):
            body = dict(document['header'])
            if 'timeEpoch' in body: body['time'] = body.pop('timeEpoch')
            body.update(version=document['version'], items=document['items'])
            return body
        def real_edit():
            body = self.body()
            body['time'] = int(datetime(2026, 11, 15, 13, 47, tzinfo=timezone(timedelta(hours=8))).timestamp() * 1000)
            body['user'] = 'forged-creator'
            identifier = self.create(body)
            initial = detail(identifier)
            assert initial['header']['user'] == self.actor and initial['header']['invoice'] == 3
            assert initial['items'][0]['goodsName'] == 'QA Stock Goods' and initial['items'][0]['goods'] == self.goods
            changed = edit(initial)
            line_id = changed['items'][0]['id']
            changed['items'][0].update(tax=.095, discount=.955)
            changed['data'] = 'QA updated real draft'
            changed['user'] = 'another-forged-creator'
            changed['total'] = 999999
            self.sale('PUT', '/sale/form/updateSale', changed)
            current = detail(identifier)
            assert current['header']['user'] == self.actor and current['items'][0]['id'] == line_id
            assert Decimal(str(current['header']['total'])) == Decimal('191') and Decimal(str(current['header']['actual'])) == Decimal('209.145')
            assert Decimal(str(current['items'][0]['tax'])) == Decimal('.095') and Decimal(str(current['items'][0]['discount'])) == Decimal('.955')
            assert sql(self.state, "SELECT DATE_FORMAT(time,'%Y-%m-%d %H:%i:%s') FROM sell WHERE id=" + literal(identifier) + ';') == '2026-11-15 13:47:00'
            assert sql(self.state, 'SELECT COUNT(*) FROM room WHERE goods=' + literal(self.goods) + ';') == '0'
            assert Decimal(sql(self.state, 'SELECT balance FROM customer WHERE id=' + literal(self.customer) + ';')) == 0
            rejected = self.request('PUT', '/sale/form/updateSale', changed, service='sale')
            assert rejected.get('code') != 10000 and detail(identifier) == current, 'Stale version overwrote current persisted draft'
            changed = edit(current)
            new_line = dict(changed['items'][0]); new_line.pop('id')
            changed['items'].append(new_line)
            self.sale('PUT', '/sale/form/updateSale', changed)
            two = detail(identifier)
            assert len(two['items']) == 2 and line_id in [line['id'] for line in two['items']]
            changed = edit(two); changed['items'] = [line for line in two['items'] if line['id'] == line_id]
            self.sale('PUT', '/sale/form/updateSale', changed)
            assert len(detail(identifier)['items']) == 1
            assert int(sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sell' AND source=" + literal(identifier) + ';')) == 4
            (QA / 'runtime/sale-browser-document.json').write_text(json.dumps({'id': identifier, 'number': body['number']}), encoding='utf-8')
            (QA / 'runtime/browser-session.json').write_text(json.dumps({'token': self.token}), encoding='utf-8')
            return ['Actual create/read/edit/add/remove lines persisted; existing detail IDs and server creator preserved', 'Tax/discount fractions retain precision and business timestamp round-trips', 'Stale update rejected; saving draft changes neither stock nor customer balance']
        self.case('sale.draft_actual_read_edit_chain', real_edit)

        def concurrent_save():
            identifier = self.create(self.body())
            body = edit(detail(identifier))
            barrier = threading.Barrier(2)
            def save(index):
                payload = json.loads(json.dumps(body)); payload['data'] = 'QA concurrent ' + str(index)
                barrier.wait()
                return self.request('PUT', '/sale/form/updateSale', payload, service='sale')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(save, [0, 1]))
            assert sum(result.get('code') == 10000 for result in results) == 1, 'Concurrent writes did not enforce one version winner'
            return ['Two simultaneous real HTTP updates with one version produce exactly one committed winner']
        self.case('sale.draft_concurrent_version_conflict', concurrent_save)

        def second_insert_failure():
            body = self.body(); marker = 'QATRIGGER' + uuid.uuid4().hex[:10]
            body['items'].append(dict(body['items'][0], data=marker))
            trigger = 'qa_sale_fail_' + uuid.uuid4().hex[:10]
            try:
                sql(self.state, 'DELIMITER $$\nCREATE TRIGGER `' + trigger + "` BEFORE INSERT ON sell_info FOR EACH ROW BEGIN IF NEW.data=" + literal(marker) + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA second detail failure'; END IF; END;$$\nDELIMITER ;\n")
                result = self.request('POST', '/sale/form/addSale', body, service='sale')
                assert result.get('code') != 10000
                assert sql(self.state, 'SELECT COUNT(*) FROM sell WHERE number=' + literal(body['number']) + ';') == '0'
                assert sql(self.state, 'SELECT COUNT(*) FROM sell_info WHERE data=' + literal(marker) + ';') == '0'
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            return ['MySQL refuses second detail after first insert; header and all details roll back']
        self.case('sale.draft_storage_failure_rolls_back', second_insert_failure)

        def unsigned_identity():
            body = self.body()
            request = urllib.request.Request('http://127.0.0.1:18022/sale/form/addSale', data=json.dumps(body).encode('utf-8'),
                                            headers={'Content-Type': 'application/json', 'user': json.dumps({'id': self.actor, 'authorities': ['ROLE_ADMIN']})})
            with self.opener.open(request, timeout=20) as response: result = json.load(response)
            assert result.get('code') in (401, 403), 'Unsigned caller identity could create a draft'
            assert sql(self.state, 'SELECT COUNT(*) FROM sell WHERE number=' + literal(body['number']) + ';') == '0'
            return ['Forged identity header without signed credential cannot persist sales data']
        self.case('sale.draft_unsigned_identity_rejected', unsigned_identity)
        self.write_report()

    def security(self):
        def role_and_frame():
            prefix='QASEC'+uuid.uuid4().hex[:18]
            own_body=self.body();own_body['number']=prefix+'A'
            own_id = self.create(own_body)
            foreign_frame = uuid.uuid4().hex
            sql(self.state, "INSERT INTO frame(id,pid,name,sort) VALUES(" + literal(foreign_frame) + ",'0','QA Other Sales Org',0);")
            foreign_body = self.body(); foreign_body['frame'] = foreign_frame;foreign_body['number']=prefix+'B'
            foreign_id = self.create(foreign_body)
            foreign_before = self.sale('GET', '/sale/form/document/' + foreign_id)
            entry_id, _ = self.create_inbound(3)
            self.audit(entry_id, 1)
            role = self.success('POST', '/role/add-role', {'name': 'QA Sales Access ' + uuid.uuid4().hex[:7], 'data': '', 'root': '[]', 'auth': '{}'})
            keyword = sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(role) + ';')
            user_id, user, _ = self.new_user(role=role)
            client = json.loads((QA / 'runtime/oauth-client.json').read_text(encoding='utf-8'))
            request = urllib.request.Request('http://127.0.0.1:18002/oauth/token', data=urllib.parse.urlencode(dict(grant_type='password', client_id=client['mgr-id'], client_secret=client['mgr-password'], username=user['user'], password=user['pwd'])).encode())
            with self.opener.open(request, timeout=20) as response: authenticated = json.load(response)
            token = authenticated.get('token') or authenticated.get('access_token')
            assert token, 'New isolated role account could not authenticate'
            container = 'psi-qa-redis-' + self.state['database'][len('psi_qa_'):]
            actual = subprocess.run(['docker', 'ps', '--filter', 'publish=18379', '--format', '{{.Names}}'], capture_output=True, text=True, check=True).stdout.strip()
            assert actual == container, 'Refusing to alter an unverified Redis instance'
            def redis(*arguments):
                return subprocess.run(['docker', 'exec', container, 'redis-cli', '--raw'] + list(arguments), capture_output=True, text=True, check=True).stdout.rstrip('\r\n')
            paths = ['/sale/form/getSaleList', '/sale/form/getSaleDetail', '/sale/form/addSale', '/sale/form/updateSale', '/sale/form/check', '/sale/form/examine']
            previous = {path: (redis('HEXISTS', 'AUTH:RESOURCE_ROLES', path), redis('HGET', 'AUTH:RESOURCE_ROLES', path)) for path in paths}
            admin = self.token
            try:
                self.token = token
                for path in paths: redis('HDEL', 'AUTH:RESOURCE_ROLES', path)
                assert self.request('GET', '/sale/form/getSaleList', service='sale').get('code') == 403, 'Role without query grant could query sales'
                assert self.request('GET', '/sale/form/document/' + own_id, service='sale').get('code') == 403
                assert self.request('POST', '/sale/form/check?check=true', [own_id], service='sale').get('code') == 403
                assert self.request('POST', '/sale/form/examine?examine=true', [own_id], service='sale').get('code') == 403
                grants = json.dumps(['java.util.ArrayList', [keyword]])
                for path in paths: redis('HSET', 'AUTH:RESOURCE_ROLES', path, grants)
                own = self.sale('GET', '/sale/form/document/' + own_id)
                assert own['header']['id'] == own_id
                listing = self.sale('GET', '/sale/form/getSaleList?pageIndex=1&pageSize=200&number='+prefix+'&authorizedFrame=' + foreign_frame)
                assert listing.get('total')==1 and own_id in [row['id'] for row in listing.get('rows', [])] and foreign_id not in [row['id'] for row in listing.get('rows', [])], 'Caller could override organization scope'
                assert self.request('GET', '/sale/form/document/' + foreign_id, service='sale').get('code') == 403
                blocked = self.body(); blocked['frame'] = foreign_frame
                assert self.request('POST', '/sale/form/addSale', blocked, service='sale').get('code') == 403
                assert sql(self.state, 'SELECT COUNT(*) FROM sell WHERE number=' + literal(blocked['number']) + ';') == '0'
                changed = dict(foreign_before['header']); changed.update(time=changed.pop('timeEpoch'), version=foreign_before['version'], items=foreign_before['items'])
                assert self.request('PUT', '/sale/form/updateSale', changed, service='sale').get('code') == 403
                assert self.request('POST', '/sale/form/check?check=true', [foreign_id], service='sale').get('code') == 403
                assert self.request('POST', '/sale/form/examine?examine=true', [foreign_id], service='sale').get('code') == 403
                self.sale('POST', '/sale/form/check?check=true', [own_id])
                self.sale('POST', '/sale/form/examine?examine=true', [own_id])
                assert self.inventory() == 1
                redis('HDEL', 'AUTH:RESOURCE_ROLES', '/sale/form/examine')
                assert self.request('POST', '/sale/form/examine?examine=false', [own_id], service='sale').get('code') == 403
                assert self.inventory() == 1, 'Revoked posting permission changed stock'
                redis('HSET', 'AUTH:RESOURCE_ROLES', '/sale/form/examine', grants)
                self.sale('POST', '/sale/form/examine?examine=false', [own_id])
                assert self.inventory() == 3
                redis('HDEL', 'AUTH:RESOURCE_ROLES', '/sale/form/getSaleDetail')
                assert self.request('GET', '/sale/form/document/' + own_id, service='sale').get('code') == 403, 'Cached credential ignored permission revocation'
                self.token = admin
                other_role = self.success('POST', '/role/add-role', {'name': 'QA Sales Revoked ' + uuid.uuid4().hex[:7], 'data': '', 'root': '[]', 'auth': '{}'})
                self.success('PUT', '/user/mod-user', {'id': user_id, 'role': other_role})
                self.token = token
                assert self.request('GET', '/sale/form/getSaleList', service='sale').get('code') == 403, 'Old token retained a role removed in the database'
            finally:
                self.token = admin
                for path, (exists, value) in previous.items():
                    if exists == '1': redis('HSET', 'AUTH:RESOURCE_ROLES', path, value)
                    else: redis('HDEL', 'AUTH:RESOURCE_ROLES', path)
            assert self.sale('GET', '/sale/form/document/' + foreign_id) == foreign_before, 'Unauthorized mutation changed another organization document'
            return ['Actual OAuth sign-in for a newly created role/user; Redis fixtures touch only verified QA Redis and are restored', 'Ungranted access denied, granted access allowed, foreign organization read/create/update denied, supplied scope ignored', 'Permission revocation and actual user-role change take effect with the existing token; no existing business account modified']
        self.case('sale.draft_real_role_and_organization_authorization', role_and_frame)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['baseline', 'lifecycle', 'security'], nargs='?', default='baseline')
    args = parser.parse_args()
    suite = SaleDraftSuite(read_state())
    getattr(suite, args.action)()
