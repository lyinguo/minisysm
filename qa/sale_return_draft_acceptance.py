"""Real sales-return draft acceptance; saving must not post/refund inventory or funds."""
import argparse
import re
import uuid
import copy
import concurrent.futures
import json
import urllib.request
from decimal import Decimal
from sale_return_preview_acceptance import SaleReturnPreviewSuite
from acceptance import QA, read_state, sql, literal
from resource_fixture import qa_resource_grants, authority
from purchase_ui_acceptance import PurchaseUiSuite


class SaleReturnDraftSuite(SaleReturnPreviewSuite):
    create_resource = '/sale/return/addSalesReturnOrder'

    def return_body(self, source, quantity=1):
        preview = self.preview(source)
        assert preview.get('code') == 10000
        item = preview['data']['items'][0]
        return dict(source=source, sourceVersion=preview['data']['sourceVersion'],
                    number='QARD' + uuid.uuid4().hex[:24], time='2026-11-16 12:00:00',
                    customer=self.customer, user=self.actor, money=0, cost=0, total=100, actual=113,
                    examine=0, check=0, nucleus=0, cse=3, invoice=3, data='QA persisted return draft',
                    salesReturnOrderInfos=[dict(source=item['source'], goods=self.goods, unit='unit', warehouse=self.warehouse,
                        nums=quantity, price=100, total=100, tax=.13, tat=13, tpt=113, discount=1, dsc=0, serial='[]')])

    def add_return(self, body):
        return self.request('POST', '/sale/return/addSalesReturnOrder', body, service='sale')

    def count_return(self, number):
        return int(sql(self.state, 'SELECT COUNT(*) FROM sre WHERE number=' + literal(number) + ';'))

    def return_doc(self, identifier):
        return self.sale('GET', '/sale/return/document/' + identifier)

    def created(self, quantity=1):
        source = self.posted(); body = self.return_body(source, quantity)
        result = self.add_return(body)
        assert result.get('code') == 10000 and re.fullmatch('[0-9a-f]{32}', str(result.get('data', '')))
        return source, result['data'], body

    def revision(self, identifier, quantity=1):
        document = self.return_doc(identifier)
        body = dict(document['header'])
        body.update(version=document['version'], sourceVersion=document['sourceVersion'], time=document['header']['timeText'], salesReturnOrderInfos=document['items'])
        body['salesReturnOrderInfos'][0]['nums'] = quantity
        return body

    def revise_return(self, body):
        return self.request('PUT', '/sale/return/updateSalesReturnOrder', body, service='sale')

    def remove_return(self, identifier, version):
        return self.request('DELETE', '/sale/return/document/' + identifier, dict(version=version), service='sale')

    def baseline(self):
        def uuid_source():
            source = self.posted(); body = self.return_body(source)
            result = self.add_return(body)
            assert result.get('code') == 10000 and re.fullmatch('[0-9a-f]{32}', str(result.get('data', ''))), 'Create must return the actual persisted UUID, not a success phrase'
            identifier = result['data']
            assert sql(self.state, 'SELECT source FROM sre WHERE id=' + literal(identifier) + ';') == source
            assert sql(self.state, 'SELECT source FROM sre_info WHERE pid=' + literal(identifier) + ';') == body['salesReturnOrderInfos'][0]['source']
            assert sql(self.state, 'SELECT frame FROM sre WHERE id=' + literal(identifier) + ';') == self.state['frame_id']
            self.unchanged()
            return ['Actual UUID source line persists with actual header ID, source organization and unchanged inventory/cash/receivable']
        self.case('sale.return_draft_actual_uuid_source_persistence', uuid_source)

        def states():
            source = self.posted(); body = self.return_body(source)
            # Omit source only in this negative case so the former Integer binder
            # cannot hide the independently unsafe forged approval write.
            body['salesReturnOrderInfos'][0].pop('source')
            body.update(examine=1, check=1, nucleus=2)
            assert self.add_return(body).get('code') != 10000, 'Draft create accepted forged approval/settlement states'
            assert self.count_return(body['number']) == 0
            self.unchanged()
            return ['Forged review/approval/settlement states cannot persist a header or stock/funds changes']
        self.case('sale.return_draft_forged_states_atomic', states)

        def unposted():
            source = self.posted(); body = self.return_body(source)
            body['salesReturnOrderInfos'][0].pop('source')
            body['source'] = self.create(self.body())
            assert self.add_return(body).get('code') != 10000, 'Unposted source accepted by actual draft create'
            assert self.count_return(body['number']) == 0
            self.unchanged()
            return ['Actual unchecked source is rejected without a return header']
        self.case('sale.return_draft_requires_actual_posted_source', unposted)

        def permission():
            source = self.posted(); body = self.return_body(source)
            body['salesReturnOrderInfos'][0].pop('source')
            token, _ = self.role_session(); admin = self.token
            try:
                self.token = token
                with qa_resource_grants(self.state, [self.create_resource], []):
                    assert self.add_return(body).get('code') == 403, 'Ungranting the actual role did not prevent draft creation'
            finally:
                self.token = admin
            assert self.count_return(body['number']) == 0
            self.unchanged()
            return ['New role/user actual OAuth session cannot create without the live create grant']
        self.case('sale.return_draft_actual_create_permission', permission)

        def number_unique():
            source = self.posted(); body = self.return_body(source)
            assert self.add_return(body).get('code') == 10000
            assert self.add_return(body).get('code') != 10000, 'Duplicate return number accepted'
            assert self.count_return(body['number']) == 1
            self.unchanged()
            return ['Repeated create cannot persist a duplicate business number']
        self.case('sale.return_draft_number_unique', number_unique)

        def invalid_line():
            source = self.posted(); body = self.return_body(source)
            body['salesReturnOrderInfos'][0].pop('source')
            body['salesReturnOrderInfos'].append(dict(body['salesReturnOrderInfos'][0], nums=0))
            assert self.add_return(body).get('code') != 10000, 'Invalid second line was persisted'
            assert self.count_return(body['number']) == 0
            self.unchanged()
            return ['Invalid second line rejects the whole draft without partially persisted header/details']
        self.case('sale.return_draft_invalid_second_line_atomic', invalid_line)
        self.write_report()

    def extended(self):
        def edit_and_delete():
            source, identifier, body = self.created()
            original = self.return_doc(identifier)
            listing = self.sale('GET', '/sale/return/saleReturnList?pageIndex=1&pageSize=10&id=' + body['number'])
            assert listing['total'] == 1 and listing['rows'][0]['version'] == original['version']
            assert listing['rows'][0]['cse'] == 3 and listing['rows'][0]['invoice'] == 3 and type(listing['rows'][0]['examine']) is int
            assert len(self.sale('GET', '/sale/return/' + identifier)) == 1
            payload = self.revision(identifier, 1.5); payload['money'] = 50; payload['account'] = self.account
            payload['user'] = 'forged-editor'
            assert self.revise_return(payload).get('code') == 10000
            changed = self.return_doc(identifier)
            assert changed['version'] != original['version'] and changed['header']['actual'] == 169.5
            assert changed['header']['money'] == 50 and changed['header']['user'] == self.actor
            assert changed['items'][0]['id'] == original['items'][0]['id'] and changed['items'][0]['nums'] == 1.5
            assert self.revise_return(payload).get('code') != 10000
            assert self.remove_return(identifier, original['version']).get('code') != 10000
            assert self.remove_return(identifier, changed['version']).get('code') == 10000
            assert self.count_return(body['number']) == 0 and sql(self.state, 'SELECT COUNT(*) FROM sre_info WHERE pid=' + literal(identifier) + ';') == '0'
            assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sre' AND source=" + literal(identifier) + ';') == '3'
            assert self.preview(source)['data']['items'][0]['available'] == 2
            self.unchanged()
            return ['Actual create/list/full and legacy detail/version edit/stale refusal/delete preserve line IDs, real operator and history; deleting releases1.5 reserved units without stock/refund changes']
        self.case('sale.return_draft_real_edit_delete_lifecycle', edit_and_delete)

        def authoritative():
            source = self.posted(discount=.955, tax=.095)
            body = self.return_body(source)
            body.update(total=9999, actual=9999, user='forged-creator')
            body['salesReturnOrderInfos'][0].update(goods='forged-product', warehouse='forged-warehouse', unit='forged-unit', price=9999, total=9999, tax=99, discount=99)
            result = self.add_return(body); assert result.get('code') == 10000
            document = self.return_doc(result['data']); row = document['items'][0]
            assert document['header']['user'] == self.actor and document['header']['frame'] == self.state['frame_id']
            assert row['goods'] == self.goods and row['warehouse'] == self.warehouse and row['unit'] == 'unit' and row['price'] == 100
            assert Decimal(str(row['discount'])) == Decimal('.955') and Decimal(str(row['tax'])) == Decimal('.095')
            assert Decimal(str(row['total'])) == Decimal('95.5') and Decimal(str(row['tpt'])) == Decimal('104.5725')
            assert self.inventory() == 8 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == Decimal('159.145')
            return ['Real create ignores forged product/unit/price/totals/operator, uses authoritative source and persists .955/.095 rates with exact95.5/104.5725 amounts']
        self.case('sale.return_draft_authoritative_source_amounts_and_rates', authoritative)

        def bounds():
            source = self.posted()
            for quantity in [0, -1, None, '.00001', 3]:
                body = self.return_body(source, quantity)
                assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
            body = self.return_body(source); body['salesReturnOrderInfos'].append(dict(body['salesReturnOrderInfos'][0]))
            assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
            self.unchanged()
            return ['Actual zero/negative/missing/overprecision/overavailable quantities and duplicate source lines are wholly rejected']
        self.case('sale.return_draft_actual_quantity_bounds', bounds)

        def race():
            source = self.posted()
            bodies = [self.return_body(source, 1.5), self.return_body(source, 1.5)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(self.add_return, bodies))
            assert sum(result.get('code') == 10000 for result in results) == 1
            assert sum(self.count_return(body['number']) for body in bodies) == 1
            assert self.preview(source)['data']['items'][0]['available'] == .5
            self.unchanged()
            return ['Two actual concurrent1.5-unit requests against2 units produce one persisted winner and .5 remaining, no overreservation or inventory/funds changes']
        self.case('sale.return_draft_concurrent_last_quantity', race)

        def repeated_number():
            source = self.posted(); body = self.return_body(source, .5)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(self.add_return, [copy.deepcopy(body), copy.deepcopy(body)]))
            assert sum(result.get('code') == 10000 for result in results) == 1 and self.count_return(body['number']) == 1
            self.unchanged()
            return ['Actual concurrent duplicate-number submits produce one persisted draft']
        self.case('sale.return_draft_concurrent_business_number', repeated_number)

        def stale_source():
            source = self.posted(); body = self.return_body(source)
            assert self.post([source], False).get('code') == 10000 and self.post([source]).get('code') == 10000
            assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
            self.unchanged()
            return ['Actual source reverse/repost roundtrip invalidates the previously displayed source version without accepting a return']
        self.case('sale.return_draft_stale_source_refused', stale_source)

        def refund_metadata():
            source = self.posted()
            for money, account in [(114, self.account), (50, ''), (-1, self.account), ('.00001', self.account), (1, uuid.uuid4().hex)]:
                body = self.return_body(source); body.update(money=money, account=account)
                assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
            body = self.return_body(source); body.update(money=50, account=self.account)
            result = self.add_return(body); assert result.get('code') == 10000 and self.return_doc(result['data'])['header']['money'] == 50
            self.unchanged()
            return ['Invalid planned refunds/accounts reject atomically; valid planned50 is stored but never debits cash or changes receivable']
        self.case('sale.return_draft_planned_refund_has_no_posting', refund_metadata)

        def history_fault():
            source = self.posted(); body = self.return_body(source)
            trigger = 'qa_return_history_' + uuid.uuid4().hex[:10]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `" + trigger + "` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='sre' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA return history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            assert self.add_return(body).get('code') == 10000
            self.unchanged()
            return ['Actual MySQL history failure rolls back real return header/details and reserved quantities; same payload retries after fault removal']
        self.case('sale.return_draft_history_failure_atomic_retry', history_fault)

        def closed_period():
            source, identifier, body = self.created(); revision = self.revision(identifier)
            period = uuid.uuid4().hex
            sql(self.state, 'INSERT INTO period(id,date,time,`user`) VALUES(' + ','.join(literal(v) for v in [period, '2026-11-16', '2026-11-16', self.actor]) + ');')
            try:
                assert self.add_return(self.return_body(source, .5)).get('code') != 10000
                assert self.revise_return(revision).get('code') != 10000
                assert self.remove_return(identifier, revision['version']).get('code') != 10000
            finally:
                sql(self.state, 'DELETE FROM period WHERE id=' + literal(period) + ';')
            assert self.return_doc(identifier)['version'] == revision['version']
            self.unchanged()
            return ['Explicit QA closed period blocks actual create/edit/delete; self-created period removed in finally, persisted draft unchanged']
        self.case('sale.return_draft_closed_period_crud_refused', closed_period)

        def storage_fault():
            self.fixture(); sale_body = self.body(); sale_body.update(money=50, account=self.account)
            sale_body['items'][0]['discount'] = 1; sale_body['items'].append(dict(sale_body['items'][0]))
            source = self.create(sale_body)
            assert self.request('POST', '/sale/form/check?check=true', [source], service='sale').get('code') == 10000 and self.post([source]).get('code') == 10000
            preview = self.preview(source); assert preview.get('code') == 10000 and len(preview['data']['items']) == 2
            body = self.return_body(source)
            marker = 'QA return detail ' + uuid.uuid4().hex[:10]
            body['salesReturnOrderInfos'].append(dict(body['salesReturnOrderInfos'][0], source=preview['data']['items'][1]['source'], data=marker))
            trigger = 'qa_return_detail_' + uuid.uuid4().hex[:10]
            sql(self.state, "DELIMITER $$\nCREATE TRIGGER `" + trigger + "` BEFORE INSERT ON sre_info FOR EACH ROW BEGIN IF NEW.data=" + literal(marker) + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA second return line failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.add_return(body).get('code') != 10000 and self.count_return(body['number']) == 0
                assert sql(self.state, 'SELECT COUNT(*) FROM sre_info WHERE data=' + literal(marker) + ';') == '0'
            finally:
                sql(self.state, 'DROP TRIGGER IF EXISTS `' + trigger + '`;')
            result = self.add_return(body); assert result.get('code') == 10000 and len(self.return_doc(result['data'])['items']) == 2
            assert self.inventory() == 6 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 402
            return ['Actual two-line posted source, real MySQL second-return-line failure: header/first line/reservations all roll back, exact request retries to a two-line draft without refund or stock changes']
        self.case('sale.return_draft_second_storage_failure_atomic', storage_fault)

        def permissions_and_scope():
            source = self.posted(); body = self.return_body(source)
            role = self.success('POST', '/role/add-role', dict(name='QA Return CRUD ' + uuid.uuid4().hex[:8], data='', root='[]', auth='{}'))
            actor, user, _ = self.new_user(role=role); token = PurchaseUiSuite.login(self, user)
            keyword = authority(role, sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(role) + ';'))
            paths = [self.create_resource, '/sale/form/getSaleDetail', '/sale/return/{id}', '/sale/return/saleReturnList', '/sale/return/updateSalesReturnOrder', '/sale/return/deleteSalesReturnOrder']
            admin = self.token
            try:
                self.token = token
                with qa_resource_grants(self.state, paths, [keyword]):
                    result = self.add_return(body); assert result.get('code') == 10000
                    identifier = result['data']; document = self.return_doc(identifier)
                    assert document['header']['user'] == actor and document['header']['frame'] == self.state['frame_id']
                    payload = self.revision(identifier, 1.5)
                    assert self.revise_return(payload).get('code') == 10000
                    current = self.return_doc(identifier)
                    with qa_resource_grants(self.state, ['/sale/return/updateSalesReturnOrder'], []):
                        assert self.revise_return(self.revision(identifier)).get('code') == 403
                    assert self.remove_return(identifier, current['version']).get('code') == 10000
                    with qa_resource_grants(self.state, [self.create_resource], []):
                        assert self.add_return(body).get('code') == 403
            finally:
                self.token = admin
            assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='sre' AND source=" + literal(identifier) + ' AND `user`=' + literal(actor) + ';') == '3'
            self.unchanged()
            return ['New role actual OAuth session creates/reads/edits/deletes with live grants and actual operator history; same-token create/update revocation refuses immediately; QA resource grants restored']
        self.case('sale.return_draft_real_role_crud_and_revocation', permissions_and_scope)

        def foreign_scope():
            frame = uuid.uuid4().hex
            sql(self.state, "INSERT INTO frame(id,pid,name,sort) VALUES(" + literal(frame) + ",'0','QA Other Return Draft Org',0);")
            source = self.posted(frame); body = self.return_body(source)
            result = self.add_return(body); assert result.get('code') == 10000; identifier = result['data']
            token, keyword = self.role_session(); admin = self.token
            try:
                self.token = token
                with qa_resource_grants(self.state, [self.create_resource, '/sale/form/getSaleDetail', '/sale/return/{id}', '/sale/return/saleReturnList', '/sale/return/updateSalesReturnOrder', '/sale/return/deleteSalesReturnOrder'], [keyword]):
                    assert self.request('GET', '/sale/return/document/' + identifier, service='sale').get('code') == 403
                    assert self.request('GET', '/sale/return/' + identifier, service='sale').get('code') == 403
                    assert self.sale('GET', '/sale/return/saleReturnList?id=' + body['number'] + '&authorizedFrame=' + frame)['total'] == 0
                    assert self.add_return(dict(body, number='QARD' + uuid.uuid4().hex[:24])).get('code') == 403
                    assert self.remove_return(identifier, 'a' * 64).get('code') == 403
            finally:
                self.token = admin
            assert self.count_return(body['number']) == 1
            self.unchanged()
            return ['Granted own-organization user cannot read legacy/full detail, list, create or delete a foreign return; forged query scope is ignored']
        self.case('sale.return_draft_cross_organization_crud_refused', foreign_scope)

        def accounts():
            source, identifier, body = self.created(2)
            number = sql(self.state, 'SELECT number FROM account WHERE id=' + literal(self.account) + ';')
            result = self.sale('GET', '/sale/return/accounts?updating=true&source=' + source + '&keyword=' + number)
            assert len(result) == 1 and result[0]['id'] == self.account and 'balance' not in result[0]
            assert all(row['frame'] in ('0', self.state['frame_id']) for row in result)
            assert self.revise_return(self.revision(identifier, 2)).get('code') == 10000
            self.unchanged()
            return ['Actual scoped account-name/number lookup still works when this draft reserves the full source quantity; editing full quantity excludes only its own existing reservation']
        self.case('sale.return_draft_full_quantity_edit_and_account_options', accounts)

        def rounding_capacity():
            self.fixture(); payload = self.body(); payload['items'][0].update(nums=3, price=.3333, discount=1)
            source = self.create(payload)
            assert self.request('POST', '/sale/form/check?check=true', [source], service='sale').get('code') == 10000 and self.post([source]).get('code') == 10000
            bodies = [self.return_body(source) for _ in range(3)]
            identifiers = []
            for body in bodies:
                result = self.add_return(body); assert result.get('code') == 10000; identifiers.append(result['data'])
            assert Decimal(str(self.return_doc(identifiers[-1])['items'][0]['tat'])) == Decimal('.0434')
            values = sql(self.state, 'SELECT SUM(i.total),SUM(i.tat),SUM(i.tpt) FROM sre_info i JOIN sre s ON s.id=i.pid WHERE s.source=' + literal(source) + ';').split('\t')
            assert list(map(Decimal, values)) == [Decimal('.9999'), Decimal('.1300'), Decimal('1.1299')]
            assert self.inventory() == 7 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == Decimal('1.1299')
            return ['Three actual partial drafts allocate final .0001 tax remainder once; cumulative net/tax/gross exactly match original .9999/.1300/1.1299, with no refunds or stock changes']
        self.case('sale.return_draft_cumulative_amount_rounding_capacity', rounding_capacity)

        def omitted_metadata():
            source = self.posted(); body = self.return_body(source)
            body.update(cost=1.2345, money=50, account=self.account, logistics='QA return tracking', more='{"qa":"preserved"}')
            result = self.add_return(body); assert result.get('code') == 10000; identifier = result['data']
            # Explicit self-created legacy attachment metadata: never fetched or migrated.
            sql(self.state, 'UPDATE sre SET file=' + literal('https://example.invalid/qa-legacy.txt') + ' WHERE id=' + literal(identifier) + ';')
            payload = self.revision(identifier)
            for field in ['money', 'cost', 'account', 'people', 'logistics', 'more', 'file']:
                payload.pop(field, None)
            payload['data'] = 'QA changed remark only'
            assert self.revise_return(payload).get('code') == 10000
            head = self.return_doc(identifier)['header']
            assert head['money'] == 50 and Decimal(str(head['cost'])) == Decimal('1.2345') and head['account'] == self.account
            assert head['logistics'] == 'QA return tracking' and head['more'] == '{"qa":"preserved"}' and head['file'] == 'https://example.invalid/qa-legacy.txt'
            assert head['data'] == 'QA changed remark only'
            self.unchanged()
            return ['Actual versioned remark edit preserves omitted planned refund/cost/account/tracking/more and explicit QA legacy file metadata without fetching it or changing funds']
        self.case('sale.return_draft_omitted_metadata_preserved', omitted_metadata)

        def legacy_delete():
            source, identifier, body = self.created(.5)
            assert self.request('DELETE', '/sale/return/deleteSalesReturnOrder?id=' + identifier, service='sale').get('code') != 10000
            assert self.count_return(body['number']) == 1
            version = self.return_doc(identifier)['version']
            assert self.request('DELETE', '/sale/return/deleteSalesReturnOrder?id=' + identifier + '&version=' + version, service='sale').get('code') == 10000
            assert self.count_return(body['number']) == 0 and self.preview(source)['data']['items'][0]['available'] == 2
            self.unchanged()
            return ['Actual legacy query-parameter delete cannot bypass mandatory review version; fresh version deletes the same free draft and releases quantities without stock/funds movements']
        self.case('sale.return_draft_legacy_delete_requires_version', legacy_delete)
        self.write_report()


def prepare_browser():
    suite = SaleReturnDraftSuite(read_state()); source = suite.posted()
    fixture = {key: getattr(suite, key) for key in ['goods', 'warehouse', 'customer', 'account', 'actor']}
    fixture.update(database=suite.state['database'], source=source, source_number=sql(suite.state, 'SELECT number FROM sell WHERE id=' + literal(source) + ';'),
                   account_number=sql(suite.state, 'SELECT number FROM account WHERE id=' + literal(suite.account) + ';'),
                   return_number='QARUI' + uuid.uuid4().hex[:20])
    (QA / 'runtime/sale-return-draft-browser.json').write_text(json.dumps(fixture), encoding='utf-8')
    (QA / 'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)), encoding='utf-8')
    print('Prepared real QA source: ' + fixture['source_number'])
    print('Use return number: ' + fixture['return_number'])
    print('Search planned-refund account number: ' + fixture['account_number'])


def verify_browser(edited):
    state = read_state(); path = QA / 'runtime/sale-return-draft-browser.json'; fixture = json.loads(path.read_text(encoding='utf-8'))
    assert fixture['database'] == state['database'] and state['sale_port'] == 18022
    rows = sql(state, 'SELECT id FROM sre WHERE number=' + literal(fixture['return_number']) + ';').splitlines()
    assert len(rows) == 1; identifier = rows[0]
    token = json.loads((QA / 'runtime/browser-session.json').read_text(encoding='utf-8'))['token']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        request = urllib.request.Request('http://127.0.0.1:18022' + path, headers={'Authorization': 'Bearer ' + token})
        with opener.open(request, timeout=20) as response: result = json.load(response)
        assert result.get('code') == 10000
        return result['data']
    document = get('/sale/return/document/' + identifier); head = document['header']; item = document['items'][0]
    assert len(document['items']) == 1 and head['source'] == fixture['source'] and head['user'] == fixture['actor']
    assert head['money'] == 50 and head['actual'] == (169.5 if edited else 113) and head['examine'] == head['check'] == head['nucleus'] == 0
    assert item['nums'] == (1.5 if edited else 1) and item['goods'] == fixture['goods'] and item['warehouse'] == fixture['warehouse']
    assert sql(state, "SELECT COUNT(*) FROM record WHERE type='sre' AND source=" + literal(identifier) + ' AND `user`=' + literal(fixture['actor']) + ';') == ('2' if edited else '1')
    if edited:
        assert fixture['id'] == identifier and fixture['line_id'] == item['id'] and fixture['version'] != document['version']
        assert head['data'] == 'QA browser revised persisted draft'
    else:
        if 'version' in fixture: assert fixture['version'] == document['version']
        fixture.update(id=identifier, line_id=item['id'], version=document['version']); path.write_text(json.dumps(fixture), encoding='utf-8')
    assert Decimal(sql(state, 'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods=' + literal(fixture['goods']) + ' AND warehouse=' + literal(fixture['warehouse']) + ';')) == 8
    assert Decimal(sql(state, 'SELECT balance FROM account WHERE id=' + literal(fixture['account']) + ';')) == 150
    assert Decimal(sql(state, 'SELECT balance FROM customer WHERE id=' + literal(fixture['customer']) + ';')) == 176
    for table in ['room_info', 'account_info', 'summary']:
        assert sql(state, 'SELECT COUNT(*) FROM ' + table + " WHERE LOWER(type)='sre' AND `class`=" + literal(identifier) + ';') == '0'
    assert sql(state, 'SELECT COUNT(*) FROM sre_bill WHERE pid=' + literal(identifier) + ';') == '0'
    assert get('/sale/form/getGenerateReturnData?saleId=' + fixture['source'])['items'][0]['available'] == (.5 if edited else 1)
    stage = 'edited' if edited else 'saved'
    (QA / ('reports/sale-return-draft-browser-' + stage + '.json')).write_text(json.dumps(dict(status='verified', stage=stage, quantity=item['nums'], actual=head['actual'], planned_refund=50, stock=8, account=150, receivable=176, production_business_writes=0, all_system_features_accepted=False), indent=2), encoding='utf-8')
    print('PASS actual browser ' + stage + ': real draft/line/operator/version/reservation verified, planned50 only; stock8/cash150/receivable176 unchanged; no refund journals')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['baseline', 'run', 'prepare', 'verify-saved', 'verify-edited'])
    action = parser.parse_args().action
    if action == 'prepare': prepare_browser()
    elif action.startswith('verify-'): verify_browser(action == 'verify-edited')
    else:
        suite = SaleReturnDraftSuite(read_state()); suite.baseline()
        if action == 'run': suite.extended()
