"""Actual C1 procurement catalog selections, canonical prefixes and business flow."""
import argparse,json,uuid,copy
from contextlib import contextmanager
from decimal import Decimal
from booking_receive_acceptance import ReceiveSuite
from purchase_return_posting_acceptance import PurchaseReturnPostingSuite
from payment_role_integration_acceptance import FUNCTIONS as PAYMENT_FUNCTIONS
from resource_fixture import qa_resource_cache_snapshot
from acceptance import QA,read_state,sql,literal,authenticate_registered_login
from purchase_ui_acceptance import PurchaseUiSuite

ORDER=['list','detail','generate-purchaseData','add','delete','update','audit','import-bor','export-bor','export/detail']
NOTE=['list','info','getBuildBre','add','delete','revise','verification','audit','import','export/simple','export/detail']
RETURN=['list','detail','add','delete','checkout','approve','import','bre-export','breInfo-export']
FUNCTIONS=[(str(start+i),mid,'/j3-purchase/'+kind+'/'+suffix) for start,mid,kind,paths in [(109,'086','purchase-order',ORDER),(119,'088','purchase-note',NOTE),(130,'090','purchase-return-form',RETURN)] for i,suffix in enumerate(paths)]
EXTRA=[('purchase_supply_manage','086','/j3-purchase/purchase-order/supply/manage'),('purchase_return_update','090','/j3-purchase/purchase-return-form/update')]

class PurchaseRoleIntegrationSuite(ReceiveSuite):
    def __init__(self,state,through_gateway=False):
        self.through_gateway=through_gateway
        super().__init__(state)

    def request(self,method,path,body=None,service='c1'):
        if self.through_gateway and service in ('c1','purchase','payment'):
            if service=='purchase':path='/j3-purchase'+path
            service='gateway'
        return super().request(method,path,body,service)

    def case(self,name,action):
        return super().case(name+('_through_gateway' if self.through_gateway else ''),action)

    @contextmanager
    def catalog(self,baseline):
        ids=[row[0] for row in FUNCTIONS]+[row[0] for row in EXTRA]+[row[0] for row in PAYMENT_FUNCTIONS]
        menus=['000','085','086','088','090','120','123']
        assert sql(self.state,'SELECT COUNT(*) FROM func_perm WHERE id IN ('+','.join(literal(v) for v in ids)+');')=='0'
        assert sql(self.state,'SELECT COUNT(*) FROM menu WHERE id IN ('+','.join(literal(v) for v in menus)+');')=='0'
        try:
            for identifier,parent in [('000','0'),('085','000'),('086','085'),('088','085'),('090','085'),('120','000'),('123','120')]:
                resource={'086':'/purchase-booking','090':'/purchase-return'}.get(identifier,'')
                sql(self.state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(v) for v in [identifier,parent,'QA Purchase Catalog','qa-purchase-'+identifier,0,0,resource,0])+');')
            for identifier,mid,path in FUNCTIONS+[(identifier,'123',path) for identifier,path in PAYMENT_FUNCTIONS]:
                sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(v) for v in [identifier,mid,'QA Purchase Function '+identifier,path,0,'1'])+');')
            if not baseline:
                migration=(QA.parent/'database/migrations/20261117_purchase_permissions.sql').read_text(encoding='utf-8')
                sql(self.state,migration);sql(self.state,migration)
                assert sql(self.state,"SELECT COUNT(*) FROM func_perm WHERE id IN ('purchase_supply_manage','purchase_return_update');")=='2'
            with qa_resource_cache_snapshot(self.state):yield
        finally:
            sql(self.state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(v) for v in ids)+');')
            for identifier in ['086','088','090','123','120','085','000']:sql(self.state,'DELETE FROM menu WHERE id='+literal(identifier)+';')

    def role_fixture(self):
        self.admin=self.token
        self.role_name='QA Procurement Live '+uuid.uuid4().hex[:8]
        self.role=self.success('POST','/role/add-role',dict(name=self.role_name,data='',root='[]',auth='{}'))
        self.user_id,user,_=self.new_user(role=self.role)
        self.ordinary=authenticate_registered_login(self.state,user['user'],user['pwd'],self.opener) if self.through_gateway else PurchaseUiSuite.login(self,user)

    def select(self,ids):
        selected=set(ids);groups={}
        for identifier,mid,path in FUNCTIONS+EXTRA+[(identifier,'123',path) for identifier,path in PAYMENT_FUNCTIONS]:
            if identifier in selected:groups.setdefault(mid,[]).append(dict(id=identifier))
        root=[]
        for parent,mids in [('085',['086','088','090']),('120',['123'])]:
            children=[dict(id=mid,fun=groups[mid]) for mid in mids if mid in groups]
            if children:root.append(dict(id=parent,children=children))
        current=self.token;self.token=self.admin
        try:assert self.request('PUT','/role/modify-role',dict(id=self.role,name=self.role_name,data='',root=json.dumps(root),auth='{}')).get('code')==10000
        finally:self.token=current

    def reload_resources(self):
        from payment_role_integration_acceptance import PaymentRoleIntegrationSuite
        PaymentRoleIntegrationSuite.reload_resources(self)

    def return_helper(self):
        helper=PurchaseReturnPostingSuite(self.state)
        for key in ['goods','warehouse','supplier','account','actor']:setattr(helper,key,getattr(self,key))
        helper.request=self.request
        return helper

    def run(self,baseline=False):
        with self.catalog(baseline):
            for kind in ['order','note','return']:
                def create(kind=kind):
                    self.fixture();self.role_fixture()
                    helper=None
                    if kind=='order':body=self.order_body();grants=['112'];path='/purchase-order/add';table='bor'
                    else:
                        self.source=self.create_order(self.order_body());self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+';').splitlines()
                        assert self.audit([self.source]).get('code')==10000
                        if kind=='note':body=self.receive_body();grants=['111','122'];path='/purchase-order/receive';table='buy'
                        else:
                            source=self.receive(self.receive_body())['data']['id']
                            assert self.check([source]).get('code')==10000 and self.post([source]).get('code')==10000
                            helper=self.return_helper();body=helper.body_return(source,1);grants=['121','131','132'];path='/purchase-return-form/add';table='bre'
                    self.select(grants);self.token=self.ordinary
                    try:
                        result=self.request('POST',path,body,service='purchase')
                        if result.get('code')!=10000:
                            self.reload_resources()
                            after=self.request('POST',path,body,service='purchase')
                            raise AssertionError('Actual prefixed catalog grant cannot create '+kind+': before reload='+str(result.get('code'))+', after actual reload='+str(after.get('code')))
                        identifier=result['data']['id'] if kind=='note' else result['data']
                        assert sql(self.state,'SELECT `user` FROM '+table+' WHERE id='+literal(identifier)+';')==self.user_id
                        self.reload_resources()
                        retry=copy.deepcopy(body);retry['number']='QADENY'+uuid.uuid4().hex[:20]
                        function={'order':'112','note':'122','return':'132'}[kind]
                        sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id="+literal(function)+';')
                        try:assert self.request('POST',path,retry,service='purchase').get('code')==403,'Disabled actual catalog function remained usable'
                        finally:sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id="+literal(function)+';')
                        self.select([])
                        assert self.request('POST',path,retry,service='purchase').get('code')==403
                        assert self.inventory()==(2 if kind=='return' else 0)
                        assert self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==(226 if kind=='return' else 0)
                        return ['Actual C1 selection of existing prefixed catalog permits current ordinary '+kind+' creation and persists real actor; true stale cache cannot retain revoked permission; draft changes no inventory/cash/payable']
                    finally:self.token=self.admin;self.select([])
                self.case('purchase.permissions_actual_catalog_'+kind+'_create_revoke',create)
            if not baseline:self.case('purchase.permissions_full_ordinary_business_lifecycle',self.full_lifecycle)
        self.write_report()

    def full_lifecycle(self):
        self.fixture();self.role_fixture()
        sql(self.state,'UPDATE account SET initial=1000,balance=1000 WHERE id='+literal(self.account)+';')
        all_ids=[row[0] for row in FUNCTIONS+EXTRA]+[row[0] for row in PAYMENT_FUNCTIONS]
        self.select(all_ids);self.token=self.ordinary
        receipts=[];returned=None;payment=None;order=None
        def balances(stock,cash,payable):
            actual=(self.inventory(),self.balance('account',self.account),self.balance('supplier',self.supplier))
            assert actual==(stock,cash,payable),'Actual stock/cash/AP '+str(actual)+' differs from '+str((stock,cash,payable))
        try:
            self.reload_resources();self.select([value for value in all_ids if value!='purchase_supply_manage'])
            assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=False),service='purchase').get('code')==403
            self.select(all_ids)
            assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=False),service='purchase').get('code')==10000
            assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=True),service='purchase').get('code')==10000
            body=self.order_body();body['purchaseOrderInfoDTOList'][0]['nums']=10
            order=self.create_order(body);self.source=order
            self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(order)+';').splitlines()
            assert self.audit([order]).get('code')==10000
            balances(0,1000,0)
            for quantity,stock,payable in [(6,6,678),(4,10,1130)]:
                result=self.receive(self.receive_body(quantity));assert result.get('code')==10000,str(result)
                identifier=result['data']['id'];receipts.append(identifier)
                assert self.check([identifier]).get('code')==10000
                assert self.post([identifier]).get('code')==10000
                balances(stock,1000,payable)
            helper=self.return_helper()
            body=helper.body_return(receipts[0],2);body.update(money=50,account=self.account,time='2026-11-16 09:00:00')
            result=helper.add_return(body);assert result.get('code')==10000,str(result);returned=result['data']
            revision=helper.revision_return(returned,quantity=2);revision.update(money=50,account=self.account,data='QA ordinary revised return')
            self.reload_resources();self.select([value for value in all_ids if value!='purchase_return_update'])
            assert helper.revise_return(returned,revision).get('code')==403
            self.select(all_ids)
            revised=helper.revise_return(returned,revision);assert revised.get('code')==10000,str(revised)
            assert helper.review([returned],versions=helper.versions([returned])).get('code')==10000
            assert helper.post_return([returned],versions=helper.versions([returned])).get('code')==10000
            balances(8,1050,954)
            payment_body=dict(supplier=self.supplier,time='2026-11-16',number='QAROLEPAY'+uuid.uuid4().hex[:20],people='',file='[]',data='QA ordinary procurement settlement',infoList=[dict(account=self.account,money=954,settle='',data1='QA')])
            result=self.request('POST','/payment-order/add',payment_body,service='payment');assert result.get('code')==10000,str(result);payment=result['data']
            (QA/'runtime/purchase-role-lifecycle.json').write_text(json.dumps(dict(database=self.state['database'],order=order,receipts=receipts,returned=returned,payment=payment,actor=self.user_id,account=self.account,supplier=self.supplier,goods=self.goods,warehouse=self.warehouse)),encoding='utf-8')
            plan=self.request('GET','/payment-order/settlement-preview?id='+payment,service='payment');assert plan.get('code')==10000,str(plan)
            assert [Decimal(str(plan['data'][key])) for key in ['invoiceTotal','creditTotal','payableNet']]==list(map(Decimal,['1130','176','954']))
            result=self.request('POST','/payment-order/settle',dict(id=payment,status=1,version=plan['data']['version'],allocations=plan['data']['allocations']),service='payment')
            assert result.get('data')==1,str(result);balances(8,96,0)
            for table,ids in [('bor',[order]),('buy',receipts),('bre',[returned]),('omy',[payment])]:
                for identifier in ids:assert sql(self.state,'SELECT `user` FROM '+table+' WHERE id='+literal(identifier)+';')==self.user_id
            doc=self.request('GET','/payment-order/document/'+payment,service='payment')['data']
            assert self.request('POST','/payment-order/settle',dict(id=payment,status=0,version=doc['version']),service='payment').get('data')==1
            balances(8,1050,954)
            doc=self.request('GET','/payment-order/document/'+payment,service='payment')['data']
            assert self.request('DELETE','/payment-order/document/'+payment,dict(version=doc['version']),service='payment').get('code')==10000
            assert helper.post_return([returned],status=0,versions=helper.versions([returned])).get('code')==10000
            balances(10,1000,1130)
            assert helper.review([returned],status=0,versions=helper.versions([returned])).get('code')==10000
            assert helper.remove_return(returned,helper.return_doc(returned)['version']).get('code')==10000
            for identifier,stock,payable in [(receipts[1],6,678),(receipts[0],0,0)]:
                assert self.post([identifier],target=0).get('code')==10000
                balances(stock,1000,payable)
                assert self.check([identifier],target=0).get('code')==10000
                result=self.request('POST','/purchase-note/delete',[identifier],service='purchase');assert result.get('code')==10000,str(result)
            assert self.audit([order],target=0).get('code')==10000
            assert self.request('DELETE','/purchase-order/delete',[order],service='purchase').get('code')==10000
            balances(0,1000,0)
            for table,ids,kind in [('bor',[order],'bor'),('buy',receipts,'buy'),('bre',[returned],'bre'),('omy',[payment],'omy')]:
                for identifier in ids:
                    assert sql(self.state,'SELECT COUNT(*) FROM '+table+' WHERE id='+literal(identifier)+';')=='0'
                    assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE type='+literal(kind)+' AND source='+literal(identifier)+' AND `user`='+literal(self.user_id)+';'))>=4
                    assert sql(self.state,'SELECT COUNT(*) FROM record WHERE type='+literal(kind)+' AND source='+literal(identifier)+' AND `user`<>'+literal(self.user_id)+';')=='0'
            return ['Actual C1 selections enable separate supply maintenance and return revision; genuine stale cache cannot retain either revoked action', 'Same ordinary operator completes order10→receipts6+4→supplier return2/refund50→reviewed payment954 (cash1000→1050→96/AP0/stock8), then reverses/deletes downstream in order and restores stock0/cash1000/AP0; all original heads deleted with attributable histories preserved']
        finally:self.token=self.admin;self.select([])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');parser.add_argument('--gateway',action='store_true');args=parser.parse_args()
    PurchaseRoleIntegrationSuite(read_state(),args.gateway).run(args.baseline)
