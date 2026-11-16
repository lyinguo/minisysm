"""Real multipart inbound files and downloaded workbooks against isolated MySQL."""
import argparse,io,json,uuid,urllib.request,urllib.parse,datetime,concurrent.futures
from openpyxl import load_workbook
from stock_role_integration_acceptance import StockRoleSuite,ENTRY
from acceptance import QA,read_state,sql,literal
from contextlib import contextmanager

class InboundFileSuite(StockRoleSuite):
    @contextmanager
    def file_catalog(self):
        with self.catalog():
            try:
                for identifier,path in [('190','exportEasyExcel'),('191','exportDetailExcel')]:
                    sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(v) for v in [identifier,'103','QA Inbound File '+identifier,'/j2-store/otherin/'+path,0,'1'])+');')
                yield
            finally:sql(self.state,"DELETE FROM func_perm WHERE id IN ('190','191');")
    def select_file(self,ids):
        previous=self.token;self.token=self.admin
        root=[dict(id='102',children=[dict(id='103',fun=[dict(id=x) for x in ids])])] if ids else []
        try:assert self.request('PUT','/role/modify-role',dict(id=self.role,name=self.role_name,data='',root=json.dumps(root),auth='{}')).get('code')==10000
        finally:self.token=previous
    def download(self,path,query=None):
        service='gateway' if self.through_gateway else 'store';prefix='/j2-store' if self.through_gateway else ''
        url='http://127.0.0.1:'+str(self.state[service+'_port'])+prefix+'/otherin/'+path
        if query:url+='?'+urllib.parse.urlencode(query)
        request=urllib.request.Request(url,headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=30) as response:raw=response.read();content=response.headers.get('Content-Type','')
        except urllib.error.HTTPError as error:
            raw=error.read();content=error.headers.get('Content-Type','')
        return json.loads(raw) if raw.startswith(b'{') else raw
    def upload(self,raw,version=None):
        boundary='qa-inbound-'+uuid.uuid4().hex
        body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="inbound.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()+raw+b'\r\n'
        if version is not None:body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="version"\r\n\r\n'+version+'\r\n').encode()
        body+=('--'+boundary+'--\r\n').encode();service='gateway' if self.through_gateway else 'store';prefix='/j2-store' if self.through_gateway else ''
        request=urllib.request.Request('http://127.0.0.1:'+str(self.state[service+'_port'])+prefix+'/otherin/import',data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=35) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return dict(code=error.code)
    def numbers(self):return ['QAFILE'+uuid.uuid4().hex[:24] for _ in range(2)]
    def rows(self,numbers):
        g=sql(self.state,'SELECT number FROM goods WHERE id='+literal(self.goods)+';');w=sql(self.state,'SELECT number FROM warehouse WHERE id='+literal(self.warehouse)+';')
        return [[n,'2026-11-14 10:30:45','其他入库',g,w,'unit',qty,2,'','','','','QA file draft','QA file line'] for n,qty in [(numbers[0],1),(numbers[0],2),(numbers[1],4)]]
    def filled(self,rows):
        raw=self.download('import/template');assert isinstance(raw,bytes),'Template did not download: '+str(raw)
        book=load_workbook(io.BytesIO(raw));assert book.sheetnames==['入库模板','填写说明'] and book.active.max_row==1
        assert '不会自动' in str(list(book['填写说明'].values))
        for row in rows:book.active.append(row)
        for row in book.active.iter_rows(min_row=2):
            if isinstance(row[1].value,datetime.datetime):row[1].number_format='yyyy-mm-dd hh:mm:ss'
            if isinstance(row[10].value,datetime.datetime):row[10].number_format='yyyy-mm-dd'
        out=io.BytesIO();book.save(out);book.close();return out.getvalue()
    def counts(self,numbers):return sql(self.state,'SELECT COUNT(*) FROM entry WHERE number IN ('+','.join(literal(n) for n in numbers)+');')
    def plan(self,raw):
        result=self.upload(raw);assert result.get('code')==10000,str(result);return result['data']
    def run(self,baseline=False):
        with self.file_catalog():
            for endpoint in ['exportEasyExcel','exportDetailExcel']:
                def denied(endpoint=endpoint):
                    self.fixture(stock=0);identifier,_=self.create_inbound();self.role_fixture();self.token=self.ordinary
                    try:
                        result=self.download(endpoint,dict(ids=identifier));assert isinstance(result,dict) and result.get('code')==403,'File endpoint bypassed export grant: '+str(type(result))
                        return ['Actual ungranted ordinary token refused download before any business data is serialized']
                    finally:self.token=self.admin;self.select_file([])
                self.case('inbound.files.'+endpoint+'_requires_permission',denied)
            def binary():
                self.fixture(stock=0);identifier,payload=self.create_inbound();raw=self.download('exportEasyExcel',dict(ids=identifier))
                assert isinstance(raw,bytes) and raw[:2]==b'PK','Export returned nested JSON instead of an actual downloadable XLSX'
                book=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
                try:rows=list(book.active.values)
                finally:book.close()
                assert rows[1][1]==payload['number'] and len(rows)==2
                return ['Actual selected export is a readable binary XLSX containing the chosen document']
            self.case('inbound.files.actual_binary_workbook',binary)
            if not baseline:
                def roundtrip():
                    self.fixture(stock=0);numbers=self.numbers();rows=self.rows(numbers);raw=self.filled(rows);plan=self.plan(raw)
                    assert plan['documentCount']==2 and plan['lineCount']==3 and plan['total']==14 and self.counts(numbers)=='0' and self.inventory()==0
                    assert self.plan(raw)['version']==plan['version'];result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
                    ids=result['data']['ids'];assert len(ids)==2 and self.counts(numbers)=='2'
                    for identifier,qty in zip(ids,[3,4]):
                        detail=self.detail(identifier);assert detail['header']['user']==self.actor and detail['header']['frame']==self.state['frame_id']
                        assert sum(line['nums'] for line in detail['items'])==qty
                        assert sql(self.state,'SELECT DATE_FORMAT(time,\'%Y-%m-%d %H:%i:%s\') FROM entry WHERE id='+literal(identifier)+';')=='2026-11-14 10:30:45'
                    assert self.upload(raw,plan['version']).get('code')!=10000 and self.counts(numbers)=='2' and self.inventory()==0
                    self.audit(ids[0],1);assert self.inventory()==3;self.audit(ids[0],0);assert self.inventory()==0
                    assert self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
                    return ['Actual downloaded template with instructions -> multipart preview0 writes -> explicit version commits two complete drafts/three rows/14; signed actor/org/full timestamp; duplicate refused; imported draft really posts3 and reverses0']
                self.case('inbound.files.template_preview_commit_stock_roundtrip',roundtrip)
                def reviewed():
                    self.fixture(stock=0);numbers=self.numbers();rows=self.rows(numbers);raw=self.filled(rows);plan=self.plan(raw)
                    rows[0][6]=2;changed=self.filled(rows);assert self.upload(changed,plan['version']).get('code')!=10000
                    sql(self.state,"UPDATE goods SET name='QA Changed After Preview' WHERE id="+literal(self.goods)+';')
                    assert self.upload(raw,plan['version']).get('code')!=10000 and self.counts(numbers)=='0' and self.inventory()==0
                    fresh=self.plan(raw);assert fresh['version']!=plan['version'];assert self.upload(raw,fresh['version']).get('code')==10000
                    return ['Changed workbook and actual changed product name both invalidate reviewed version without writes; fresh actual preview then commits successfully']
                self.case('inbound.files.file_and_reference_review_version',reviewed)
                def bad_second():
                    self.fixture(stock=0);numbers=self.numbers();rows=self.rows(numbers);rows[2][3]='missing-product'
                    result=self.upload(self.filled(rows));assert result.get('code')!=10000 and self.counts(numbers)=='0' and self.inventory()==0
                    return ['Invalid actual second-document reference rejects entire multipart batch with no earlier header/detail or inventory']
                self.case('inbound.files.invalid_last_reference_no_partial_draft',bad_second)
                def foreign():
                    self.fixture(stock=0);numbers=self.numbers();frame=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA File Foreign');UPDATE warehouse SET frame="+literal(frame)+' WHERE id='+literal(self.warehouse)+';')
                    result=self.upload(self.filled(self.rows(numbers)));assert result.get('code')!=10000 and self.counts(numbers)=='0'
                    return ['Actual foreign warehouse business code refused even for admin import into the signed current organization']
                self.case('inbound.files.foreign_warehouse_rejected',foreign)
                def permissions():
                    self.fixture(stock=0);numbers=self.numbers();raw=self.filled(self.rows(numbers));self.role_fixture();self.token=self.ordinary
                    try:
                        assert self.upload(raw).get('code')==403 and self.download('import/template').get('code')==403
                        self.select_file(['184']);plan=self.plan(raw);result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
                        for identifier in result['data']['ids']:assert sql(self.state,'SELECT `user` FROM entry WHERE id='+literal(identifier)+';')==self.user_id
                        self.select_file([]);assert self.upload(raw).get('code')==403 and self.inventory()==0
                        return ['Actual C1 create184 alone grants template/preview/commit consistently without invented import189 or extra basic read grants; signed ordinary actor used; live revocation403']
                    finally:self.token=self.admin;self.select_file([])
                self.case('inbound.files.actual_create_grant_and_revocation',permissions)
                def exports_scope():
                    self.fixture(stock=0);first,_=self.create_inbound();second,_=self.create_inbound();frame=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA File Scope');UPDATE entry SET frame="+literal(frame)+' WHERE id='+literal(second)+';');self.role_fixture();self.token=self.ordinary
                    try:
                        for grant,path in [('190','exportEasyExcel'),('191','exportDetailExcel')]:
                            self.select_file([grant]);raw=self.download(path,dict(ids=first));assert isinstance(raw,bytes),str(raw)
                            mixed=self.download(path,dict(ids=first+'+'+second));assert isinstance(mixed,dict) and mixed.get('code')==403,str(mixed)
                            self.select_file([]);assert self.download(path,dict(ids=first)).get('code')==403
                        return ['Actual190/191 separately grant binary downloads; mixed own/foreign selection fails before response bytes; revoked live grant403']
                    finally:self.token=self.admin;self.select_file([])
                self.case('inbound.files.actual_export_grants_and_org_scope',exports_scope)
                def download_detail():
                    self.fixture(stock=0);identifier,payload=self.create_inbound();sql(self.state,"UPDATE entry SET data='=2+3' WHERE id="+literal(identifier)+';')
                    raw=self.download('exportDetailExcel',dict(ids=identifier));assert isinstance(raw,bytes),str(raw)
                    book=load_workbook(io.BytesIO(raw),read_only=True,data_only=False)
                    try:
                        lines=list(book.active.iter_rows());headers=[c.value for c in lines[0]];record={key:cell for key,cell in zip(headers,lines[1])}
                        assert len(lines)==2 and record['数量'].value==4 and record['单位成本'].value==2 and record['成本金额'].value==8
                        assert record['商品名称'].value=='QA Posting Goods' and record['入库仓库'].value=='QA Posting Warehouse'
                        assert record['费用状态'].value=='无需结算' and record['单据备注'].value=='=2+3' and record['单据备注'].data_type=='s'
                    finally:book.close()
                    assert self.inventory()==0
                    for ids in ['',identifier+'+'+identifier,identifier+'+missing']:
                        rejected=self.download('exportDetailExcel',dict(ids=ids));assert isinstance(rejected,dict) and rejected.get('code')!=10000
                    return ['Actual detail XLSX has full selected quantities/costs/business references/numeric-derived fee state; formula-looking note remains literal string; invalid/duplicate/missing selections refused and stock0']
                self.case('inbound.files.complete_detail_xlsx_and_literal_cells',download_detail)
                def late_failure():
                    self.fixture(stock=0);numbers=self.numbers();rows=self.rows(numbers);marker='qa-file-'+uuid.uuid4().hex;rows[2][13]=marker;raw=self.filled(rows);plan=self.plan(raw);trigger='qa_file_'+uuid.uuid4().hex[:12]
                    history=sql(self.state,'SELECT COUNT(*) FROM record;SELECT COUNT(*) FROM `log`;')
                    sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON entry_info FOR EACH ROW BEGIN IF NEW.data='+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA inbound file late failure'; END IF; END$$\nDELIMITER ;\n")
                    try:assert self.upload(raw,plan['version']).get('code')!=10000
                    finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
                    assert self.counts(numbers)=='0' and self.inventory()==0
                    assert sql(self.state,'SELECT COUNT(*) FROM record;SELECT COUNT(*) FROM `log`;')==history
                    assert self.upload(raw,plan['version']).get('code')==10000
                    return ['Real MySQL second-document line failure rolls back earlier complete draft/details/history; identical reviewed multipart version succeeds after removing owned trigger']
                self.case('inbound.files.last_document_storage_failure_whole_batch_rollback',late_failure)
                def concurrent_confirm():
                    self.fixture(stock=0);numbers=self.numbers();raw=self.filled(self.rows(numbers));plan=self.plan(raw)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.upload(raw,plan['version']),range(2)))
                    assert sum(r.get('code')==10000 for r in results)==1,str(results);assert self.counts(numbers)=='2' and self.inventory()==0
                    return ['Two actual concurrent confirmations of same reviewed file commit exactly one complete two-document batch, stock0']
                self.case('inbound.files.concurrent_confirm_exactly_one_batch',concurrent_confirm)
                def batch_serial():
                    self.fixture(stock=0);numbers=self.numbers();row=self.rows(numbers)[0];row[1]=datetime.datetime(2026,11,14,10,30,45);row[6]=2;row[9]='QA-BATCH';row[10]=datetime.datetime(2026,11,13);row[11]=json.dumps(['QA-'+uuid.uuid4().hex,'QA-'+uuid.uuid4().hex])
                    sql(self.state,'UPDATE goods SET batch=1,serial=1 WHERE id='+literal(self.goods)+';');raw=self.filled([row]);plan=self.plan(raw);result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
                    identifier=result['data']['ids'][0];self.audit(identifier,1);assert self.inventory()==2
                    assert sql(self.state,'SELECT COUNT(*) FROM serial WHERE goods='+literal(self.goods)+';')=='2';self.audit(identifier,0);assert self.inventory()==0
                    assert sql(self.state,'SELECT COUNT(*) FROM serial WHERE goods='+literal(self.goods)+';')=='0'
                    return ['Actual native Excel date/time, batch and two JSON serials import complete draft; real audit creates stock2/batch/serials2, reversal removes original serials and restores0']
                self.case('inbound.files.native_dates_batch_serial_actual_post_reverse',batch_serial)
                def invalid_files():
                    self.fixture(stock=0);numbers=self.numbers();rows=self.rows(numbers)
                    for column,value in [(3,'=2+3'),(6,0),(7,-1),(5,'wrong-unit'),(1,'2026-99-99'),(2,'unknown')]:
                        changed=[list(r) for r in rows];changed[0][column]=value;assert self.upload(self.filled(changed)).get('code')!=10000
                    assert self.upload(b'not-an-excel').get('code')!=10000 and self.counts(numbers)=='0' and self.inventory()==0
                    return ['Actual multipart formula, zero quantity, negative cost, wrong base unit, invalid date/type and corrupt workbook all refuse without draft or stock writes']
                self.case('inbound.files.invalid_cells_and_corrupt_workbook_no_writes',invalid_files)
                def closed():
                    self.fixture(stock=0);numbers=self.numbers();raw=self.filled(self.rows(numbers));plan=self.plan(raw);period=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+literal(period)+",'2026-11-14',NOW(),"+literal(self.actor)+');')
                    try:assert self.upload(raw).get('code')!=10000 and self.upload(raw,plan['version']).get('code')!=10000 and self.counts(numbers)=='0' and self.inventory()==0
                    finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
                    return ['Actual closed business period prevents import preview/commit without temporarily disabling period rules']
                self.case('inbound.files.closed_period_refused',closed)
                def zero_cost():
                    self.fixture(stock=0);numbers=self.numbers();row=self.rows(numbers)[0];row[2]='盘盈';row[7]=0;raw=self.filled([row]);plan=self.plan(raw)
                    assert plan['total']==0;result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
                    identifier=result['data']['ids'][0];assert sql(self.state,'SELECT CAST(type AS SIGNED),total FROM entry WHERE id='+literal(identifier)+';')=='1\t0.0000'
                    self.audit(identifier,1);assert self.inventory()==1;self.audit(identifier,0);assert self.inventory()==0
                    return ['Actual zero-cost stock-surplus draft imports, posts stock1 with cost0 and reverses0; a legitimate nonpurchase intake is not blocked by price>0 rules']
                self.case('inbound.files.zero_cost_surplus_actual_post_reverse',zero_cost)
                def actor_review():
                    self.fixture(stock=0);numbers=self.numbers();raw=self.filled(self.rows(numbers));admin_plan=self.plan(raw);self.role_fixture();self.select_file(['184']);self.token=self.ordinary
                    try:
                        assert self.upload(raw,admin_plan['version']).get('code')!=10000 and self.counts(numbers)=='0'
                        own=self.plan(raw);assert own['version']!=admin_plan['version'];assert self.upload(raw,own['version']).get('code')==10000
                        return ['Actual preview is bound to signed actor and organization: another granted operator must review independently before committing']
                    finally:self.token=self.admin;self.select_file([])
                self.case('inbound.files.review_bound_to_actual_operator',actor_review)
                def imported_business_flow():
                    original=self.create_inbound
                    def imported(quantity=4):
                        numbers=self.numbers();row=self.rows(numbers)[0];row[6]=quantity;raw=self.filled([row]);plan=self.plan(raw);result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
                        body=self.inbound(quantity);body['number']=numbers[0];return result['data']['ids'][0],body
                    self.create_inbound=imported
                    try:return self.full_stock_flow()+['The same ordinary operator establishes initial inventory through actual template/multipart preview+confirmation instead of manual create; imported draft continues through real stock/sale/return/receipt and ordered reversal']
                    finally:self.create_inbound=original
                self.case('inbound.files.same_operator_import_sale_return_receipt',imported_business_flow)
        self.write_report()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',action='store_true');p.add_argument('--gateway',action='store_true');a=p.parse_args();InboundFileSuite(read_state(),a.gateway).run(a.baseline)
