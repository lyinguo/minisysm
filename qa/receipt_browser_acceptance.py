"""Real receipt browser fixture and independent persistent business verification."""
import argparse,json,io,hashlib,uuid
from decimal import Decimal
from receipt_settlement_acceptance import ReceiptSettlementSuite
from acceptance import read_state,sql,literal,QA

class ReceiptBrowserSuite(ReceiptSettlementSuite):
    def attached(self):
        fixture=json.loads((QA/'runtime/receipt-browser-fixture.json').read_text(encoding='utf-8'))
        assert fixture['database']==self.state['database']
        for key in ['goods','warehouse','customer','account','actor']:setattr(self,key,fixture[key])
        return fixture
    def run_browser(self,action,download_path=None):
        if action=='prepare':
            fixture=self.prepare_trade();document=self.document_for_browser(fixture['receipt'])
            fixture['initial_version']=document['version'];fixture['detail_ids']=[row['id'] for row in document['items']]
            fixture.update(import_number='QARB'+uuid.uuid4().hex[:24],manual_number='QARM'+uuid.uuid4().hex[:24],manual_time='2026-11-16 15:00:00',manual_amount='3.1256')
            fixture['customer_number']=sql(self.state,'SELECT number FROM customer WHERE id='+literal(fixture['customer'])+';')
            fixture['account_number']=sql(self.state,'SELECT number FROM account WHERE id='+literal(fixture['account'])+';')
            (QA/'runtime/receipt-browser-fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
            (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=self.token)),encoding='utf-8')
            print('QA receipt: http://127.0.0.1:18030/qa-receipt.html?receipt='+fixture['receipt'])
            print('Use remark: QA browser receipt revised; amount151, source239 minus return88; expected cash1171 ->1322 ->1171, customer151 ->0 ->151, stock6 unchanged')
            print('Template import: number='+fixture['import_number']+'; time=2026-11-16 14:30:00; customer code='+fixture['customer_number']+'; account code='+fixture['account_number']+'; two rows10 and15')
            print('Manual draft: number='+fixture['manual_number']+'; time='+fixture['manual_time']+'; same customer/account codes; amount='+fixture['manual_amount']+'; remark=QA browser manual receipt')
            return
        if action=='verify-export':
            def exported():
                from pathlib import Path
                from openpyxl import load_workbook
                fixture=self.attached();self.balances(fixture,1171,151)
                assert download_path and Path(download_path).is_file(),'Pass --download-path with the actual browser-downloaded detail workbook'
                raw=Path(download_path).read_bytes();workbook=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
                try:values=list(workbook.active.values)
                finally:workbook.close()
                assert len(values)==3
                rows=[dict(zip(values[0],row)) for row in values[1:]]
                assert all(row['收款单编号']==fixture['import_number'] and row['客户']=='QA Sale Customer' and row['结算账户']=='QA Purchase Posting Account' and row['收款日期']=='2026-11-16 14:30:00' for row in rows)
                assert sorted(Decimal(str(row['结算金额'])) for row in rows)==[Decimal(10),Decimal(15)]
                (QA/'reports/receipt-browser-export.xlsx').write_bytes(raw)
                fixture['export_sha256']=hashlib.sha256(raw).hexdigest();(QA/'runtime/receipt-browser-fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
                return ['Independent openpyxl parses actual browser-downloaded filtered workbook: exactly two10/15 rows from requested25 receipt, real parent/customer/account names and full14:30 timestamp; stock/cash/AR unchanged']
            self.case('receipt.browser.'+action,exported);self.write_report();return
        if action=='verify-manual':
            def manual():
                fixture=self.attached();self.balances(fixture,1171,151)
                assert sql(self.state,'SELECT COUNT(*) FROM imy WHERE number='+literal(fixture['manual_number'])+';')=='1'
                identifier=sql(self.state,'SELECT id FROM imy WHERE number='+literal(fixture['manual_number'])+';');document=self.document_for_browser(identifier);head=document['header']
                assert head['customer']==fixture['customer'] and head['user']==fixture['actor'] and head['frame']==self.state['frame_id']
                assert head['data']=='QA browser manual receipt' and head['timeText']==fixture['manual_time']
                assert Decimal(str(head['total']))==Decimal(fixture['manual_amount']) and head['examine']==head['nucleus']==0
                assert len(document['items'])==1 and document['items'][0]['account']==fixture['account'] and Decimal(str(document['items'][0]['money']))==Decimal(fixture['manual_amount'])
                assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+' AND `user`='+literal(fixture['actor'])+';')=='1'
                assert sql(self.state,'SELECT COUNT(*) FROM psi_receipt_posting WHERE receipt_id='+literal(identifier)+';')=='0'
                fixture['manual_id']=identifier;(QA/'runtime/receipt-browser-fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
                return ['Independent MySQL confirms actual manual browser customer/account search and creation persisted one3.1256 draft/detail, exact15:00 timestamp, actor/org and one history, no cash/AR/stock effect']
            self.case('receipt.browser.'+action,manual);self.write_report();return
        if action in ['verify-import-preview','verify-imported']:
            def imported():
                fixture=self.attached();self.balances(fixture,1171,151)
                count=sql(self.state,'SELECT COUNT(*) FROM imy WHERE number='+literal(fixture['import_number'])+';')
                if action=='verify-import-preview':
                    assert count=='0'
                    return ['Independent MySQL confirms actual browser multipart upload is preview-only: receipt number absent, stock6/cash1171/customer151/supplier0 unchanged']
                assert count=='1';identifier=sql(self.state,'SELECT id FROM imy WHERE number='+literal(fixture['import_number'])+';')
                document=self.document_for_browser(identifier);head=document['header']
                assert head['customer']==fixture['customer'] and head['user']==fixture['actor'] and head['frame']==self.state['frame_id']
                assert head['total']==25 and head['examine']==head['nucleus']==0 and head['timeText']=='2026-11-16 14:30:00'
                assert len(document['items'])==2 and sorted(Decimal(str(line['money'])) for line in document['items'])==[Decimal(10),Decimal(15)]
                assert all(line['pid']==identifier and line['account']==fixture['account'] for line in document['items'])
                assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(identifier)+' AND `user`='+literal(fixture['actor'])+';')=='1'
                assert sql(self.state,'SELECT COUNT(*) FROM psi_receipt_posting WHERE receipt_id='+literal(identifier)+';')=='0'
                fixture['import_id']=identifier;(QA/'runtime/receipt-browser-fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
                return ['Independent MySQL confirms actual browser file confirmation saves exactly one complete25 draft/two real10+15 rows, current actor/org, full14:30 timestamp, one history and no posting/cash/AR/stock effect']
            self.case('receipt.browser.'+action,imported);self.write_report();return
        def verify():
            fixture=self.attached();document=self.document_for_browser(fixture['receipt']);head=document['header']
            assert head['data']=='QA browser receipt revised' and head['timeText']=='2026-11-16 14:00:00'
            assert head['user']==fixture['actor'] and [row['id'] for row in document['items']]==fixture['detail_ids']
            assert Decimal(str(head['total']))==151
            forward=action=='verify-posted';self.balances(fixture,1322 if forward else 1171,0 if forward else 151)
            assert head['examine']==(1 if forward else 0) and head['nucleus']==(2 if forward else 0)
            assert document['version']!=fixture['initial_version']
            count=int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(fixture['receipt'])+' AND `user`='+literal(fixture['actor'])+';'))
            expected={'verify-edited':2,'verify-posted':3,'verify-reversed':4}[action];assert count==expected,(count,expected)
            assert sql(self.state,'SELECT COUNT(*) FROM psi_receipt_posting WHERE receipt_id='+literal(fixture['receipt'])+';')==('1' if forward else '0')
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='imy' AND `class`="+literal(fixture['receipt'])+';')==('1' if forward else '0')
            for table,identifier in [('sell',fixture['sale']),('sre',fixture['sales_return'])]:
                assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM '+table+' WHERE id='+literal(identifier)+';')==('2' if forward else '1')
            return ['Independent MySQL confirms actual browser '+action+': stable receipt/detail identity, exact full timestamp/actor/151, stock6 and both party balances, own account journal/proof and original sale/return states, expected actor history count']
        self.case('receipt.browser.'+action,verify);self.write_report()
    def document_for_browser(self,identifier):
        result=self.request('GET','/fund/receipt/document/'+identifier,service='fund');assert result.get('code')==10000,str(result);return result['data']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','verify-edited','verify-posted','verify-reversed','verify-import-preview','verify-imported','verify-manual','verify-export']);parser.add_argument('--download-path');args=parser.parse_args()
    ReceiptBrowserSuite(read_state()).run_browser(args.action,args.download_path)
