"""Actual downloaded receipt workbooks: references, filters and live DB permissions."""
import io,json,urllib.request,urllib.parse,uuid
from openpyxl import load_workbook
from receipt_document_scope_acceptance import ReceiptDocumentScopeSuite
from resource_fixture import qa_database_resource_grants
from acceptance import read_state,sql,literal

class ReceiptExportSuite(ReceiptDocumentScopeSuite):
    def export(self,kind,query):
        request=urllib.request.Request('http://127.0.0.1:18026/fund/receipt/export/'+kind+'?'+urllib.parse.urlencode(query),headers={'Authorization':'Bearer '+self.token})
        try:
            with self.opener.open(request,timeout=30) as response:raw=response.read()
        except urllib.error.HTTPError as error:
            raw=error.read()
            if raw.startswith(b'{'):return json.loads(raw)
            return dict(code=error.code)
        if raw.startswith(b'{'):return json.loads(raw)
        workbook=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
        try:return list(workbook.active.values)
        finally:workbook.close()
    def drafts(self):
        self.fixture(stock=0);first=self.receipt_body();first['info'][0]['amount']=10;first['info'].append(dict(first['info'][0],amount=15,data='QA second account line'))
        second=self.receipt_body();second['info'][0]['amount']=20
        return [first,second],[self.create_receipt(first),self.create_receipt(second)]
    def run(self):
        def actual():
            rows,ids=self.drafts();simple=self.export('simple',dict(ids=','.join(ids)))
            assert isinstance(simple,list) and len(simple)==3,'Simple export ignored selected parent IDs'
            assert {'客户','核销状态','审核状态','核销金额'}<=set(simple[0]),'Simple export lacks meaningful states/settlement columns'
            records=[dict(zip(simple[0],row)) for row in simple[1:]]
            assert {row['单据编号'] for row in records}=={row['number'] for row in rows}
            assert all(row['客户']=='QA Posting Customer' and row['核销状态']=='未核销' and row['审核状态']=='未审核' and row['核销金额']==0 for row in records)
            detail=self.export('detail',dict(ids=','.join(ids)))
            assert isinstance(detail,list) and len(detail)==4,'Detail export ignored selected parent IDs or omitted rows'
            lines=[dict(zip(detail[0],row)) for row in detail[1:]]
            assert sum(row['结算金额'] for row in lines)==45
            assert all(row['客户']=='QA Posting Customer' and row['结算账户']=='QA Posting Account' and row['收款单编号'] in {r['number'] for r in rows} and row['收款日期']=='2026-11-16 14:00:00' for row in lines)
            self.unchanged_receipt();return ['Actual selected simple/detail XLSX bytes parsed independently: two parents, three complete account rows, real customer/account names, full time, amounts and integer-derived status descriptions; no funds moved']
        self.case('receipt.export_actual_selected_xlsx_and_references',actual)
        def scope():
            rows,ids=self.drafts();foreign=ids[1];frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Receipt Export Foreign');UPDATE imy SET frame="+literal(frame)+' WHERE id='+literal(foreign)+';')
            _,token,role=self.role_user();admin=self.token
            try:
                self.token=token
                for kind in ['simple','detail']:
                    denied=self.export(kind,dict(ids=','.join(ids)))
                    assert isinstance(denied,dict) and denied.get('code')==403,'Actual Excel downloaded without an export grant'
                    with qa_database_resource_grants(self.state,['/fund/receipt/export/'+kind],[role]):
                        values=self.export(kind,dict(ids=','.join(ids)));assert isinstance(values,list)
                        key='单据编号' if kind=='simple' else '收款单编号'
                        assert values[1:] and all(dict(zip(values[0],row))[key]==rows[0]['number'] for row in values[1:])
                        assert len(self.export(kind,dict(ids=foreign)))==1
                    assert self.export(kind,dict(ids=','.join(ids))).get('code')==403
            finally:self.token=admin
            self.unchanged_receipt();return ['Actual ordinary OAuth export separately requires current DB function selections, excludes foreign parents/details even by explicit IDs, same token immediately loses revoked export access']
        self.case('receipt.export_live_grants_and_organization',scope)
        def filters():
            rows,ids=self.drafts()
            for kind in ['simple','detail']:
                values=self.export(kind,dict(number=rows[0]['number'],startTime='2026-11-16',endTime='2026-11-16'))
                assert isinstance(values,list) and len(values)==(2 if kind=='simple' else 3),'Inclusive date/number filter ignored'
                assert len(self.export(kind,dict(ids=','.join(ids),number="' OR 1=1 -- ")))==1
                for key,value in [('examine',1),('nucleus',2)]:assert len(self.export(kind,dict(ids=','.join(ids),**{key:value})))==1
                for bad in [dict(ids="bad') OR 1=1 --"),dict(examine=2),dict(startTime='invalid'),dict(startTime='2026-11-17',endTime='2026-11-16')]:
                    result=self.export(kind,bad);assert isinstance(result,dict) and result.get('code')!=10000,'Invalid export query accepted'
            self.unchanged_receipt();return ['Actual workbook export applies inclusive dates, number/status filters and literal quotes; malformed IDs, invalid states/dates and reversed date ranges rejected without writes']
        self.case('receipt.export_filters_and_invalid_queries',filters)
        self.write_report()

if __name__=='__main__':ReceiptExportSuite(read_state()).run()
