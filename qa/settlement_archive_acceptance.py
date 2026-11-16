"""Real settlement APIs with explicit bulk archived-history SQL fixtures.

The current trade is created through actual purchase/sale/return APIs. The 501
closed historical heads and matching bills are setup fixtures, not 501 claimed
end-to-end transactions. They must never change the current trade's balances.
"""
import json
import uuid
from decimal import Decimal
from acceptance import QA, Suite, read_state, sql, literal
from trade_flow_acceptance import TradeFlowSuite


class SettlementArchiveSuite(Suite):
    def prepare(self):
        trade = TradeFlowSuite(self.state)
        trade.run('prepare')
        self.token = trade.token
        self.f = json.loads((QA / 'runtime/trade-flow-fixture.json').read_text(encoding='utf-8'))
        assert self.f['database'] == self.state['database']
        result = self.request('POST', '/fund/receipt', dict(
            customer=self.f['customer'], time='2026-11-16 14:00:00',
            number='QAARCHIVE' + uuid.uuid4().hex[:20], people='', file=[],
            data='QA historical-volume active receipt',
            info=[dict(account=self.f['account'], amount=151, settle='', data='')]), service='fund')
        assert result.get('code') == 10000, str(result)
        self.f['receipt'] = result['data']

    def balances(self, cash=2125, payable=954, receivable=151):
        for table, key, amount in [('account', 'account', cash), ('supplier', 'supplier', payable), ('customer', 'customer', receivable)]:
            assert Decimal(sql(self.state, 'SELECT balance FROM ' + table + ' WHERE id=' + literal(self.f[key]) + ';')) == amount
        assert Decimal(sql(self.state, 'SELECT SUM(nums) FROM room WHERE goods=' + literal(self.f['goods']) + ' AND warehouse=' + literal(self.f['warehouse']) + ';')) == 6

    def archive(self, table, source):
        assert table in ('buy', 'bre', 'sell', 'sre')
        prefix = 'QAA' + uuid.uuid4().hex[:16]
        columns = [row.split('\t')[0] for row in sql(self.state, 'SHOW COLUMNS FROM `' + table + '`;').splitlines()]
        fields = ','.join('`' + column + '`' for column in columns)
        identifier = 'MD5(CONCAT(' + literal(prefix) + ',n.i))'
        number = 'CONCAT(' + literal(prefix) + ',n.i)'
        expressions = [identifier if column == 'id' else number if column == 'number' else '2' if column == 'nucleus' else 'h.`' + column + '`' for column in columns]
        integers = ' UNION ALL '.join('SELECT ' + str(i) + ' AS i' for i in range(501))
        sql(self.state, 'INSERT INTO `' + table + '`(' + fields + ') SELECT ' + ','.join(expressions) + ' FROM `' + table + '` h JOIN (' + integers + ') n ON 1=1 WHERE h.id=' + literal(source) + ';')
        where = 'number LIKE ' + literal(prefix + '%')
        sql(self.state, 'INSERT INTO `' + table + '_bill`(id,pid,type,source,time,money) SELECT MD5(CONCAT(id,' + literal('bill') + ')),id,' + literal(table) + ',id,time,actual FROM `' + table + '` WHERE ' + where + ';')
        assert sql(self.state, 'SELECT COUNT(*) FROM `' + table + '` WHERE ' + where + ' AND nucleus=2;') == '501'
        return where

    def run(self):
        self.prepare()
        for table, source in [('buy', self.f['receipts'][0]), ('bre', self.f['purchase_return']), ('sell', self.f['sale']), ('sre', self.f['sales_return'])]:
            def check(table=table, source=source):
                receipt = table in ('sell', 'sre')
                service = 'fund' if receipt else 'payment'
                identifier = self.f['receipt' if receipt else 'payment']
                base = '/fund/receipt' if receipt else '/payment-order'
                preview_url = base + '/settlement-preview?id=' + identifier
                before = self.request('GET', preview_url, service=service)
                assert before.get('code') == 10000, str(before)
                where = self.archive(table, source)
                try:
                    self.balances()
                    plan = self.request('GET', preview_url, service=service)
                    assert plan.get('code') == 10000, '501 closed ' + table + ' histories block current settlement: ' + str(plan)
                    assert plan['data'] == before['data'], 'Closed history changed the current reviewed plan'
                    body = dict(id=identifier, status=1, version=plan['data']['version'], allocations=plan['data']['allocations'])
                    result = self.request('POST', base + '/settle', body, service=service)
                    assert result.get('code') == 10000 and result.get('data') == 1, str(result)
                    self.balances(cash=2276 if receipt else 1171, payable=954 if receipt else 0, receivable=0 if receipt else 151)
                    detail_path = base + ('/document/' if receipt else '/settlement-document/') + identifier
                    document = self.request('GET', detail_path, service=service)
                    assert document.get('code') == 10000, str(document)
                    result = self.request('POST', base + '/settle', dict(id=identifier, status=0, version=document['data']['version']), service=service)
                    assert result.get('code') == 10000 and result.get('data') == 1, str(result)
                    self.balances()
                    assert sql(self.state, 'SELECT COUNT(*) FROM `' + table + '` WHERE ' + where + ' AND nucleus=2;') == '501'
                    historical = sql(self.state, 'SELECT id FROM `' + table + '` WHERE ' + where + ' ORDER BY id LIMIT 1;')
                    for mutation, restore, message in [
                        ('UPDATE `' + table + '_bill` SET money=money+1 WHERE pid=' + literal(historical), 'UPDATE `' + table + '_bill` SET money=money-1 WHERE pid=' + literal(historical), '超过实际金额'),
                        ('UPDATE `' + table + '` SET nucleus=1 WHERE id=' + literal(historical), 'UPDATE `' + table + '` SET nucleus=2 WHERE id=' + literal(historical), '状态与实际核销明细不一致')
                    ]:
                        sql(self.state, mutation + ';')
                        try:
                            refused = self.request('GET', preview_url, service=service)
                            assert refused.get('code') != 10000 and message in refused.get('message', ''), str(refused)
                            self.balances()
                        finally:
                            sql(self.state, restore + ';')
                    negative = uuid.uuid4().hex
                    sql(self.state, 'UPDATE `' + table + '_bill` SET money=money+1 WHERE pid=' + literal(historical) + '; INSERT INTO `' + table + '_bill`(id,pid,type,source,time,money) SELECT ' + literal(negative) + ',id,' + literal(table) + ',id,time,-1 FROM `' + table + '` WHERE id=' + literal(historical) + ';')
                    try:
                        refused = self.request('GET', preview_url, service=service)
                        assert refused.get('code') != 10000 and '核销金额无效' in refused.get('message', ''), str(refused)
                        self.balances()
                    finally:
                        sql(self.state, 'DELETE FROM `' + table + '_bill` WHERE id=' + literal(negative) + '; UPDATE `' + table + '_bill` SET money=money-1 WHERE pid=' + literal(historical) + ';')
                    assert self.request('GET', preview_url, service=service).get('code') == 10000
                    return ['501 explicit SQL closed-history fixtures do not alter the exact active source plan; actual posting/reversal changes and restores cash, AR/AP and current original allocations; stock6 and all archived heads remain unchanged', 'Even closed history refuses over-allocation, inconsistent settled state, and a hidden negative bill whose compensating positive bill keeps the same net total; correcting each fixture restores preview without business writes']
                finally:
                    sql(self.state, 'DELETE b FROM `' + table + '_bill` b JOIN `' + table + '` h ON b.pid=h.id WHERE h.' + where + '; DELETE FROM `' + table + '` WHERE ' + where + ';')
            self.case('settlement.closed_history_' + table + '_does_not_block_actual_roundtrip', check)
        self.write_report()


if __name__ == '__main__':
    SettlementArchiveSuite(read_state()).run()
