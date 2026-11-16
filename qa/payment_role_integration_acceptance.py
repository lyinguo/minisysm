"""Actual C1 role saves and OAuth payment access; no injected resource grants."""
import json
import uuid
import urllib.request
import urllib.error
import argparse
from decimal import Decimal
from contextlib import contextmanager
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_resource_cache_snapshot
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import QA, read_state, sql, literal, authenticate_registered_login, verify_qa_gateway_routes

FUNCTIONS = [
    ('220', '/payment-order/query-all'), ('221', '/payment-order/query-by-id/{id}'),
    ('222', '/payment-order/add'), ('223', '/payment-order/modify'),
    ('224', '/payment-order/modify-examine-status'), ('225', '/payment-order/remove'),
    ('226', '/payment-order/addmore'), ('227', '/payment-order/export/simple'),
    ('228', '/payment-order/export/detail')]


class PaymentRoleIntegrationSuite(PaymentDocumentScopeSuite):
    def __init__(self,state,through_gateway=False):
        self.through_gateway=through_gateway
        super().__init__(state)

    def request(self, method, path, body=None, service='c1'):
        if getattr(self, 'through_gateway', False) and service in ('c1', 'payment'):
            service = 'gateway'
        return super().request(method, path, body, service)

    def case(self, name, action):
        if getattr(self, 'through_gateway', False):
            name += '_through_gateway'
        return super().case(name, action)

    def verify_gateway(self):
        assert self.state['gateway_port'] == 18001
        verify_qa_gateway_routes(self.opener,self.state)
        for headers in [{}, {'Authorization': 'Bearer qa-invalid-token'}]:
            request = urllib.request.Request('http://127.0.0.1:18001/payment-order/documents?pageIndex=1&pageSize=1', headers=headers)
            try:
                with self.opener.open(request, timeout=20) as response:
                    denied = json.load(response)
                assert denied.get('code') == 401 and not isinstance(denied.get('data'), dict), 'Gateway path did not reject missing/invalid token'
            except urllib.error.HTTPError as error:
                assert error.code == 401, 'Gateway unauthenticated access not rejected with401'
        self.payment_export_port = 18001

    @contextmanager
    def catalog(self):
        assert sql(self.state, "SELECT COUNT(*) FROM menu WHERE id IN ('000','120','123');") == '0'
        assert sql(self.state, "SELECT COUNT(*) FROM func_perm WHERE id IN ('220','221','222','223','224','225','226','227','228');") == '0'
        try:
            for identifier, parent in [('000', '0'), ('120', '000'), ('123', '120')]:
                sql(self.state, 'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES(' + ','.join(literal(value) for value in [identifier, parent, 'QA Payment Catalog', 'qa-pay-' + identifier, 0, 0, '', 0]) + ');')
            for identifier, path in FUNCTIONS:
                sql(self.state, 'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES(' + ','.join(literal(value) for value in [identifier, '123', 'QA Payment ' + identifier, path, 1, '1']) + ');')
            with qa_resource_cache_snapshot(self.state):
                yield
        finally:
            sql(self.state, "DELETE FROM func_perm WHERE mid='123' AND id IN ('220','221','222','223','224','225','226','227','228');DELETE FROM menu WHERE id='123';DELETE FROM menu WHERE id='120';DELETE FROM menu WHERE id='000';")

    def reload_resources(self):
        request = urllib.request.Request('http://127.0.0.1:18002/open/resources/cache/reload', method='PUT', headers={'Authorization': 'Bearer ' + self.admin})
        with self.opener.open(request, timeout=20) as response:
            result = json.load(response)
        assert result.get('code') == 10000, str(result)

    def role_fixture(self):
        self.admin = self.token
        self.fixture()
        self.role_name = 'QA Payment Live ' + uuid.uuid4().hex[:8]
        self.role = self.success('POST', '/role/add-role', dict(name=self.role_name, data='', root='[]', auth='{}'))
        self.user_id, user, _ = self.new_user(role=self.role)
        self.ordinary = authenticate_registered_login(self.state,user['user'],user['pwd'],self.opener) if self.through_gateway else PurchaseUiSuite.login(self, user)

    def select(self, identifiers):
        current = self.token
        self.token = self.admin
        try:
            root = [dict(id='120', children=[dict(id='123', fun=[dict(id=identifier) for identifier in identifiers])])] if identifiers else []
            result = self.request('PUT', '/role/modify-role', dict(id=self.role, name=self.role_name, data='', root=json.dumps(root), auth='{}'))
            assert result.get('code') == 10000, str(result)
        finally:
            self.token = current

    def run(self):
        if getattr(self, 'through_gateway', False):
            self.verify_gateway()
        with self.catalog():
            def create_live():
                self.role_fixture()
                self.reload_resources()
                self.token = self.ordinary
                try:
                    assert self.payment(self.body()).get('code') == 403
                    self.select(['222'])
                    body = self.body()
                    granted = self.payment(body)
                    if granted.get('code') != 10000:
                        self.reload_resources()
                        assert self.payment(body).get('code') == 10000, 'Actual cache reload still cannot enable valid create grant'
                        self.select([])
                        revoked = self.payment(self.body())
                        self.reload_resources()
                        assert self.payment(self.body()).get('code') == 403
                        raise AssertionError('Real role save grant returned ' + str(granted.get('code')) + '; actual cache reload enabled it; revoke before reload returned ' + str(revoked.get('code')) + '. No injected Redis grants.')
                    assert self.count_payment(body['number']) == 1
                    self.reload_resources()
                    self.select([])
                    denied = self.body()
                    assert self.payment(denied).get('code') == 403 and self.count_payment(denied['number']) == 0
                    self.unchanged()
                    return ['Actual C1 role save grants and revokes payment creation using the same ordinary OAuth token; genuine stale derived cache cannot override current selection; draft moves no money or inventory']
                finally:
                    self.token = self.admin
                    self.select([])
            self.case('payment.permissions_real_role_save_immediate_create_and_revoke', create_live)

            def exact_detail():
                self.role_fixture()
                identifier = self.create_payment(self.body())
                self.select(['221'])
                self.reload_resources()
                self.token = self.ordinary
                try:
                    for path in ['/payment-order/document/', '/payment-order/query-by-id/']:
                        result = self.request('GET', path + identifier, service='payment')
                        assert result.get('code') == 10000, 'Real enabled catalog221 /query-by-id/{id} grant cannot read ' + path + ': ' + str(result)
                    self.select([])
                    assert self.request('GET', '/payment-order/document/' + identifier, service='payment').get('code') == 403
                    self.unchanged()
                    return ['Actual catalog221 placeholder resource enables both full document and legacy detail; revocation denies the same token without refreshing the genuinely granted cache']
                finally:
                    self.token = self.admin
                    self.select([])
            self.case('payment.permissions_actual_detail_catalog_resource', exact_detail)

            def disabled_and_current_role():
                self.role_fixture()
                self.select(['222'])
                self.reload_resources()
                self.token = self.ordinary
                try:
                    assert self.payment(self.body()).get('code') == 10000
                    sql(self.state, "UPDATE func_perm SET is_enable='0' WHERE id='222' AND mid='123';")
                    try:
                        rejected = self.body()
                        assert self.payment(rejected).get('code') == 403 and self.count_payment(rejected['number']) == 0
                    finally:
                        sql(self.state, "UPDATE func_perm SET is_enable='1' WHERE id='222' AND mid='123';")
                    other_name = 'QA Payment Empty ' + uuid.uuid4().hex[:8]
                    self.token = self.admin
                    other_role = self.success('POST', '/role/add-role', dict(name=other_name, data='', root='[]', auth='{}'))
                    assert self.request('PUT', '/user/mod-user', dict(id=self.user_id, role=other_role)).get('code') == 10000
                    self.token = self.ordinary
                    assert self.payment(self.body()).get('code') == 403
                    self.token = self.admin
                    assert self.request('PUT', '/user/mod-user', dict(id=self.user_id, role=self.role)).get('code') == 10000
                    self.token = self.ordinary
                    assert self.payment(self.body()).get('code') == 10000
                    self.unchanged()
                    return ['Genuinely granted stale cache cannot authorize disabled create function; real C1 user role reassignment denies the old token immediately and restoring its permitted role restores access, without funds or inventory changes']
                finally:
                    self.token = self.admin
                    self.select([])
            self.case('payment.permissions_disabled_function_and_live_role_identity', disabled_and_current_role)

            def full_workflow():
                from trade_flow_acceptance import TradeFlowSuite
                from payment_export_acceptance import PaymentExportSuite
                self.role_fixture()
                trade = TradeFlowSuite(self.state)
                trade.run('prepare')
                fixture = json.loads((QA / 'runtime/trade-flow-fixture.json').read_text(encoding='utf-8'))
                for key in ['goods', 'warehouse', 'supplier', 'account']:
                    setattr(self, key, fixture[key])
                identifier = fixture['payment']
                base = ['220', '221']
                def balances(cash=2125, payable=954):
                    assert self.inventory() == 6 and self.balance('account', self.account) == cash and self.balance('supplier', self.supplier) == payable
                    assert Decimal(sql(self.state, 'SELECT balance FROM customer WHERE id=' + literal(fixture['customer']) + ';')) == 151
                self.token = self.ordinary
                try:
                    assert self.request('GET', '/payment-order/document/' + identifier, service='payment').get('code') == 403
                    self.select(base)
                    document = self.document(identifier)
                    listing = self.request('GET', '/payment-order/documents?number=' + document['header']['number'], service='payment')
                    assert listing.get('code') == 10000 and len(listing['data']['rows']) == 1
                    revision = self.revision(document, money=954)
                    assert self.edit(identifier, revision).get('code') == 403
                    self.select(base + ['223'])
                    assert self.edit(identifier, revision).get('code') == 10000
                    document = self.document(identifier)
                    self.reload_resources()
                    self.select(base)
                    assert self.edit(identifier, self.revision(document, money=954)).get('code') == 403
                    balances()
                    self.select(base + ['227'])
                    assert isinstance(PaymentExportSuite.export(self, 'simple', dict(ids=identifier)), list)
                    assert PaymentExportSuite.export(self, 'detail', dict(ids=identifier)).get('code') == 403
                    self.select(base + ['227', '228'])
                    assert isinstance(PaymentExportSuite.export(self, 'detail', dict(ids=identifier)), list)
                    self.reload_resources()
                    self.select(base + ['228'])
                    assert PaymentExportSuite.export(self, 'simple', dict(ids=identifier)).get('code') == 403
                    supplier = sql(self.state, 'SELECT number FROM supplier WHERE id=' + literal(self.supplier) + ';')
                    account = sql(self.state, 'SELECT number FROM account WHERE id=' + literal(self.account) + ';')
                    number = 'QALIVEIMP' + uuid.uuid4().hex[:20]
                    rows = [dict(number=number, date='2026-11-16', supplierNumber=supplier, accountNumber=account, money=25, settle='', remark='QA actual role import', lineRemark='QA')]
                    self.select(base + ['226'])
                    assert self.request('POST', '/payment-order/import-preview', dict(rows=rows), service='payment').get('code') == 403
                    self.select(base + ['226', '222'])
                    options = self.request('GET', '/payment-order/options?kind=account&keyword=' + account, service='payment')
                    assert options.get('code') == 10000 and any(row['id'] == self.account for row in options['data']['rows'])
                    plan = self.request('POST', '/payment-order/import-preview', dict(rows=rows), service='payment')
                    assert plan.get('code') == 10000, str(plan)
                    imported = self.request('POST', '/payment-order/addmore', dict(rows=rows, version=plan['data']['version']), service='payment')
                    assert imported.get('code') == 10000, str(imported)
                    imported_id = imported['data']['ids'][0]
                    assert sql(self.state, 'SELECT `user` FROM omy WHERE id=' + literal(imported_id) + ';') == self.user_id
                    self.reload_resources()
                    self.select(base)
                    assert self.request('POST', '/payment-order/import-preview', dict(rows=rows), service='payment').get('code') == 403
                    self.select(base + ['225'])
                    assert self.remove(imported_id, self.document(imported_id)['version']).get('code') == 10000
                    balances()
                    self.select(base + ['224'])
                    plan = self.request('GET', '/payment-order/settlement-preview?id=' + identifier, service='payment')
                    assert plan.get('code') == 10000, str(plan)
                    command = dict(id=identifier, status=1, version=plan['data']['version'], allocations=plan['data']['allocations'])
                    assert self.request('POST', '/payment-order/settle', command, service='payment').get('data') == 1
                    balances(cash=1171, payable=0)
                    reverse = dict(id=identifier, status=0, version=self.document(identifier)['version'])
                    self.reload_resources()
                    self.select(base)
                    assert self.request('POST', '/payment-order/settle', reverse, service='payment').get('code') == 403
                    balances(cash=1171, payable=0)
                    self.select(base + ['224'])
                    assert self.request('POST', '/payment-order/settle', reverse, service='payment').get('data') == 1
                    balances()
                    self.select(base + ['225'])
                    assert self.remove(identifier, self.document(identifier)['version']).get('code') == 10000
                    balances()
                    assert sql(self.state, "SELECT COUNT(*) FROM record WHERE type='omy' AND source=" + literal(identifier) + ' AND `user`=' + literal(self.user_id) + ';') == '4'
                    return ['Real C1 saves using all nine actual payment function IDs control ordinary list/detail/edit/options, independently parsed XLSX exports, reviewed import/save/delete, actual954 payment and reverse/delete; genuine stale cache cannot retain revoked edit/export/import/audit access; cash2125→1171→2125, payable954→0→954, inventory6 and customer151 agree, all four current operations attributed to actual operator']
                finally:
                    self.token = self.admin
                    self.select([])
            self.case('payment.permissions_real_role_to_complete_business_workflow', full_workflow)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gateway', action='store_true')
    suite = PaymentRoleIntegrationSuite(read_state(),through_gateway=parser.parse_args().gateway)
    suite.run()
