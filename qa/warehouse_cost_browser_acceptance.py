"""Real posted cost report browser fixture; no claim for legacy draft creation."""
import argparse,io,json,uuid
from pathlib import Path
from decimal import Decimal
from openpyxl import load_workbook
from warehouse_cost_flow_acceptance import WarehouseCostFlowSuite
from sale_return_cost_acceptance import owned_cost_mode
from acceptance import QA,read_state,sql,literal

class WarehouseCostBrowserSuite(WarehouseCostFlowSuite):
    def run_browser(self,stage,path=None):
        target=QA/'runtime/warehouse-cost-browser-fixture.json'
        if stage=='prepare':
            with owned_cost_mode(self.state,'ma'):
                self.fixture(stock=0);self.incoming(3,2);self.incoming(2,8,'2026-11-14 11:00:00');identifier=self.document('extry');assert self.action('extry',identifier,1).get('code')==10000
                number=sql(self.state,'SELECT number FROM extry WHERE id='+literal(identifier)+';');missing=self.document('extry',quantity=1,price=100)
                sql(self.state,'UPDATE extry SET examine=1 WHERE id='+literal(missing)+';')
                missing_number=sql(self.state,'SELECT number FROM extry WHERE id='+literal(missing)+';')
                fixture=dict(database=self.state['database'],id=identifier,number=number,missing=missing,missing_number=missing_number,goods=self.goods,warehouse=self.warehouse,account=self.account,customer=self.customer,actor=self.actor)
                target.write_text(json.dumps(fixture),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
                print('Open actual QA other-outbound-report; filter '+number+'; expected actual17.6/unit4.4, never estimate400/100. Missing-journal document: '+missing_number)
            return
        def verify():
            f=json.loads(target.read_text());assert f['database']==self.state['database']
            assert Decimal(sql(self.state,'SELECT total FROM extry WHERE id='+literal(f['id'])+';'))==400
            assert Decimal(sql(self.state,'SELECT SUM(bct) FROM summary WHERE `class`='+literal(f['id'])+';'))==Decimal('17.6')
            assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(f['goods'])+';'))==1
            assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
            assert Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0
            assert sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(f['id'])+';')=='1'
            if stage=='export':
                assert path and Path(path).is_file();book=load_workbook(path,read_only=True,data_only=True)
                try:
                    values=list(book.active.values);assert len(values)==2;record=dict(zip(values[0],values[1]));assert record['单据编号']==f['number'] and Decimal(str(record['单据成本']))==Decimal('17.6')
                finally:book.close()
                return ['Actual browser-downloaded report XLSX contains actual17.6, not original estimate400; persisted estimate and stock1/cash100/AR0/history unchanged']
            if stage=='missing':
                assert sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(f['missing'])+';SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(f['missing'])+';')=='0\n0'
                return ['Independent MySQL confirms explicitly owned simulated historical approval has no cost journal/proof; browser must identify unknown actual cost without backfill or writes']
            return ['Independent MySQL verifies actual posted report17.6 with original estimate400 intact, physical1 and cash100/AR0/history unchanged; browser must show actual unit4.4']
        self.case('warehouse.cost_browser.'+stage,verify);self.write_report()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','view','export','missing']);p.add_argument('--path');a=p.parse_args();WarehouseCostBrowserSuite(read_state()).run_browser(a.stage,a.path)
