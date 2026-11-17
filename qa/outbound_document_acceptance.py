"""Actual other-outbound entry points; SQL fixture drafts are explicitly marked."""
import argparse,json,re,uuid,copy,concurrent.futures,io,urllib.request,urllib.parse,threading
from openpyxl import load_workbook
from warehouse_cost_flow_acceptance import WarehouseCostFlowSuite
from stock_role_integration_acceptance import StockRoleSuite
from acceptance import QA,read_state,sql,literal

class OutboundDocumentSuite(WarehouseCostFlowSuite):
    through_gateway=False
    def case(self,name,action):return super().case(name+('_through_gateway' if self.through_gateway else ''),action)
    def request(self,method,path,body=None,service='c1'):
        if self.through_gateway and service=='store':path='/j2-store'+path;service='gateway'
        return super().request(method,path,body,service)
    def permissions(self):return StockRoleSuite(self.state,through_gateway=self.through_gateway)
    def download(self,identifier,detail=False):
        service='gateway' if self.through_gateway else 'store';prefix='/j2-store' if self.through_gateway else ''
        path='/otherout/'+('exportDetailExcel' if detail else 'exportEasyExcel')+'?'+urllib.parse.urlencode(dict(ids=identifier))
        request=urllib.request.Request('http://127.0.0.1:'+str(self.state[service+'_port'])+prefix+path,headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=25) as response:raw=response.read();content=response.headers.get('Content-Type','')
        except urllib.error.HTTPError as error:raw=error.read();content=error.headers.get('Content-Type','')
        return json.loads(raw) if raw.startswith(b'{') else raw,content
    def upload_legacy(self):
        boundary='qa-outbound-'+uuid.uuid4().hex
        body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="legacy.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\nlegacy-header-only\r\n--'+boundary+'--\r\n').encode()
        service='gateway' if self.through_gateway else 'store';prefix='/j2-store' if self.through_gateway else ''
        request=urllib.request.Request('http://127.0.0.1:'+str(self.state[service+'_port'])+prefix+'/otherout/import',data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=25) as response:return json.load(response)
        except urllib.error.HTTPError as error:return json.load(error)
    def outbound(self,qty=2):
        return dict(frame=self.state['frame_id'],customer='',time='2026-11-16T09:47:32',number='QAOUT'+uuid.uuid4().hex[:24],type=0,total=qty*2,cost=0,people='',logistics='',file='[]',data='QA actual outbound',more='{}',examine=0,check=0,cse=3,user=self.actor,costDTOList=[],otherOutListInfoDTOList=[dict(goods=self.goods,attr='',unit='unit',warehouse=self.warehouse,price=2,nums=qty,total=qty*2,serial='[]',batch='',mfd=None,data='QA line')])
    def document_count(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM extry WHERE number='+literal(number)+';'))
    def read_out(self,identifier):return self.store('GET','/otherout/getInfo?id='+identifier)
    def create_out(self,body=None):
        body=body or self.outbound();result=self.request('POST','/otherout/add',body,service='store');assert result.get('code')==10000,str(result);return result['data'],body
    def cmd(self,identifier,target=None):
        result=dict(ids=[identifier],versions={identifier:self.read_out(identifier)['version']})
        if target is not None:result['target']=target
        return result
    def mutate_out(self,action,body):return self.request('DELETE' if action=='delete' else 'PUT','/otherout/'+action,body,service='store')
    def baseline(self):
        def empty():
            self.fixture();body=self.outbound();body['otherOutListInfoDTOList']=[]
            result=self.request('POST','/otherout/add',body,service='store')
            assert result.get('code')!=10000,'Empty outbound draft reported success'
            assert self.document_count(body['number'])==0,'Rejected empty detail list left an orphan outbound header'
            return ['Actual empty create refuses without persisting header, stock or funds']
        self.case('outbound.create_empty_no_partial_header',empty)
        def actual_id():
            self.fixture();body=self.outbound();result=self.request('POST','/otherout/add',body,service='store')
            assert result.get('code')==10000,str(result)
            identifier=str(result.get('data',''));assert re.fullmatch('[0-9a-f]{32}',identifier),'Create must return actual persisted UUID for next-step detail/audit, not a success phrase'
            assert sql(self.state,'SELECT id FROM extry WHERE number='+literal(body['number'])+';')==identifier
            assert self.inventory()==10 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            return ['Actual create returns persisted UUID and does not post stock, funds or receivable']
        self.case('outbound.create_uuid_usable_by_next_step',actual_id)
        def detail():
            self.fixture();identifier=self.document('extry',quantity=2,price=2)
            result=self.request('GET','/otherout/getInfo?id='+identifier,service='store')
            assert result.get('code')==10000 and isinstance(result.get('data'),dict),str(result)
            document=result['data'];assert document.get('header',{}).get('id')==identifier and len(document.get('items',[]))==1,'Actual UUID detail must include header, all child lines and edit version'
            assert re.fullmatch('[0-9a-f]{32}',document.get('version',''))
            return ['Explicit SQL-owned fixture actual old detail returns complete document and version']
        self.case('outbound.detail_complete_uuid_document',detail)
        def command():
            self.fixture();identifier=self.document('extry',quantity=2,price=2)
            version=self.store('GET','/transfer/report-documents/extry/'+identifier)['version']
            result=self.request('PUT','/otherout/check',dict(ids=[identifier],versions={identifier:version},target=1),service='store')
            assert result.get('code')==10000,str(result)
            assert sql(self.state,'SELECT CAST(`check` AS SIGNED) FROM extry WHERE id='+literal(identifier)+';')=='1' and self.inventory()==10
            return ['Actual UUID explicit check persists without stock movement']
        self.case('outbound.legacy_uuid_explicit_check',command)
        def unauthorized_list():
            permissions=self.permissions()
            with permissions.catalog():
                permissions.role_fixture();permissions.token=permissions.ordinary
                result=permissions.request('GET','/otherout/list?pageIndex=1&pageSize=1',service='store')
                assert result.get('code')==403,'Ungranting list function does not protect old outbound list'
            return ['Actual signed ordinary account without outbound grant receives403']
        self.case('outbound.list_requires_current_function',unauthorized_list)
        self.write_report()

    def extended(self):
        def lifecycle():
            self.fixture();identifier,body=self.create_out();assert self.inventory()==10
            assert self.mutate_out('check',self.cmd(identifier,1)).get('code')==10000
            document=self.read_out(identifier);body.update(id=identifier,version=document['version']);body['otherOutListInfoDTOList'][0]['nums']=3
            assert self.mutate_out('update',body).get('code')!=10000
            assert self.request('PUT','/transfer/report-documents/extry/'+identifier,document,service='store').get('code')!=10000
            assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')==10000 and self.inventory()==8
            assert self.movement_cost(identifier,'extry')==4 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            assert self.read_out(identifier)['header']['actualCost']==4
            assert self.mutate_out('delete',self.cmd(identifier)).get('code')!=10000
            assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==10000 and self.inventory()==10
            assert self.mutate_out('check',self.cmd(identifier,0)).get('code')==10000
            assert self.mutate_out('delete',self.cmd(identifier)).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM extry WHERE id='+literal(identifier)+';SELECT COUNT(*) FROM extry_info WHERE pid='+literal(identifier)+';')=='0\n0'
            assert sql(self.state,'SELECT COUNT(*) FROM record WHERE type=\'extry\' AND source='+literal(identifier)+';')=='6'
            return ['Actual create -> check -> blocked edits through both URLs -> issue2 at cost4 -> reverse -> uncheck -> physical draft delete; stock10->8->10, cash100/AR0 and six signed history records retained']
        self.case('outbound.actual_create_check_post_reverse_delete',lifecycle)
        def edit():
            self.fixture();identifier,body=self.create_out();document=self.read_out(identifier);original=document['items'][0]['id'];body.update(id=identifier,version=document['version'])
            body['otherOutListInfoDTOList'][0].update(id=original,nums=3,total=999)
            body['otherOutListInfoDTOList'].append(copy.deepcopy(self.outbound(1)['otherOutListInfoDTOList'][0]))
            assert self.mutate_out('update',body).get('code')==10000
            document=self.read_out(identifier);assert document['header']['total']==8 and len(document['items'])==2 and original in [r['id'] for r in document['items']]
            assert self.mutate_out('update',body).get('code')!=10000
            body['version']=document['version'];body['otherOutListInfoDTOList']=document['items'][:1]
            assert self.mutate_out('update',body).get('code')==10000 and len(self.read_out(identifier)['items'])==1
            assert self.inventory()==10 and self.balance('account',self.account)==100
            return ['Actual edit adds/removes real child lines, preserves retained line ID, recomputes estimate rather than trusting supplied total, rejects stale version, does not post stock/funds']
        self.case('outbound.actual_full_edit_and_stale_version',edit)
        def rollback():
            self.fixture();body=self.outbound();body['otherOutListInfoDTOList'].append(copy.deepcopy(body['otherOutListInfoDTOList'][0]));trigger='qa_out_create_'+uuid.uuid4().hex[:12]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON extry_info FOR EACH ROW BEGIN IF NEW.pid IN (SELECT id FROM extry WHERE number='+literal(body['number'])+") AND (SELECT COUNT(*) FROM extry_info WHERE pid=NEW.pid)>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA outbound last line'; END IF; END$$\nDELIMITER ;\n")
            try:assert self.request('POST','/otherout/add',body,service='store').get('code')!=10000
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.document_count(body['number'])==0 and self.inventory()==10
            identifier,_=self.create_out(body);assert len(self.read_out(identifier)['items'])==2
            return ['Real MySQL last detail INSERT failure rolls back header and first detail; removing owned trigger lets same request persist exactly once']
        self.case('outbound.create_last_line_storage_failure_atomic_retry',rollback)
        def concurrent_commands():
            self.fixture();body=self.outbound()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.request('POST','/otherout/add',copy.deepcopy(body),service='store'),range(2)))
            assert sum(r.get('code')==10000 for r in results)==1 and self.document_count(body['number'])==1
            identifier=next(r['data'] for r in results if r.get('code')==10000);command=self.cmd(identifier,1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.mutate_out('examine',copy.deepcopy(command)),range(2)))
            assert sum(r.get('code')==10000 for r in results)>=1 and self.inventory()==8
            assert sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';')=='1'
            return ['Actual concurrent same-number create has one winner; frozen concurrent audit cannot duplicate stock deduction or posting proof']
        self.case('outbound.concurrent_number_and_single_stock_effect',concurrent_commands)
        def protocol():
            self.fixture();identifier,_=self.create_out();valid=self.cmd(identifier,1)
            for body in [dict(ids=[identifier],target=1),dict(valid,target=2),dict(valid,ids=[identifier,identifier]),dict(valid,versions={identifier:'0'*32}),[identifier]]:
                assert self.mutate_out('check',body).get('code')!=10000
            assert self.read_out(identifier)['header']['check']==0 and self.inventory()==10
            second='z'*32;body=dict(ids=[identifier,second],versions={identifier:valid['versions'][identifier],second:'0'*32},target=1)
            assert self.mutate_out('examine',body).get('code')!=10000 and self.inventory()==10
            assert self.read_out(identifier)['header']['examine']==0
            return ['Actual HTTP rejects missing/stale/duplicate version protocol, old toggle arrays and invalid target; missing later batch member cannot partially post first real document']
        self.case('outbound.explicit_protocol_and_batch_no_partial_effect',protocol)
        def stock_and_reference():
            self.fixture();identifier,_=self.create_out(self.outbound(11));before=self.read_out(identifier)
            assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')!=10000 and self.inventory()==10 and self.read_out(identifier)==before
            body=self.outbound();body['otherOutListInfoDTOList'][0]['goods']='missing'
            assert self.request('POST','/otherout/add',body,service='store').get('code')!=10000 and self.document_count(body['number'])==0
            body=self.outbound();body.update(examine=1)
            assert self.request('POST','/otherout/add',body,service='store').get('code')!=10000 and self.document_count(body['number'])==0
            return ['Actual insufficient stock approval rolls all state/journals back; missing product and forged approval state cannot persist new drafts']
        self.case('outbound.actual_stock_and_invalid_draft_atomic',stock_and_reference)
        def metadata():
            self.fixture();body=self.outbound();body.update(file='[{"name":"qa-reference"}]',more='{"qa":true}',logistics='{"qa":"route"}',customer=self.customer)
            identifier,body=self.create_out(body);before=self.read_out(identifier);body.update(id=identifier,version=before['version']);body['otherOutListInfoDTOList']=before['items'];body['otherOutListInfoDTOList'][0]['nums']=3
            for key in ['file','more','logistics','customer']:body.pop(key)
            assert self.mutate_out('update',body).get('code')==10000
            after=self.read_out(identifier);assert all(before['header'][key]==after['header'][key] for key in ['file','more','logistics','customer','user','frame'])
            assert self.inventory()==10 and self.balance('customer',self.customer)==0
            return ['Actual ordinary edit preserves omitted metadata, original customer/creator/organization; associated customer remains trace-only, no receivable or stock changes']
        self.case('outbound.edit_omitted_metadata_and_trace_customer',metadata)
        def deletion_fault():
            self.fixture();identifier,_=self.create_out();command=self.cmd(identifier);before=self.read_out(identifier);trigger='qa_out_delete_'+uuid.uuid4().hex[:12]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source='+literal(identifier)+" AND NEW.type='extry' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA outbound deletion history'; END IF; END$$\nDELIMITER ;\n")
            try:assert self.mutate_out('delete',command).get('code')!=10000
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.read_out(identifier)==before and self.inventory()==10
            assert self.mutate_out('delete',command).get('code')==10000
            return ['Real MySQL final history failure rolls back both header/child deletion; identical original version succeeds after removing owned fault trigger']
        self.case('outbound.delete_late_storage_failure_atomic_retry',deletion_fault)
        def file_export():
            self.fixture();body=self.outbound();body['otherOutListInfoDTOList'][0]['price']=100;identifier,_=self.create_out(body)
            assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')==10000 and self.inventory()==8
            for detail in [False,True]:
                raw,content=self.download(identifier,detail);assert isinstance(raw,bytes) and raw.startswith(b'PK') and 'spreadsheetml' in content
                book=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
                try:
                    rows=list(book.active.values);record=dict(zip(rows[0],rows[1]));assert len(rows)==2 and record['单据编号']==body['number'] and record['成本合计']==4 and record['成本类型']=='实际成本'
                    if detail:assert record['单位成本']==2 and record['成本金额']==4 and record['数量']==2
                finally:book.close()
            assert self.inventory()==8 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            return ['Both actual legacy export URLs return binary XLSX, independently parsed cost4/unit2/quantity2 rather than original estimated200; read-only export preserves stock8/cash100/AR0']
        self.case('outbound.actual_binary_exports_use_posted_cost',file_export)
        def old_import():
            before=sql(self.state,'SELECT COUNT(*) FROM extry;SELECT COUNT(*) FROM extry_info;')
            result=self.upload_legacy();assert result.get('code')!=10000
            assert sql(self.state,'SELECT COUNT(*) FROM extry;SELECT COUNT(*) FROM extry_info;')==before
            return ['Actual old multipart import is explicitly refused without writing orphan headers; complete reviewed import remains pending, not accepted as implemented']
        self.case('outbound.legacy_header_only_import_cannot_bypass_drafts',old_import)
        def actual_role():
            self.fixture();permissions=self.permissions();identifiers=[str(x) for x in range(192,202)]
            paths=['/list','/getInfo','/add','/delete','/update','/check','/examine','/import','/exportEasyExcel','/exportDetailExcel']
            with permissions.catalog():
                assert sql(self.state,"SELECT COUNT(*) FROM menu WHERE id='105';")=='0'
                assert sql(self.state,'SELECT COUNT(*) FROM func_perm WHERE id IN ('+','.join(literal(x) for x in identifiers)+');')=='0'
                try:
                    sql(self.state,"INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('105','102','QA Outbound Catalog','qa-outbound',0,0,'',0);")
                    for identifier,path in zip(identifiers,paths):sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(v) for v in [identifier,'105','QA Outbound '+identifier,'/j2-store/otherout'+path,0,'1'])+');')
                    permissions.role_fixture()
                    def grant(ids):
                        root=[dict(id='102',children=[dict(id='105',fun=[dict(id=x) for x in ids])])] if ids else []
                        assert permissions.request('PUT','/role/modify-role',dict(id=permissions.role,name=permissions.role_name,data='',root=json.dumps(root),auth='{}')).get('code')==10000
                    token=self.token;self.token=permissions.ordinary
                    try:
                        denied=self.request('POST','/otherout/add',self.outbound(),service='store');assert denied.get('code')==403,str(denied)
                        assert self.upload_legacy().get('code')==403
                        grant(['194']);identifier,body=self.create_out()
                        assert sql(self.state,'SELECT `user` FROM extry WHERE id='+literal(identifier)+';')==permissions.user_id
                        assert self.request('GET','/otherout/getInfo?id='+identifier,service='store').get('code')==403
                        grant(['192','193','194','195','196','197','198','200','201'])
                        assert self.mutate_out('check',self.cmd(identifier,1)).get('code')==10000
                        assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')==10000 and self.inventory()==8
                        assert isinstance(self.download(identifier)[0],bytes)
                        grant(['193','197']);assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==403
                        assert self.download(identifier)[0].get('code')==403
                        grant(['193','197','198']);sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id='198';")
                        assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==403
                        sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id='198';")
                        assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==10000 and self.inventory()==10
                        sql(self.state,"UPDATE `user` SET frame='0' WHERE id="+literal(permissions.user_id)+';')
                        assert self.request('GET','/otherout/list',service='store').get('code')==403
                        assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='extry' AND source="+literal(identifier)+' AND `user`<>'+literal(permissions.user_id)+';')=='0'
                    finally:self.token=token
                finally:sql(self.state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(x) for x in identifiers)+");DELETE FROM menu WHERE id='105';")
            return ['Actual new role/user OAuth and C1 role saving grant independent create/read/check/audit/export; creator/history use signed ID; revocation/disabled function and live account organization invalidate old token immediately without cache reload']
        self.case('outbound.actual_role_grant_revoke_disabled_live_scope',actual_role)
        self.write_report()

    def variants(self):
        def batch_serial():
            self.fixture(stock=0);sql(self.state,'UPDATE goods SET batch=1,serial=1 WHERE id='+literal(self.goods)+';')
            serials=['QA-OUT-SN-'+uuid.uuid4().hex for _ in range(2)]
            incoming=self.inbound(2);incoming['otherInListDetailInfoDTOList'][0].update(batch='QA-OUT-BATCH',mfd='2026-11-01',serial=json.dumps(serials))
            receipt=self.store('POST','/otherin/add',incoming);self.audit(receipt,1)
            body=self.outbound(1);body['otherOutListInfoDTOList'][0].update(batch='QA-OUT-BATCH',mfd='2026-11-01T00:00:00',serial=json.dumps([serials[1]]),price=100)
            identifier,_=self.create_out(body);assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')==10000
            assert self.inventory()==1 and self.movement_cost(identifier,'extry')==2
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM serial WHERE goods='+literal(self.goods)+' AND number='+literal(serials[1])+';')=='1'
            assert sql(self.state,'SELECT SUM(nums) FROM batch WHERE goods='+literal(self.goods)+';')=='1.0000'
            assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==10000 and self.inventory()==2
            assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM serial WHERE goods='+literal(self.goods)+' AND number='+literal(serials[1])+';')=='0'
            assert self.mutate_out('delete',self.cmd(identifier)).get('code')==10000
            self.audit(receipt,0);assert self.inventory()==0 and self.balance('account',self.account)==100
            return ['Actual batch/serial inbound2 -> real outbound creation selecting one serial -> audit physical/batch2->1 and selected serial sold at original cost2 rather than estimate100 -> reverse/delete -> reverse receipt restores0/cash100']
        self.case('outbound.actual_batch_serial_create_post_reverse',batch_serial);self.write_report()

    def interoperability(self):
        def report_number_race():
            self.fixture(stock=0);ids=[self.create_out()[0] for _ in range(2)];docs=[self.read_out(identifier) for identifier in ids];number='QARN'+uuid.uuid4().hex[:24]
            for doc in docs:doc['header']['number']=number;doc['items'][0]['nums']=3
            trigger='qa_out_number_'+uuid.uuid4().hex[:12]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE UPDATE ON extry FOR EACH ROW BEGIN IF NEW.id IN ('+','.join(literal(x) for x in ids)+') AND NEW.number='+literal(number)+' THEN DO SLEEP(1); END IF; END$$\nDELIMITER ;\n')
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda pair:self.request('PUT','/transfer/report-documents/extry/'+pair[0],pair[1],service='store'),zip(ids,docs)))
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert sum(result.get('code')==10000 for result in results)==1 and self.document_count(number)==1,'Concurrent report edits allowed duplicate document numbers'
            documents=[self.read_out(identifier) for identifier in ids];assert sorted(float(doc['items'][0]['nums']) for doc in documents)==[2,3]
            assert sorted(float(doc['header']['total']) for doc in documents)==[4,6] and self.inventory()==0
            return ['Real MySQL delayed concurrent report edits compete for one number: one succeeds, loser rolls prior line update back; same locking path as workbench writes, quantities2/3 and totals4/6, no stock change']
        self.case('outbound.report_concurrent_number_and_late_line_rollback',report_number_race)
        def different_numbers():
            self.fixture(stock=0)
            for _ in range(3):
                bodies=[self.outbound() for _ in range(4)];barrier=threading.Barrier(4)
                def create(body):barrier.wait();return self.request('POST','/otherout/add',body,service='store')
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(create,bodies))
                assert all(result.get('code')==10000 for result in results),[result.get('code') for result in results]
                assert all(self.document_count(body['number'])==1 for body in bodies)
            assert self.inventory()==0 and self.balance('account',self.account)==100
            return ['Three rounds of four actual simultaneous distinct-number creates all persist once; exclusive UPSERT document lock avoids shared-to-exclusive upgrade deadlocks, stock/funds untouched']
        self.case('outbound.concurrent_distinct_numbers_all_succeed',different_numbers)
        def report_guards():
            self.fixture();identifier,_=self.create_out();sql(self.state,'UPDATE extry SET cse=2 WHERE id='+literal(identifier)+';');doc=self.read_out(identifier);doc['items'][0]['nums']=3
            assert self.request('PUT','/transfer/report-documents/extry/'+identifier,doc,service='store').get('code')!=10000
            sql(self.state,'UPDATE extry SET cse=3 WHERE id='+literal(identifier)+';');assert self.mutate_out('examine',self.cmd(identifier,1)).get('code')==10000 and self.inventory()==8
            sql(self.state,'UPDATE extry SET examine=0 WHERE id='+literal(identifier)+';');doc=self.read_out(identifier);doc['items'][0]['nums']=3
            assert self.request('PUT','/transfer/report-documents/extry/'+identifier,doc,service='store').get('code')!=10000 and self.inventory()==8
            assert self.read_out(identifier)['items'][0]['nums']==2
            sql(self.state,'UPDATE extry SET examine=1 WHERE id='+literal(identifier)+';');assert self.mutate_out('examine',self.cmd(identifier,0)).get('code')==10000 and self.inventory()==10
            return ['Explicit owned settled-state fixture cannot bypass workbench edit guard through report; actual posted document with simulated wrong audit flag0 still protected by original journals/proof; restore flag then actual reverse restores10']
        self.case('outbound.report_settlement_and_legacy_posting_edit_guards',report_guards);self.write_report()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['baseline','extended','variants','interoperability'],default='baseline',nargs='?');p.add_argument('--gateway',action='store_true');a=p.parse_args();OutboundDocumentSuite.through_gateway=a.gateway;s=OutboundDocumentSuite(read_state());getattr(s,a.action)()
