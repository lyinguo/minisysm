"""Actual order list metadata, filters, pagination and live scope; dedicated QA fixtures."""
import uuid,urllib.parse
from booking_audit_acceptance import OrderAuditSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal
class OrderListSuite(OrderAuditSuite):
    def list(self,**query):
        args=dict(pageIndex=1,pageSize=10,number=self.prefix);args.update(query)
        return self.request('GET','/purchase-order/list?'+urllib.parse.urlencode(args),service='purchase')
    def setup(self):
        self.fixture();self.prefix='QALIST'+uuid.uuid4().hex[:15];self.ids=[]
        for index in range(3):
            body=self.order_body();body['number']=self.prefix+str(index);body['data']='remark-'+str(index);self.ids.append(self.create_order(body))
        assert self.audit([self.ids[1]]).get('code')==10000
    def run(self,baseline=False):
        def metadata():
            self.setup();rows=self.list()['data']['rows'];row=next(r for r in rows if r['id']==self.ids[0])
            assert row.get('supplierName')=='QA Posting Supplier' and row.get('peopleName')=='QA Booking Person','List lacks actual reference names'
            assert row.get('frameName') and row.get('userName') and row['supplier']==self.supplier and row['people']==self.person
            assert row.get('documentTime')=='2026-11-15 00:00:00' and row.get('arrivalTime')=='2026-11-16'
            assert row.get('examineName')=='未审核' and row.get('stateName')=='未入库';self.unchanged()
            return ['Actual list preserves reference IDs and adds real names, valid dates and human-readable states']
        self.case('booking.list_real_names_dates_and_ids',metadata)
        def status():
            self.setup()
            for value in ['1','已审核']:
                result=self.list(examine=value);assert result.get('code')==10000 and [r['id'] for r in result['data']['rows']]==[self.ids[1]],'Approved filter returned wrong state'
            sql(self.state,'UPDATE bor SET state=3 WHERE id='+literal(self.ids[0])+';')
            for value in ['3','关闭']:
                rows=self.list(state=value)['data']['rows'];assert [r['id'] for r in rows]==[self.ids[0]] and rows[0]['stateName']=='关闭'
            return ['Numeric and legacy Chinese approval/execution filters select actual states including closed3']
        self.case('booking.list_state_filter_not_numeric_coercion',status)
        def filters():
            self.setup();assert self.list(name='absent-'+uuid.uuid4().hex[:12])['data']['total']==0,'Unknown product filter was ignored'
            assert self.list(data='remark-2')['data']['total']==1 and self.list(data='remark-2')['data']['rows'][0]['id']==self.ids[2]
            assert self.list(name='QA Purchase Posting Goods')['data']['total']==3
            return ['Real product-name EXISTS and remark filters apply without duplicating multi-line orders']
        self.case('booking.list_product_and_remark_filters',filters)
        def references():
            self.setup()
            for args in [dict(supplier=self.supplier),dict(supplier='QA Posting Supplier'),dict(people=self.person),dict(people='QA Booking Person'),dict(user=self.actor),dict(user=sql(self.state,'SELECT name FROM `user` WHERE id='+literal(self.actor)+';'))]:
                assert self.list(**args)['data']['total']==3,'Reference name/ID filtering rejected actual fixture'
            return ['Supplier/person/creator filters accept original IDs and human names within document scope']
        self.case('booking.list_reference_name_or_id',references)
        if not baseline:
            def pagination():
                self.setup();pages=[self.list(pageIndex=index,pageSize=1)['data'] for index in [1,2,3,4]]
                assert all(p['total']==3 for p in pages) and [p['rows'][0]['id'] for p in pages[:3]]==sorted(self.ids) and not pages[3]['rows']
                return ['Equal-date records paginate deterministically by ID without duplicates or missing members; empty later page retains total']
            self.case('booking.list_stable_pagination',pagination)
            def invalid():
                self.setup()
                for args in [dict(documentStartTime='2026-02-30'),dict(documentStartTime='2026-11-16',documentEndTime='2026-11-15'),dict(arrivalStartTime='2026-11-17',arrivalEndTime='2026-11-16'),dict(examine='unknown'),dict(state='99'),dict(pageSize=201),dict(pageIndex=0)]:assert self.list(**args).get('code')!=10000
                assert self.list(documentStartTime='2026-11-15',documentEndTime='2026-11-15',arrivalStartTime='2026-11-16',arrivalEndTime='2026-11-16')['data']['total']==3
                return ['Strict valid calendars/ranges/states/pagination; inclusive document and arrival dates match actual persisted dates']
            self.case('booking.list_strict_filters_ranges',invalid)
            def scope():
                self.setup();role=self.success('POST','/role/add-role',dict(name='QA List '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
                try:
                    assert self.list().get('code')==403
                    with qa_resource_grants(self.state,['/purchase-order/list'],[keyword]):
                        assert self.list()['data']['total']==3
                        other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA List Other');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                        assert self.list()['data']['total']==0
                    assert self.list().get('code')==403
                finally:self.token=admin
                self.unchanged();return ['Actual OAuth list grant, current organization move and revoked grant enforce live data scope']
            self.case('booking.list_live_grant_and_frame',scope)
            def damaged():
                self.setup()
                try:sql(self.state,'UPDATE bor SET people='+literal(uuid.uuid4().hex)+' WHERE id='+literal(self.ids[0])+';');raise AssertionError('Missing-person corruption bypassed integrity guard')
                except RuntimeError as error:
                    assert 'PSI_INTEGRITY:missing:people' in str(error),str(error)
                sql(self.state,'UPDATE bor SET examine=2,state=4 WHERE id='+literal(self.ids[0])+';');before=self.records(self.ids[0]);row=next(r for r in self.list()['data']['rows'] if r['id']==self.ids[0])
                assert row['examine']=='2' and row['state']=='4' and '异常' in row['examineName'] and '异常' in row['stateName'] and row['people']==self.person
                assert self.records(self.ids[0])==before;self.unchanged();return ['Actual integrity guard rejects a new missing-person reference without disabling it; malformed enums stay explicit with unchanged original reference/history/balances; legacy orphan display remains unverified']
            self.case('booking.list_corrupt_metadata_not_hidden',damaged)
        self.write_report()
if __name__=='__main__':
    import sys
    OrderListSuite(read_state()).run(len(sys.argv)>1 and sys.argv[1]=='baseline')
