"""Isolated master fixtures for a complete browser procurement entry, with independent SQL checks."""
import argparse
import json
import uuid
from decimal import Decimal,ROUND_HALF_UP
from purchase_posting_acceptance import PurchasePostingSuite
from acceptance import QA,read_state,sql,literal


fixture_path=QA/'runtime/purchase-entry-browser.json'


class PurchaseEntrySuite(PurchasePostingSuite):
    def run(self):
        def totals():
            self.fixture();body=self.body()
            body['purchaseNoteBuyDTO'].update(total=226,actual=0)
            body['purchaseNoteInfoDTOS'][0].update(discount=0,dsc=999,total=0,tax=13,tat=0,tpt=0,batch='',mfd=None,serial='[]')
            identifier=self.create(body)
            amounts=sql(self.state,"SELECT CONCAT(total,',',actual,',',money) FROM buy WHERE id="+literal(identifier)+';')
            assert list(map(Decimal,amounts.split(',')))==[Decimal(200),Decimal(226),Decimal(0)]
            assert sql(self.state,'SELECT COUNT(*) FROM room WHERE goods='+literal(self.goods)+';')=='0'
            assert self.check([identifier]).get('code')==10000 and self.post([identifier]).get('code')==10000
            assert self.inventory()==2 and self.balance('supplier',self.supplier)==226
            return ['Actual create ignores client header/derived amounts, computes net/tax totals and can proceed through real audit into stock/payables']
        self.case('purchase.entry_server_derived_amounts',totals)

        def precision():
            self.fixture();body=self.body()
            body['purchaseNoteInfoDTOS'][0].update(price=1.2345,nums=2.5,discount=0,dsc=0,total=0,tax=13.25,tat=0,tpt=0,batch='',mfd=None,serial='[]')
            identifier=self.create(body)
            net=(Decimal('1.2345')*Decimal('2.5')).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
            tax=(net*Decimal('.1325')).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP)
            assert Decimal(sql(self.state,'SELECT total FROM buy WHERE id='+literal(identifier)+';'))==net
            assert Decimal(sql(self.state,'SELECT actual FROM buy WHERE id='+literal(identifier)+';'))==net+tax
            assert self.check([identifier]).get('code')==10000 and self.post([identifier]).get('code')==10000
            assert self.inventory()==Decimal('2.5') and self.balance('supplier',self.supplier)==net+tax
            return ['Four-decimal price/quantity and percentage VAT calculate identically in persisted header/line and real payable']
        self.case('purchase.entry_four_decimal_amounts',precision)

        def legacy():
            self.fixture();body=self.body();body['purchaseNoteBuyDTO'].update(total=0,actual=0)
            identifier=self.create(body)
            assert Decimal(sql(self.state,'SELECT actual FROM buy WHERE id='+literal(identifier)+';'))==226
            assert Decimal(sql(self.state,'SELECT tax FROM buy_info WHERE pid='+literal(identifier)+';'))==Decimal('.13')
            assert Decimal(sql(self.state,'SELECT discount FROM buy_info WHERE pid='+literal(identifier)+';'))==1
            return ['Legacy fraction hints retain effective 13% VAT/no discount without rewriting submitted rate representation']
        self.case('purchase.entry_legacy_rate_hints',legacy)

        def invalid():
            self.fixture()
            changes=[('head','money',-1),('head','money','abc'),('head','money',300),('line','price',-1),('line','nums',.00001),('line','attr','unknown-category-not-an-attribute')]
            for scope,key,value in changes:
                body=self.body();body['purchaseNoteBuyDTO']['actual']=999
                body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
                target=body['purchaseNoteBuyDTO'] if scope=='head' else body['purchaseNoteInfoDTOS'][0]
                target[key]=value
                result=self.request('POST','/purchase-note/add',body,service='purchase')
                assert result.get('code')!=10000,'Invalid entry accepted: '+key
                assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
            return ['Invalid numeric input/precision, payment above recomputed actual and nonexistent auxiliary attribute reject without persisted header']
        self.case('purchase.entry_invalid_values_no_persistence',invalid)
        self.write_report()


def prepare():
    suite=PurchasePostingSuite(read_state());suite.fixture();suffix=uuid.uuid4().hex[:8]
    names=dict(goods='QA Entry Goods '+suffix,warehouse='QA Entry Warehouse '+suffix,supplier='QA Entry Supplier '+suffix)
    for table,key in [('goods','goods'),('warehouse','warehouse'),('supplier','supplier')]:
        sql(suite.state,'UPDATE '+table+' SET name='+literal(names[key])+' WHERE id='+literal(getattr(suite,key))+';')
    fixture={key:getattr(suite,key) for key in ['goods','warehouse','supplier','account','actor']}
    fixture.update(database=suite.state['database'],names=names,number='QAENTRY'+uuid.uuid4().hex[:20])
    fixture_path.write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated entry: '+json.dumps(dict(names=names,number=fixture['number'])))


def verify(quantity=2,audited=False):
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database'] and state['purchase_port']==18023
    number=literal(fixture['number'])
    assert sql(state,'SELECT COUNT(*) FROM buy WHERE number='+number+';')=='1','Browser save did not create exactly one real purchase'
    identifier=sql(state,'SELECT id FROM buy WHERE number='+number+';')
    assert sql(state,'SELECT supplier FROM buy WHERE id='+literal(identifier)+';')==fixture['supplier']
    assert sql(state,'SELECT goods FROM buy_info WHERE pid='+literal(identifier)+';')==fixture['goods']
    assert sql(state,'SELECT warehouse FROM buy_info WHERE pid='+literal(identifier)+';')==fixture['warehouse']
    assert Decimal(sql(state,'SELECT nums FROM buy_info WHERE pid='+literal(identifier)+';'))==quantity
    assert Decimal(sql(state,'SELECT total FROM buy WHERE id='+literal(identifier)+';'))==quantity*100
    assert Decimal(sql(state,'SELECT actual FROM buy WHERE id='+literal(identifier)+';'))==quantity*113
    assert sql(state,"SELECT IF(COALESCE(attr,'')='',1,0) FROM buy_info WHERE pid="+literal(identifier)+';')=='1'
    assert Decimal(sql(state,'SELECT money FROM buy WHERE id='+literal(identifier)+';'))==0
    assert sql(state,'SELECT `user` FROM buy WHERE id='+literal(identifier)+';')==fixture['actor']
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+';'))==(quantity if audited else 0)
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';'))==(quantity*113 if audited else 0)
    assert sql(state,'SELECT CAST(examine AS SIGNED) FROM buy WHERE id='+literal(identifier)+';')==('1' if audited else '0')
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(fixture['account'])+';'))==100
    report=dict(case='purchase.browser_complete_entry',status='verified',quantity=quantity,audited=audited,production_business_writes=0,all_system_features_accepted=False)
    (QA/('reports/purchase-entry-browser-'+str(quantity)+'-'+str(int(audited))+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS actual browser entry: real supplier/goods/warehouse IDs, quantity='+str(quantity)+' net='+str(quantity*100)+' actual='+str(quantity*113)+' paid=0; creator/attribute preserved; audited='+str(audited)+' with matching stock/payable')


def prepare_multi():
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database']
    goods=uuid.uuid4().hex
    sql(state,'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES('+','.join(literal(v) for v in [goods,fixture['names']['goods']+' Second','qa','QG'+goods[:16],'0','unit',75,90,0,0,'{}'])+');')
    fixture.update(multi_goods=goods,multi_number='QAENTRY'+uuid.uuid4().hex[:20])
    fixture['multi_before']={key:sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(key)+';') for key in [fixture['goods'],goods]}
    fixture['multi_balance']=sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';')
    fixture_path.write_text(json.dumps(fixture),encoding='utf-8')
    print('Prepared multi-entry number: '+fixture['multi_number']+'; search goods prefix: '+fixture['names']['goods'])


def verify_multi():
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database'] and state['purchase_port']==18023
    identifier=sql(state,'SELECT id FROM buy WHERE number='+literal(fixture['multi_number'])+';')
    assert identifier and '\n' not in identifier
    assert sql(state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(identifier)+';')=='2'
    assert set(sql(state,'SELECT goods FROM buy_info WHERE pid='+literal(identifier)+';').splitlines())=={fixture['goods'],fixture['multi_goods']}
    assert sql(state,"SELECT COUNT(*) FROM buy_info WHERE pid="+literal(identifier)+" AND warehouse="+literal(fixture['warehouse'])+" AND nums=1 AND tax=13 AND COALESCE(attr,'')='';")=='2'
    assert Decimal(sql(state,'SELECT total FROM buy WHERE id='+literal(identifier)+';'))==175
    assert Decimal(sql(state,'SELECT actual FROM buy WHERE id='+literal(identifier)+';'))==Decimal('197.75')
    assert Decimal(sql(state,'SELECT money FROM buy WHERE id='+literal(identifier)+';'))==0
    for goods,before in fixture['multi_before'].items():
        assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(goods)+';'))==Decimal(before)
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';'))==Decimal(fixture['multi_balance'])
    report=dict(case='purchase.browser_multi_entry',status='verified',line_count=2,production_business_writes=0,all_system_features_accepted=False)
    (QA/'reports/purchase-entry-browser-multi.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS browser multi-selection: two real lines, actual warehouse IDs, net175 actual197.75 paid0; earlier stock/payable unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify','verify-edited','verify-audited','prepare-multi','verify-multi','run'])
    action=parser.parse_args().action
    if action=='prepare':prepare()
    elif action=='run':PurchaseEntrySuite(read_state()).run()
    elif action=='prepare-multi':prepare_multi()
    elif action=='verify-multi':verify_multi()
    elif action=='verify-edited':verify(3)
    elif action=='verify-audited':verify(3,True)
    else:verify()
