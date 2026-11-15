"""Procurement function grants/data scope gates using real OAuth, HTTP, Excel and dedicated QA Redis."""
import json
import uuid
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import zipfile
import io
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import QA,read_state,sql,literal


class PurchaseSecuritySuite(PurchaseUiSuite):
    resources=['/purchase-note/'+path for path in ['list','info','add','revise','import','export/simple','export/detail','getBuildBre','verification','audit','delete']]

    def binary(self,path):
        request=urllib.request.Request('http://127.0.0.1:18023'+path,headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=30) as response:
                data=response.read()
                if data.startswith(b'PK'):return 10000,data
                parsed=json.loads(data);return parsed.get('code'),data
        except urllib.error.HTTPError as error:
            return error.code,error.read()

    def import_probe(self):
        # Supply the required multipart field so method validation cannot reject
        # the request before the controller's authorization check is exercised.
        boundary='qa'+uuid.uuid4().hex
        payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="excelFile"; filename="qa.xlsx"\r\n'
                 'Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'
                 'QA unauthorized import must not parse this file\r\n--'+boundary+'--\r\n').encode()
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/import',data=payload,
            headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=20) as response:return json.load(response).get('code')
        except urllib.error.HTTPError as error:return error.code

    def run(self):
        own=self.draft();own_doc=self.document(own);number=own_doc['header']['number']
        foreign,warehouse,supplier=[uuid.uuid4().hex for _ in range(3)]
        sql(self.state,'INSERT INTO frame(id,pid,name,sort) VALUES('+','.join(literal(v) for v in [foreign,'0','QA Security Foreign Org',0])+');'+
            'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [warehouse,'QA Security Foreign Warehouse','QW'+warehouse[:16],foreign])+');'+
            'INSERT INTO supplier(id,name,py,number,frame,`user`,category) VALUES('+','.join(literal(v) for v in [supplier,'QA Security Foreign Supplier','qa','QS'+supplier[:16],foreign,self.actor,'0'])+');')
        self.success('PUT','/user/mod-user',dict(id=self.actor,frame=foreign))
        try:
            body=self.body();body['purchaseNoteBuyDTO']['supplier']=supplier
            body['purchaseNoteInfoDTOS'][0].update(warehouse=warehouse,discount=0,tax=13,batch='',mfd=None,serial='[]')
            foreign_doc=self.create(body)
        finally:self.success('PUT','/user/mod-user',dict(id=self.actor,frame=self.state['frame_id']))
        foreign_line=sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(foreign_doc)+';')
        own_line=sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(own)+';')
        role=self.success('POST','/role/add-role',dict(name='QA Purchase Resource '+uuid.uuid4().hex[:7],data='',root='[]',auth='{}'))
        keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
        user_id,user,_=self.new_user(role=role);token=self.login(user)
        container='psi-qa-redis-'+self.state['database'][len('psi_qa_'):]
        actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
        assert actual==container,'Refusing to alter unverified Redis'
        def redis(*args):return subprocess.run(['docker','exec',container,'redis-cli','--raw']+list(args),capture_output=True,text=True,check=True).stdout.rstrip('\r\n')
        previous={path:(redis('HEXISTS','AUTH:RESOURCE_ROLES',path),redis('HGET','AUTH:RESOURCE_ROLES',path)) for path in self.resources}
        admin=self.token
        try:
            for path in self.resources:redis('HDEL','AUTH:RESOURCE_ROLES',path)
            self.token=token

            def no_query():
                assert self.request('GET','/purchase-note/list?number='+number,service='purchase').get('code')==403,'Role without list grant could query purchases'
                return ['Actual ungranted OAuth role cannot list same-organization purchase records']
            self.case('purchase.security_list_requires_grant',no_query)

            def no_detail():
                for path in ['/purchase-note/document/'+own,'/purchase-note/info?id='+own_line,'/purchase-note/getBuildBre?id='+own]:
                    assert self.request('GET',path,service='purchase').get('code')==403,'Ungranted purchase detail/legacy preview accessible'
                return ['Canonical detail, legacy line detail and return-data preview all require explicit function grants']
            self.case('purchase.security_all_detail_routes_require_grant',no_detail)

            def no_create():
                body=self.body();body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial='[]')
                assert self.request('POST','/purchase-note/add',body,service='purchase').get('code')==403,'Ungranted role created a purchase draft'
                assert sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(body['purchaseNoteBuyDTO']['number'])+';')=='0'
                return ['Ungranted actual draft create rejected without persisted header']
            self.case('purchase.security_add_requires_grant',no_create)

            def no_edit():
                self.token=admin
                try:edit=self.revision(own)
                finally:self.token=token
                before=sql(self.state,'SELECT CONCAT(total,\':\',actual) FROM buy WHERE id='+literal(own)+';')
                assert self.revise(edit).get('code')==403,'Ungranted role edited a purchase draft'
                assert sql(self.state,'SELECT CONCAT(total,\':\',actual) FROM buy WHERE id='+literal(own)+';')==before
                return ['Ungranted actual revision rejected and persisted amounts retained']
            self.case('purchase.security_revise_requires_grant',no_edit)

            def no_export_import():
                for kind in ['simple','detail']:
                    assert self.binary('/purchase-note/export/'+kind+'?ids='+own)[0]==403,'Ungranted role downloaded a procurement export'
                before=sql(self.state,'SELECT COUNT(*) FROM buy;')
                assert self.import_probe()==403,'Unauthorized multipart import reached file parsing'
                assert sql(self.state,'SELECT COUNT(*) FROM buy;')==before,'Unauthorized import persisted a document'
                return ['Both binary exports and multipart import entry require explicit grants; rejected import leaves documents unchanged; import lifecycle remains pending']
            self.case('purchase.security_export_and_import_require_grants',no_export_import)

            grant=json.dumps(['java.util.ArrayList',[keyword]])
            for path in self.resources:redis('HSET','AUTH:RESOURCE_ROLES',path,grant)

            def scope_and_exports():
                listing=self.request('GET','/purchase-note/list?number='+number+'&frame='+foreign,service='purchase')
                assert listing.get('code')==10000 and listing.get('data',{}).get('total')==1
                assert self.document(own)['header']['frame']==self.state['frame_id']
                assert self.request('GET','/purchase-note/info?id='+own_line,service='purchase').get('code')==10000
                for path in ['/purchase-note/document/'+foreign_doc,'/purchase-note/info?id='+foreign_line,'/purchase-note/getBuildBre?id='+foreign_doc]:
                    assert self.request('GET',path,service='purchase').get('code')==403,'Granted user read a foreign organization via an alternate route'
                for kind in ['simple','detail']:
                    assert self.binary('/purchase-note/export/'+kind+'?ids='+foreign_doc)[0]==403,'Export leaked another organization document'
                    assert self.binary('/purchase-note/export/'+kind+'?ids='+own+'&ids='+foreign_doc)[0]==403,'Mixed export partially leaked foreign documents'
                code,data=self.binary('/purchase-note/export/simple?ids='+own)
                assert code==10000 and zipfile.is_zipfile(io.BytesIO(data))
                workbook=zipfile.ZipFile(io.BytesIO(data))
                assert number.encode() in b''.join(workbook.read(name) for name in workbook.namelist() if name.endswith('.xml'))
                detail_code,detail_data=self.binary('/purchase-note/export/detail?ids='+own)
                assert detail_code==10000 and zipfile.is_zipfile(io.BytesIO(detail_data))
                archive=zipfile.ZipFile(io.BytesIO(detail_data))
                assert archive.namelist()==[number+'.xlsx'] and zipfile.is_zipfile(io.BytesIO(archive.read(number+'.xlsx'))),'Own detailed export missing its selected workbook'
                return ['Actual granted same-org canonical/legacy queries and Excel content work; supplied frame cannot expand scope', 'Canonical/legacy/return preview plus both single and mixed foreign exports are denied before file output']
            self.case('purchase.security_granted_scope_and_actual_export',scope_and_exports)

            def grant_revoke():
                for path in ['/purchase-note/list','/purchase-note/info','/purchase-note/export/simple']:redis('HDEL','AUTH:RESOURCE_ROLES',path)
                assert self.request('GET','/purchase-note/list?number='+number,service='purchase').get('code')==403
                assert self.request('GET','/purchase-note/document/'+own,service='purchase').get('code')==403
                assert self.binary('/purchase-note/export/simple?ids='+own)[0]==403
                return ['Revoked grants take effect with the same signed token for list/detail/export']
            self.case('purchase.security_revocation_immediate',grant_revoke)
        finally:
            self.token=admin
            for path,(exists,value) in previous.items():
                if exists=='1':redis('HSET','AUTH:RESOURCE_ROLES',path,value)
                else:redis('HDEL','AUTH:RESOURCE_ROLES',path)
        self.write_report()


if __name__=='__main__':PurchaseSecuritySuite(read_state()).run()
