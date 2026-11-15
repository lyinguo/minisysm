"""Actual XLSX upload, persistence, atomicity and posting in the dedicated QA environment."""
import io
import json
import uuid
import urllib.request
import urllib.error
import concurrent.futures
import argparse
import datetime
from decimal import Decimal
from openpyxl import Workbook,load_workbook
from purchase_posting_acceptance import PurchasePostingSuite
from acceptance import QA,read_state,sql,literal
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

HEADERS=['供应商编号','单据日期','单据编号','单据金额(自动计算)','实际金额(自动计算)','实付金额','结算账户编号','关联人员编号','物流信息','单据备注','商品编号','辅助属性','单位','仓库编号','批次号','生产日期','单价','数量','序列号(JSON数组)','折扣率(%)','折扣额(自动计算)','金额(自动计算)','税率(%)','税额(自动计算)','价税合计(自动计算)','商品备注']


class PurchaseImportSuite(PurchasePostingSuite):
    def rows(self):
        self.fixture()
        number='QAIMP'+uuid.uuid4().hex[:24]
        row=[self.supplier,'2026-11-15 13:47:00',number,'999','999',0,self.account,'','','QA import',self.goods,'','unit',self.warehouse,'','',100,2,'[]',0,'999','999',13,'999','999','QA line']
        return number,row

    def workbook(self,rows,headers=None):
        if getattr(self,'template_bytes',None) and headers is None:
            book=load_workbook(io.BytesIO(self.template_bytes));sheet=book.worksheets[0]
        else:
            book=Workbook();sheet=book.active;sheet.title='采购导入'
            sheet.append(['采购单导入模板 V1']);sheet.append(headers or HEADERS)
        for row in rows:sheet.append(row)
        target=io.BytesIO();book.save(target);return target.getvalue()

    def upload(self,data,token=None):
        assert self.state['purchase_port']==18023
        boundary='qa'+uuid.uuid4().hex
        payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="excelFile"; filename="qa.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/import',data=payload,headers={'Authorization':'Bearer '+(token or self.token),'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=40) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return {'code':error.code}

    def count(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM buy WHERE number='+literal(number)+';'))

    def run(self):
        def template():
            request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/import/template',headers={'Authorization':'Bearer '+self.token})
            with self.opener.open(request,timeout=20) as response:data=response.read()
            self.template_bytes=data
            book=load_workbook(io.BytesIO(data));sheet=book.worksheets[0]
            assert [sheet.cell(2,i+1).value for i in range(26)]==HEADERS
            assert '填写说明' in book.sheetnames and sheet.max_row==2,'Template must have instructions, not importable fake examples'
            return ['Actual downloaded XLSX has exact headers, a separate guide and no example business rows']
        self.case('purchase.import_actual_template',template)

        def draft():
            number,row=self.rows();second=list(row);second[0:10]=['']*10;second[17]=1
            result=self.upload(self.workbook([row,second]));assert result.get('code')==10000,'Valid XLSX rejected'
            identifier=sql(self.state,'SELECT id FROM buy WHERE number='+literal(number)+';');assert identifier
            doc=self.document(identifier)
            assert doc['header']['frame']==self.state['frame_id'] and doc['header']['user']==self.actor,'Import fabricated organization or creator'
            assert len(doc['items'])==2 and all(item['goods']==self.goods for item in doc['items'])
            assert Decimal(str(doc['header']['total']))==300 and Decimal(str(doc['header']['actual']))==339
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            assert self.check([identifier]).get('code')==10000 and self.post([identifier]).get('code')==10000
            assert self.inventory()==3 and self.balance('supplier',self.supplier)==339
            assert self.post([identifier],0).get('code')==10000 and self.inventory()==0 and self.balance('supplier',self.supplier)==0
            return ['Actual two-line import uses real actor/references and authoritative amounts; draft leaves balances untouched; real audit/reverse moves inventory and payable correctly']
        self.case('purchase.import_real_draft_and_posting',draft)

        def invalid():
            number,row=self.rows();bad=list(row);bad[17]=-1
            result=self.upload(self.workbook([row,bad]))
            assert result.get('code')!=10000,'Invalid line silently skipped'
            assert '第4行' in result.get('message',''),'Bad line not identified for correction'
            assert self.count(number)==0,'Failed import left a partial header or first line'
            return ['Invalid second line rejects the entire actual upload without partial documents']
        self.case('purchase.import_invalid_line_atomic',invalid)

        def multi_duplicate():
            number,row=self.rows();existing=self.create_document();existing_number=self.document(existing)['header']['number']
            duplicate=list(row);duplicate[2]=existing_number
            assert self.upload(self.workbook([row,duplicate])).get('code')!=10000
            assert self.count(number)==0 and self.count(existing_number)==1,'Duplicate later document left partial commits'
            return ['Existing number in second document rejects whole workbook; prior existing draft is preserved']
        self.case('purchase.import_multiple_documents_duplicate_atomic',multi_duplicate)

        def wrong_refs():
            number,row=self.rows();row[10]='Missing goods '+uuid.uuid4().hex[:6]
            assert self.upload(self.workbook([row])).get('code')!=10000,'Unknown product imported'
            assert self.count(number)==0
            return ['Unknown product rejects upload instead of writing its label as a goods identifier']
        self.case('purchase.import_unknown_reference_denied',wrong_refs)

        def malformed():
            for index,value in [(1,'2026-02-30'),(17,'not-a-number'),(19,'-1'),(22,101),(18,'bad-json')]:
                number,row=self.rows();row[index]=value
                assert self.upload(self.workbook([row])).get('code')!=10000,'Invalid cell accepted at column '+str(index)
                assert self.count(number)==0
            return ['Invalid calendar date, quantity, rates and serial JSON rejected without persisted documents']
        self.case('purchase.import_invalid_cells_denied',malformed)

        def codes_and_paid():
            first,row=self.rows();second=list(row);second[2]='QAIMP'+uuid.uuid4().hex[:24]
            for index,table,identifier in [(0,'supplier',self.supplier),(6,'account',self.account),(10,'goods',self.goods),(13,'warehouse',self.warehouse)]:
                row[index]=sql(self.state,'SELECT number FROM '+table+' WHERE id='+literal(identifier)+';');second[index]=row[index]
            row[5]=50;row[19]=10;row[22]='13%';row[3]=0;row[4]=0
            book=load_workbook(io.BytesIO(self.workbook([row,second])));sheet=book.worksheets[0]
            sheet.cell(3,2,datetime.datetime(2026,11,15,13,47)).number_format='yyyy-mm-dd hh:mm:ss'
            sheet.cell(4,23,0.13).number_format='0%'
            stream=io.BytesIO();book.save(stream)
            assert self.upload(stream.getvalue()).get('code')==10000,'Multiple numbered documents or percentage cells rejected'
            identifiers=[sql(self.state,'SELECT id FROM buy WHERE number='+literal(number)+';') for number in [first,second[2]]]
            assert all(identifiers)
            a,b=[self.document(identifier) for identifier in identifiers]
            assert a['header']['time_text']=='2026-11-15 13:47:00','Excel date cell lost its actual time'
            assert sql(self.state,"SELECT DATE_FORMAT(time,'%Y-%m-%d %H:%i:%s') FROM buy WHERE id="+literal(identifiers[0])+';')=='2026-11-15 13:47:00','Persisted Excel datetime differs from its entered value'
            assert Decimal(str(a['header']['total']))==180 and Decimal(str(a['header']['actual']))==Decimal('203.4')
            assert Decimal(str(b['header']['actual']))==226
            assert self.inventory()==0 and self.balance('account',self.account)==100
            assert self.check([identifiers[0]]).get('code')==10000 and self.post([identifiers[0]]).get('code')==10000
            assert self.inventory()==2 and self.balance('account',self.account)==50 and self.balance('supplier',self.supplier)==Decimal('153.4')
            assert self.post([identifiers[0]],0).get('code')==10000 and self.inventory()==0 and self.balance('account',self.account)==100
            return ['Actual downloaded template imports two documents using business codes and both textual/numeric Excel percentages; discount and partial payment post/reverse correctly']
        self.case('purchase.import_codes_multi_document_and_payment',codes_and_paid)

        def storage_failure():
            number,row=self.rows();second=list(row);second[2]='QAIMP'+uuid.uuid4().hex[:24];marker='QAFAIL'+uuid.uuid4().hex[:12];second[25]=marker
            trigger='qa_import_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON buy_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA import storage failure'; END IF; END$$\nDELIMITER ;")
            data=self.workbook([row,second])
            try:
                assert self.upload(data).get('code')!=10000
                assert self.count(number)==0 and self.count(second[2])==0,'Second-document failure partially committed the first'
                assert sql(self.state,'SELECT COUNT(*) FROM buy_info WHERE data='+literal(marker)+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.upload(data).get('code')==10000 and self.count(number)==1 and self.count(second[2])==1
            assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0
            return ['Actual second-document MySQL insert failure rolls back both documents; fault removal permits the same workbook to succeed without stock/funds movement']
        self.case('purchase.import_storage_failure_atomic_retry',storage_failure)

        def concurrency():
            number,row=self.rows();data=self.workbook([row])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.upload(data),range(2)))
            assert sum(result.get('code')==10000 for result in results)==1 and self.count(number)==1
            assert sql(self.state,'SELECT COUNT(*) FROM buy_info i JOIN buy b ON b.id=i.pid WHERE b.number='+literal(number)+';')=='1'
            return ['Two actual simultaneous uploads of one number create exactly one header and one line']
        self.case('purchase.import_concurrent_number_unique',concurrency)

        def formats():
            number,row=self.rows()
            for data in [self.workbook([]),b'not an Excel workbook',self.workbook([row],headers=['wrong']+HEADERS[1:])]:
                assert self.upload(data).get('code')!=10000 and self.count(number)==0
            formula=list(row);formula[16]='=100+1'
            conflict=list(row);conflict[5]=1
            for rows in [[formula],[row,conflict]]:
                assert self.upload(self.workbook(rows)).get('code')!=10000 and self.count(number)==0
            assert self.upload(b'x'*(5*1024*1024+1)).get('code')!=10000 and self.count(number)==0
            return ['Empty/corrupt/wrong-header/formula/conflicting-header/oversized workbooks leave no drafts']
        self.case('purchase.import_bad_workbooks_denied',formats)

        def permission_scope():
            number,row=self.rows()
            role=self.success('POST','/role/add-role',dict(name='QA Import '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,user)
            assert self.upload(self.workbook([row]),token).get('code')==403 and self.count(number)==0
            foreign=uuid.uuid4().hex;warehouse=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA Import Other Org');"+
                'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [warehouse,'QA Import Other Warehouse','QW'+warehouse[:16],foreign])+');')
            with qa_resource_grants(self.state,['/purchase-note/import'],[keyword]):
                bad=list(row);bad[13]=warehouse
                assert self.upload(self.workbook([bad]),token).get('code')!=10000 and self.count(number)==0
                assert self.upload(self.workbook([row]),token).get('code')==10000,'Import-only grant did not allow draft creation'
                identifier=sql(self.state,'SELECT id FROM buy WHERE number='+literal(number)+';')
                doc=self.document(identifier);assert doc['header']['user']==user_id and doc['header']['frame']==self.state['frame_id']
            another=list(row);another[2]='QAIMP'+uuid.uuid4().hex[:24]
            assert self.upload(self.workbook([another]),token).get('code')==403 and self.count(another[2])==0
            return ['Real new OAuth role requires import grant; import-only grant works with current actor ownership; foreign warehouse denied; same token denied after grant restoration']
        self.case('purchase.import_actual_grant_and_organization',permission_scope)
        self.write_report()


def prepare_browser():
    suite=PurchaseImportSuite(read_state());number,row=suite.rows()
    request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/import/template',headers={'Authorization':'Bearer '+suite.token})
    with suite.opener.open(request,timeout=20) as response:suite.template_bytes=response.read()
    second=list(row);second[:10]=['']*10;second[17]=1
    (QA/'runtime/purchase-import-browser.xlsx').write_bytes(suite.workbook([row,second]))
    second[17]=-1
    (QA/'runtime/purchase-import-browser-invalid.xlsx').write_bytes(suite.workbook([row,second]))
    fixture=dict(database=suite.state['database'],number=number,actor=suite.actor,goods=suite.goods,warehouse=suite.warehouse,supplier=suite.supplier,account=suite.account)
    (QA/'runtime/purchase-import-browser.json').write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated browser import: '+number+'; upload invalid workbook first, then valid workbook')


def verify_browser(saved):
    state=read_state();fixture=json.loads((QA/'runtime/purchase-import-browser.json').read_text(encoding='utf-8'))
    assert state['database']==fixture['database']
    rows=sql(state,'SELECT JSON_OBJECT(\'id\',id,\'actor\',`user`,\'frame\',frame,\'total\',total,\'actual\',actual,\'paid\',money,\'check\',`check`,\'audit\',examine) FROM buy WHERE number='+literal(fixture['number'])+';')
    if saved:
        head=json.loads(rows);assert head['actor']==fixture['actor'] and head['frame']==state['frame_id']
        assert Decimal(str(head['total']))==300 and Decimal(str(head['actual']))==339 and Decimal(str(head['paid']))==0
        assert not head['check'] and not head['audit']
        assert sql(state,'SELECT COUNT(*) FROM buy_info WHERE pid='+literal(head['id'])+' AND goods='+literal(fixture['goods'])+' AND warehouse='+literal(fixture['warehouse'])+';')=='2'
    else:assert not rows,'Failed browser upload left a persisted document'
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(fixture['account'])+';'))==100
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';'))==0
    report=dict(case='purchase.browser_import_saved' if saved else 'purchase.browser_import_rejected',status='verified',draft_saved=saved,production_business_writes=0,all_system_features_accepted=False)
    (QA/('reports/purchase-import-browser-'+('saved' if saved else 'rejected')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS browser import '+('saved two-line draft with authoritative amounts' if saved else 'rejected without partial draft')+'; stock/funds unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify-rejected','verify-saved'],nargs='?',default='run')
    action=parser.parse_args().action
    if action=='prepare':prepare_browser()
    elif action.startswith('verify-'):verify_browser(action=='verify-saved')
    else:PurchaseImportSuite(read_state()).run()
