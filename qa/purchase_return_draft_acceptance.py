"""Real source-bound procurement-return drafts; draft saves must not post stock/refunds/payables."""
import argparse
import uuid
import copy
import concurrent.futures
from decimal import Decimal
from purchase_return_preview_acceptance import PurchaseReturnPreviewSuite
from acceptance import read_state,sql,literal
from resource_fixture import qa_resource_grants,authority
from purchase_ui_acceptance import PurchaseUiSuite


class PurchaseReturnDraftSuite(PurchaseReturnPreviewSuite):
    def body_return(self,source,quantity=1):
        result=self.preview(source);assert result.get('code')==10000
        return dict(source=source,sourceVersion=result['data']['sourceVersion'],supplier=self.supplier,
            number='QABRD'+uuid.uuid4().hex[:23],time='2026-11-16 12:00:00',money=0,cost=0,account='',data='QA actual return draft',
            details=[dict(source=result['data']['items'][0]['source'],nums=quantity,serial='[]',goods=self.goods,
                number=sql(self.state,'SELECT number FROM goods WHERE id='+literal(self.goods)+';'),unit='unit',warehouse=self.warehouse,price=999,total=999,tax=99,tat=99,tpt=1098)])
    def add_return(self,body):return self.request('POST','/purchase-return-form/add',body,service='purchase')
    def return_doc(self,identifier):
        result=self.request('GET','/purchase-return-form/document/'+identifier,service='purchase')
        assert result.get('code')==10000,'Actual procurement return detail failed'
        return result['data']
    def created(self,quantity=1):
        source=self.posted();body=self.body_return(source,quantity);result=self.add_return(body)
        assert result.get('code')==10000,'Actual return draft create failed'
        return source,result['data'],body
    def revision_return(self,identifier,quantity=1):
        doc=self.return_doc(identifier);body=dict(doc['header'])
        body.update(version=doc['version'],sourceVersion=doc['sourceVersion'],time=doc['header']['timeText'],details=doc['items'])
        body['details'][0]['nums']=quantity;return body
    def revise_return(self,identifier,body):return self.request('PUT','/purchase-return-form/document/'+identifier,body,service='purchase')
    def remove_return(self,identifier,version):return self.request('DELETE','/purchase-return-form/document/'+identifier,dict(version=version),service='purchase')
    def count_return(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM bre WHERE number='+literal(number)+';'))
    def baseline(self):
        def uuid_source():
            source=self.posted();body=self.body_return(source);result=self.add_return(body)
            assert result.get('code')==10000,'Actual UUID source-bound return draft cannot be saved'
            identifier=result['data'];assert isinstance(identifier,str) and len(identifier)==32
            assert sql(self.state,'SELECT source FROM bre WHERE id='+literal(identifier)+';')==source
            assert sql(self.state,'SELECT frame FROM bre WHERE id='+literal(identifier)+';')==self.state['frame_id']
            assert sql(self.state,'SELECT `user` FROM bre WHERE id='+literal(identifier)+';')==self.actor
            assert Decimal(sql(self.state,'SELECT total FROM bre WHERE id='+literal(identifier)+';'))==100
            assert Decimal(sql(self.state,'SELECT actual FROM bre WHERE id='+literal(identifier)+';'))==113
            self.unchanged();return ['Actual source UUID persists correct main/detail identity, organization/current operator and authoritative net100/gross113 despite forged client prices; no stock/refund/payable changes']
        self.case('purchase.return_draft_actual_source_uuid_persistence',uuid_source)
        def legacy_delete():
            source=self.posted();identifier,_,_=self.linked_fixture(source,1)
            assert self.request('DELETE','/purchase-return-form/delete',[identifier],service='purchase').get('code')!=10000,'Legacy delete removed a return without its displayed version'
            assert sql(self.state,'SELECT COUNT(*) FROM bre WHERE id='+literal(identifier)+';')=='1'
            self.unchanged();return ['Explicit legacy draft fixture cannot be deleted through old array endpoint without a reviewed version']
        self.case('purchase.return_draft_legacy_delete_requires_version',legacy_delete)
        self.write_report()

    def run(self):
        def lifecycle():
            source,identifier,body=self.created();first=self.return_doc(identifier);line=first['items'][0]['id']
            assert first['header']['source']==source and all(type(first['header'][key]) is int for key in ['check','examine','nucleus','cse','invoice'])
            page=self.request('GET','/purchase-return-form/list?number='+body['number'],service='purchase')
            assert page.get('code')==10000 and page['data']['total']==1 and page['data']['rows'][0]['version']==first['version']
            legacy=self.request('GET','/purchase-return-form/detail?id='+identifier,service='purchase');assert legacy.get('code')==10000 and legacy['data']['version']==first['version']
            revision=self.revision_return(identifier,.5);revision['data']='QA real revised return'
            assert self.revise_return(identifier,revision).get('data')==identifier
            current=self.return_doc(identifier);assert current['version']!=first['version'] and current['items'][0]['id']==line and current['header']['actual']==56.5
            assert self.remove_return(identifier,first['version']).get('code')!=10000
            assert self.remove_return(identifier,current['version']).get('data')==identifier
            assert self.count_return(body['number'])==0 and sql(self.state,'SELECT COUNT(*) FROM bre_info WHERE pid='+literal(identifier)+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bre' AND source="+literal(identifier)+';')=='3'
            assert self.preview(source)['data']['items'][0]['available']==2
            self.unchanged();return ['Actual create/list/legacy and full detail/edit/delete lifecycle uses identical visible snapshots, retains line identity and independent history, frees quantity, and never posts stock/refunds/payables']
        self.case('purchase.return_draft_actual_crud_lifecycle',lifecycle)

        def stale_edit():
            _,identifier,_=self.created();frozen=self.revision_return(identifier,1)
            changed=copy.deepcopy(frozen);changed['data']='first editor'
            assert self.revise_return(identifier,changed).get('code')==10000
            frozen['data']='stale editor';assert self.revise_return(identifier,frozen).get('code')!=10000
            assert self.return_doc(identifier)['header']['data']=='first editor'
            self.unchanged();return ['Actual successful first edit invalidates frozen second editor instead of silently overwriting persisted remarks']
        self.case('purchase.return_draft_stale_editor_refused',stale_edit)

        def invalid_inputs():
            source=self.posted()
            for quantity in [0,-1,2.0001,.00001]:
                body=self.body_return(source,quantity);assert self.add_return(body).get('code')!=10000 and self.count_return(body['number'])==0
            for field,value in [('examine',1),('check',1),('nucleus',2),('cse',2),('sourceVersion',None),('supplier',uuid.uuid4().hex)]:
                body=self.body_return(source);body[field]=value;assert self.add_return(body).get('code')!=10000 and self.count_return(body['number'])==0
            body=self.body_return(source,.5);body['details'].append(dict(body['details'][0]));assert self.add_return(body).get('code')!=10000 and self.count_return(body['number'])==0
            self.unchanged();return ['Actual negative/zero/excess/overprecision quantities, duplicate source rows, forged states, missing source version and wrong supplier all reject atomically']
        self.case('purchase.return_draft_invalid_inputs_atomic',invalid_inputs)

        def original_source_version():
            source=self.posted();body=self.body_return(source)
            assert self.post([source],0).get('code')==10000 and self.post([source]).get('code')==10000
            assert self.add_return(body).get('code')!=10000 and self.count_return(body['number'])==0
            body['sourceVersion']=self.preview(source)['data']['sourceVersion']
            assert self.add_return(body).get('code')==10000
            self.unchanged();return ['Actual original purchase reverse/repost changes source history/version; frozen return create refuses and explicitly reread source permits retry']
        self.case('purchase.return_draft_actual_source_version_conflict',original_source_version)

        def refund_metadata():
            source=self.posted();body=self.body_return(source);body.update(money=25,account=self.account,cost=1)
            result=self.add_return(body);assert result.get('code')==10000
            doc=self.return_doc(result['data']);assert doc['header']['money']==25 and doc['header']['cost']==1 and doc['header']['actual']==113
            assert sql(self.state,'SELECT COUNT(*) FROM bre_bill WHERE pid='+literal(result['data'])+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='bre' AND `class`="+literal(result['data'])+';')=='0'
            self.unchanged();return ['Actual planned supplier refund25 and fee1 remain draft metadata; no refund settlement or account/payable/inventory movement is invented']
        self.case('purchase.return_draft_planned_refund_not_posted',refund_metadata)

        def concurrent_allowance():
            source=self.posted();bodies=[self.body_return(source,2) for _ in range(2)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(self.add_return,bodies))
            assert sum(result.get('code')==10000 for result in results)==1 and sum(self.count_return(body['number']) for body in bodies)==1
            identifier=next(result['data'] for result in results if result.get('code')==10000)
            options=self.request('GET','/purchase-return-form/document/'+identifier+'/source-options',service='purchase');assert options.get('code')==10000 and options['data']['items'][0]['available']==2
            account=self.request('GET','/purchase-return-form/accounts?source='+source+'&updating=true&draft='+identifier,service='purchase');assert account.get('code')==10000 and all('balance' not in row for row in account['data'])
            self.unchanged();return ['Actual concurrent full-quota drafts have one winner; full own reservation does not prevent source options or refund account editing; account options disclose no balances']
        self.case('purchase.return_draft_concurrent_source_allowance',concurrent_allowance)

        def second_storage_failure():
            self.fixture();body=self.body();body['purchaseNoteBuyDTO'].update(money=25,account=self.account)
            row=body['purchaseNoteInfoDTOS'][0];row.update(nums=1,discount=0,tax=13,batch='',mfd=None,serial='[]');body['purchaseNoteInfoDTOS'].append(dict(row))
            source=self.create(body);assert self.check([source]).get('code')==10000 and self.post([source]).get('code')==10000
            preview=self.preview(source)['data'];assert len(preview['items'])==2
            payload=self.body_return(source,.5);payload['details']=[dict(source=item['source'],nums=.5,serial='[]') for item in preview['items']]
            trigger='qa_bre_second_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bre_info FOR EACH ROW BEGIN IF NEW.source="+literal(preview['items'][1]['source'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA second return line failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.add_return(payload).get('code')!=10000 and self.count_return(payload['number'])==0
                assert sql(self.state,'SELECT COUNT(*) FROM bre_info WHERE source IN ('+','.join(literal(item['source']) for item in preview['items'])+');')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.add_return(payload).get('code')==10000
            self.unchanged();return ['Actual second-detail MySQL failure rolls back earlier main/first detail/history; identical complete payload retries after owned trigger removal']
        self.case('purchase.return_draft_second_storage_failure_atomic',second_storage_failure)

        def live_role():
            source=self.posted();body=self.body_return(source)
            role=self.success('POST','/role/add-role',dict(name='QA Return CRUD '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,user);admin=self.token
            paths=['/purchase-return-form/add','/purchase-return-form/update','/purchase-return-form/detail','/purchase-return-form/list','/purchase-return-form/delete','/purchase-note/getBuildBre']
            try:
                self.token=token;assert self.add_return(body).get('code')==403
                with qa_resource_grants(self.state,paths,[authority(role,keyword)]):
                    created=self.add_return(body);assert created.get('code')==10000;identifier=created['data']
                    assert self.return_doc(identifier)['header']['user']==actor
                    assert self.revise_return(identifier,self.revision_return(identifier,.5)).get('code')==10000
                    doc=self.return_doc(identifier);assert self.request('DELETE','/purchase-return-form/delete',dict(ids=[identifier],versions={identifier:doc['version']}),service='purchase').get('code')==10000
                body['number']='QABRD'+uuid.uuid4().hex[:23];assert self.add_return(body).get('code')==403
            finally:self.token=admin
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bre' AND source="+literal(identifier)+' AND `user`='+literal(actor)+';')=='3'
            self.unchanged();return ['Actual new OAuth actor requires live CRUD/source grants; create/edit/complete-version legacy-path delete persist current operator history; same token loses access immediately after revoke']
        self.case('purchase.return_draft_live_role_crud_and_revoke',live_role)
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['baseline','run']);action=parser.parse_args().action
    suite=PurchaseReturnDraftSuite(read_state())
    if action=='baseline':suite.baseline()
    else:suite.run()
