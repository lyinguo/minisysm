"""Actual procurement order XLSX upload and persisted business gates, dedicated QA only."""
from decimal import Decimal
import io,json,uuid,concurrent.futures,urllib.request,urllib.error
from openpyxl import Workbook,load_workbook
from booking_receive_acceptance import ReceiveSuite
from acceptance import read_state,sql,literal
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

HEADERS=['供应商编号','单据日期','单据编号','单据金额(自动计算)','实际金额(自动计算)','关联人员编号','到货日期','物流信息','单据备注','商品编号','辅助属性','单位','仓库编号','单价','数量','折扣率(%)','折扣额(自动计算)','金额(自动计算)','税率(%)','税额(自动计算)','价税合计(自动计算)','商品备注']
class OrderImportSuite(ReceiveSuite):
    def row(self,number=None):return [self.supplier,'2026-11-15',number or 'QAORI'+uuid.uuid4().hex[:24],999,999,self.person,'2026-11-16','','QA import',self.goods,'','unit',self.warehouse,100,2,10,999,999,13,999,999,'QA import line']
    def workbook(self,rows,headers=None):
        book=Workbook();sheet=book.active;sheet.append(['采购订单导入模板 V1']);sheet.append(headers or HEADERS)
        for row in rows:sheet.append(row)
        output=io.BytesIO();book.save(output);return output.getvalue()
    def upload(self,data):
        assert self.state['purchase_port']==18023
        boundary='qa'+uuid.uuid4().hex;payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="qa.xlsx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n').encode()+data+('\r\n--'+boundary+'--\r\n').encode()
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-order/import-bor',data=payload,headers={'Authorization':'Bearer '+self.token,'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with self.opener.open(request,timeout=40) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            try:return json.loads(error.read())
            except Exception:return dict(code=error.code)
    def downloaded(self):
        request=urllib.request.Request('http://127.0.0.1:18023/purchase-order/import/template',headers={'Authorization':'Bearer '+self.token})
        with self.opener.open(request,timeout=25) as response:return response.read()
    def imported(self,row):
        result=self.upload(self.workbook([row]));assert result.get('code')==10000,'Actual order XLSX rejected code='+str(result.get('code'))
        id=sql(self.state,'SELECT id FROM bor WHERE number='+literal(row[2])+';');assert id;return id
    def run(self,baseline=False):
        def template():
            data=self.downloaded();book=load_workbook(io.BytesIO(data));sheet=book.worksheets[0]
            assert [sheet.cell(2,i+1).value for i in range(22)]==HEADERS and sheet.max_row==2 and '填写说明' in book.sheetnames
            self.fixture();row=self.row();sheet.append(row);output=io.BytesIO();book.save(output)
            assert self.upload(output.getvalue()).get('code')==10000 and self.count_order(row[2])==1
            return ['Actual downloadable workbook has exact22 headers, separate instructions, no business example rows and is accepted after filling']
        self.case('booking.import_downloaded_template_usable',template)
        def owner():
            self.fixture();row=self.row();second=list(row);second[:9]=['']*9;second[14]=1
            assert self.upload(self.workbook([row,second])).get('code')==10000
            id=sql(self.state,'SELECT id FROM bor WHERE number='+literal(row[2])+';')
            head=json.loads(sql(self.state,"SELECT JSON_OBJECT('user',`user`,'frame',frame,'total',total,'actual',actual) FROM bor WHERE id="+literal(id)+';'))
            assert head['user']==self.actor and head['frame']==self.state['frame_id'],'Import fabricated creator or organization'
            assert Decimal(str(head['total']))==270 and Decimal(str(head['actual']))==Decimal('305.1'),'Untrusted workbook amounts persisted'
            assert sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(id)+' AND goods='+literal(self.goods)+';')=='2'
            self.unchanged();return ['Real two-line continuation import uses current actor/frame and existing product IDs, computes270/305.1, leaves stock/funds unchanged']
        self.case('booking.import_actual_owner_amounts_lines',owner)
        def duplicate():
            self.setup();id=self.source;number=sql(self.state,'SELECT number FROM bor WHERE id='+literal(id)+';');before=sql(self.state,'SELECT GROUP_CONCAT(id ORDER BY id) FROM bor_info WHERE pid='+literal(id)+';');row=self.row(number)
            assert self.upload(self.workbook([row])).get('code')!=10000,'Import overwrote existing approved order'
            assert self.state_of(id)=='1' and sql(self.state,'SELECT GROUP_CONCAT(id ORDER BY id) FROM bor_info WHERE pid='+literal(id)+';')==before
            self.unchanged();return ['Existing approved order number is rejected without changing approval or replacing source line UUIDs']
        self.case('booking.import_existing_approved_not_overwritten',duplicate)
        def invalid():
            self.fixture();row=self.row();bad=list(row);bad[14]=-1
            result=self.upload(self.workbook([row,bad]));assert result.get('code')!=10000,'Negative quantity accepted'
            assert '第4行' in result.get('message','') and self.count_order(row[2])==0
            self.unchanged();return ['Invalid second line gives actual Excel row4 and leaves no partial order']
        self.case('booking.import_invalid_second_line_atomic',invalid)
        def no_phantom():
            self.fixture();row=self.row();row[9]='QA Missing '+uuid.uuid4().hex
            assert self.upload(self.workbook([row])).get('code')!=10000,'Unknown product silently auto-created'
            assert sql(self.state,'SELECT COUNT(*) FROM goods WHERE name='+literal(row[9])+';')=='0' and self.count_order(row[2])==0
            return ['Unknown product refuses upload without creating unintended goods or incomplete order']
        self.case('booking.import_unknown_product_no_phantom',no_phantom)
        def supply():
            self.fixture();row=self.row();assert self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=self.supplier,enabled=False),service='purchase').get('code')==10000
            assert self.upload(self.workbook([row])).get('code')!=10000 and self.count_order(row[2])==0,'Import bypassed disabled catalog'
            return ['Actual disabled supplier-product relationship blocks imported orders']
        self.case('booking.import_live_supply_required',supply)
        def auth():
            self.fixture();row=self.row();role=self.success('POST','/role/add-role',dict(name='QA Order Import '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.upload(self.workbook([row])).get('code')==403 and self.count_order(row[2])==0,'Import route did not enforce forbidden403 before parsing'
                with qa_resource_grants(self.state,['/purchase-order/import-bor'],[keyword]):
                    id=self.imported(row);assert sql(self.state,'SELECT `user` FROM bor WHERE id='+literal(id)+';')==actor
                    other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Other Import');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    foreign=self.row();assert self.upload(self.workbook([foreign])).get('code')!=10000 and self.count_order(foreign[2])==0
                revoked=self.row();assert self.upload(self.workbook([revoked])).get('code')==403 and self.count_order(revoked[2])==0
            finally:self.token=admin
            return ['Actual OAuth import-only grant (no add grant), current actor/frame checks, revoked grant and foreign references enforced']
        self.case('booking.import_actual_permission_scope',auth)
        if not baseline:
            def references():
                self.fixture()
                for column in [0,5,9,12]:
                    row=self.row();row[column]=uuid.uuid4().hex
                    assert self.upload(self.workbook([row])).get('code')!=10000 and self.count_order(row[2])==0
                row=self.row()
                for column,table in [(0,'supplier'),(5,'people'),(9,'goods'),(12,'warehouse')]:row[column]=sql(self.state,'SELECT number FROM '+table+' WHERE id='+literal(row[column])+';')
                id=self.imported(row);assert sql(self.state,'SELECT goods FROM bor_info WHERE pid='+literal(id)+';')==self.goods
                return ['Unknown references reject atomically; actual supplier/person/product/warehouse codes resolve to original IDs']
            self.case('booking.import_actual_reference_codes',references)
            def formats():
                self.fixture();row=self.row()
                for data in [b'',b'bad workbook',self.workbook([]),self.workbook([row],['wrong']*22)]:assert self.upload(data).get('code')!=10000 and self.count_order(row[2])==0
                bad=list(row);bad[13]='=100+1';assert self.upload(self.workbook([bad])).get('code')!=10000 and self.count_order(row[2])==0
                second=list(row);second[0]='different';assert self.upload(self.workbook([row,second])).get('code')!=10000 and self.count_order(row[2])==0
                return ['Empty/damaged/header mismatch/formula and conflicting same-number headers reject before persistence']
            self.case('booking.import_strict_workbook_headers',formats)
            def dates():
                self.fixture()
                for column,value in [(1,'2026-02-30'),(6,'2026-02-30'),(6,'2026-11-14'),(14,'0.00001'),(15,'101'),(11,'unknown-unit')]:
                    row=self.row();row[column]=value;assert self.upload(self.workbook([row])).get('code')!=10000 and self.count_order(row[2])==0
                return ['Invalid calendar/arrival-before-order, precision and out-of-range rate reject instead of coercing values']
            self.case('booking.import_dates_precision_rates',dates)
            def limits_period():
                self.fixture();row=self.row();period=uuid.uuid4().hex
                for data in [b'x'*(5*1024*1024+1),self.workbook([row]*1001),self.workbook([row]*201)]:assert self.upload(data).get('code')!=10000 and self.count_order(row[2])==0
                try:
                    sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-15','2026-11-15',self.actor])+');')
                    assert self.upload(self.workbook([row])).get('code')!=10000 and self.count_order(row[2])==0
                finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
                return ['Actual oversized payload,1001 rows,201 same-order lines and owned closed-period fixture reject without partial documents']
            self.case('booking.import_actual_limits_closed_period',limits_period)
            def typed_multiunit():
                import datetime
                self.fixture();sql(self.state,"UPDATE goods SET unit='-1',units="+literal(json.dumps([dict(source='unit',name='box',nums=5)]))+' WHERE id='+literal(self.goods)+';');row=self.row();row[11]='box';row[14]=1
                book=load_workbook(io.BytesIO(self.workbook([row])));sheet=book.worksheets[0]
                for column,value in [(2,datetime.date(2026,11,15)),(7,datetime.date(2026,11,16))]:sheet.cell(3,column,value).number_format='yyyy-mm-dd'
                for column,value in [(16,.1),(19,.13)]:sheet.cell(3,column,value).number_format='0%'
                output=io.BytesIO();book.save(output);assert self.upload(output.getvalue()).get('code')==10000
                self.source=sql(self.state,'SELECT id FROM bor WHERE number='+literal(row[2])+';');self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+';').splitlines()
                assert sql(self.state,'SELECT CONCAT(discount,\':\',tax,\':\',tpt) FROM bor_info WHERE pid='+literal(self.source)+';')=='10.00:13.00:101.7000'
                assert self.audit([self.source]).get('code')==10000;receipt=self.create_receipt(self.receive_body(1));assert self.check([receipt]).get('code')==10000 and self.post([receipt]).get('code')==10000
                assert self.inventory()==5 and self.balance('supplier',self.supplier)==Decimal('101.7');assert self.post([receipt],0).get('code')==10000;self.unchanged()
                return ['Actual Excel date and percentage cells, configured box unit -> order -> receiving posts5 base units/payable101.7; reversal restores originals']
            self.case('booking.import_excel_cells_multiunit_lifecycle',typed_multiunit)
            def fault():
                self.fixture();first,second=self.row(),self.row();trigger='qa_ori_'+uuid.uuid4().hex[:12]
                sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bor FOR EACH ROW BEGIN IF NEW.number="+literal(second[2])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA import second order failure'; END IF; END$$\nDELIMITER ;")
                try:assert self.upload(self.workbook([first,second])).get('code')!=10000 and self.count_order(first[2])==self.count_order(second[2])==0
                finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
                assert self.upload(self.workbook([first,second])).get('code')==10000 and self.count_order(first[2])==self.count_order(second[2])==1
                self.unchanged();return ['Real second-order MySQL failure rolls back first order/details/history; identical-file retry succeeds']
            self.case('booking.import_second_order_failure_rollback',fault)
            def concurrency():
                self.fixture();row=self.row();data=self.workbook([row])
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.upload(data),range(2)))
                assert sum(r.get('code')==10000 for r in results)==1 and self.count_order(row[2])==1
                return ['Concurrent same-file imports create exactly one order and refuse replacement']
            self.case('booking.import_concurrent_duplicate_once',concurrency)
            def lifecycle():
                self.fixture();row=self.row();self.source=self.imported(row);self.lines=sql(self.state,'SELECT id FROM bor_info WHERE pid='+literal(self.source)+';').splitlines()
                assert self.audit([self.source]).get('code')==10000;receipt=self.create_receipt(self.receive_body());assert self.check([receipt]).get('code')==10000 and self.post([receipt]).get('code')==10000
                assert self.inventory()==2 and self.balance('supplier',self.supplier)==Decimal('203.4')
                assert self.post([receipt],0).get('code')==10000;self.unchanged()
                return ['Actual XLSX -> order approval -> receiving -> check/audit posts stock2/payable203.4; reverse restores stock/payable0 and cash100']
            self.case('booking.import_actual_receiving_lifecycle',lifecycle)
        self.write_report()

if __name__=='__main__':
    import sys
    OrderImportSuite(read_state()).run(len(sys.argv)>1 and sys.argv[1]=='baseline')
