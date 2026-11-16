"""Actual signed C1 role writes: ordinary users cannot grant themselves authority."""
import uuid
from sale_posting_acceptance import SalePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import read_state,sql,literal

class RoleWriteAccessSuite(SalePostingSuite):
    def assert_business_unchanged(self):
        assert self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0 and self.inventory()==0
        assert sql(self.state,'SELECT COUNT(*) FROM account_info WHERE pid='+literal(self.account)+';')=='0'
    def run(self):
        def ordinary_writes():
            self.fixture(stock=0);admin=self.token
            role=self.success('POST','/role/add-role',dict(name='QA Role Security '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            victim=self.success('POST','/role/add-role',dict(name='QA Unused Role '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            _,user,_=self.new_user(role=role);ordinary=PurchaseUiSuite.login(self,user)
            original=sql(self.state,'SELECT name FROM role WHERE id='+literal(role)+';');extra='QA Denied Role '+uuid.uuid4().hex[:8]
            try:
                self.token=ordinary
                added=self.request('POST','/role/add-role',dict(name=extra,data='',root='[]',auth='{}'))
                changed=self.request('PUT','/role/modify-role',dict(id=role,name=original,data='QA unauthorized change',root='[]',auth='{}'))
                removed=self.request('DELETE','/role/delete-role',[victim])
            finally:self.token=admin
            assert [added.get('code'),changed.get('code'),removed.get('code')]==[403,403,403],str(dict(add=added.get('code'),update=changed.get('code'),remove=removed.get('code')))
            assert sql(self.state,'SELECT COUNT(*) FROM role WHERE name='+literal(extra)+';')=='0'
            assert sql(self.state,'SELECT data FROM role WHERE id='+literal(role)+';')==''
            assert sql(self.state,'SELECT COUNT(*) FROM role WHERE id='+literal(victim)+';')=='1'
            self.assert_business_unchanged()
            return ['Real ordinary OAuth account cannot create, change its own permissions, or delete another unused role; no role mutation or money effect']
        self.case('roles.ordinary_cannot_create_modify_or_delete',ordinary_writes)
        def identity_escalation():
            self.fixture(stock=0);admin=self.token
            user_id,user,_=self.new_user();ordinary=PurchaseUiSuite.login(self,user);before=self.user_row(user_id)
            victim,_,_=self.new_user();new_admin=self.user_payload()
            target_role=self.success('POST','/role/add-role',dict(name='QA Protected Assignment '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            update={key:value for key,value in user.items() if key!='pwd'};update.update(id=user_id,role=target_role)
            try:
                self.token=ordinary
                added=self.request('POST','/user/add-user',new_admin)
                removed=self.request('DELETE','/user/del-user?id='+victim)
                promoted=self.request('PUT','/user/mod-user',update)
            finally:self.token=admin
            assert [added.get('code'),removed.get('code'),promoted.get('code')]==[403,403,403],str(dict(create_user=added.get('code'),delete_user=removed.get('code'),change_own_role=promoted.get('code')))
            assert self.user_row(user_id)==before and self.user_row(victim) is not None
            assert sql(self.state,'SELECT COUNT(*) FROM `user` WHERE `user`='+literal(new_admin['user'])+';')=='0'
            self.assert_business_unchanged()
            return ['Real ordinary signed account cannot bypass role maintenance through user APIs: valid account creation, another user deletion and own role reassignment all refuse without persisted identity/funds changes']
        self.case('users.ordinary_cannot_bypass_roles_via_identity_writes',identity_escalation)
        def administrator_writes():
            self.fixture(stock=0);name='QA Admin Lifecycle '+uuid.uuid4().hex[:8]
            role=self.success('POST','/role/add-role',dict(name=name,data='',root='[]',auth='{}'))
            body=dict(id=role,name=name,data='QA administrator correction',root='[]',auth='{}')
            assert self.request('PUT','/role/modify-role',body).get('code')==10000
            assert self.request('PUT','/role/modify-role',body).get('code')==10000
            assert sql(self.state,'SELECT data FROM role WHERE id='+literal(role)+';')==body['data']
            assert self.request('DELETE','/role/delete-role',[role]).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM role WHERE id='+literal(role)+';')=='0'
            self.assert_business_unchanged()
            return ['Current actual system administrator can create, correct, repeat an unchanged save and physically remove an unused role; verified persistence and no inventory/funds changes']
        self.case('roles.current_administrator_actual_lifecycle',administrator_writes)
        def demotion():
            self.fixture(stock=0);admin=self.token
            role=self.success('POST','/role/add-role',dict(name='QA Demotion Target '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            user_id,user,_=self.new_user()
            # Reserved administrator role0 is not an assignable role in C1.
            # Explicitly prepare only this fresh QA identity, then use real OAuth
            # and real maintenance APIs for the privilege change under test.
            sql(self.state,"UPDATE `user` SET role='0' WHERE id="+literal(user_id)+';')
            former_admin=PurchaseUiSuite.login(self,user)
            self.token=former_admin
            victim=self.success('POST','/role/add-role',dict(name='QA Before Demotion '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            self.token=admin;update={key:value for key,value in user.items() if key!='pwd'};update.update(id=user_id,role=role)
            self.success('PUT','/user/mod-user',update)
            extra='QA After Demotion '+uuid.uuid4().hex[:8]
            try:
                self.token=former_admin
                assert self.request('POST','/role/add-role',dict(name=extra,data='',root='[]',auth='{}')).get('code')==403
                assert self.request('PUT','/role/modify-role',dict(id=role,name='QA Unauthorized Rename',data='',root='[]',auth='{}')).get('code')==403
                assert self.request('DELETE','/role/delete-role',[victim]).get('code')==403
            finally:self.token=admin
            assert sql(self.state,'SELECT COUNT(*) FROM role WHERE name='+literal(extra)+';')=='0'
            assert sql(self.state,'SELECT COUNT(*) FROM role WHERE id='+literal(victim)+';')=='1'
            self.assert_business_unchanged()
            return ['Explicit fresh QA administrator identity fixture obtains a real OAuth token and creates a role; actual user maintenance demotes it and the same previously privileged token immediately loses all three role writes']
        self.case('roles.demoted_administrator_old_token_denied',demotion)
        self.write_report()

if __name__=='__main__':RoleWriteAccessSuite(read_state()).run()
