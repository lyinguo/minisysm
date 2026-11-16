"""Real inbound-role grants, warehouse references and stock -> sale -> receipt flow."""
import argparse,json,uuid
from contextlib import contextmanager
from sale_role_integration_acceptance import SaleRoleIntegrationSuite,FUNCTIONS as SALE_FUNCTIONS
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import QA,read_state,sql,literal,authenticate_registered_login

ENTRY=[(str(identifier),'103','/j2-store/otherin'+suffix) for identifier,suffix in [(182,''),(183,'/detail'),(184,'/add'),(185,'/delete'),(186,'/update'),(187,'/check'),(188,'/examine')]]
ALL=SALE_FUNCTIONS+ENTRY

class StockRoleSuite(SaleRoleIntegrationSuite):
    bootstrap=False
    def request(self,method,path,body=None,service='c1'):
        if self.through_gateway and service=='store':path='/j2-store'+path;service='gateway'
        return super().request(method,path,body,service)
    @contextmanager
    def catalog(self,baseline=False):
        with super().catalog():
            ids=[row[0] for row in ENTRY]
            assert sql(self.state,"SELECT COUNT(*) FROM menu WHERE id IN ('102','103');")=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM func_perm WHERE id IN ('+','.join(literal(x) for x in ids)+');')=='0'
            try:
                for identifier,parent in [('102','000'),('103','102')]:
                    sql(self.state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(v) for v in [identifier,parent,'QA Stock Catalog','qa-stock-'+identifier,0,0,'',0])+');')
                for identifier,mid,path in ENTRY:
                    if identifier=='182':path='/j2-store\r\n/otherin'
                    sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(v) for v in [identifier,mid,'QA Stock '+identifier,path,0,'1'])+');')
                if not baseline:
                    migration=(QA.parent/'database/migrations/20261117_stock_permission_urls.sql').read_text(encoding='utf-8')
                    sql(self.state,migration);sql(self.state,migration)
                    assert sql(self.state,"SELECT url FROM func_perm WHERE id='182';")=='/j2-store/otherin'
                yield
            finally:
                sql(self.state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(x) for x in ids)+");DELETE FROM menu WHERE id='103';DELETE FROM menu WHERE id='102';")
    def select(self,ids):
        selected=set(ids)
        if self.bootstrap and selected & {row[0] for row in SALE_FUNCTIONS}:selected.update(row[0] for row in ENTRY)
        groups={}
        for identifier,mid,path in ALL:
            if identifier in selected:groups.setdefault(mid,[]).append(dict(id=identifier))
        root=[]
        for parent,mids in [('092',['095','097']),('120',['121']),('102',['103'])]:
            children=[dict(id=mid,fun=groups[mid]) for mid in mids if mid in groups]
            if children:root.append(dict(id=parent,children=children))
        previous=self.token;self.token=self.admin
        try:assert self.request('PUT','/role/modify-role',dict(id=self.role,name=self.role_name,data='',root=json.dumps(root),auth='{}')).get('code')==10000
        finally:self.token=previous
        if self.bootstrap and selected and not getattr(self,'bootstrap_entry',None):
            self.token=self.ordinary
            try:
                self.bootstrap_entry,_=self.create_inbound(10);self.audit(self.bootstrap_entry,1)
                assert self.inventory()==10
                assert sql(self.state,'SELECT `user` FROM entry WHERE id='+literal(self.bootstrap_entry)+';')==self.user_id
            finally:self.token=previous
    def fixture(self,stock=10):super().fixture(stock=0 if self.bootstrap else stock)
    def full_stock_flow(self):
        self.bootstrap=True;self.bootstrap_entry=None
        try:
            evidence=super().full_lifecycle()
            self.select([row[0] for row in ENTRY]);self.token=self.ordinary
            self.audit(self.bootstrap_entry,0)
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='entry' AND source="+literal(self.bootstrap_entry)+' AND `user`<>'+literal(self.user_id)+';')=='0'
            return evidence+['Initial stock0 is actually received and posted by this same ordinary operator through granted inbound functions; final reversal restores stock0/cash100/AR0; all inbound histories use the signed user ID']
        finally:self.bootstrap=False;self.token=self.admin;self.select([])
    def run(self,baseline=False):
        with self.catalog(baseline):
            def grants():
                self.fixture(stock=0);self.role_fixture();self.reload_resources();self.token=self.ordinary
                try:
                    assert self.request('POST','/otherin/add',self.inbound(),service='store').get('code')==403
                    self.select(['184']);result=self.request('POST','/otherin/add',self.inbound(),service='store')
                    assert result.get('code')==10000,'Actual184 role grant failed: code='+str(result.get('code'))
                    self.reload_resources();self.select([])
                    assert self.request('POST','/otherin/add',self.inbound(),service='store').get('code')==403
                    assert self.inventory()==0
                    return ['Actual C1 normal184 selection grants creation immediately; genuine stale cache cannot retain revoked creation; draft leaves actual stock0']
                finally:self.token=self.admin;self.select([])
            self.case('stock.permissions_actual_catalog_create_revoke',grants)
            def reserved():
                self.fixture(stock=0);self.role_fixture();keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(self.role)+';')
                sql(self.state,"UPDATE role SET keyword='ROLE_ADMIN' WHERE id="+literal(self.role)+';')
                try:
                    _,user,_=self.new_user(role=self.role);self.token=authenticate_registered_login(self.state,user['user'],user['pwd'],self.opener) if self.through_gateway else PurchaseUiSuite.login(self,user)
                    result=self.request('POST','/otherin/add',self.inbound(),service='store')
                    assert result.get('code')==403,'Nonzero legacy administrator label bypassed inbound permission: '+str(result.get('code'))
                    assert self.inventory()==0
                    return ['Actual OAuth nonzero role with explicit owned legacy ROLE_ADMIN keyword cannot bypass missing inbound function grant']
                finally:self.token=self.admin;sql(self.state,'UPDATE role SET keyword='+literal(keyword)+' WHERE id='+literal(self.role)+';');self.select([])
            self.case('stock.permissions_legacy_admin_label_cannot_bypass',reserved)
            def foreign_warehouse():
                self.fixture(stock=0);frame,warehouse=[uuid.uuid4().hex for _ in range(2)]
                sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Stock Foreign');INSERT INTO warehouse(id,name,number,frame) VALUES("+','.join(literal(v) for v in [warehouse,'QA Stock Foreign Warehouse','QA'+warehouse[:20],frame])+');')
                body=self.inbound();body['otherInListDetailInfoDTOList'][0]['warehouse']=warehouse
                result=self.request('POST','/otherin/add',body,service='store')
                assert result.get('code')!=10000,'Own-organization header accepted a foreign warehouse'
                assert sql(self.state,'SELECT COUNT(*) FROM entry WHERE number='+literal(body['number'])+';')=='0'
                identifier,_=self.create_inbound();original=self.detail(identifier)
                changed=json.loads(json.dumps(original));changed['items'][0]['warehouse']=warehouse
                result=self.request('PUT','/transfer/report-documents/entry/'+identifier,{k:changed[k] for k in ['version','header','items']},service='store')
                assert result.get('code')!=10000 and self.detail(identifier)==original
                assert self.inventory()==0
                sql(self.state,'UPDATE entry_info SET warehouse='+literal(warehouse)+' WHERE pid='+literal(identifier)+';')
                try:
                    bad=self.detail(identifier)
                    result=self.request('POST','/transfer/report-documents/entry/'+identifier+'/audit',dict(target=1,version=bad['version']),service='store')
                    assert result.get('code')!=10000,'Owned legacy inconsistent warehouse reference was posted'
                    assert sql(self.state,'SELECT CAST(examine AS SIGNED) FROM entry WHERE id='+literal(identifier)+';')=='0'
                    assert sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(identifier)+';')=='0'
                finally:sql(self.state,'UPDATE entry_info SET warehouse='+literal(self.warehouse)+' WHERE pid='+literal(identifier)+';')
                return ['Actual create and report revision reject own-header/foreign-warehouse references before persistence; source document/version and stock remain unchanged']
            self.case('stock.references_foreign_warehouse_create_and_report_edit',foreign_warehouse)
            def signed_actor():
                self.fixture(stock=0);identifier,_=self.create_inbound();self.audit(identifier,1)
                assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='entry' AND source="+literal(identifier)+' AND `user`='+literal(self.actor)+';')=='2','Inbound report audit stored login name instead of actual user ID'
                self.audit(identifier,0);assert self.inventory()==0
                return ['Actual report audit/reversal retain signed user ID in histories, not mutable login name; stock4→0 agrees']
            self.case('stock.audit_signed_operator_id',signed_actor)
            if not baseline:
                def separate_reads():
                    self.fixture(stock=0);identifier,payload=self.create_inbound();self.role_fixture();self.select(['183']);self.token=self.ordinary
                    path='/transfer/report-documents/entry'
                    try:
                        assert self.request('GET',path+'/'+identifier,service='store').get('code')==10000
                        assert self.request('GET',path+'?number='+payload['number'],service='store').get('code')==403
                        self.select(['182']);page=self.request('GET',path+'?number='+payload['number'],service='store')
                        assert page.get('code')==10000 and page['data']['total']==1
                        assert self.request('GET',path+'/'+identifier,service='store').get('code')==403
                        self.reload_resources();sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id='182';")
                        try:assert self.request('GET',path+'?number='+payload['number'],service='store').get('code')==403
                        finally:sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id='182';")
                        return ['Actual normal182 list and183 detail are independent grants; genuine stale resource cache cannot override disabled182; normalized catalog path works']
                    finally:self.token=self.admin;self.select([])
                self.case('stock.permissions_list_detail_and_disabled_function',separate_reads)
                self.case('stock.permissions_ordinary_inbound_sale_return_receipt_and_reverse',self.full_stock_flow)
        self.write_report()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');parser.add_argument('--gateway',action='store_true');args=parser.parse_args()
    StockRoleSuite(read_state(),args.gateway).run(args.baseline)
