"""Actual XLSX exports and live authorization; never export real business fixtures."""
import io,json,uuid,base64,urllib.request,urllib.error,urllib.parse
from decimal import Decimal
from openpyxl import load_workbook
from booking_audit_acceptance import OrderAuditSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal

class OrderExportSuite(OrderAuditSuite):
    def export(self,ids,detail=False):
        assert self.state['purchase_port']==18023
        path='/purchase-order/export/detail' if detail else '/purchase-order/export-bor?pid='+urllib.parse.quote(','.join(ids))
        request=urllib.request.Request('http://127.0.0.1:18023'+path,method='POST' if detail else 'GET',data=json.dumps(ids).encode() if detail else None,headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with self.opener.open(request,timeout=30) as response:
                raw=response.read()
                if raw.startswith(b'PK'):return raw
                result=json.loads(raw)
                if result.get('code')==10000 and detail:return base64.b64decode(result['data'])
                return result
        except urllib.error.HTTPError as error:return dict(code=error.code)
    def book(self,ids,detail=False):
        result=self.export(ids,detail);assert isinstance(result,bytes),'Export rejected; code='+str(result.get('code'));return load_workbook(io.BytesIO(result),data_only=False)
    def fixture_order(self,multi=False):
        self.fixture();body=self.order_body();body['purchaseOrderInfoDTOList'][0].update(price='1.0001',nums=1,tax=13)
        if multi:body['purchaseOrderInfoDTOList'].append(dict(body['purchaseOrderInfoDTOList'][0]))
        id=self.create_order(body);return id,body['number']
    def run(self,baseline=False):
        def summary():
            id,number=self.fixture_order();sql(self.state,'UPDATE bor SET state=3 WHERE id='+literal(id)+';')
            rows=list(self.book([id]).worksheets[0].values);row=dict(zip(rows[0],rows[1]))
            assert row['供应商']=='QA Posting Supplier' and row['关联人员']=='QA Booking Person','Summary exposes reference IDs instead of real names'
            assert row['入库状态']=='关闭' and Decimal(str(row['单据金额']))==Decimal('1.0001'),'Closed enum or four-decimal amount lost'
            assert row['单据编号']==number;self.unchanged();return ['Actual simple XLSX preserves closed3, names, selected document and four-decimal1.0001']
        self.case('booking.export_summary_real_names_precision_state',summary)
        def detail():
            id,number=self.fixture_order(True);book=self.book([id],True)
            assert book.sheetnames==['订单汇总','商品明细'],'Detailed export lacks complete separate summary/detail workbook'
            rows=list(book['商品明细'].values);assert len(rows)==4
            first=dict(zip(rows[0],rows[1]));assert first['商品名称']=='QA Purchase Posting Goods' and first['仓库']=='QA Purchase Posting Warehouse'
            assert Decimal(str(first['单价']))==Decimal('1.0001') and Decimal(str(first['税额']))==Decimal('.13')
            assert Decimal(str(first['价税合计']))==Decimal('1.1301') and Decimal(str(rows[-1][rows[0].index('数量')]))==2
            assert book['订单汇总'].cell(2,4).value==number;self.unchanged();return ['Actual detailed XLSX contains all source lines, tax/discount/handled fields and distinct document summary; exact line1.0001/.13/1.1301 and quantity sum2']
        self.case('booking.export_complete_detail_tax_and_totals',detail)
        def empty():
            self.fixture_order()
            assert not isinstance(self.export([],True),bytes),'Empty selection exported every order'
            return ['Empty detail IDs reject instead of exporting all organizations']
        self.case('booking.export_empty_selection_not_all',empty)
        def missing():
            id,_=self.fixture_order()
            for detail in [False,True]:
                assert not isinstance(self.export([id,'zz'+uuid.uuid4().hex[:30]],detail),bytes),'Missing batch member silently omitted'
            self.unchanged();return ['Both formats reject missing batch members without partial download']
        self.case('booking.export_missing_member_not_partial',missing)
        def auth():
            id,_=self.fixture_order();role=self.success('POST','/role/add-role',dict(name='QA Order Export '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                for detail in [False,True]:assert self.export([id],detail).get('code')==403,'Export lacks live forbidden403'
                with qa_resource_grants(self.state,['/purchase-order/export-bor'],[keyword]):
                    assert isinstance(self.export([id]),bytes);assert self.export([id],True).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/export/detail'],[keyword]):
                    assert isinstance(self.export([id],True),bytes);other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Foreign Export');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.export([id],True).get('code')==403
                assert self.export([id],True).get('code')==403
            finally:self.token=admin
            return ['Real OAuth simple/detail grants separate, current frame change and revoked permissions immediately deny export']
        self.case('booking.export_live_permission_and_frame',auth)
        if not baseline:
            def invalid():
                id,_=self.fixture_order()
                for ids in [[id,id],[''],[id,''],[id]+[uuid.uuid4().hex for _ in range(200)]]:
                    for detail in [False,True]:assert not isinstance(self.export(ids,detail),bytes)
                return ['Duplicate/empty/oversized selected IDs reject in both formats']
            self.case('booking.export_invalid_selection_denied',invalid)
            def multi_orders():
                first,number=self.fixture_order();body=self.order_body();body['purchaseOrderInfoDTOList'][0].update(price=2,nums=2);second=self.create_order(body)
                for detailed in [False,True]:
                    rows=list(self.book([first,second],detailed).worksheets[0].values)
                    assert len(rows)==4 and rows[1][3]==number and rows[2][3]==body['number']
                    assert Decimal(str(rows[-1][4]))==Decimal('5.0001') and Decimal(str(rows[-1][5]))==Decimal('5.6501')
                self.unchanged();return ['Actual multi-selection exports both chosen orders in selection order with distinct-header totals5.0001/5.6501']
            self.case('booking.export_all_selected_orders_totals',multi_orders)
            def safe_values():
                id,_=self.fixture_order();sql(self.state,'UPDATE bor SET examine=2,state=4,data='+literal('=1+1')+' WHERE id='+literal(id)+';')
                for detail in [False,True]:
                    sheet=self.book([id],detail).worksheets[0];rows=list(sheet.values);head=list(rows[0]);row=dict(zip(head,rows[1]))
                    assert '异常' in row['审核状态'] and '异常' in row['入库状态']
                    cell=sheet.cell(2,head.index('备注信息')+1);assert cell.value=='=1+1' and cell.data_type=='s','Remark exported as executable formula'
                return ['Damaged enums are explicitly abnormal; user remark beginning equals is a literal string in real XLSX']
            self.case('booking.export_enum_and_literal_cells',safe_values)
            def readonly():
                id,_=self.fixture_order(True);before=self.records(id);lines=sql(self.state,'SELECT GROUP_CONCAT(CONCAT(id,\':\',nums,\':\',handle) ORDER BY id) FROM bor_info WHERE pid='+literal(id)+';')
                for detail in [False,True]:self.book([id],detail)
                assert self.records(id)==before and self.state_of(id)=='0' and sql(self.state,'SELECT GROUP_CONCAT(CONCAT(id,\':\',nums,\':\',handle) ORDER BY id) FROM bor_info WHERE pid='+literal(id)+';')==lines
                self.unchanged();return ['Actual export changes no document/detail/history, stock, cash or payable']
            self.case('booking.export_no_business_mutations',readonly)
        self.write_report()

if __name__=='__main__':
    import sys
    OrderExportSuite(read_state()).run(len(sys.argv)>1 and sys.argv[1]=='baseline')
