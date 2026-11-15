"""Actual procurement order create, persistence, transaction and authorization gates."""
import uuid
import json
import concurrent.futures
import urllib.request
import urllib.parse
import argparse
from decimal import Decimal
from purchase_posting_acceptance import PurchasePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants
from acceptance import QA,read_state,sql,literal


class BookingDraftSuite(PurchasePostingSuite):
    def fixture(self):
        super().fixture();self.person=uuid.uuid4().hex
        sql(self.state,'INSERT INTO people(id,name,py,number,frame,sex,tel) VALUES('+','.join(literal(v) for v in [self.person,'QA Booking Person','qa','QP'+self.person[:16],self.state['frame_id'],0,'19900000000'])+');')

    def order_body(self):
        return dict(supplier=self.supplier,people=self.person,time='2026-11-15',arrival='2026-11-16',number='QABOR'+uuid.uuid4().hex[:24],total=999,actual=999,source='0',file='[]',data='QA Booking',purchaseOrderInfoDTOList=[dict(goods=self.goods,attr='',unit='unit',warehouse=self.warehouse,price=100,nums=2,discount=0,dsc=0,total=999,tax=13,tat=999,tpt=999,data='QA order line')])

    def add(self,body):return self.request('POST','/purchase-order/add',body,service='purchase')
    def create_order(self,body):
        result=self.add(body);assert result.get('code')==10000 and isinstance(result.get('data'),str),'Actual order create rejected; code='+str(result.get('code'))
        return result['data']
    def count_order(self,number):return int(sql(self.state,'SELECT COUNT(*) FROM bor WHERE number='+literal(number)+';'))
    def unchanged(self):assert self.inventory()==0 and self.balance('account',self.account)==100 and self.balance('supplier',self.supplier)==0

    def run(self):
        def ownership_amounts():
            self.fixture();body=self.order_body();identifier=self.create_order(body)
            header=json.loads(sql(self.state,"SELECT JSON_OBJECT('frame',frame,'user',`user`,'total',total,'actual',actual,'audit',examine,'state',state) FROM bor WHERE id="+literal(identifier)+';'))
            assert header['frame']==self.state['frame_id'] and header['user']==self.actor,'Order not owned by current actual organization/actor'
            assert Decimal(str(header['total']))==200 and Decimal(str(header['actual']))==226,'Order trusted fabricated derived totals'
            assert header['audit']==0 and header['state']==0
            assert sql(self.state,'SELECT CONCAT(total,\':\',tat,\':\',tpt,\':\',handle) FROM bor_info WHERE pid='+literal(identifier)+';')=='200.0000:26.0000:226.0000:0.0000'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(identifier)+' AND `user`='+literal(self.actor)+';')=='1'
            self.unchanged();return ['Actual order uses signed current owner and authoritative line/header amounts, remains unaudited/unreceived, writes creator history and leaves stock/funds/payable untouched']
        self.case('booking.draft_real_owner_and_amounts',ownership_amounts)

        def duplicate():
            self.fixture();body=self.order_body();self.create_order(body)
            assert self.add(body).get('code')!=10000 and self.count_order(body['number'])==1
            other=self.order_body()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.add(other),range(2)))
            assert sum(item.get('code')==10000 for item in results)==1 and self.count_order(other['number'])==1
            self.unchanged();return ['Repeated and simultaneous actual same-number requests persist exactly one order each']
        self.case('booking.draft_duplicate_and_concurrent_number',duplicate)

        def invalid():
            self.fixture()
            for field,value in [('goods',uuid.uuid4().hex),('warehouse',uuid.uuid4().hex),('nums',-1),('price',-1),('tax',101),('discount','0.001'),('attr','not a real attribute')]:
                body=self.order_body();body['purchaseOrderInfoDTOList'][0][field]=value
                assert self.add(body).get('code')!=10000 and self.count_order(body['number'])==0,'Invalid order data persisted: '+field
            self.unchanged();return ['Unknown product/warehouse/attribute and invalid quantities/prices/rates refuse persistence']
        self.case('booking.draft_invalid_lines_denied',invalid)

        def rollback():
            self.fixture();body=self.order_body();marker='QAFAIL'+uuid.uuid4().hex[:12]
            second=dict(body['purchaseOrderInfoDTOList'][0]);second['data']=marker;body['purchaseOrderInfoDTOList'].append(second)
            trigger='qa_bor_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bor_info FOR EACH ROW BEGIN IF NEW.data="+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA order second line failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.add(body).get('code')!=10000 and self.count_order(body['number'])==0
                assert sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE data='+literal(marker)+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            identifier=self.create_order(body)
            assert sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(identifier)+';')=='2'
            self.unchanged();return ['Actual second-line database failure rolls back header/first line/history; removing fault permits same-request retry']
        self.case('booking.draft_storage_failure_atomic_retry',rollback)

        def permissions():
            self.fixture();role=self.success('POST','/role/add-role',dict(name='QA Order '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            user_id,user,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,user);admin=self.token
            self.token=token
            try:
                body=self.order_body();assert self.add(body).get('code')==403 and self.count_order(body['number'])==0
                with qa_resource_grants(self.state,['/purchase-order/add'],[keyword]):
                    identifier=self.create_order(body)
                    assert sql(self.state,'SELECT `user` FROM bor WHERE id='+literal(identifier)+';')==user_id
                    foreign=uuid.uuid4().hex;warehouse=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA Order Other Org');"+'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [warehouse,'QA Foreign Order Warehouse','QW'+warehouse[:16],foreign])+');')
                    bad=self.order_body();bad['purchaseOrderInfoDTOList'][0]['warehouse']=warehouse
                    assert self.add(bad).get('code')!=10000 and self.count_order(bad['number'])==0
                assert self.add(self.order_body()).get('code')==403
            finally:self.token=admin
            self.unchanged();return ['Actual OAuth role requires order-create grant, keeps real creator, refuses foreign warehouse and denies same token immediately after revocation']
        self.case('booking.draft_actual_role_and_scope',permissions)

        def invalid_headers():
            self.fixture()
            for field,value in [('supplier',uuid.uuid4().hex),('people',uuid.uuid4().hex),('source',uuid.uuid4().hex),('arrival','2026-11-14'),('time','2026-02-30'),('purchaseOrderInfoDTOList',None)]:
                body=self.order_body();body[field]=value
                assert self.add(body).get('code')!=10000 and self.count_order(body['number'])==0,'Invalid order header persisted: '+field
            self.unchanged();return ['Unknown supplier/person/source, invalid calendar/arrival order and missing lines reject the whole actual request']
        self.case('booking.draft_invalid_headers_denied',invalid_headers)

        def precision():
            self.fixture();body=self.order_body();body['file']=json.dumps([dict(name='qa-order.txt',url='/qa-order.txt')])
            body['purchaseOrderInfoDTOList'][0].update(price='1.1250',nums='1.2500',discount='12.50',tax=13)
            identifier=self.create_order(body)
            assert sql(self.state,'SELECT CONCAT(price,\':\',nums,\':\',discount,\':\',dsc,\':\',total,\':\',tax,\':\',tat,\':\',tpt) FROM bor_info WHERE pid='+literal(identifier)+';')=='1.1250:1.2500:12.50:0.1758:1.2305:13.00:0.1600:1.3905'
            assert json.loads(sql(self.state,'SELECT file FROM bor WHERE id='+literal(identifier)+';'))==json.loads(body['file'])
            self.unchanged();return ['Actual four-decimal price/quantity and two-decimal percentage use authoritative rounded net/tax totals; attachment metadata retained']
        self.case('booking.draft_precision_and_metadata',precision)

        def history_fault():
            self.fixture();body=self.order_body();trigger='qa_bor_record_'+uuid.uuid4().hex[:9]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bor' AND NEW.info="+literal('新增采购订单 '+body['number'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA order record failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.add(body).get('code')!=10000 and self.count_order(body['number'])==0
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            identifier=self.create_order(body)
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(identifier)+';')=='1'
            self.unchanged();return ['Actual operation-record write failure rolls back order/lines; retry creates exactly one creator record']
        self.case('booking.draft_history_failure_atomic_retry',history_fault)

        def unsigned():
            self.fixture();body=self.order_body()
            request=urllib.request.Request('http://127.0.0.1:18023/purchase-order/add',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','user':urllib.parse.quote(json.dumps(dict(id=self.actor,frameId=self.state['frame_id'],authorities=['ROLE_ADMIN'])))})
            with self.opener.open(request,timeout=20) as response:result=json.load(response)
            assert result.get('code')==401 and self.count_order(body['number'])==0
            return ['Unsigned forged user header is refused before draft persistence']
        self.case('booking.draft_unsigned_identity_denied',unsigned)
        self.write_report()


def prepare_browser():
    suite=BookingDraftSuite(read_state());suite.fixture();nonce=uuid.uuid4().hex[:8]
    names={key:'QA Order '+key+' '+nonce for key in ['goods','warehouse','supplier','person']}
    for key,table in [('goods','goods'),('warehouse','warehouse'),('supplier','supplier'),('person','people')]:
        sql(suite.state,'UPDATE '+table+' SET name='+literal(names[key])+' WHERE id='+literal(getattr(suite,key))+';')
    fixture=dict(database=suite.state['database'],actor=suite.actor,number='QABROWSER'+uuid.uuid4().hex[:22],goods=suite.goods,warehouse=suite.warehouse,supplier=suite.supplier,person=suite.person,names=names)
    fixture['goodsNumber']=sql(suite.state,'SELECT number FROM goods WHERE id='+literal(suite.goods)+';')
    people=suite.request('GET','/personnel/query-by-list?'+urllib.parse.urlencode(dict(pageIndex=1,pageSize=20,name=names['person']),quote_via=urllib.parse.quote))
    assert people.get('code')==10000 and people.get('data',{}).get('total')==1 and people['data']['rows'][0]['id']==suite.person,'Real personnel picker query cannot find fixture'
    (QA/'runtime/booking-draft-browser.json').write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated order browser entry: '+fixture['number']+'; goods code '+fixture['goodsNumber']+'; '+json.dumps(names))


def verify_browser():
    state=read_state();fixture=json.loads((QA/'runtime/booking-draft-browser.json').read_text(encoding='utf-8'));assert fixture['database']==state['database']
    header=json.loads(sql(state,"SELECT JSON_OBJECT('id',id,'frame',frame,'user',`user`,'total',total,'actual',actual,'audit',examine,'state',state,'supplier',supplier,'people',people) FROM bor WHERE number="+literal(fixture['number'])+';'))
    assert header['frame']==state['frame_id'] and header['user']==fixture['actor'] and header['supplier']==fixture['supplier'] and header['people']==fixture['person']
    assert Decimal(str(header['total']))==200 and Decimal(str(header['actual']))==226 and header['audit']==0 and header['state']==0
    assert sql(state,'SELECT CONCAT(goods,\':\',warehouse,\':\',nums,\':\',total,\':\',tpt,\':\',handle,\':\',COALESCE(attr,\'\')) FROM bor_info WHERE pid='+literal(header['id'])+';')==fixture['goods']+':'+fixture['warehouse']+':2.0000:200.0000:226.0000:0.0000:'
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(fixture['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';'))==0
    (QA/'reports/booking-draft-browser.json').write_text(json.dumps(dict(case='booking.browser_real_draft_save',status='verified',stock_payable_unchanged=True,actual_supplier_person_product_warehouse=True,production_business_writes=0,all_system_features_accepted=False)),encoding='utf-8')
    print('PASS actual browser order persisted real references and 200/226 amounts; remains unaudited/unreceived; stock/payable unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify'],nargs='?',default='run')
    action=parser.parse_args().action
    if action=='prepare':prepare_browser()
    elif action=='verify':verify_browser()
    else:BookingDraftSuite(read_state()).run()
