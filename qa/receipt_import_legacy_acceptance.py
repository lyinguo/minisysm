"""Actual obsolete raw-ID spreadsheet cannot partially persist an import batch."""
import io,json,uuid,urllib.request
from openpyxl import Workbook
from receipt_draft_acceptance import ReceiptDraftSuite
from acceptance import read_state

class ReceiptLegacyImportSuite(ReceiptDraftSuite):
    def upload(self,raw,version=None):
        boundary='qa-receipt-'+uuid.uuid4().hex
        body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="receipt.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()+raw+b'\r\n'
        if version is not None:body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="version"\r\n\r\n'+version+'\r\n').encode()
        body+=('--'+boundary+'--\r\n').encode()
        request=urllib.request.Request('http://127.0.0.1:18026/fund/receipt/import',data=body,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=30) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return dict(code=error.code)
    def run(self):
        def partial():
            self.fixture(stock=0);numbers=['QALIMP'+uuid.uuid4().hex[:24] for _ in range(2)]
            workbook=Workbook();sheet=workbook.active
            sheet.append(['frame','customer','time','number','total','people','user','data','account','money','settle','lineData','file'])
            for index,number in enumerate(numbers):sheet.append([self.state['frame_id'],self.customer,'2026-11-16T14:00:00',number,999,'',self.actor,'QA raw legacy',self.account if index==0 else 'missing-account',25,'','QA legacy line',''])
            out=io.BytesIO();workbook.save(out);workbook.close();result=self.upload(out.getvalue())
            counts=[self.count_receipt(number) for number in numbers]
            assert result.get('code')!=10000 and counts==[0,0],'Obsolete raw-ID import partially saved a batch: code='+str(result.get('code'))+', persisted counts='+str(counts)
            self.unchanged_receipt();return ['Actual obsolete raw-ID/invalid-second-row workbook refuses without partial drafts or funds; use the real business-code template and reviewed batch instead']
        self.case('receipt.import_legacy_raw_ids_cannot_partially_save',partial)
        def unreviewed():
            self.fixture(stock=0);number='QALIMP'+uuid.uuid4().hex[:24]
            workbook=Workbook();sheet=workbook.active
            sheet.append(['frame','customer','time','number','total','people','user','data','account','money','settle','lineData','file'])
            sheet.append([self.state['frame_id'],self.customer,'2026-11-16T14:00:00',number,999,'',self.actor,'QA unreviewed legacy',self.account,25,'','QA legacy line',''])
            out=io.BytesIO();workbook.save(out);workbook.close();result=self.upload(out.getvalue())
            count=self.count_receipt(number)
            assert count==0,'Uploading an unreviewed raw-ID file immediately persisted a receipt: code='+str(result.get('code'))+', count='+str(count)
            self.unchanged_receipt();return ['Actual obsolete valid raw-ID workbook cannot persist a receipt merely by uploading, without business-code preview and explicit reviewed confirmation']
        self.case('receipt.import_legacy_unreviewed_upload_cannot_write',unreviewed)
        self.write_report()

if __name__=='__main__':ReceiptLegacyImportSuite(read_state()).run()
