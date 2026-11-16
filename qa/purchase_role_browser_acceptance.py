"""Prepare isolated real role UI; independently verify saved grants and business access."""
import argparse,copy,json,uuid
from decimal import Decimal
from acceptance import QA,Suite,read_state,sql,literal,authenticate_registered_login
from purchase_role_integration_acceptance import PurchaseRoleIntegrationSuite,FUNCTIONS,EXTRA,PAYMENT_FUNCTIONS

PATH=QA/'runtime/purchase-role-browser-fixture.json'
MENUS=[('000','0','QA根目录',''),('085','000','采购管理',''),('086','085','采购订单','/purchase-booking'),('088','085','采购单','/purchase-order'),('090','085','采购退货','/purchase-return'),('120','000','财务管理',''),('123','120','付款单','')]
ALL_FUNCTIONS=FUNCTIONS+EXTRA+[(identifier,'123',url) for identifier,url in PAYMENT_FUNCTIONS]

def selected(root):
    assert isinstance(root,list),'Role UI must persist canonical tree, not a boolean map'
    result=[]
    def walk(nodes):
        for node in nodes:
            result.extend(str(item['id']) for item in node.get('fun',[]));walk(node.get('children',[]))
    walk(root);return set(result)

def prepare():
    state=read_state();suite=PurchaseRoleIntegrationSuite(state);suite.fixture()
    ids=[row[0] for row in ALL_FUNCTIONS]
    assert sql(state,'SELECT COUNT(*) FROM func_perm WHERE id IN ('+','.join(literal(value) for value in ids)+');')=='0'
    assert sql(state,'SELECT COUNT(*) FROM menu WHERE id IN ('+','.join(literal(row[0]) for row in MENUS)+');')=='0'
    for identifier,parent,name,resource in MENUS:
        sql(state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(value) for value in [identifier,parent,name,'qa-role-browser-'+identifier,0,0,resource,0])+');')
    names={'112':'新增采购订单','120':'采购单详情','123':'删除采购单','purchase_supply_manage':'维护商品供货关系','purchase_return_update':'修改采购退货草稿'}
    for identifier,mid,url in ALL_FUNCTIONS:
        sql(state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(value) for value in [identifier,mid,names.get(identifier,'QA功能'+identifier),url,0,'1'])+');')
    name='QA浏览器采购权限'+uuid.uuid4().hex[:8]
    legacy=json.dumps({'112':True,'120':True,'purchase_supply_manage':True})
    role=suite.success('POST','/role/add-role',dict(name=name,data='QA browser permissions',root=legacy,auth='{}'))
    user_id,user,_=suite.new_user(role=role)
    ordinary=authenticate_registered_login(state,user['user'],user['pwd'],suite.opener)
    fixture=dict(database=state['database'],role=role,name=name,user=user_id,admin_token=suite.token,ordinary_token=ordinary,body=suite.order_body(),goods=suite.goods,supplier=suite.supplier,warehouse=suite.warehouse,account=suite.account)
    PATH.write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    suite.token=ordinary
    response=suite.request('POST','/j3-purchase/purchase-order/add',fixture['body'],service='gateway')
    assert response.get('code')==403
    (QA/'reports/purchase-role-ui-legacy-baseline.json').write_text(json.dumps(dict(database_isolated=True,production_business_writes=0,status='failed',case='role_ui_saved_boolean_map_does_not_enable_order',actual_code=403,desired_code=10000),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Role browser fixture:',name)
    print('Open http://127.0.0.1:18030/qa-role.html; find role, open details/functions; verify named supply+order grants checked and ambiguous detail unchecked; explicitly confirm selection then save')

def verify(action):
    state=read_state();f=json.loads(PATH.read_text(encoding='utf-8'));assert f['database']==state['database']
    suite=Suite(state);suite.token=f['ordinary_token']
    root=json.loads(bytes.fromhex(sql(state,'SELECT HEX(root) FROM role WHERE id='+literal(f['role'])+';')).decode('utf-8'))
    if action=='verify-granted':
        assert selected(root)=={'112','purchase_supply_manage'},'Saved UI selection includes menu/ambiguous/unselected permissions'
        for enabled in [False,True]:
            response=suite.request('POST','/j3-purchase/purchase-order/supply',dict(goods=f['goods'],supplier=f['supplier'],enabled=enabled),service='gateway')
            assert response.get('code')==10000,str(response)
        response=suite.request('POST','/j3-purchase/purchase-order/add',f['body'],service='gateway')
        assert response.get('code')==10000,str(response);identifier=response['data'];f['order']=identifier
        assert sql(state,'SELECT `user` FROM bor WHERE id='+literal(identifier)+';')==f['user']
        assert sql(state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(identifier)+';')=='1'
        PATH.write_text(json.dumps(f,ensure_ascii=False),encoding='utf-8')
    else:
        assert selected(root)==set()
        body=copy.deepcopy(f['body']);body['number']='QAGUIDENY'+uuid.uuid4().hex[:20]
        assert suite.request('POST','/j3-purchase/purchase-order/add',body,service='gateway').get('code')==403
        assert suite.request('POST','/j3-purchase/purchase-order/supply',dict(goods=f['goods'],supplier=f['supplier'],enabled=False),service='gateway').get('code')==403
        assert sql(state,'SELECT COUNT(*) FROM bor WHERE number='+literal(body['number'])+';')=='0'
        assert sql(state,'SELECT COUNT(*) FROM bor WHERE id='+literal(f['order'])+';')=='1'
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';'))==0
    report=dict(database_isolated=True,production_business_writes=0,status='verified',case='role.browser_'+action,all_system_features_accepted=False)
    (QA/('reports/purchase-role-browser-'+action+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('VERIFIED actual browser role '+action+' plus ordinary Login/Gateway operation and independent DB balances')

def cleanup():
    state=read_state();f=json.loads(PATH.read_text(encoding='utf-8'));assert f['database']==state['database']
    assert sql(state,'SELECT COUNT(*) FROM role WHERE id='+literal(f['role'])+' AND name='+literal(f['name'])+';')=='1'
    suite=Suite(state)
    assert suite.request('PUT','/role/modify-role',dict(id=f['role'],name=f['name'],data='QA browser permissions',root='[]',auth='{}')).get('code')==10000
    for identifier,parent,name,resource in MENUS:
        key=sql(state,'SELECT `key` FROM menu WHERE id='+literal(identifier)+';')
        assert key in ('','qa-role-browser-'+identifier),'Refusing to remove metadata not owned by this browser fixture'
    sql(state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(row[0]) for row in ALL_FUNCTIONS)+');')
    for identifier in ['086','088','090','123','120','085','000']:
        sql(state,'DELETE FROM menu WHERE id='+literal(identifier)+" AND `key`="+literal('qa-role-browser-'+identifier)+';')
    print('QA browser catalog removed, owned role revoked; real tested order/history retained, normal data untouched')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify-granted','verify-revoked','cleanup']);args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='cleanup':cleanup()
    else:verify(args.action)
