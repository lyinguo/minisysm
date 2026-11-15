"""Actual goods create/query/pagination used by the shared product chooser."""
import json
import uuid
from urllib.parse import urlencode
from acceptance import Suite, QA, read_state, sql, literal


class ProductSelectionSuite(Suite):
    def run(self):
        marker = 'QASEL' + uuid.uuid4().hex[:12]
        identifiers = []
        def create_and_search():
            for index in range(3):
                body = dict(name=marker + '商品' + str(index), number=marker + str(index),
                            category='0', unit='件', buy=2, sell=3, code='BAR' + marker + str(index),
                            brand='QA测试品牌', spec='QA规格', serial=0, batch=0, validity=0)
                response = self.request('POST', '/goods/add', body, service='basic')
                assert response.get('code') == 10000, 'Actual product create failed'
                identifiers.append(response['data'])
            def query(**parameters):
                response = self.request('GET', '/goods/query-list?' + urlencode(dict(pageIndex=1, pageSize=2, **parameters)), service='basic')
                assert response.get('code') == 10000, 'Actual product search failed'
                return response['data']
            first = query(keyword=marker)
            assert first['total'] == 3 and len(first['rows']) == 2
            page2 = self.request('GET', '/goods/query-list?' + urlencode(dict(pageIndex=2, pageSize=2, keyword=marker)), service='basic')['data']
            assert len(page2['rows']) == 1
            assert {row['id'] for row in first['rows'] + page2['rows']} == set(identifiers)
            barcode = query(keyword='BAR' + marker + '1')
            assert barcode['total'] == 1 and barcode['rows'][0]['id'] == identifiers[1]
            assert query(keyword=marker, brand='other')['total'] == 0
            assert query(keyword=marker, spec='no-such-spec')['total'] == 0
            assert query(keyword=marker + '不存在')['total'] == 0
            assert sql(self.state, 'SELECT COUNT(*) FROM goods WHERE number LIKE ' + literal(marker + '%') + ';') == '3'
            (QA / 'runtime/product-selection.json').write_text(json.dumps({'keyword': marker, 'ids': identifiers}), encoding='utf-8')
            return ['Three actual goods created through HTTP and confirmed in MySQL',
                    'Keyword/name/number/barcode, combined brand/spec filters, empty result and disjoint paging verified']
        self.case('product.actual_selector_queries', create_and_search)
        self.write_report()


if __name__ == '__main__':
    ProductSelectionSuite(read_state()).run()
