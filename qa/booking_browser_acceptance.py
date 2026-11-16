"""Independent checkpoints after real browser upload/download actions; dedicated QA only."""
import argparse,io,json,uuid,urllib.request,urllib.error,urllib.parse
from decimal import Decimal
from openpyxl import load_workbook
from booking_import_acceptance import OrderImportSuite,HEADERS
from acceptance import QA,read_state,sql,literal

FIXTURE=QA/'runtime/order-browser-import.json'
def fixture():
    state=read_state();f=json.loads(FIXTURE.read_text(encoding='utf-8'));assert f['database']==state['database'];return state,f
def report(stage):
    (QA/('reports/booking-browser-'+stage+'.json')).write_text(json.dumps(dict(case='booking.browser_'+stage,status='verified',production_business_writes=0,all_system_features_accepted=False)),encoding='utf-8')
    print('PASS actual browser checkpoint '+stage)
def prepare():
    s=OrderImportSuite(read_state());s.fixture();row=s.row();second=list(row);second[:9]=['']*9;second[14]=1
    (QA/'runtime/order-browser-valid.xlsx').write_bytes(s.workbook([row,second]));bad=list(row);bad[2]='QAORBAD'+uuid.uuid4().hex[:23];second[14]=-1
    (QA/'runtime/order-browser-invalid.xlsx').write_bytes(s.workbook([bad,second]))
    f=dict(database=s.state['database'],number=row[2],invalidNumber=bad[2],actor=s.actor,goods=s.goods,warehouse=s.warehouse,supplier=s.supplier,account=s.account)
    FIXTURE.write_text(json.dumps(f),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared disposable browser orders '+row[2]+'; invalid first, then valid upload on /purchase-booking-report')
def balances(state,f):
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
def rejected():
    state,f=fixture();assert sql(state,'SELECT COUNT(*) FROM bor WHERE number='+literal(f['invalidNumber'])+';')=='0';balances(state,f);report('invalid_upload_no_partial_order')
def saved():
    state,f=fixture();rows=sql(state,"SELECT JSON_OBJECT('id',id,'user',`user`,'frame',frame,'total',total,'actual',actual,'audit',CAST(examine AS SIGNED),'state',CAST(state AS SIGNED)) FROM bor WHERE number="+literal(f['number'])+';')
    head=json.loads(rows);assert head['user']==f['actor'] and head['frame']==state['frame_id'] and head['audit']==head['state']==0
    assert Decimal(str(head['total']))==270 and Decimal(str(head['actual']))==Decimal('305.1')
    assert sql(state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(head['id'])+' AND goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';')=='2'
    assert sql(state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(head['id'])+';')=='1'
    balances(state,f);report('valid_upload_real_owner_two_lines')
def files():
    state,f=fixture();book=load_workbook(QA/'runtime/browser-template.xlsx');assert '填写说明' in book.sheetnames and book.worksheets[0].max_row==2
    assert [book.worksheets[0].cell(2,i+1).value for i in range(22)]==HEADERS
    for name,detail in [('browser-export-simple.xlsx',False),('browser-export-detail.xlsx',True)]:
        book=load_workbook(QA/'runtime'/name);assert book.sheetnames==(['订单汇总','商品明细'] if detail else ['订单汇总'])
        rows=list(book['订单汇总'].values);assert len(rows)==3 and rows[1][3]==f['number'] and rows[1][1]=='QA Posting Supplier'
        assert Decimal(str(rows[1][4]))==270 and Decimal(str(rows[1][5]))==Decimal('305.1')
        if detail:
            rows=list(book['商品明细'].values);assert len(rows)==4
            assert all(row[3]=='QA Purchase Posting Goods' and row[7]=='QA Purchase Posting Warehouse' for row in rows[1:3])
            assert Decimal(str(rows[-1][9]))==3 and Decimal(str(rows[-1][13]))==270 and Decimal(str(rows[-1][15]))==Decimal('35.1') and Decimal(str(rows[-1][16]))==Decimal('305.1')
    saved();report('downloaded_template_and_real_workbooks')
def prepare_extra():
    state,f=fixture()
    for key,suffix,filename in [('secondNumber','B','second'),('thirdNumber','C','third')]:
        f[key]=f['number']+suffix;book=load_workbook(QA/'runtime/order-browser-valid.xlsx');book.worksheets[0].cell(3,3,f[key]);book.save(QA/('runtime/order-browser-'+filename+'.xlsx'))
    FIXTURE.write_text(json.dumps(f),encoding='utf-8');print('Prepared second/third disposable browser upload files; filter original prefix before third upload')
def multi_files():
    state,f=fixture();expected={f['number'],f['secondNumber']}
    for key in ['number','secondNumber','thirdNumber']:
        head=json.loads(sql(state,"SELECT JSON_OBJECT('id',id,'user',`user`,'frame',frame,'total',total,'actual',actual) FROM bor WHERE number="+literal(f[key])+';'))
        assert head['user']==f['actor'] and head['frame']==state['frame_id'] and Decimal(str(head['actual']))==Decimal('305.1')
        assert sql(state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(head['id'])+';')=='2'
    for name,detailed in [('browser-export-multi-simple.xlsx',False),('browser-export-multi-detail.xlsx',True)]:
        book=load_workbook(QA/'runtime'/name);rows=list(book['订单汇总'].values)
        assert len(rows)==4 and {row[3] for row in rows[1:3]}==expected
        assert Decimal(str(rows[-1][4]))==540 and Decimal(str(rows[-1][5]))==Decimal('610.2')
        if detailed:
            rows=list(book['商品明细'].values);assert len(rows)==6 and {row[0] for row in rows[1:5]}==expected
            assert Decimal(str(rows[-1][9]))==6 and Decimal(str(rows[-1][15]))==Decimal('70.2') and Decimal(str(rows[-1][16]))==Decimal('610.2')
    balances(state,f);report('multi_selected_workbooks_exclude_unchecked')
def session():
    state,f=fixture();token=json.loads((QA/'runtime/browser-session.json').read_text())['token'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for value,expected in [(token,200),('.'.join(token.split('.')[:2])+'.invalid',401),('',401)]:
        request=urllib.request.Request('http://127.0.0.1:18030/api/login/current-user',headers={'Authorization':'Bearer '+value})
        try:
            with opener.open(request,timeout=25) as response:status=response.status;data=json.load(response)
        except urllib.error.HTTPError as error:status=error.code;data=json.loads(error.read())
        assert status==expected
        if status==200:assert data['data']['id']==f['actor']
    report('qa_session_validated_against_real_backend')
def list_state(target):
    state,f=fixture();assert state['purchase_port']==18023
    id=sql(state,'SELECT id FROM bor WHERE number='+literal(f['secondNumber'])+';')
    assert sql(state,'SELECT CAST(examine AS SIGNED) FROM bor WHERE id='+literal(id)+';')==str(target)
    assert sql(state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(id)+';')==str(2 if target else 3)
    token=json.loads((QA/'runtime/browser-session.json').read_text())['token'];url='http://127.0.0.1:18023/purchase-order/list?'+urllib.parse.urlencode(dict(pageIndex=1,pageSize=10,number=f['number'],examine=target))
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+token});opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=25) as response:result=json.load(response)
    assert result['code']==10000 and result['data']['total']==(1 if target else 3)
    for row in result['data']['rows']:
        assert row['supplierName']=='QA Posting Supplier' and row['peopleName']=='QA Booking Person' and row['userName'] and row['frameName']
        assert row['documentTime']=='2026-11-15 00:00:00' and row['arrivalTime']=='2026-11-16' and row['examineName']==('已审核' if target else '未审核') and row['stateName']=='未入库'
    balances(state,f);report('list_approved_filter' if target else 'list_reversed_filter')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','prepare-extra','verify-rejected','verify-saved','verify-files','verify-session','verify-multi-files','verify-list-approved','verify-list-reversed']);action=parser.parse_args().action
    {'prepare':prepare,'prepare-extra':prepare_extra,'verify-rejected':rejected,'verify-saved':saved,'verify-files':files,'verify-session':session,'verify-multi-files':multi_files,'verify-list-approved':lambda:list_state(1),'verify-list-reversed':lambda:list_state(0)}[action]()
