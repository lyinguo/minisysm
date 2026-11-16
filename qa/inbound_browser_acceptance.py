"""Prepare real OAuth/catalog data, then independently verify manual browser actions.

The UI must be operated through the actual OtherInbound component. This program
does not click the UI or post documents on behalf of browser verification.
"""
import argparse,json,uuid
from decimal import Decimal
from warehouse_acceptance import WarehouseSuite
from acceptance import QA,read_state,sql,literal

class InboundBrowserSuite(WarehouseSuite):
    def run_browser(self,stage):
        path=QA/'runtime/inbound-browser-fixture.json'
        if stage=='prepare':
            number='QABROWSER'+uuid.uuid4().hex[:16]
            sql(self.state,"UPDATE warehouse SET name='QA Browser Inbound Warehouse' WHERE id="+literal(self.warehouse)+';')
            fixture=dict(database=self.state['database'],goods=self.goods,warehouse=self.warehouse,actor=self.actor,number=number)
            path.write_text(json.dumps(fixture),encoding='utf-8')
            (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print('Open http://127.0.0.1:18030/qa-inbound.html; select QG'+self.goods[:16])
            print('Number: '+number+'; warehouse QA Browser Inbound Warehouse; quantity3, price2; remark QA browser inbound actual')
            return
        def verify():
            f=json.loads(path.read_text(encoding='utf-8'));assert f['database']==self.state['database']
            identifier=sql(self.state,'SELECT id FROM entry WHERE number='+literal(f['number'])+';')
            assert identifier,'The browser must actually save this document before verification'
            f['id']=identifier;path.write_text(json.dumps(f),encoding='utf-8')
            rows=sql(self.state,'SELECT CAST(examine AS SIGNED),CAST(`check` AS SIGNED),CAST(cse AS SIGNED),CAST(type AS SIGNED),total,data,`user`,frame FROM entry WHERE id='+literal(identifier)+';').split('\t')
            expected={'draft':(0,0,0),'checked':(0,1,0),'posted':(1,1,3),'reversed':(0,1,0),'unchecked':(0,0,0),'edited':(0,0,0)}[stage]
            assert (int(rows[0]),int(rows[1]))==expected[:2] and rows[2:4]==['3','0']
            assert Decimal(rows[4])==6 and rows[5]=='QA browser inbound actual' and rows[6]==f['actor'] and rows[7]==self.state['frame_id']
            assert sql(self.state,'SELECT COUNT(*) FROM entry_info WHERE pid='+literal(identifier)+' AND goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+' AND nums=3 AND price=2;')=='1'
            assert Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==expected[2]
            assert int(sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';'))==expected[0]
            assert int(sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(identifier)+';'))==expected[0]
            histories={'draft':1,'checked':2,'posted':3,'reversed':4,'unchecked':5,'edited':6}[stage]
            assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+' AND `user`='+literal(f['actor'])+';'))==histories
            return ['Independent MySQL verifies actual browser '+stage+': complete3x2=6 draft, signed actor/org, numeric states, stock'+str(expected[2])+', proof/movement'+str(expected[0])+', history'+str(histories)]
        self.case('inbound.browser.'+stage,verify);self.write_report()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','draft','checked','posted','reversed','unchecked','edited']);args=parser.parse_args()
    InboundBrowserSuite(read_state()).run_browser(args.stage)
