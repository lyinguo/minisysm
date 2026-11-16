"""Real HTTP XLSX bytes inspected independently for scope and business references."""
import io,json,urllib.request,urllib.parse,uuid
from openpyxl import load_workbook
from payment_import_acceptance import PaymentImportSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal

class PaymentExportSuite(PaymentImportSuite):
    def export(self,kind,query):
        request=urllib.request.Request('http://127.0.0.1:18024/payment-order/export/'+kind+'?'+urllib.parse.urlencode(query),headers={'Authorization':'Bearer '+self.token})
        with self.opener.open(request,timeout=30) as response:raw=response.read()
        if raw.startswith(b'{'):return json.loads(raw)
        workbook=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
        try:return list(workbook.active.values)
        finally:workbook.close()
    def imported(self):
        rows=self.rows();plan=self.prepared(rows);result=self.import_rows(rows,plan['version']);assert result.get('code')==10000,str(result)
        return rows,result['data']['ids']
    def run(self):
        def real_names():
            rows,ids=self.imported()
            simple=self.export('simple',dict(ids=','.join(ids)));assert isinstance(simple,list),str(simple)
            assert len(simple)==3 and '供应商' in simple[0] and '核销状态' in simple[0]
            records=[dict(zip(simple[0],row)) for row in simple[1:]]
            assert {row['单据编号'] for row in records}=={row['number'] for row in rows}
            assert all(row['供应商']=='QA Posting Supplier' and row['核销状态']=='未核销' and row['审核状态']=='未审核' and row['核销金额']==0 for row in records),str(records)
            detail=self.export('detail',dict(ids=','.join(ids)));assert isinstance(detail,list),str(detail)
            assert len(detail)==4 and '付款单编号' in detail[0]
            lines=[dict(zip(detail[0],row)) for row in detail[1:]]
            assert sum(row['结算金额'] for row in lines)==45
            assert all(row['供应商']=='QA Posting Supplier' and row['结算账户']=='QA Purchase Posting Account' and row['付款单编号'] in {r['number'] for r in rows} for row in lines)
            self.unchanged()
            return ['Actual downloaded simple/detail XLSX contain selected complete parent documents, usable supplier/account names and parent number, accurate totals/status/allocations; independent workbook parser verifies bytes']
        self.case('payment.export_actual_xlsx_business_references',real_names)

        def scoped():
            rows,ids=self.imported();foreign=ids[1];frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Export Other Org');UPDATE omy SET frame="+literal(frame)+' WHERE id='+literal(foreign)+';')
            _,token,role=self.role_user();admin=self.token;self.token=token
            try:
                for kind in ['simple','detail']:
                    denied=self.export(kind,dict(ids=','.join(ids)));assert isinstance(denied,dict) and denied.get('code')==403,str(denied)
                    with qa_resource_grants(self.state,['/payment-order/export/'+kind],[role]):
                        data=self.export(kind,dict(ids=','.join(ids)));assert isinstance(data,list),str(data)
                        key='单据编号' if kind=='simple' else '付款单编号'
                        values=[dict(zip(data[0],row)) for row in data[1:]]
                        assert values and all(row[key]==rows[0]['number'] for row in values),str(values)
                        empty=self.export(kind,dict(ids=foreign));assert len(empty)==1,str(empty)
                    assert self.export(kind,dict(ids=','.join(ids))).get('code')==403
            finally:self.token=admin
            self.unchanged()
            return ['Actual ordinary OAuth export requires current separate grants, XLSX excludes foreign parent and all foreign details even for explicit IDs; revocation effective with same token']
        self.case('payment.export_actual_live_grants_and_org',scoped)

        def filters():
            rows,ids=self.imported()
            for kind in ['simple','detail']:
                data=self.export(kind,dict(number=rows[0]['number'],startTime='2026-11-15',endTime='2026-11-15'))
                assert isinstance(data,list),str(data);assert len(data)==(2 if kind=='simple' else 3)
                empty=self.export(kind,dict(number="' OR 1=1 -- ",ids=','.join(ids)))
                assert isinstance(empty,list) and len(empty)==1,str(empty)
                for state,value in [('examine',1),('nucleus',2)]:
                    empty=self.export(kind,dict(ids=','.join(ids),**{state:value}))
                    assert isinstance(empty,list) and len(empty)==1,'Export ignored document state filter'
                assert self.export(kind,dict(ids=','.join(ids),examine=2)).get('code')!=10000
                assert self.export(kind,dict(ids="bad') OR 1=1 --")).get('code')!=10000
            self.unchanged()
            return ['Real exports apply inclusive date/number filters, quoted strings remain literal, malformed explicit IDs rejected without changing drafts or funds']
        self.case('payment.export_actual_filters_and_literal_text',filters)
        self.write_report()

if __name__=='__main__':PaymentExportSuite(read_state()).run()
