"""Real supplier catalog, atomic split orders, role and persistence acceptance."""
import uuid,json,concurrent.futures,argparse
from booking_draft_acceptance import BookingDraftSuite
from acceptance import read_state,sql,literal,QA
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class SplitSuite(BookingDraftSuite):
    def setup(self):
        self.fixture();self.other=uuid.uuid4().hex
        sql(self.state,'INSERT INTO supplier(id,name,py,number,frame,`user`,category,rate,balance,more) VALUES('+','.join(literal(v) for v in [self.other,'QA Split Second','qa','QS'+self.other[:16],self.state['frame_id'],self.actor,'0',0,0,'{}'])+');')
        assert self.link(self.other).get('code')==10000
    def link(self,supplier,enabled=True):return self.request('POST','/purchase-order/supply',dict(goods=self.goods,supplier=supplier,enabled=enabled),service='purchase')
    def body(self):
        row=self.order_body()['purchaseOrderInfoDTOList'][0]
        return dict(number='QASPLIT'+uuid.uuid4().hex[:18],time='2026-11-15',arrival='2026-11-16',rows=[dict(row,supplier=self.supplier),dict(row,supplier=self.other),dict(row,supplier=self.supplier)])
    def split(self,body):return self.request('POST','/purchase-order/split',body,service='purchase')
    def count(self,body):return int(sql(self.state,'SELECT COUNT(*) FROM bor WHERE number LIKE '+literal(body['number']+'-%')+';'))
    def run(self):
        def ordinary():
            self.setup();body=self.body();result=self.split(body);assert result.get('code')==10000 and len(result['data'])==2
            for index,(supplier,lines,total) in enumerate([(self.supplier,2,452),(self.other,1,226)]):
                item=result['data'][index];assert item['supplier']==supplier and item['lineCount']==lines and item['number']==body['number']+'-%03d'%(index+1)
                assert sql(self.state,'SELECT CONCAT(supplier,\':\',actual,\':\',examine,\':\',state,\':\',`user`,\':\',frame) FROM bor WHERE id='+literal(item['id'])+';')==supplier+':%.4f:0:0:'%total+self.actor+':'+self.state['frame_id']
                assert sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(item['id'])+';')==str(lines)
            self.unchanged();return ['Three actual rows/two suppliers persist two independent drafts with correct grouping, references, amounts and no posting']
        self.case('split.real_grouping_persistence',ordinary)
        def disabled():
            self.setup();body=self.body();assert self.link(self.other,False).get('code')==10000
            assert self.split(body).get('code')!=10000 and self.count(body)==0
            direct=self.order_body();direct['supplier']=self.other;assert self.add(direct).get('code')!=10000 and self.count_order(direct['number'])==0
            assert self.link(self.other).get('code')==10000 and self.split(body).get('code')==10000
            self.unchanged();return ['Disabled relationship blocks split and legacy add; no partial first supplier order; re-enable permits retry']
        self.case('split.disabled_supply_atomic_retry',disabled)
        def unlinked():
            self.setup();body=self.body();body['rows'][1]['goods']=uuid.uuid4().hex
            assert self.split(body).get('code')!=10000 and self.count(body)==0
            sql(self.state,'DELETE FROM psi_goods_supplier WHERE frame='+literal(self.state['frame_id'])+' AND goods='+literal(self.goods)+' AND supplier='+literal(self.other)+';')
            body=self.body();assert self.split(body).get('code')!=10000 and self.count(body)==0
            return ['Unknown product and unlinked supplier/product combination refuse the entire batch']
        self.case('split.unlinked_supply_denied',unlinked)
        def fault():
            self.setup();body=self.body();trigger='qa_split_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON bor FOR EACH ROW BEGIN IF NEW.supplier="+literal(self.other)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA second split order failure'; END IF; END$$\nDELIMITER ;")
            try:assert self.split(body).get('code')!=10000 and self.count(body)==0
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.split(body).get('code')==10000 and self.count(body)==2;self.unchanged()
            return ['Actual second-order MySQL failure rolls back all earlier headers/lines/history and same payload retries successfully']
        self.case('split.second_order_storage_rollback',fault)
        def concurrent_requests():
            self.setup();body=self.body()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.split(body),range(2)))
            assert sum(r.get('code')==10000 for r in results)==1 and self.count(body)==2
            assert self.split(body).get('code')!=10000 and self.count(body)==2
            self.unchanged();return ['Two actual same-batch concurrent requests persist exactly one complete group, repeat creates no extra drafts']
        self.case('split.concurrent_duplicate_atomic',concurrent_requests)
        def auth():
            self.setup();role=self.success('POST','/role/add-role',dict(name='QA Split '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
            _,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.link(self.other).get('code')==403 and self.split(self.body()).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/add'],[keyword]):
                    assert self.split(self.body()).get('code')==10000 and self.link(self.other).get('code')==403
                with qa_resource_grants(self.state,['/purchase-order/supply/manage'],[keyword]):assert self.link(self.other).get('code')==10000
                assert self.link(self.other).get('code')==403
            finally:self.token=admin
            return ['Actual OAuth user needs separate catalog-management grant; order create alone cannot modify catalog; revocation is immediate']
        self.case('split.actual_role_catalog_separation',auth)
        def scope():
            self.setup();other_frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other_frame)+",'0','QA Split Foreign');"+'UPDATE supplier SET frame='+literal(other_frame)+' WHERE id='+literal(self.other)+';')
            assert self.link(self.other).get('code')!=10000
            rows=self.request('GET','/purchase-order/supply?goods='+self.goods,service='purchase');assert rows.get('code')==10000 and self.other not in [r['id'] for r in rows['data']]
            body=self.body();assert self.split(body).get('code')!=10000 and self.count(body)==0
            return ['Foreign-organization supplier cannot be linked, selected or persisted even if an old catalog row exists']
        self.case('split.supplier_organization_scope',scope)
        def invalid():
            self.setup()
            for field,value in [('rows',[]),('number','X'*29),('arrival','2026-11-14'),('time','2026-02-30')]:
                body=self.body();body[field]=value;assert self.split(body).get('code')!=10000 and self.count(body)==0
            body=self.body();body['rows'][1]['supplier']='';assert self.split(body).get('code')!=10000 and self.count(body)==0
            return ['Missing row supplier, empty rows, invalid numbering and invalid dates reject without persistence']
        self.case('split.invalid_entry_atomic',invalid)
        self.write_report()

def prepare_browser():
    suite=SplitSuite(read_state());suite.setup();nonce=uuid.uuid4().hex[:8];second=uuid.uuid4().hex
    sql(suite.state,'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES('+','.join(literal(v) for v in [second,'QA Split B '+nonce,'qa','QGS'+nonce,'0','unit',75,90,0,0,'{}'])+');')
    sql(suite.state,'UPDATE goods SET name='+literal('QA Split A '+nonce)+' WHERE id='+literal(suite.goods)+';'+'UPDATE supplier SET name='+literal('QA Supply A '+nonce)+' WHERE id='+literal(suite.supplier)+';'+'UPDATE supplier SET name='+literal('QA Supply B '+nonce)+' WHERE id='+literal(suite.other)+';')
    sql(suite.state,'UPDATE warehouse SET name='+literal('QA Split Warehouse '+nonce)+' WHERE id='+literal(suite.warehouse)+';')
    fixture=dict(database=suite.state['database'],actor=suite.actor,number='QABATCH'+uuid.uuid4().hex[:18],goods=[suite.goods,second],suppliers=[suite.supplier,suite.other],warehouse=suite.warehouse,nonce=nonce)
    (QA/'runtime/split-browser.json').write_text(json.dumps(fixture),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared actual split browser fixture '+json.dumps(dict(number=fixture['number'],nonce=nonce,secondGoodsCode='QGS'+nonce,firstGoodsCode=sql(suite.state,'SELECT number FROM goods WHERE id='+literal(suite.goods)+';'),warehouse=sql(suite.state,'SELECT name FROM warehouse WHERE id='+literal(suite.warehouse)+';'))))

def verify_browser():
    state=read_state();f=json.loads((QA/'runtime/split-browser.json').read_text(encoding='utf-8'));assert f['database']==state['database']
    for index,(goods,supplier,total) in enumerate(zip(f['goods'],f['suppliers'],[100,75])):
        number=f['number']+'-%03d'%(index+1)
        assert sql(state,'SELECT CONCAT(supplier,\':\',total,\':\',actual,\':\',examine,\':\',state,\':\',`user`,\':\',frame) FROM bor WHERE number='+literal(number)+';')==supplier+':%.4f:%.4f:0:0:'%(total,total)+f['actor']+':'+state['frame_id']
        assert sql(state,'SELECT CONCAT(i.goods,\':\',i.warehouse,\':\',i.nums) FROM bor_info i JOIN bor b ON b.id=i.pid WHERE b.number='+literal(number)+';')==goods+':'+f['warehouse']+':1.0000'
        assert sql(state,'SELECT COUNT(*) FROM room WHERE goods='+literal(goods)+';')=='0'
        assert sql(state,'SELECT balance FROM supplier WHERE id='+literal(supplier)+';')=='0.0000'
        assert sql(state,'SELECT enabled FROM psi_goods_supplier WHERE frame='+literal(state['frame_id'])+' AND goods='+literal(goods)+' AND supplier='+literal(supplier)+';')=='1'
    (QA/'reports/split-browser.json').write_text(json.dumps(dict(case='split.browser_catalog_and_two_orders',status='verified',production_business_writes=0,all_system_features_accepted=False)),encoding='utf-8')
    print('PASS browser actual supply link, per-row different suppliers, two 100/75 drafts, true references, no stock or payable change')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify'],nargs='?',default='run');action=parser.parse_args().action
    if action=='prepare':prepare_browser()
    elif action=='verify':verify_browser()
    else:SplitSuite(read_state()).run()
