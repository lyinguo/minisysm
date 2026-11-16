"""Downloaded receipt template roundtrip through actual multipart HTTP and MySQL."""
import copy,datetime,io,json,urllib.request,uuid,zipfile,os,xml.etree.ElementTree as ET
from decimal import Decimal
from openpyxl import load_workbook
from receipt_import_acceptance import ReceiptImportSuite
from receipt_import_legacy_acceptance import ReceiptLegacyImportSuite
from resource_fixture import qa_database_resource_grants
from acceptance import read_state,sql,literal

class ReceiptFileImportSuite(ReceiptImportSuite):
    upload=ReceiptLegacyImportSuite.upload
    def template(self):
        request=urllib.request.Request('http://127.0.0.1:18026/fund/receipt/import-template',headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=25) as response:raw=response.read()
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return dict(code=error.code)
        return json.loads(raw) if raw.startswith(b'{') else raw
    def filled(self,rows,native_date=False):
        raw=self.template();assert isinstance(raw,bytes),'Actual template download failed'
        workbook=load_workbook(io.BytesIO(raw));sheet=workbook.worksheets[0]
        assert sheet.max_row==1 and workbook.sheetnames==['收款模板','填写说明']
        assert list(next(sheet.values))==['收款单编号','收款时间','客户编号','结算账户编号','结算金额','结算号','单据备注','明细备注']
        assert '客户编号' in str(list(workbook['填写说明'].values)) and '不会自动' in str(list(workbook['填写说明'].values))
        for row in rows:sheet.append([row['number'],datetime.datetime.fromisoformat(row['date']) if native_date else row['date'],row['customerNumber'],row['accountNumber'],row['money'],row.get('settle',''),row.get('remark',''),row.get('lineRemark','')])
        if native_date:
            for index in range(2,len(rows)+2):sheet.cell(index,2).number_format='yyyy-mm-dd hh:mm:ss'
        out=io.BytesIO();workbook.save(out);workbook.close();return out.getvalue()
    def run(self):
        def roundtrip():
            rows=self.rows();raw=self.filled(rows,native_date=True);result=self.upload(raw)
            assert result.get('code')==10000,str(result);plan=result['data'];self.absent(rows)
            assert plan['documentCount']==2 and plan['lineCount']==3 and plan['cash']==45
            assert all(ref['customer']=='QA Posting Customer' and ref['account']=='QA Posting Account' for ref in plan['references'])
            assert self.upload(raw)['data']['version']==plan['version']
            result=self.upload(raw,plan['version']);assert result.get('code')==10000,str(result)
            first,second=[self.document(identifier) for identifier in result['data']['ids']]
            assert first['header']['total']==25 and len(first['items'])==2 and second['header']['total']==20
            assert all(document['header']['timeText']=='2026-11-16 14:00:00' and document['header']['user']==self.actor for document in [first,second])
            assert self.upload(raw,plan['version']).get('code')!=10000
            assert all(self.count_receipt(row['number'])==1 for row in rows);self.unchanged_receipt()
            return ['Actual downloaded empty template includes instructions; native Excel timestamps and real business codes preview actual names without writes, then same original multipart file+version commits two complete drafts/three rows/45 with actual actor; duplicate commit refused, no money movement']
        self.case('receipt.import_actual_template_multipart_roundtrip',roundtrip)
        def bad_files():
            rows=self.rows();base=self.filled(rows)
            for column,value in [(1,'wrong header'),(5,'1,2'),(5,'=10+15'),(5,'10.12345'),(2,'2026-02-30 14:00:00')]:
                workbook=load_workbook(io.BytesIO(base));sheet=workbook.worksheets[0]
                sheet.cell(1 if value=='wrong header' else 2,column).value=value
                out=io.BytesIO();workbook.save(out);workbook.close();result=self.upload(out.getvalue())
                assert result.get('code')!=10000,'Invalid real spreadsheet accepted: column='+str(column)+', input='+value
                self.absent(rows)
            assert self.upload(b'not a workbook').get('code')!=10000;self.absent(rows)
            return ['Actual malformed header/workbook, malformed grouped number, formula, excessive precision and invalid calendar date reject; none persist headers/details or alter cash/AR/stock']
        self.case('receipt.import_actual_invalid_workbooks_atomic',bad_files)
        def late_failure():
            rows=self.rows();raw=self.filled(rows);plan=self.upload(raw)['data'];trigger='qa_file_'+uuid.uuid4().hex[:12];marker=rows[-1]['lineRemark']
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON imy_info FOR EACH ROW BEGIN IF NEW.account="+literal(self.account)+' AND NEW.data='+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA actual file import fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.upload(raw,plan['version']).get('code')!=10000;self.absent(rows)
                assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND info LIKE "+literal('%'+rows[0]['number']+'%')+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.upload(raw,plan['version']).get('code')==10000;self.unchanged_receipt()
            return ['Actual second-document storage failure via multipart file endpoint rolls back first complete draft plus histories, same original file/version retries after removing test fault']
        self.case('receipt.import_actual_file_entire_batch_rollback',late_failure)
        def stale_file():
            rows=self.rows();raw=self.filled(rows);plan=self.upload(raw)['data'];changed=copy.deepcopy(rows);changed[0]['money']=11
            assert self.upload(self.filled(changed),plan['version']).get('code')!=10000;self.absent(rows)
            old_name=sql(self.state,'SELECT name FROM account WHERE id='+literal(self.account)+';')
            sql(self.state,'UPDATE account SET name='+literal('QA Changed Reviewed Account')+' WHERE id='+literal(self.account)+';')
            try:assert self.upload(raw,plan['version']).get('code')!=10000;self.absent(rows)
            finally:sql(self.state,'UPDATE account SET name='+literal(old_name)+' WHERE id='+literal(self.account)+';')
            assert self.upload(raw,plan['version']).get('code')==10000;self.unchanged_receipt()
            return ['Changed actual file or reviewed account display name invalidates preview without writes; exact original file/version can retry after fixture master restored']
        self.case('receipt.import_actual_file_and_display_reference_versions',stale_file)
        def grants():
            rows=self.rows();raw=self.filled(rows);_,token,role=self.role_user();admin=self.token
            try:
                self.token=token;assert self.template().get('code')==403 and self.upload(raw).get('code')==403
                with qa_database_resource_grants(self.state,['/fund/receipt/import'],[role]):
                    assert self.template().get('code')==403
                    with qa_database_resource_grants(self.state,['/fund/receipt/add'],[role]):
                        assert isinstance(self.template(),bytes)
                        plan=self.upload(raw);assert plan.get('code')==10000
                assert self.upload(raw,plan['data']['version']).get('code')==403
            finally:self.token=admin
            self.absent(rows);return ['Actual downloaded template and multipart file require both current import/add DB grants; revoked ordinary OAuth cannot confirm previously reviewed file; no drafts or money created']
        self.case('receipt.import_actual_template_file_live_grants',grants)
        def exact_amount():
            rows=self.rows();rows=[dict(rows[0],money='1,000.1234',date='2026-11-16')]
            raw=self.filled(rows);result=self.upload(raw);assert result.get('code')==10000,str(result)
            plan=result['data'];assert Decimal(str(plan['cash']))==Decimal('1000.1234');self.absent(rows)
            saved=self.upload(raw,plan['version']);assert saved.get('code')==10000,str(saved)
            document=self.document(saved['data']['ids'][0])
            assert Decimal(str(document['header']['total']))==Decimal('1000.1234') and document['header']['timeText']=='2026-11-16 00:00:00'
            self.unchanged_receipt();return ['Real template accepts a correctly grouped thousand amount with all four decimal places preserved through MySQL; date-only input explicitly becomes midnight, draft does not move money']
        self.case('receipt.import_actual_grouped_amount_and_date_precision',exact_amount)
        def advertised_size():
            rows=self.rows();original=self.filled(rows)
            for padding in [2*1024*1024,5*1024*1024-65536,5*1024*1024+65536]:
                output=io.BytesIO()
                with zipfile.ZipFile(io.BytesIO(original)) as source,zipfile.ZipFile(output,'w') as target:
                    for entry in source.infolist():
                        raw=source.read(entry.filename)
                        if entry.filename=='[Content_Types].xml':
                            types=ET.fromstring(raw);namespace='http://schemas.openxmlformats.org/package/2006/content-types'
                            if not any(node.get('Extension')=='bin' for node in types):ET.SubElement(types,'{'+namespace+'}Default',dict(Extension='bin',ContentType='application/octet-stream'))
                            raw=ET.tostring(types,encoding='utf-8')
                        target.writestr(entry,raw)
                    target.writestr('qa-extra-content.bin',os.urandom(padding),compress_type=zipfile.ZIP_STORED)
                raw=output.getvalue();result=self.upload(raw)
                if len(raw)<=5*1024*1024:
                    assert result.get('code')==10000,'Actual valid workbook below advertised5MiB refused: size='+str(len(raw))+', code='+str(result.get('code'))
                    assert result['data']['documentCount']==2 and result['data']['cash']==45
                else:assert result.get('code')!=10000,'Workbook over advertised5MiB accepted'
                self.absent(rows)
            return ['Actual valid workbooks at2MiB and just below5MiB preview both complete documents, just above5MiB refuses; all leave zero drafts/funds and match user-facing file size limits']
        self.case('receipt.import_actual_advertised_file_size',advertised_size)
        self.write_report()

if __name__=='__main__':ReceiptFileImportSuite(read_state()).run()
