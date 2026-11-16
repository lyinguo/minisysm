"""Real role-save -> ordinary receipt access, including a stale derived cache."""
import json,uuid,urllib.request
from receipt_document_scope_acceptance import ReceiptDocumentScopeSuite
from resource_fixture import qa_resource_cache_snapshot
from acceptance import read_state,sql,literal,QA

class ReceiptRoleIntegrationSuite(ReceiptDocumentScopeSuite):
    def reload_actual_qa_resources(self):
        request=urllib.request.Request('http://127.0.0.1:18002/open/resources/cache/reload',method='PUT',headers={'Authorization':'Bearer '+self.token})
        with self.opener.open(request,timeout=20) as response:result=json.load(response)
        assert result.get('code')==10000,'Actual isolated resource cache reload failed'
    def run(self):
        def role_save():
            self.fixture(stock=0);role=self.success('POST','/role/add-role',dict(name='QA Receipt Integration '+uuid.uuid4().hex[:6],data='',root='[]',auth='{}'))
            from purchase_ui_acceptance import PurchaseUiSuite
            _,user,_=self.new_user(role=role);ordinary=PurchaseUiSuite.login(self,user);admin=self.token
            role_name=sql(self.state,'SELECT name FROM role WHERE id='+literal(role)+';')
            assert sql(self.state,"SELECT COUNT(*) FROM menu WHERE id IN ('000','118','121');")=='0','QA catalog fixture IDs already exist; inspect before seeding'
            assert sql(self.state,"SELECT COUNT(*) FROM func_perm WHERE id IN ('213','214','216');")=='0'
            menus=[('000','0','QA Root','qa-root',''),('118','000','QA Funds','qa-funds',''),('121','118','QA Receipts','qa-receipts','/receipt-order')]
            for identifier,parent,name,key,url in menus:
                sql(self.state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(value) for value in [identifier,parent,name,key,0,0,url,0])+');')
            functions=[('213','QA Create Receipt','/fund/receipt'),('214','QA Update Receipt','/fund/receipt/{id}'),('216','QA Remove Receipt','/fund/receipt')]
            for identifier,name,url in functions:
                sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(value) for value in [identifier,'121',name,url,1,'1'])+');')
            payload=dict(id=role,name=role_name,data='',root='[]',auth='{}')
            try:
                migration=(QA.parent/'database/migrations/20261116_receipt_settlement.sql').read_text(encoding='utf-8')
                sql(self.state,migration);sql(self.state,migration)
                assert sql(self.state,"SELECT url FROM func_perm WHERE id='213';")=='/fund/receipt/add'
                assert sql(self.state,"SELECT url FROM func_perm WHERE id='214';")=='/fund/receipt/update'
                assert sql(self.state,"SELECT url FROM func_perm WHERE id='216';")=='/fund/receipt/remove'
                with qa_resource_cache_snapshot(self.state):
                    self.reload_actual_qa_resources()
                    self.token=ordinary
                    assert self.receipt(self.receipt_body()).get('code')==403
                    self.token=admin
                    granted=dict(payload,root=json.dumps([dict(id='118',children=[dict(id='121',fun=[dict(id='213')])])]))
                    assert self.request('PUT','/role/modify-role',granted).get('code')==10000
                    self.token=ordinary;body=self.receipt_body();result=self.receipt(body)
                    if result.get('code')!=10000:
                        denied_code=result.get('code')
                        self.token=admin;self.reload_actual_qa_resources()
                        self.token=ordinary
                        assert self.receipt(body).get('code')==10000,'Receipt remains inaccessible even after real resource reload; inspect catalog mapping rather than assuming cache invalidation'
                        assert self.count_receipt(body['number'])==1
                        self.token=admin;assert self.request('PUT','/role/modify-role',payload).get('code')==10000
                        self.token=ordinary;revoked_body=self.receipt_body();revoked_result=self.receipt(revoked_body)
                        self.token=admin;self.reload_actual_qa_resources()
                        self.token=ordinary
                        assert self.receipt(self.receipt_body()).get('code')==403,'Actual reload failed to remove revoked permission'
                        raise AssertionError('Real role save did not refresh effective resources: grant returned '+str(denied_code)+', actual reload enabled creation; revoke before reload returned '+str(revoked_result.get('code'))+', actual reload denied creation. No Redis grants injected.')
                    assert self.count_receipt(body['number'])==1
                    # Populate a genuine granted cache, then disable the catalog entry.
                    # Neither a cached grant nor the still-selected ID may override it.
                    self.token=admin;self.reload_actual_qa_resources()
                    sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id='213' AND mid='121';")
                    try:
                        self.token=ordinary;assert self.receipt(self.receipt_body()).get('code')==403,'Disabled function remained usable through a stale granted cache'
                    finally:sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id='213' AND mid='121';")
                    self.token=admin;assert self.request('PUT','/role/modify-role',payload).get('code')==10000
                    self.token=ordinary;assert self.receipt(self.receipt_body()).get('code')==403,'Role save did not immediately revoke receipt creation'
            finally:
                self.token=admin;self.request('PUT','/role/modify-role',payload)
                sql(self.state,"DELETE FROM func_perm WHERE id IN ('213','214','216') AND mid='121';DELETE FROM menu WHERE id='121';DELETE FROM menu WHERE id='118';DELETE FROM menu WHERE id='000';")
            self.unchanged_receipt()
            return ['Actual original catalog migration retains function IDs and is idempotent; real C1 role save grants/revokes ordinary receipt creation with the same OAuth token, without injected Redis grants; a genuine stale granted cache cannot override a disabled function or revoked DB selection']
        self.case('receipt.permissions_real_role_save_immediate_effect',role_save)
        self.write_report()

if __name__=='__main__':ReceiptRoleIntegrationSuite(read_state()).run()
