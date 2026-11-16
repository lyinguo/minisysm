"""Real C1 sale/return/receipt grants and an ordinary operator's complete flow."""
import argparse,copy,json,uuid
from contextlib import contextmanager
from decimal import Decimal
from sale_return_posting_acceptance import SaleReturnPostingSuite
from resource_fixture import qa_resource_cache_snapshot
from purchase_ui_acceptance import PurchaseUiSuite
from payment_role_integration_acceptance import PaymentRoleIntegrationSuite
from acceptance import QA,read_state,sql,literal,authenticate_registered_login

SALE=['getSaleList','getSaleDetail','getGenerateReturnData','addSale','deleteSales','updateSale','check','examine','import','export-simple','export-detail']
RETURN=['saleReturnList','{id}','addSalesReturnOrder','deleteSalesReturnOrder','updateSalesReturnOrder','return/check','return/examine','importFund','exportSimpleFund','exportDetailFund']
RECEIPT=['fundReceiptList','fundReceiptDetail','add','update','audit','remove','import','export/simple','export/detail']
FUNCTIONS=[(str(start+i),mid,prefix+suffix) for start,mid,prefix,paths in [(150,'095','/sale/form/',SALE),(161,'097','/sale/return/',RETURN),(211,'121','/fund/receipt/',RECEIPT)] for i,suffix in enumerate(paths)]

class SaleRoleIntegrationSuite(SaleReturnPostingSuite):
    def __init__(self,state,through_gateway=False):
        self.through_gateway=through_gateway
        super().__init__(state)
    def request(self,method,path,body=None,service='c1'):
        if service=='sale' and method=='POST' and isinstance(body,list) and path.split('?')[0] in ('/sale/form/check','/sale/form/examine'):
            versions={}
            for identifier in body:
                response=self.request('GET','/sale/form/document/'+identifier,service='sale')
                versions[identifier]=response.get('data',{}).get('version','0'*64) if response.get('code')==10000 else '0'*64
            body=dict(ids=body,versions=versions)
        if self.through_gateway and service in ('c1','sale','fund'):service='gateway'
        return super().request(method,path,body,service)
    def case(self,name,action):return super().case(name+('_through_gateway' if self.through_gateway else ''),action)
    @contextmanager
    def catalog(self):
        ids=[row[0] for row in FUNCTIONS];menus=['000','092','095','097','120','121']
        assert sql(self.state,'SELECT COUNT(*) FROM func_perm WHERE id IN ('+','.join(literal(value) for value in ids)+');')=='0'
        assert sql(self.state,'SELECT COUNT(*) FROM menu WHERE id IN ('+','.join(literal(value) for value in menus)+');')=='0'
        try:
            for identifier,parent in [('000','0'),('092','000'),('095','092'),('097','092'),('120','000'),('121','120')]:
                sql(self.state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(value) for value in [identifier,parent,'QA Sales Catalog','qa-sale-'+identifier,0,0,'',0])+');')
            for identifier,mid,path in FUNCTIONS:
                sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(value) for value in [identifier,mid,'QA Sales '+identifier,path,0,'1'])+');')
            with qa_resource_cache_snapshot(self.state):yield
        finally:
            sql(self.state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(value) for value in ids)+');')
            for identifier in ['095','097','121','120','092','000']:sql(self.state,'DELETE FROM menu WHERE id='+literal(identifier)+';')
    def role_fixture(self):
        self.admin=self.token;self.role_name='QA Sale Live '+uuid.uuid4().hex[:8]
        self.role=self.success('POST','/role/add-role',dict(name=self.role_name,data='',root='[]',auth='{}'))
        self.user_id,user,_=self.new_user(role=self.role)
        self.ordinary=authenticate_registered_login(self.state,user['user'],user['pwd'],self.opener) if self.through_gateway else PurchaseUiSuite.login(self,user)
    def select(self,ids):
        groups={}
        for identifier,mid,path in FUNCTIONS:
            if identifier in ids:groups.setdefault(mid,[]).append(dict(id=identifier))
        root=[]
        for parent,mids in [('092',['095','097']),('120',['121'])]:
            children=[dict(id=mid,fun=groups[mid]) for mid in mids if mid in groups]
            if children:root.append(dict(id=parent,children=children))
        previous=self.token;self.token=self.admin
        try:assert self.request('PUT','/role/modify-role',dict(id=self.role,name=self.role_name,data='',root=json.dumps(root),auth='{}')).get('code')==10000
        finally:self.token=previous
    def reload_resources(self):return PaymentRoleIntegrationSuite.reload_resources(self)
    def run(self,baseline=False):
        with self.catalog():
            def create_live():
                self.fixture();self.role_fixture();self.reload_resources();self.token=self.ordinary
                try:
                    assert self.request('POST','/sale/form/addSale',self.body(),service='sale').get('code')==403
                    self.select(['153']);body=self.body();result=self.request('POST','/sale/form/addSale',body,service='sale')
                    if result.get('code')!=10000:
                        self.reload_resources();after=self.request('POST','/sale/form/addSale',body,service='sale');assert after.get('code')==10000,str(after)
                        self.select([]);revoked=self.request('POST','/sale/form/addSale',self.body(),service='sale');self.reload_resources()
                        raise AssertionError('Actual role grant returned '+str(result.get('code'))+'; resource reload enabled it; revoke with genuine granted cache returned '+str(revoked.get('code')))
                    identifier=result['data']['id'];assert sql(self.state,'SELECT `user` FROM sell WHERE id='+literal(identifier)+';')==self.user_id
                    self.reload_resources();sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id='153';")
                    try:assert self.request('POST','/sale/form/addSale',self.body(),service='sale').get('code')==403
                    finally:sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id='153';")
                    self.select([]);assert self.request('POST','/sale/form/addSale',self.body(),service='sale').get('code')==403
                    assert self.inventory()==10 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
                    return ['Real C1 save grants sale creation immediately; actual disabled function and revoke deny same OAuth token despite genuine stale cache; signed ordinary actor persists with no stock/cash/AR changes']
                finally:self.token=self.admin;self.select([])
            self.case('sale.permissions_real_role_save_create_disable_revoke',create_live)
            def preview_grant():
                source=self.posted();self.role_fixture();self.select(['152']);self.reload_resources();self.token=self.ordinary
                try:
                    result=self.preview(source);assert result.get('code')==10000,'Actual152 generate-return grant denied: '+str(result)
                    assert self.request('GET','/sale/form/document/'+source,service='sale').get('code')==403
                    self.select(['151']);assert self.preview(source).get('code')==403
                    return ['Actual152 alone permits scoped return-generation data; full original detail remains separately protected151 and detail-only cannot substitute generation permission']
                finally:self.token=self.admin;self.select([])
            self.case('sale.permissions_return_preview_uses_actual_catalog152',preview_grant)
            def return_detail():
                source,identifier,_=self.created();self.role_fixture();self.select(['162']);self.reload_resources();self.token=self.ordinary
                try:
                    result=self.request('GET','/sale/return/document/'+identifier,service='sale');assert result.get('code')==10000,'Actual162 return detail depends on unrelated sale detail: '+str(result)
                    assert result['data']['header']['id']==identifier
                    assert self.request('GET','/sale/form/document/'+source,service='sale').get('code')==403
                    self.select([]);assert self.request('GET','/sale/return/document/'+identifier,service='sale').get('code')==403
                    return ['Return detail162 works without unrelated original-sale detail151; source validation stays scoped and the same token loses detail on revoke']
                finally:self.token=self.admin;self.select([])
            self.case('sale.permissions_return_detail_has_no_hidden_original_grant',return_detail)
            if not baseline:self.case('sale.permissions_full_ordinary_sale_return_receipt_lifecycle',self.full_lifecycle)
        self.write_report()

    def full_lifecycle(self):
        self.fixture();self.role_fixture();ids=[row[0] for row in FUNCTIONS];self.select(ids);self.token=self.ordinary
        def balances(stock,cash,ar):
            actual=(self.inventory(),self.balance('account',self.account),self.balance('customer',self.customer))
            assert actual==(stock,cash,ar),'Actual stock/cash/AR '+str(actual)+' differs from '+str((stock,cash,ar))
        try:
            body=self.body();body.update(time='2026-11-16 10:00:00',money=100,account=self.account);body['items'][0].update(nums=3,discount=1,tax=.13)
            sale=self.create(body);assert self.request('POST','/sale/form/check?check=true',[sale],service='sale').get('code')==10000
            assert self.post([sale]).get('code')==10000;balances(7,200,239)
            body=self.return_body(sale,1);body.update(money=25,account=self.account)
            result=self.add_return(body);assert result.get('code')==10000,str(result);returned=result['data']
            self.reload_resources();self.select([value for value in ids if value!='165'])
            revision=self.revision(returned);assert self.revise_return(revision).get('code')==403
            self.select(ids);assert self.revise_return(revision).get('code')==10000
            assert self.review([returned],versions=self.versions([returned])).get('code')==10000
            assert self.post_return([returned],versions=self.versions([returned])).get('code')==10000;balances(8,175,151)
            body=dict(customer=self.customer,time='2026-11-16 14:00:00',number='QASALERC'+uuid.uuid4().hex[:20],people='',file=[],data='QA sale final receipt',info=[dict(account=self.account,amount=151,settle='',data='QA')])
            result=self.request('POST','/fund/receipt',body,service='fund');assert result.get('code')==10000,str(result);receipt=result['data']
            plan=self.request('GET','/fund/receipt/settlement-preview?id='+receipt,service='fund');assert plan.get('code')==10000,str(plan)
            assert [Decimal(str(plan['data'][key])) for key in ['invoiceTotal','creditTotal','receivableNet']]==list(map(Decimal,['239','88','151']))
            assert self.request('POST','/fund/receipt/settle',dict(id=receipt,status=1,version=plan['data']['version'],allocations=plan['data']['allocations']),service='fund').get('data')==1;balances(8,326,0)
            for table,identifier in [('sell',sale),('sre',returned),('imy',receipt)]:assert sql(self.state,'SELECT `user` FROM '+table+' WHERE id='+literal(identifier)+';')==self.user_id
            doc=self.request('GET','/fund/receipt/document/'+receipt,service='fund')['data'];reverse=dict(id=receipt,status=0,version=doc['version'])
            self.reload_resources();self.select([value for value in ids if value!='215'])
            assert self.request('POST','/fund/receipt/settle',reverse,service='fund').get('code')==403;balances(8,326,0)
            self.select(ids);assert self.request('POST','/fund/receipt/settle',reverse,service='fund').get('data')==1;balances(8,175,151)
            doc=self.request('GET','/fund/receipt/document/'+receipt,service='fund')['data']
            assert self.request('DELETE','/fund/receipt/document/'+receipt,dict(version=doc['version']),service='fund').get('code')==10000
            assert self.post_return([returned],status=0,versions=self.versions([returned])).get('code')==10000;balances(7,200,239)
            assert self.review([returned],status=0,versions=self.versions([returned])).get('code')==10000
            assert self.remove_return(returned,self.return_doc(returned)['version']).get('code')==10000
            assert self.post([sale],False).get('code')==10000;balances(10,100,0)
            assert self.request('POST','/sale/form/check?check=false',[sale],service='sale').get('code')==10000
            assert self.request('DELETE','/sale/form/deleteSales',[sale],service='sale').get('code')==10000
            for table,identifier,kind in [('sell',sale,'sell'),('sre',returned,'sre'),('imy',receipt,'imy')]:
                assert sql(self.state,'SELECT COUNT(*) FROM '+table+' WHERE id='+literal(identifier)+';')=='0'
                assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE type='+literal(kind)+' AND source='+literal(identifier)+' AND `user`='+literal(self.user_id)+';'))>=4
                assert sql(self.state,'SELECT COUNT(*) FROM record WHERE type='+literal(kind)+' AND source='+literal(identifier)+' AND `user`<>'+literal(self.user_id)+';')=='0'
            return ['Same real C1-authorized ordinary operator completes sale3/receive100→return1/refund25→receipt151, reaching stock8/cash326/AR0; revocation blocks return edit and receipt reverse under actual stale caches', 'Reverse/delete receipt, return and sale in dependency order restores initial real stock10/cash100/AR0; all heads removed with attributable histories retained']
        finally:self.token=self.admin;self.select([])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');parser.add_argument('--gateway',action='store_true');args=parser.parse_args()
    SaleRoleIntegrationSuite(read_state(),args.gateway).run(args.baseline)
