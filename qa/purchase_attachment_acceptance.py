"""Actual HTTP multipart/binary and independent MySQL checks. Dedicated QA only."""
import argparse, concurrent.futures, hashlib, json, urllib.request, urllib.error, uuid
import time
from purchase_posting_acceptance import PurchasePostingSuite
from acceptance import read_state, sql, literal, QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class PurchaseAttachmentSuite(PurchasePostingSuite):
    def document(self,id):return self.request('GET','/purchase-note/document/'+id,service='purchase')
    def fixture(self):PurchasePostingSuite.fixture(self)
    def order(self):return self.create_document()
    def records(self,id):return int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='buy' AND source="+literal(id)+';'))
    def state_of(self,id):return self.checked(id)
    def unchanged(self):assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
    def upload(self, order, version=None, data=b'QA actual attachment\x00\xff', name='QA contract.txt'):
        assert self.state['purchase_port']==18023
        if version is None: version=self.document(order)['data']['version']
        boundary='qa'+uuid.uuid4().hex
        payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="version"\r\n\r\n'+version+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="'+name+'"\r\nContent-Type: application/octet-stream\r\n\r\n').encode('utf-8')+data+('\r\n--'+boundary+'--\r\n').encode()
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/attachments/'+order,data=payload,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=40) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return dict(code=error.code)
    def download(self,order,id):
        assert self.state['purchase_port']==18023
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/attachments/'+order+'/'+id,headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=25) as response:return response.read(),dict(response.headers)
        except urllib.error.HTTPError as error:return error.read(),dict(error.headers)
    def remove(self,order,id,version=None):
        if version is None:version=self.document(order)['data']['version']
        return self.request('DELETE','/purchase-note/attachments/'+order+'/'+id,dict(version=version),service='purchase')
    def fresh(self):self.fixture();return self.order()
    def added(self,order,**kwargs):
        result=self.upload(order,**kwargs);assert result.get('code')==10000, 'Upload rejected: '+str(result.get('message'))
        return result['data']['items'][-1]
    def binary(self,order,id,data):
        actual,headers=self.download(order,id);assert actual==data and headers.get('Content-Type','').startswith('application/octet-stream')
        assert headers.get('X-Content-Type-Options')=='nosniff' and 'attachment' in headers.get('Content-Disposition','')
    def run(self):
        def actual():
            order=self.fresh();old=self.document(order)['data']['version'];data=b'QA actual persisted document\x00\xff'
            item=self.added(order,data=data,name='QA 合同.txt');doc=self.document(order)['data']
            assert doc['attachments']==[item] and doc['version']!=old and item['sha256']==hashlib.sha256(data).hexdigest() and item['size']==len(data)
            assert abs(float(item['uploadedAtMillis'])/1000-time.time())<30,'Uploaded timestamp does not represent the actual current instant'
            assert sql(self.state,'SELECT CONCAT(file_size,\':\',sha256,\':\',user_id,\':\',HEX(body)) FROM psi_buy_attachment WHERE id='+literal(item['id'])+';')==str(len(data))+':'+hashlib.sha256(data).hexdigest()+':'+self.actor+':'+data.hex().upper()
            self.binary(order,item['id'],data);assert self.records(order)==2;self.unchanged()
            return ['Actual Unicode multipart persists exact binary/SHA/operator; reopened document and binary download agree; stock/funds unchanged']
        self.case('purchase.attachment_actual_persistence_download',actual)
        def removed():
            order=self.fresh();item=self.added(order);old=self.document(order)['data']['version'];result=self.remove(order,item['id']);assert result.get('code')==10000 and not result['data']['items'] and result['data']['version']!=old
            assert self.document(order)['data']['attachments']==[]
            assert 'application/json' in self.download(order,item['id'])[1].get('Content-Type','')
            assert sql(self.state,'SELECT CONCAT(removed_by,\':\',removed_at IS NOT NULL,\':\',LENGTH(body)>0) FROM psi_buy_attachment WHERE id='+literal(item['id'])+';')==self.actor+':1:1'
            assert self.records(order)==3 and self.remove(order,item['id']).get('code')!=10000;self.unchanged()
            return ['Logical removal survives reopen, denies download, retains bytes/operator/history and advances version']
        self.case('purchase.attachment_logical_remove',removed)
        def stale():
            order=self.fresh();old=self.document(order)['data']['version'];item=self.added(order)
            assert self.upload(order,old,name='other.txt').get('code')!=10000 and self.remove(order,item['id'],old).get('code')!=10000
            assert self.request('POST','/purchase-note/verification',dict(ids=[order],type=1,version=old),service='purchase').get('code')!=10000
            assert self.state_of(order)=='0' and self.records(order)==2
            page=self.request('GET','/purchase-note/list?pageIndex=1&pageSize=10&number='+sql(self.state,'SELECT number FROM buy WHERE id='+literal(order)+';'),service='purchase')
            assert page.get('code')==10000 and page['data']['rows'][0]['version']==self.document(order)['data']['version']
            assert self.check([order]).get('code')==10000;self.binary(order,item['id'],b'QA actual attachment\x00\xff');self.unchanged()
            return ['Attachment mutation invalidates old upload/remove/check versions; list/detail versions match; checked download remains available']
        self.case('purchase.attachment_stale_version_and_batch_digest',stale)
        def guards():
            order=self.fresh();item=self.added(order);assert self.check([order]).get('code')==10000
            assert self.upload(order,name='checked.txt').get('code')!=10000 and self.remove(order,item['id']).get('code')!=10000
            assert self.post([order]).get('code')==10000;self.binary(order,item['id'],b'QA actual attachment\x00\xff')
            assert self.upload(order,name='posted.txt').get('code')!=10000
            sql(self.state,'UPDATE buy SET examine=0,`check`=0 WHERE id='+literal(order)+';')
            assert self.upload(order,name='legacy-marker.txt').get('code')!=10000 and self.remove(order,item['id']).get('code')!=10000
            sql(self.state,'UPDATE buy SET examine=1,`check`=1 WHERE id='+literal(order)+';')
            assert self.post([order],0).get('code')==10000 and self.check([order],0).get('code')==10000
            period=uuid.uuid4().hex
            sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+literal(period)+",'2026-11-15','2026-11-15',"+literal(self.actor)+');')
            try:assert self.upload(order,name='period.txt').get('code')!=10000 and self.remove(order,item['id']).get('code')!=10000
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            self.unchanged();return ['Actual checked/posted states deny mutation, posted files download; owned corrupt-zero flags cannot hide real stock/funds marker; actual reversal restores originals; explicit QA period rejects attachments']
        self.case('purchase.attachment_document_state_period',guards)
        def duplicate():
            order=self.fresh();item=self.added(order);old=self.document(order)['data']['version'];result=self.upload(order)
            assert result.get('code')==10000 and result['data']['version']==old and result['data']['items']==[item] and self.records(order)==2
            assert self.upload(order,data=b'changed').get('code')!=10000 and self.records(order)==2
            self.unchanged();return ['Fresh-version exact retry is idempotent; same-name different bytes cannot silently replace file']
        self.case('purchase.attachment_duplicate_not_replaced',duplicate)
        def invalid():
            order=self.fresh()
            for name,data in [('empty.txt',b''),('../outside.txt',b'x'),('..\\outside.txt',b'x'),('x'*201,b'x'),('large.bin',b'x'*(5*1024*1024+1))]:assert self.upload(order,name=name,data=data).get('code')!=10000
            assert not self.document(order)['data']['attachments'] and self.records(order)==1
            data=b'z'*(5*1024*1024);item=self.added(order,data=data,name='limit.bin');self.binary(order,item['id'],data)
            return ['Empty/path/overlong/over5MiB files rejected with no persistence; exact5MiB truly uploads/downloads']
        self.case('purchase.attachment_filename_and_actual_size_limits',invalid)
        def quota():
            order=self.fresh()
            for index in range(10):self.added(order,name='quota'+str(index)+'.txt')
            assert self.upload(order,name='eleventh.txt').get('code')!=10000 and len(self.document(order)['data']['attachments'])==10
            item=self.document(order)['data']['attachments'][0];assert self.remove(order,item['id']).get('code')==10000
            self.added(order,name='eleventh.txt');assert len(self.document(order)['data']['attachments'])==10
            return ['Actual ten active-file quota enforced and logical removal frees one slot']
        self.case('purchase.attachment_active_quota',quota)
        def rollback():
            order=self.fresh();old=self.document(order)['data']['version'];trigger='qa_attachment_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source="+literal(order)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA attachment history failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.upload(order).get('code')!=10000 and sql(self.state,'SELECT COUNT(*) FROM psi_buy_attachment WHERE purchase_id='+literal(order)+';')=='0' and self.document(order)['data']['version']==old
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            item=self.added(order);old=self.document(order)['data']['version']
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source="+literal(order)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA attachment remove failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.remove(order,item['id']).get('code')!=10000 and self.document(order)['data']['version']==old;self.binary(order,item['id'],b'QA actual attachment\x00\xff')
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.remove(order,item['id']).get('code')==10000;self.unchanged()
            return ['Real MySQL history failure atomically rolls back upload bytes and removal state; retry succeeds']
        self.case('purchase.attachment_storage_failure_rollback',rollback)
        def race():
            order=self.fresh();version=self.document(order)['data']['version']
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda n:self.upload(order,version,name=n+'.txt'),['first','second']))
            assert sum(r.get('code')==10000 for r in results)==1 and len(self.document(order)['data']['attachments'])==1 and self.records(order)==2
            order=self.order();version=self.document(order)['data']['version']
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                upload=pool.submit(self.upload,order,version);audit=pool.submit(self.request,'POST','/purchase-note/verification',dict(ids=[order],type=1,version=version),service='purchase');results=[upload.result(),audit.result()]
            assert sum(r.get('code')==10000 for r in results)==1
            assert (self.state_of(order)=='1')==(results[1].get('code')==10000) and len(self.document(order)['data']['attachments'])==(1 if results[0].get('code')==10000 else 0)
            self.unchanged();return ['Actual concurrent same-version uploads have one winner; upload versus check cannot check an unseen attachment']
        self.case('purchase.attachment_concurrent_upload_check',race)
        def scope():
            order=self.fresh();item=self.added(order);other=self.order()
            assert 'application/json' in self.download(other,item['id'])[1].get('Content-Type','') and self.remove(other,item['id']).get('code')!=10000
            foreign=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA attachment foreign');UPDATE buy SET frame="+literal(foreign)+' WHERE id='+literal(order)+';')
            role=self.success('POST','/role/add-role',dict(name='QA Attachment Scope '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            _,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                with qa_resource_grants(self.state,['/purchase-note/info','/purchase-note/revise'],[keyword]):
                    assert self.upload(order,'0'*64).get('code')==403 and self.remove(order,item['id'],'0'*64).get('code')==403 and 'application/json' in self.download(order,item['id'])[1].get('Content-Type','')
            finally:self.token=admin
            return ['Attachment IDs are bound to order and current organization on upload/remove/download']
        self.case('purchase.attachment_order_and_organization_scope',scope)
        def auth():
            order=self.fresh();item=self.added(order)
            role=self.success('POST','/role/add-role',dict(name='QA Attachment '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            _,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.upload(order,'0'*64).get('code')==403 and 'application/json' in self.download(order,item['id'])[1].get('Content-Type','')
                with qa_resource_grants(self.state,['/purchase-note/info'],[keyword]):
                    self.binary(order,item['id'],b'QA actual attachment\x00\xff');assert self.upload(order).get('code')==403
                    with qa_resource_grants(self.state,['/purchase-note/revise'],[keyword]):
                        added=self.added(order,name='role.txt');assert self.remove(order,added['id']).get('code')==10000
                    assert self.upload(order).get('code')==403
                assert 'application/json' in self.download(order,item['id'])[1].get('Content-Type','')
            finally:self.token=admin
            return ['Actual OAuth user needs detail to download and detail+update to mutate; revocation immediately enforced']
        self.case('purchase.attachment_actual_role_permissions',auth)
        def cascade():
            order=self.fresh();item=self.added(order);assert self.remove(order,item['id']).get('code')==10000;self.added(order,name='active.txt')
            assert self.request('POST','/purchase-note/delete',[order],service='purchase').get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM psi_buy_attachment WHERE purchase_id='+literal(order)+';')=='0' and self.records(order)==5
            self.unchanged();return ['Allowed physical deletion of unused draft cascades both active and removed blobs while audit records survive']
        self.case('purchase.attachment_draft_deletion_cascade',cascade)
        def checksum():
            order=self.fresh();item=self.added(order);sql(self.state,'UPDATE psi_buy_attachment SET body=0x626164 WHERE id='+literal(item['id'])+';')
            data,headers=self.download(order,item['id']);assert 'application/json' in headers.get('Content-Type','') and json.loads(data).get('code')!=10000
            return ['Actual corrupted stored bytes are never returned as a successful binary download']
        self.case('purchase.attachment_corruption_refused',checksum)
        def edit_preserves():
            order=self.fresh();old=self.document(order)['data']['version'];item=self.added(order);doc=self.document(order)['data'];line=doc['items'][0];head=doc['header']
            body=dict(id=order,version=old,supplier=self.supplier,time=head['time_text'],number=head['number'],actual=226,money=0,data='QA receipt attachment preserved',details=[dict(id=line['id'],goods=self.goods,unit='unit',warehouse=self.warehouse,price=100,nums=2,discount=0,tax=13,retreat=0)])
            assert self.revise(body).get('code')!=10000;body['version']=doc['version'];assert self.revise(body).get('code')==10000
            assert self.document(order)['data']['attachments']==[item];self.binary(order,item['id'],b'QA actual attachment\x00\xff')
            assert self.check([order]).get('code')==10000;self.unchanged()
            return ['Old receipt edit cannot overwrite uploaded files; fresh actual revise retains exact binary and permits versioned check']
        self.case('purchase.attachment_revise_preserves_files',edit_preserves)
        def lifecycle():
            self.fixture();order=self.create_document(50);item=self.added(order);assert self.check([order]).get('code')==10000
            assert self.post([order]).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==176
            self.binary(order,item['id'],b'QA actual attachment\x00\xff')
            assert self.post([order],0).get('code')==10000 and self.check([order],0).get('code')==10000;self.unchanged()
            assert self.remove(order,item['id']).get('code')==10000
            assert not self.document(order)['data']['attachments'];self.unchanged()
            return ['Actual binary survives check/post with2 units/50 cash/176 payable, reversal/uncheck restores0/100/0 and then permits logical removal']
        self.case('purchase.attachment_real_stock_funds_roundtrip',lifecycle)
        def stale_audit():
            order=self.fresh();assert self.check([order]).get('code')==10000;old=self.review_versions([order])
            assert self.check([order],0).get('code')==10000;self.added(order)
            assert self.check([order]).get('code')==10000
            before=self.records(order);assert self.post([order],versions=old).get('code')!=10000 and self.records(order)==before;self.unchanged()
            assert self.post([order]).get('code')==10000 and self.inventory()==2 and self.balance('supplier',self.supplier)==226
            assert self.post([order],0).get('code')==10000 and self.check([order],0).get('code')==10000;self.unchanged()
            return ['A checked page predating actual file upload/uncheck/recheck cannot audit; fresh explicit version posts and reverses exact stock/payable']
        self.case('purchase.attachment_stale_review_cannot_post',stale_audit)
        def metadata():
            order=self.fresh();item=self.added(order);old=self.document(order)['data']['version'];before=self.records(order)
            sql(self.state,'UPDATE psi_buy_attachment SET name='+literal('QA owned metadata scheduling fixture.txt')+' WHERE id='+literal(item['id'])+';')
            after=self.document(order)['data'];assert after['version']!=old and self.records(order)==before
            page=self.request('GET','/purchase-note/list?pageIndex=1&pageSize=10&number='+after['header']['number'],service='purchase')
            assert page.get('code')==10000 and page['data']['rows'][0]['version']==after['version']
            assert self.request('POST','/purchase-note/verification',dict(ids=[order],type=1,version=old),service='purchase').get('code')!=10000;self.unchanged()
            return ['Owned SQL metadata-only integrity fixture changes both canonical versions without fabricating an operation history; old check refuses; this does not claim a user-facing rename feature']
        self.case('purchase.attachment_metadata_in_canonical_snapshot',metadata)
        self.write_report()


FIXTURE=QA/'runtime/purchase-attachment-browser.json'
def prepare():
    s=PurchaseAttachmentSuite(read_state());s.fixture();body=s.body();body['purchaseNoteBuyDTO'].update(time='2026-11-15 13:47:00',file='[]',money=50,account=s.account)
    body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]');id=s.create(body)
    name='QA purchase receipt attachment.txt';data=b'QA generated purchase receipt attachment\r\nExact persisted bytes.\x00\xff';(QA/'runtime'/name).write_bytes(data)
    f=dict(database=s.state['database'],id=id,number=body['purchaseNoteBuyDTO']['number'],actor=s.actor,goods=s.goods,warehouse=s.warehouse,supplier=s.supplier,account=s.account,name=name,sha256=hashlib.sha256(data).hexdigest(),size=len(data))
    FIXTURE.write_text(json.dumps(f),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared actual purchase attachment browser document '+f['number'])
def verify(stage,download=None):
    state=read_state();f=json.loads(FIXTURE.read_text());assert state['database']==f['database'];s=PurchaseAttachmentSuite(state)
    row=json.loads(sql(state,"SELECT JSON_OBJECT('name',name,'size',file_size,'sha',sha256,'user',user_id,'removed',removed_at IS NOT NULL,'operator',removed_by,'body',HEX(body)) FROM psi_buy_attachment WHERE purchase_id="+literal(f['id'])+';'))
    assert row['name']==f['name'] and row['size']==f['size'] and row['sha']==f['sha256'] and row['user']==f['actor'] and hashlib.sha256(bytes.fromhex(row['body'])).hexdigest()==f['sha256']
    assert bool(row['removed'])==(stage=='removed')
    if stage=='removed':assert row['operator']==f['actor']
    if download:assert hashlib.sha256(__import__('pathlib').Path(download).read_bytes()).hexdigest()==f['sha256']
    audited=stage=='posted'
    assert sql(state,'SELECT CONCAT(CAST(`check` AS SIGNED),\':\',CAST(examine AS SIGNED),\':\',`user`,\':\',file) FROM buy WHERE id='+literal(f['id'])+';')==('1:1:' if audited else '0:0:')+f['actor']+':[]'
    assert s.records(f['id'])=={'uploaded':2,'posted':4,'removed':7}[stage]
    assert float(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==(2 if audited else 0)
    assert float(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==(50 if audited else 100)
    assert float(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==(176 if audited else 0)
    (QA/('reports/purchase-attachment-browser-'+stage+'.json')).write_text(json.dumps(dict(status='verified',stage=stage,exact_download_verified=bool(download),production_business_writes=0,all_system_features_accepted=False)))
    print('PASS actual browser purchase attachment '+stage+': exact bytes/operator/persistence and stock/cash/payable independently verified')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','uploaded','posted','removed'],nargs='?',default='run');parser.add_argument('--download');args=parser.parse_args()
    if args.action=='run':PurchaseAttachmentSuite(read_state()).run()
    elif args.action=='prepare':prepare()
    else:verify(args.action,args.download)
