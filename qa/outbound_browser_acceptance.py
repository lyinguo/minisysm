"""Independent verification of real browser actions on OtherOutbound.vue."""
import argparse,json,uuid
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook
from outbound_document_acceptance import OutboundDocumentSuite
from outbound_document_workflow import snapshot
from acceptance import QA,read_state,sql,literal

class OutboundBrowserSuite(OutboundDocumentSuite):
    through_gateway=True
    def write_report(self):
        super().write_report()
        path=QA/'reports/latest.json';report=json.loads(path.read_text(encoding='utf-8'));report['candidate']=snapshot();path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def run_browser(self,stage,path=None):
        if stage.startswith('metadata-'):
            return self.metadata_browser(stage)
        target=QA/'runtime/outbound-browser-fixture.json'
        if stage=='prepare':
            self.fixture();sql(self.state,"UPDATE warehouse SET name='QA Browser Outbound Warehouse' WHERE id="+literal(self.warehouse)+";UPDATE goods SET name='QA Browser Outbound Goods' WHERE id="+literal(self.goods)+';')
            fixture=dict(database=self.state['database'],goods=self.goods,warehouse=self.warehouse,account=self.account,customer=self.customer,actor=self.actor,number='QAOUTB'+uuid.uuid4().hex[:20],candidate=snapshot())
            target.write_text(json.dumps(fixture),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print('Actual inbound established stock10; open18030/qa-outbound.html, choose QG'+self.goods[:16]+' and QA Browser Outbound Warehouse; quantity3 price2; number='+fixture['number']);return
        def verify():
            f=json.loads(target.read_text());assert f['database']==self.state['database']
            assert f['candidate']==snapshot(),'Actual browser candidate changed since setup'
            identifier=sql(self.state,'SELECT id FROM extry WHERE number='+literal(f['number'])+';')
            if stage=='deleted':
                assert not identifier and f.get('id');identifier=f['id']
                assert sql(self.state,'SELECT COUNT(*) FROM extry_info WHERE pid='+literal(identifier)+';')=='0'
            else:
                assert identifier,'The browser must save this actual document first';f['id']=identifier;target.write_text(json.dumps(f),encoding='utf-8')
                expected={'draft':(0,0,3),'checked':(0,1,3),'posted':(1,1,3),'reversed':(0,1,3),'unchecked':(0,0,3),'edited':(0,0,4),'export':(1,1,3)}[stage]
                raw=sql(self.state,'SELECT CAST(examine AS SIGNED),CAST(`check` AS SIGNED),CAST(cse AS SIGNED),total,`user`,frame FROM extry WHERE id='+literal(identifier)+';').split('\t')
                assert tuple(map(int,raw[:2]))==expected[:2] and int(raw[2])==3 and Decimal(raw[3])==expected[2]*2 and raw[4]==f['actor'] and raw[5]==self.state['frame_id']
                assert sql(self.state,'SELECT (`file` IS NULL AND more IS NULL AND logistics IS NULL) FROM extry WHERE id='+literal(identifier)+';')=='1','Untouched missing metadata must remain NULL through actual UI save/edit'
                assert sql(self.state,'SELECT COUNT(*) FROM extry_info WHERE pid='+literal(identifier)+' AND goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+' AND nums='+str(expected[2])+' AND price=2;')=='1'
            stock=Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'));assert stock==(7 if stage in ['posted','export'] else 10)
            assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100 and Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0
            history={'draft':1,'checked':2,'posted':3,'export':3,'reversed':4,'unchecked':5,'edited':6,'deleted':7}[stage]
            assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+' AND `user`='+literal(f['actor'])+';'))==history
            assert sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';')==('1' if stage in ['posted','export'] else '0')
            if stage=='export':
                assert path and Path(path).is_file();book=load_workbook(path,read_only=True,data_only=True)
                try:
                    rows=list(book.active.values);record=dict(zip(rows[0],rows[1]));assert record['单据编号']==f['number'] and record['成本合计']==6 and record['数量']==3 and record['成本金额']==6
                finally:book.close()
            return ['Independent MySQL/file validation of actual browser '+stage+': stock'+str(stock)+', cash100/AR0, actual actor/org and history'+str(history)+'; not an API substitute for UI actions']
        self.case('outbound.browser.'+stage,verify);self.write_report()

    def metadata_browser(self,stage):
        target=QA/'runtime/outbound-browser-metadata-fixture.json'
        if stage=='metadata-prepare':
            self.fixture();body=self.outbound(2);body.update(file='legacy-file-reference.txt',more='legacy plain extension',logistics='legacy shipment')
            identifier,_=self.create_out(body)
            fixture=dict(database=self.state['database'],id=identifier,number=body['number'],goods=self.goods,warehouse=self.warehouse,account=self.account,customer=self.customer,actor=self.actor,candidate=snapshot())
            target.write_text(json.dumps(fixture),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print('Open actual QA workbench /qa-outbound.html?id='+identifier+'; edit quantity2->3 and save without changing any opaque metadata');return
        def verify():
            f=json.loads(target.read_text());assert f['database']==self.state['database']
            assert f['candidate']==snapshot(),'Actual metadata browser candidate changed since setup'
            values=sql(self.state,'SELECT file,more,logistics,`user`,frame,total FROM extry WHERE id='+literal(f['id'])+';').split('\t')
            assert values[:3]==['legacy-file-reference.txt','legacy plain extension','legacy shipment'] and values[3]==f['actor'] and values[4]==self.state['frame_id'] and Decimal(values[5])==6
            assert sql(self.state,'SELECT COUNT(*) FROM extry_info WHERE pid='+literal(f['id'])+' AND goods='+literal(f['goods'])+' AND nums=3;')=='1'
            assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(f['goods'])+';'))==10 and Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100 and Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0
            assert sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(f['id'])+' AND `user`='+literal(f['actor'])+';')=='2'
            return ['Actual browser opens legacy plain-string attachment/extension/shipment metadata, edits quantity2->3, saves amount6 with exact original strings/creator/org and stock10/cash100/AR0 unchanged; no JSON parsing or silent metadata normalization']
        self.case('outbound.browser.metadata_plain_strings_preserved',verify);self.write_report()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','draft','checked','posted','reversed','unchecked','edited','deleted','export','metadata-prepare','metadata-edited']);p.add_argument('--path');a=p.parse_args();OutboundBrowserSuite(read_state()).run_browser(a.stage,a.path)
