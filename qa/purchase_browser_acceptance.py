"""Actual browser purchase posting fixture and independent SQL verification, QA only."""
import argparse
import json
from decimal import Decimal
from purchase_posting_acceptance import PurchasePostingSuite
from acceptance import QA,read_state,sql,literal


fixture_path=QA/'runtime/purchase-posting-browser.json'


def prepare():
    suite=PurchasePostingSuite(read_state());suite.fixture();body=suite.body()
    body['purchaseNoteBuyDTO'].update(time='2026-11-15 13:47:00',money=50,account=suite.account)
    body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
    identifier=suite.create(body)
    fixture={key:getattr(suite,key) for key in ['goods','warehouse','supplier','account','actor']}
    fixture.update(database=suite.state['database'],id=identifier,number=body['purchaseNoteBuyDTO']['number'])
    fixture_path.write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated procurement posting browser document: '+fixture['number'])


def verify(audited):
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database'] and state['purchase_port']==18023
    identifier=literal(fixture['id'])
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+' AND warehouse='+literal(fixture['warehouse'])+';'))==Decimal(2 if audited else 0)
    for table,key,value in [('account','account',50 if audited else 100),('supplier','supplier',176 if audited else 0)]:
        assert Decimal(sql(state,'SELECT balance FROM '+table+' WHERE id='+literal(fixture[key])+';'))==value
    actual=sql(state,'SELECT CONCAT(CAST(examine AS SIGNED),\',\',CAST(`check` AS SIGNED),\',\',CAST(nucleus AS SIGNED)) FROM buy WHERE id='+identifier+';')
    assert actual==('1,1,1' if audited else '0,1,0')
    assert sql(state,'SELECT `user` FROM buy WHERE id='+identifier+';')==fixture['actor']
    assert sql(state,"SELECT DATE_FORMAT(time,'%H:%i:%s') FROM buy WHERE id="+identifier+';')=='13:47:00'
    for table in ['room_info','summary','account_info']:
        assert int(sql(state,"SELECT COUNT(*) FROM "+table+" WHERE type='buy' AND `class`="+identifier+';'))==int(audited)
    assert Decimal(sql(state,'SELECT COALESCE(SUM(money),0) FROM buy_bill WHERE pid='+identifier+';'))==Decimal(50 if audited else 0)
    assert int(sql(state,'SELECT COUNT(*) FROM psi_purchase_posting WHERE purchase_id='+identifier+';'))==int(audited)
    report=dict(case='purchase.browser_posted' if audited else 'purchase.browser_reversed',status='verified',production_business_writes=0,all_system_features_accepted=False)
    (QA/('reports/purchase-posting-browser-'+str(int(audited))+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS browser procurement '+('posted: stock=2 cash=50 payable=176' if audited else 'reversed: stock=0 cash=100 payable=0')+'; supporting ledger/status/creator/time verified')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify-audited','verify-reversed'])
    action=parser.parse_args().action
    if action=='prepare':prepare()
    else:verify(action=='verify-audited')
