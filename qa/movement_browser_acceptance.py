"""Independent MySQL assertions for actual MovementWorkspace browser actions."""
import argparse,json,datetime
from decimal import Decimal
from movement_document_acceptance import MovementSuite
from movement_document_workflow import snapshot
from acceptance import QA,read_state,sql,literal

class MovementBrowserSuite(MovementSuite):
    through_gateway=True
    def run_browser(self,stage):
        target=QA/'runtime/movement-browser-fixture.json'
        if stage=='prepare':
            self.fixture();destination=self.destination()
            sql(self.state,"UPDATE goods SET name='QA Browser Movement Goods' WHERE id="+literal(self.goods)+";UPDATE warehouse SET name='QA Browser Source' WHERE id="+literal(self.warehouse)+";UPDATE warehouse SET name='QA Browser Destination' WHERE id="+literal(destination)+';')
            f=dict(database=self.state['database'],goods=self.goods,warehouse=self.warehouse,destination=destination,actor=self.actor,account=self.account,customer=self.customer,transfer_number='QABDB'+self.goods[:20],count_number='QABPD'+self.goods[:20],candidate=snapshot())
            target.write_text(json.dumps(f),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print(json.dumps({k:v for k,v in f.items() if k in ['goods','warehouse','destination','transfer_number','count_number']},ensure_ascii=False));return
        f=json.loads(target.read_text());assert f['database']==self.state['database'] and f['candidate']==snapshot(),'Browser candidate changed'
        if stage=='sale':
            self.goods=f['goods'];self.warehouse=f['warehouse'];self.account=f['account'];self.customer=f['customer'];b=self.body();b['time']=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S');b['items'][0].update(warehouse=f['destination'],nums=2,discount=1);sale=self.post_source(b);f['sale']=sale;target.write_text(json.dumps(f),encoding='utf-8');assert self.qty(f['destination'])==2;print('Actual sale2 from browser-created transfer accepted; try browser reverse and expect dependency rejection');return
        if stage=='unwind-sale':assert self.post([f['sale']],False).get('code')==10000;print('Downstream actual sale reversed; browser may now reverse transfer');return
        def verify():
            count=stage.startswith('count-');kind='count' if count else 'swap';no=f['count_number'] if count else f['transfer_number'];table='psi_inventory_count' if count else 'swap';line='psi_inventory_count_line' if count else 'swap_info'
            identifier=sql(self.state,'SELECT id FROM '+table+' WHERE number='+literal(no)+';');assert len(identifier)==32
            row=sql(self.state,'SELECT `user`,frame FROM swap WHERE id='+literal(identifier)+';' if not count else 'SELECT creator,frame FROM psi_inventory_count WHERE id='+literal(identifier)+';').split('\t');assert row==[f['actor'],self.state['frame_id']]
            assert sql(self.state,'SELECT COUNT(*) FROM '+line+' WHERE pid='+literal(identifier)+' AND goods='+literal(f['goods'])+';')=='1'
            source=Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';'));dest=Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['destination'])+';'))
            expected={'transfer-draft':(10,0,0),'transfer-posted':(6,4,1),'transfer-blocked':(6,2,1),'transfer-reversed':(10,0,0),'count-draft':(10,0,0),'count-posted':(7,0,1),'count-reversed':(10,0,0),'count-gain-draft':(10,0,0),'count-gain-posted':(12,0,1),'count-gain-reversed':(10,0,0)}[stage]
            state=int(sql(self.state,'SELECT '+('state' if count else 'CAST(examine AS SIGNED)')+' FROM '+table+' WHERE id='+literal(identifier)+';'));assert (source,dest,state)==expected,(source,dest,state,expected)
            if count:
                qty=12 if 'gain' in stage else 7;assert sql(self.state,'SELECT book_qty,counted FROM '+line+' WHERE pid='+literal(identifier)+';')=='10.0000\t'+str(qty)+'.0000'
                assert len(self.doc(kind,identifier)['adjustments'])==expected[2]
            else:
                assert sql(self.state,'SELECT warehouse,storehouse,nums FROM swap_info WHERE pid='+literal(identifier)+';')==f['warehouse']+'\t'+f['destination']+'\t4.0000'
                if expected[2]:assert self.movement_cost(identifier,'swapOut')==self.movement_cost(identifier,'swapEnter')==8
            if stage!='transfer-blocked':
                assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100 and Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0
            return ['Actual browser '+stage+' independently verified: source'+str(source)+'/destination'+str(dest)+', state'+str(state)+', real actor/org, persisted child and actual costs; UI actions were not replaced by API calls']
        self.case('movement.browser.'+stage,verify);self.write_report();p=QA/'reports/latest.json';r=json.loads(p.read_text());r['candidate']=snapshot();(QA/('reports/movement-browser-'+stage+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','transfer-draft','transfer-posted','sale','transfer-blocked','unwind-sale','transfer-reversed','count-draft','count-posted','count-reversed','count-gain-draft','count-gain-posted','count-gain-reversed']);a=p.parse_args();MovementBrowserSuite(read_state()).run_browser(a.stage)
