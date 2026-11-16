"""Independent verification for actual browser template, multipart and stock actions."""
import argparse,io,json,uuid,datetime
from pathlib import Path
from decimal import Decimal
from openpyxl import load_workbook
from inbound_file_acceptance import InboundFileSuite
from acceptance import QA,read_state,sql,literal

class InboundFileBrowserSuite(InboundFileSuite):
    def run_browser(self,stage,path=None):
        fixture_path=QA/'runtime/inbound-file-browser-fixture.json'
        if stage=='prepare':
            self.fixture(stock=0);f=dict(database=self.state['database'],goods=self.goods,warehouse=self.warehouse,account=self.account,customer=self.customer,actor=self.actor,number='QAFB'+uuid.uuid4().hex[:24])
            sql(self.state,"UPDATE goods SET name='QA Browser File Goods' WHERE id="+literal(self.goods)+";UPDATE warehouse SET name='QA Browser File Warehouse' WHERE id="+literal(self.warehouse)+';')
            f['goodsNumber']=sql(self.state,'SELECT number FROM goods WHERE id='+literal(self.goods)+';');f['warehouseNumber']=sql(self.state,'SELECT number FROM warehouse WHERE id='+literal(self.warehouse)+';')
            fixture_path.write_text(json.dumps(f),encoding='utf-8');(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print('Open http://127.0.0.1:18030/qa-inbound.html; use actual template download, then fill with this program. Number: '+f['number']);return
        f=json.loads(fixture_path.read_text(encoding='utf-8'));assert f['database']==self.state['database']
        if stage=='fill':
            assert path and Path(path).is_file();book=load_workbook(path);assert book.sheetnames==['入库模板','填写说明'] and book.active.max_row==1
            assert '不会自动' in str(list(book['填写说明'].values))
            for qty in [1.25,2.75]:book.active.append([f['number'],'2026-11-16 12:30:45','其他入库',f['goodsNumber'],f['warehouseNumber'],'unit',qty,2.5,'','','','','QA browser file import','QA browser file detail'])
            output=QA/'runtime/inbound-browser-upload.xlsx';book.save(output);book.close();print('Filled actual browser-downloaded template: '+str(output));return
        def verify():
            identifier=sql(self.state,'SELECT id FROM entry WHERE number='+literal(f['number'])+';')
            inventory=Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))
            assert Decimal(sql(self.state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
            assert Decimal(sql(self.state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==0
            if stage=='preview':
                assert not identifier and inventory==0
                return ['Independent MySQL confirms actual browser multipart preview did not create draft or change stock/cash/AR']
            assert identifier
            rows=sql(self.state,'SELECT CAST(examine AS SIGNED),CAST(`check` AS SIGNED),CAST(cse AS SIGNED),total,`user`,frame,DATE_FORMAT(time,\'%Y-%m-%d %H:%i:%s\'),data FROM entry WHERE id='+literal(identifier)+';').split('\t')
            assert rows[1:3]==['0','3'] and Decimal(rows[3])==10 and rows[4]==f['actor'] and rows[5]==self.state['frame_id'] and rows[6]=='2026-11-16 12:30:45' and rows[7]=='QA browser file import'
            assert sql(self.state,'SELECT COUNT(*),SUM(nums),SUM(total) FROM entry_info WHERE pid='+literal(identifier)+' AND goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+' AND price=2.5;')=='2\t4.0000\t10.0000'
            if stage=='export':
                assert path and Path(path).is_file();book=load_workbook(path,read_only=True,data_only=False)
                try:
                    values=list(book.active.values);records=[dict(zip(values[0],row)) for row in values[1:]]
                    assert len(records)==2 and all(r['单据编号']==f['number'] and r['商品名称']=='QA Browser File Goods' and r['入库仓库']=='QA Browser File Warehouse' and r['费用状态']=='无需结算' for r in records)
                    assert sum(Decimal(str(r['数量'])) for r in records)==4 and sum(Decimal(str(r['成本金额'])) for r in records)==10
                finally:book.close()
                return ['Actual browser-downloaded detail XLSX independently opened: same imported document/two rows, actual goods/warehouse names, quantities4/cost10, cash/AR unchanged']
            posted=stage=='posted';assert rows[0]==('1' if posted else '0') and inventory==(4 if posted else 0)
            assert int(sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';'))==(1 if posted else 0)
            assert int(sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(identifier)+';'))==(2 if posted else 0)
            assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+' AND `user`='+literal(f['actor'])+';'))=={'draft':1,'posted':2,'reversed':3}[stage]
            f['id']=identifier;fixture_path.write_text(json.dumps(f),encoding='utf-8')
            return ['Independent MySQL verifies actual browser '+stage+': one signed draft/two complete lines/cost10, stock'+str(inventory)+', original proof/journals and exact history; account100/customer0']
        self.case('inbound.file_browser.'+stage,verify);self.write_report()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','fill','preview','draft','posted','reversed','export']);p.add_argument('--path');a=p.parse_args();InboundFileBrowserSuite(read_state()).run_browser(a.stage,a.path)
