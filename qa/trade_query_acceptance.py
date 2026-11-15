"""Real HTTP query acceptance. SQL fixtures are not evidence of document creation/audit."""
import json
import uuid
from urllib.parse import urlencode
from warehouse_acceptance import WarehouseSuite
from acceptance import QA, read_state, sql, literal


class TradeQuerySuite(WarehouseSuite):
    def run(self):
        marker = 'QAT' + uuid.uuid4().hex[:10]
        customer, supplier, person = [uuid.uuid4().hex for _ in range(3)]
        def insert(table, values):
            sql(self.state, 'INSERT INTO `' + table + '`(' + ','.join('`' + key + '`' for key in values) + ') VALUES(' + ','.join(literal(value) for value in values.values()) + ');')
        common = dict(py='qa', frame=self.state['frame_id'])
        insert('customer', dict(common, id=customer, name='QA Customer ' + marker, number='C' + marker, user=self.actor, category='0', grade='0'))
        insert('supplier', dict(common, id=supplier, name='QA Supplier ' + marker, number='S' + marker, user=self.actor, category='0'))
        insert('people', dict(common, id=person, name='QA People ' + marker, number='P' + marker, sex=0, tel=''))
        document_ids = {}
        for kind, table, party_key, party in [('sale', 'sell', 'customer', customer), ('purchase', 'buy', 'supplier', supplier)]:
            ids = []
            for index, time in enumerate(['2026-11-14 00:00:00', '2026-11-15 12:00:00', '2026-11-15 23:59:59', '2026-11-16 00:00:00']):
                identifier = uuid.uuid4().hex
                ids.append(identifier)
                insert(table, dict(id=identifier, frame=self.state['frame_id'], **{party_key: party}, time=time,
                       number=marker + str(index), total=10+index, actual=10+index, money=index, cost=0,
                       people=person, examine=index % 2, nucleus=0, cse=3, invoice=3, check=0, user=self.actor, data='QA query fixture'))
                insert(table + '_info', dict(id=uuid.uuid4().hex, pid=identifier, goods=self.goods, unit='unit', warehouse=self.warehouse, price=2, nums=5, total=10, tpt=10))
            document_ids[kind] = ids

        def query(kind, **parameters):
            path = '/sale/form/getSaleList' if kind == 'sale' else '/purchase-note/list'
            response = self.request('GET', path + '?' + urlencode(dict(pageIndex=1, pageSize=2, number=marker, **parameters)), service=kind)
            assert response.get('code') == 10000, kind + ': query failed; code=' + str(response.get('code'))
            return response['data']

        for kind in ['sale', 'purchase']:
            def check_query(kind=kind):
                first = query(kind)
                assert first['total'] == 4 and len(first['rows']) == 2, kind + ': wrong total/page size'
                path = '/sale/form/getSaleList' if kind == 'sale' else '/purchase-note/list'
                second = self.request('GET', path + '?' + urlencode(dict(pageIndex=2, pageSize=2, number=marker)), service=kind)['data']
                assert {row['id'] for row in first['rows'] + second['rows']} == set(document_ids[kind]), kind + ': duplicated/skipped pages'
                dates = dict(startTime='2026-11-15T00:00:00', endTime='2026-11-15T23:59:59.999999') if kind == 'sale' else dict(startTime='2026-11-15', endTime='2026-11-15')
                ranged = query(kind, **dates)
                assert ranged['total'] == 2 and {row['id'] for row in ranged['rows']} == set(document_ids[kind][1:3]), kind + ': date end excluded afternoon/evening'
                party_key, party_number = ('customer', 'C' + marker) if kind == 'sale' else ('supplier', 'S' + marker)
                assert query(kind, **{party_key: party_number})['total'] == 4, kind + ': business number search failed'
                assert query(kind, **{party_key: 'QA Customer ' + marker if kind == 'sale' else 'QA Supplier ' + marker})['total'] == 4, kind + ': name search failed'
                goods_key = 'goodsName' if kind == 'sale' else 'name'
                assert query(kind, **{goods_key: 'QA Stock Goods'})['total'] == 4, kind + ': product name search failed'
                assert query(kind, **{goods_key: 'no-such-product'})['total'] == 0, kind + ': invalid product name matched'
                assert query(kind, people='QA People ' + marker)['total'] == 4, kind + ': people name filter failed'
                assert query(kind, examine=0)['total'] == 2, kind + ': zero-valued status ignored'
                if kind == 'sale':
                    assert first['rows'][0]['customer'] == customer and first['rows'][0]['customerName'] == 'QA Customer ' + marker, 'Display name overwrote identity'
                else:
                    assert first['rows'][0]['buyMoney'] == 3 and first['rows'][0]['checkStatus'] == 0 and first['rows'][0]['noteUser'] == self.actor, 'Purchase payment/check/creator mapping missing'
                return ['Actual dedicated HTTP queries over isolated MySQL fixtures', 'Server pagination and total, whole-day date boundaries, party ID/name/business-number and goods/people/status filters verified', 'No creation/audit, stock, funds or complete permission acceptance implied']
            self.case(kind + '.actual_document_queries', check_query)
        (QA / 'runtime/trade-query.json').write_text(json.dumps({'number': marker}), encoding='utf-8')
        def organization_choices():
            root_ids = []
            for index, parent in enumerate([None, '', '0']):
                identifier = uuid.uuid4().hex
                root_ids.append(identifier)
                insert('frame', dict(id=identifier, pid=parent, name='QA Root ' + marker + str(index), sort=index))
            child = uuid.uuid4().hex
            insert('frame', dict(id=child, pid=root_ids[1], name='QA Child ' + marker, sort=1))
            result = self.request('GET', '/basic_information/frame/getFrame', service='basic')
            assert result.get('code') == 10000 and isinstance(result.get('data'), list), 'Real organization tree endpoint failed'
            def identifiers(nodes):
                return [str(node['id']) for node in nodes] + [identifier for node in nodes for identifier in identifiers(node.get('children') or [])]
            actual = identifiers(result['data'])
            assert self.state['frame_id'] in actual, 'QA organization missing from actual tree'
            assert set(root_ids + [child]).issubset(actual) and len(actual) == len(set(actual)), 'Root variants or children missing/duplicated'
            assert child in identifiers(next(node for node in result['data'] if node['id'] == root_ids[1]).get('children', [])), 'Real parent-child relation lost'
            return ['Real basic service organization tree includes the isolated organization used by sales entry', 'NULL/empty/zero roots, child attachment and no duplicate IDs verified against actual MySQL fixtures']
        self.case('trade.actual_organization_choices', organization_choices)
        (QA / 'runtime/browser-session.json').write_text(json.dumps({'token': self.token}), encoding='utf-8')
        self.write_report()


if __name__ == '__main__':
    TradeQuerySuite(read_state()).run()
