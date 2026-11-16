"""Sales-return source preview: actual OAuth/HTTP/MySQL, no refund completion claim."""
import argparse
import uuid
import json
from decimal import Decimal
from sale_posting_acceptance import SalePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import QA, read_state, sql, literal
from resource_fixture import qa_resource_grants, qa_database_permission_switches, authority


class SaleReturnPreviewSuite(SalePostingSuite):
    resource = '/sale/form/getGenerateReturnData'

    def preview(self, identifier):
        return self.request('GET', '/sale/form/getGenerateReturnData?saleId=' + identifier, service='sale')

    def posted(self, frame=None, discount=1, tax=.13):
        self.fixture()
        body = self.body(); body.update(money=50, account=self.account)
        body['items'][0].update(discount=discount, tax=tax)
        if frame:
            body['frame'] = frame
            # Only this case's new QA references are scoped to the foreign organization.
            for table, identifier in [('warehouse', self.warehouse), ('customer', self.customer), ('account', self.account)]:
                sql(self.state, 'UPDATE ' + table + ' SET frame=' + literal(frame) + ' WHERE id=' + literal(identifier) + ';')
        identifier = self.create(body)
        assert self.request('POST', '/sale/form/check?check=true', [identifier], service='sale').get('code') == 10000
        assert self.post([identifier]).get('code') == 10000
        return identifier

    def role_session(self):
        role = self.success('POST', '/role/add-role', dict(name='QA Return Preview ' + uuid.uuid4().hex[:8], data='', root='[]', auth='{}'))
        _, user, _ = self.new_user(role=role)
        keyword = sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(role) + ';')
        return PurchaseUiSuite.login(self, user), authority(role, keyword)

    def unchanged(self):
        assert self.inventory() == 8 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == 176

    def linked_fixture(self, identifier, quantity, approved=0):
        """Explicit QA legacy-state fixture, not evidence of return creation/audit."""
        parent, line = uuid.uuid4().hex, uuid.uuid4().hex
        source = sql(self.state, 'SELECT id FROM sell_info WHERE pid=' + literal(identifier) + ' LIMIT 1;')
        sql(self.state, 'INSERT INTO sre(id,source,frame,customer,time,number,total,actual,money,cost,examine,nucleus,cse,invoice,`check`,`user`) SELECT ' +
            literal(parent) + ',id,frame,customer,time,' + literal('QAR' + parent[:20]) + ',0,0,0,0,' + str(approved) + ',0,3,3,0,' + literal(self.actor) + ' FROM sell WHERE id=' + literal(identifier) + ';' +
            'INSERT INTO sre_info(id,pid,source,goods,attr,unit,warehouse,price,nums,total,tpt) SELECT ' + literal(line) + ',' + literal(parent) + ',id,goods,attr,unit,warehouse,price,' + literal(quantity) + ',0,0 FROM sell_info WHERE id=' + literal(source) + ';')
        return parent, line, source

    def run(self):
        def defaults():
            identifier = self.posted()
            document = self.sale('GET', '/sale/form/document/' + identifier)
            result = self.preview(identifier)
            assert result.get('code') == 10000
            data = result['data']
            assert not data.get('id'), 'Source sale ID incorrectly reused as a new return ID'
            assert data['source'] == identifier and data.get('sourceVersion') == document['version']
            assert data['money'] == 0 and data['examine'] == 0 and data['check'] == 0 and data['user'] == self.actor
            assert data.get('number') == '' and data.get('sourceNumber') == document['header']['number']
            assert len(data.get('items', [])) == 1 and data['items'][0]['source'] == document['items'][0]['id']
            assert data['items'][0]['available'] == 2
            self.unchanged()
            return ['Real posted sale preview contains source/version and authoritative line identity; new return defaults never reuse original ID/approval/payment']
        self.case('sale.return_preview_actual_source_and_draft_defaults', defaults)

        def unchecked():
            self.fixture()
            identifier = self.create(self.body())
            assert self.preview(identifier).get('code') != 10000, 'Unposted sale offered as a return source'
            assert self.inventory() == 10 and self.balance('customer', self.customer) == 0
            return ['Actual unchecked sale cannot be a return source; stock/funds remain unchanged']
        self.case('sale.return_preview_requires_real_posting', unchecked)

        def permission():
            identifier = self.posted()
            token, keyword = self.role_session(); admin = self.token
            try:
                self.token = token
                with qa_database_permission_switches(self.state,[self.resource],[keyword]) as toggle:
                    assert self.preview(identifier).get('code') == 403, 'Ungranted actual role can preview sales data'
                    toggle(self.resource,True)
                    assert self.preview(identifier).get('code') == 10000
                    toggle(self.resource,False)
                    assert self.preview(identifier).get('code') == 403, 'Old token ignores live permission revocation'
            finally:
                self.token = admin
            self.unchanged()
            return ['New role/user actually logs in; no grant refuses, own grant works, same-token live revocation refuses; QA database function selection/enabled state restored']
        self.case('sale.return_preview_actual_role_and_revocation', permission)

        def organization():
            frame = uuid.uuid4().hex
            sql(self.state, "INSERT INTO frame(id,pid,name,sort) VALUES(" + literal(frame) + ",'0','QA Return Other Org',0);")
            identifier = self.posted(frame)
            token, keyword = self.role_session(); admin = self.token
            try:
                self.token = token
                with qa_resource_grants(self.state, [self.resource], [keyword]):
                    assert self.preview(identifier).get('code') == 403, 'Other organization sale leaked through return preview'
            finally:
                self.token = admin
            self.unchanged()
            return ['Actual granted user cannot preview another organization source; no stock/funds changes']
        self.case('sale.return_preview_cross_organization_refused', organization)

        def no_write():
            identifier = self.posted()
            before = sql(self.state, 'SELECT COUNT(*) FROM sre;SELECT COUNT(*) FROM sre_info;SELECT COUNT(*) FROM record WHERE source=' + literal(identifier) + ';')
            for _ in range(2):
                assert self.preview(identifier).get('code') == 10000
            assert sql(self.state, 'SELECT COUNT(*) FROM sre;SELECT COUNT(*) FROM sre_info;SELECT COUNT(*) FROM record WHERE source=' + literal(identifier) + ';') == before
            self.unchanged()
            return ['Repeated actual preview does not create a return or change source history/stock/cash/receivable']
        self.case('sale.return_preview_is_read_only', no_write)

        def reservations():
            identifier = self.posted()
            _, _, source = self.linked_fixture(identifier, '.5')
            result = self.preview(identifier)
            assert result.get('code') == 10000
            row = result['data']['items'][0]
            assert row['source'] == source and row['sourceQuantity'] == 2 and row['returned'] == 0 and Decimal(str(row['reserved'])) == Decimal('.5')
            assert Decimal(str(row['available'])) == Decimal('1.5') and row['nums'] == row['available']
            assert Decimal(str(row['total'])) == 150 and Decimal(str(row['tat'])) == Decimal('19.5') and Decimal(str(row['tpt'])) == Decimal('169.5')
            assert Decimal(str(result['data']['actual'])) == Decimal('169.5')
            self.unchanged()
            return ['Explicit self-created QA return-draft fixture reserves .5 source units; actual preview returns1.5 units/150 net/19.5 tax/169.5 gross without business writes; this is not return-create acceptance']
        self.case('sale.return_preview_pending_quantities_and_money', reservations)

        def posted_and_pending():
            identifier = self.posted()
            _, _, source = self.linked_fixture(identifier, '.5', 1)
            self.linked_fixture(identifier, '.5')
            sql(self.state, 'UPDATE sell_info SET retreat=.5 WHERE id=' + literal(source) + ';')
            result = self.preview(identifier)
            assert result.get('code') == 10000
            row = result['data']['items'][0]
            assert row['returned'] == row['reserved'] == .5 and row['available'] == 1 and row['tpt'] == 113
            self.unchanged()
            return ['Explicit already-returned .5 and draft .5 fixture counted once each; preview reports exactly1 remaining, not double-counted or full source quantity']
        self.case('sale.return_preview_posted_and_pending_not_double_counted', posted_and_pending)

        def corruption():
            identifier = self.posted()
            parent, line, source = self.linked_fixture(identifier, '.5')
            other_goods = uuid.uuid4().hex
            sql(self.state, 'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) SELECT ' + literal(other_goods) + ",'QA other return goods','qa'," + literal('QG' + other_goods[:16]) + ',category,unit,buy,sell,stock,type,more FROM goods WHERE id=' + literal(self.goods) + ';')
            other_sale = self.create(self.body())
            for statement in ['UPDATE sre_info SET nums=3 WHERE id=' + literal(line),
                              'UPDATE sre_info SET nums=-1 WHERE id=' + literal(line),
                              'UPDATE sre_info SET nums=.5,goods=' + literal(other_goods) + ' WHERE id=' + literal(line)]:
                sql(self.state, statement + ';')
                assert self.preview(identifier).get('code') != 10000
            sql(self.state, 'UPDATE sre_info i JOIN sell_info s ON s.id=i.source SET i.goods=s.goods,i.nums=.5 WHERE i.id=' + literal(line) + ';UPDATE sre SET source=' + literal(other_sale) + ' WHERE id=' + literal(parent) + ';')
            assert self.preview(identifier).get('code') != 10000
            self.unchanged()
            return ['Explicit inconsistent/negative/overquantity/mismatched-source QA return links are refused rather than undercounted; original stock/funds preserved']
        self.case('sale.return_preview_corrupt_associations_refused', corruption)

        def historical():
            identifier = self.posted()
            sql(self.state, 'DELETE FROM psi_sale_posting WHERE sale_id=' + literal(identifier) + ';')
            assert self.preview(identifier).get('code') != 10000
            self.unchanged()
            return ['Self-created QA sale with removed marker cannot masquerade as a valid source merely through its audited flag; no automatic repair/reposting']
        self.case('sale.return_preview_legacy_flag_without_posting_refused', historical)

        def exhausted():
            identifier = self.posted()
            self.linked_fixture(identifier, 2)
            assert self.preview(identifier).get('code') != 10000
            self.unchanged()
            return ['Explicit all-quantity pending return fixture leaves no available source; preview refuses rather than producing a zero-line draft']
        self.case('sale.return_preview_exhausted_source_refused', exhausted)

        def precision():
            identifier = self.posted(discount=.955, tax=.095)
            self.linked_fixture(identifier, '.5')
            result = self.preview(identifier)
            assert result.get('code') == 10000
            row = result['data']['items'][0]
            assert Decimal(str(row['discount'])) == Decimal('.955') and Decimal(str(row['tax'])) == Decimal('.095')
            assert Decimal(str(row['total'])) == Decimal('143.25') and Decimal(str(row['tat'])) == Decimal('13.6088')
            assert Decimal(str(row['tpt'])) == Decimal('156.8588') and Decimal(str(result['data']['actual'])) == Decimal('156.8588')
            assert self.inventory() == 8 and self.balance('account', self.account) == 150 and self.balance('customer', self.customer) == Decimal('159.145')
            return ['Actual sale with .955 discount/.095 tax and explicit .5 reserved fixture previews1.5 units/143.25 net/13.6088 rounded tax/156.8588 gross, preserving original stock/funds']
        self.case('sale.return_preview_fractional_rates_and_rounding', precision)

        def missing():
            self.fixture()
            for identifier in ['', uuid.uuid4().hex, 'x' * 33]:
                assert self.preview(identifier).get('code') != 10000
            assert self.inventory() == 10 and self.balance('account', self.account) == 100 and self.balance('customer', self.customer) == 0
            return ['Empty, unknown and overlength source IDs fail without creating returns or movements']
        self.case('sale.return_preview_invalid_source_refused', missing)
        self.write_report()


def prepare_browser():
    suite = SaleReturnPreviewSuite(read_state())
    identifier = suite.posted()
    _, line, source = suite.linked_fixture(identifier, '.5')
    fixture = {key: getattr(suite, key) for key in ['goods', 'warehouse', 'customer', 'account', 'actor']}
    fixture.update(database=suite.state['database'], id=identifier, reservation_line=line, source_line=source,
                   number=sql(suite.state, 'SELECT number FROM sell WHERE id=' + literal(identifier) + ';'))
    (QA / 'runtime/sale-return-preview-browser.json').write_text(json.dumps(fixture), encoding='utf-8')
    (QA / 'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)), encoding='utf-8')
    print('Prepared isolated preview source: ' + fixture['number'])


def verify_browser():
    state = read_state()
    fixture = json.loads((QA / 'runtime/sale-return-preview-browser.json').read_text(encoding='utf-8'))
    assert fixture['database'] == state['database']
    identifier = literal(fixture['id'])
    assert sql(state, 'SELECT CONCAT(CAST(examine AS SIGNED),CAST(`check` AS SIGNED)) FROM sell WHERE id=' + identifier + ';') == '11'
    assert Decimal(sql(state, 'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods=' + literal(fixture['goods']) + ' AND warehouse=' + literal(fixture['warehouse']) + ';')) == 8
    assert Decimal(sql(state, 'SELECT balance FROM account WHERE id=' + literal(fixture['account']) + ';')) == 150
    assert Decimal(sql(state, 'SELECT balance FROM customer WHERE id=' + literal(fixture['customer']) + ';')) == 176
    assert sql(state, 'SELECT COUNT(*) FROM sre WHERE source=' + identifier + ';') == '1'
    assert Decimal(sql(state, 'SELECT nums FROM sre_info WHERE id=' + literal(fixture['reservation_line']) + ';')) == Decimal('.5')
    assert sql(state, "SELECT COUNT(*) FROM record WHERE type='sell' AND source=" + identifier + ';') == '3'
    report = dict(status='verified', source_quantity=2, reserved=.5, available=1.5, actual=169.5,
                  stock=8, account=150, receivable=176, return_rows_created_by_browser=0,
                  reservation_is_explicit_sql_fixture=True, all_system_features_accepted=False)
    (QA / 'reports/sale-return-preview-browser.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PASS actual preview browser: source/QA reservation/history unchanged; stock8/cash150/receivable176; no return created')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['run', 'prepare', 'verify-browser'])
    action = parser.parse_args().action
    if action == 'prepare':
        prepare_browser()
    elif action == 'verify-browser':
        verify_browser()
    else:
        SaleReturnPreviewSuite(read_state()).run()
