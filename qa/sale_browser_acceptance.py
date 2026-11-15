"""Prepare isolated real records, then independently verify browser audit/reverse writes."""
import argparse
import json
from decimal import Decimal
from acceptance import QA, read_state, sql, literal
from sale_posting_acceptance import SalePostingSuite


path=QA / 'runtime/sale-posting-browser.json'


def prepare():
    suite=SalePostingSuite(read_state())
    suite.fixture()
    body=suite.body(); body.update(money=50,account=suite.account)
    identifier=suite.create(body)
    fixture={key:getattr(suite,key) for key in ('goods','warehouse','customer','account','actor')}
    fixture.update(database=suite.state['database'],id=identifier,number=body['number'])
    path.write_text(json.dumps(fixture),encoding='utf-8')
    (QA / 'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated browser sale: '+body['number'])


def verify(audited):
    state=read_state(); fixture=json.loads(path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database'], 'Browser fixture belongs to another QA database'
    identifier=literal(fixture['id'])
    def scalar(query): return sql(state,query)
    actual=scalar('SELECT CONCAT(CAST(examine AS SIGNED),\',\',CAST(nucleus AS SIGNED),\',\',money) FROM sell WHERE id='+identifier+';').split(',')
    assert actual[:2]==(['1','1'] if audited else ['0','0']) and Decimal(actual[2])==50
    assert scalar('SELECT `user` FROM sell WHERE id='+identifier+';')==fixture['actor'], 'Browser changed original creator'
    stock=Decimal(scalar('SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+' AND warehouse='+literal(fixture['warehouse'])+';'))
    assert stock==(8 if audited else 10)
    for table,expected in [('account',150 if audited else 100),('customer',176 if audited else 0)]:
        assert Decimal(scalar('SELECT balance FROM '+table+' WHERE id='+literal(fixture[table])+';'))==expected
    for table in ('room_info','summary','account_info'):
        assert int(scalar("SELECT COUNT(*) FROM "+table+" WHERE type='sell' AND `class`="+identifier+';'))==(1 if audited else 0)
    assert int(scalar('SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id='+identifier+';'))==(1 if audited else 0)
    result=dict(case='sale.browser_real_'+('audit' if audited else 'reverse'),status='verified',stock=str(stock),account=150 if audited else 100,receivable=176 if audited else 0,production_business_writes=0,all_system_features_accepted=False)
    (QA / ('reports/sale-browser-'+('audit' if audited else 'reverse')+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS browser '+('audit' if audited else 'reverse')+' independent SQL: stock='+str(stock)+' and stock/cash/receivable journals agree')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','verify-audited','verify-reversed'])
    action=parser.parse_args().action
    if action=='prepare': prepare()
    else: verify(action=='verify-audited')
