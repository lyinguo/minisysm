"""Prepare an actual isolated trade fixture; independently verify browser mutations."""
import argparse,json,datetime
from decimal import Decimal
from trade_flow_acceptance import TradeFlowSuite
from acceptance import read_state,sql,literal,QA

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','edited','posted','reversed','fill-template','imported','exported']);parser.add_argument('--download')
    args=parser.parse_args();action=args.action;state=read_state();path=QA/'runtime/payment-browser-fixture.json'
    if action=='prepare':
        suite=TradeFlowSuite(state);suite.run('prepare')
        f=json.loads((QA/'runtime/trade-flow-fixture.json').read_text(encoding='utf-8'))
        f['lines']=sql(state,'SELECT id FROM omy_info WHERE pid='+literal(f['payment'])+' ORDER BY id;').splitlines()
        f['number']=sql(state,'SELECT number FROM omy WHERE id='+literal(f['payment'])+';')
        path.write_text(json.dumps(f),encoding='utf-8')
        (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
        print('BROWSER URL http://127.0.0.1:18030/qa-payment.html?payment='+f['payment'])
        print('PAYMENT NUMBER '+f['number'])
        print('EDIT REMARK QA browser corrected payment')
        return
    f=json.loads(path.read_text(encoding='utf-8'));assert f['database']==state['database']
    if action=='fill-template':
        import uuid
        from openpyxl import load_workbook
        assert args.download,'Downloaded real template path required'
        book=load_workbook(args.download);assert book.sheetnames==['付款模板','填写说明']
        sheet=book['付款模板'];assert sheet.max_row==1
        assert [cell.value for cell in sheet[1]]==['付款单编号','付款日期','供应商编号','结算账户编号','付款金额','结算号','单据备注','明细备注']
        number='QABIMP'+uuid.uuid4().hex[:22]
        supplier=sql(state,'SELECT number FROM supplier WHERE id='+literal(f['supplier'])+';');account=sql(state,'SELECT number FROM account WHERE id='+literal(f['account'])+';')
        for index,money in enumerate([10,15]):sheet.append([number,'2026-11-16',supplier,account,money,'QA import bank','QA browser imported draft','QA imported line'+str(index+1)])
        target=QA/'runtime/payment-browser-filled.xlsx';book.save(target);book.close()
        f.update(import_number=number,import_path=str(target));path.write_text(json.dumps(f),encoding='utf-8')
        print('FILLED ACTUAL DOWNLOADED TEMPLATE '+str(target));print('IMPORT NUMBER '+number);return
    payment=f['payment'];posted=action=='posted'
    assert sql(state,'SELECT data FROM omy WHERE id='+literal(payment)+';')=='QA browser corrected payment'
    assert sql(state,'SELECT id FROM omy_info WHERE pid='+literal(payment)+' ORDER BY id;').splitlines()==f['lines']
    assert Decimal(sql(state,'SELECT total FROM omy WHERE id='+literal(payment)+';'))==954
    assert sql(state,'SELECT CAST(examine AS SIGNED) FROM omy WHERE id='+literal(payment)+';')==('1' if posted else '0')
    assert sql(state,'SELECT CAST(nucleus AS SIGNED) FROM omy WHERE id='+literal(payment)+';')==('2' if posted else '0')
    assert Decimal(sql(state,'SELECT SUM(nums) FROM room WHERE goods='+literal(f['goods'])+' AND warehouse='+literal(f['warehouse'])+';'))==6
    assert Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==(1171 if posted else 2125)
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==(0 if posted else 954)
    assert Decimal(sql(state,'SELECT balance FROM customer WHERE id='+literal(f['customer'])+';'))==151
    assert sql(state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(payment)+';')==('1' if posted else '0')
    assert sql(state,'SELECT COUNT(*) FROM psi_payment_posting WHERE payment_id='+literal(payment)+';')==('1' if posted else '0')
    for source in f['receipts']:assert sql(state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(source)+';')==('2' if posted else '0')
    assert sql(state,'SELECT CAST(nucleus AS SIGNED) FROM bre WHERE id='+literal(f['purchase_return'])+';')==('2' if posted else '1')
    expected={'edited':2,'posted':3,'reversed':4,'imported':4,'exported':4}[action]
    assert int(sql(state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(payment)+' AND `user`='+literal(f['actor'])+';'))==expected
    if posted:
        assert Decimal(sql(state,'SELECT SUM(money) FROM omy_bill WHERE pid='+literal(payment)+';'))==954
        assert Decimal(sql(state,"SELECT SUM(money) FROM buy_bill WHERE type='omy' AND source="+literal(payment)+';'))==1130
        assert Decimal(sql(state,"SELECT SUM(money) FROM bre_bill WHERE type='omy' AND source="+literal(payment)+';'))==176
    if action in ['imported','exported']:
        identifier=sql(state,'SELECT id FROM omy WHERE number='+literal(f['import_number'])+';');assert identifier and len(identifier.splitlines())==1
        assert sql(state,'SELECT CAST(examine AS SIGNED) FROM omy WHERE id='+literal(identifier)+';')=='0'
        assert Decimal(sql(state,'SELECT total FROM omy WHERE id='+literal(identifier)+';'))==25
        assert sql(state,'SELECT `user` FROM omy WHERE id='+literal(identifier)+';')==f['actor']
        assert sql(state,'SELECT frame FROM omy WHERE id='+literal(identifier)+';')==state['frame_id']
        assert sql(state,'SELECT COUNT(*) FROM omy_info WHERE pid='+literal(identifier)+' AND account='+literal(f['account'])+';')=='2'
        assert Decimal(sql(state,'SELECT SUM(money) FROM omy_info WHERE pid='+literal(identifier)+';'))==25
        assert sql(state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(identifier)+';')=='0'
        assert sql(state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(identifier)+';')=='0'
        f['import_id']=identifier;path.write_text(json.dumps(f),encoding='utf-8')
    if action=='exported':
        from openpyxl import load_workbook
        assert args.download,'Actual browser download required'
        book=load_workbook(args.download,read_only=True,data_only=True)
        try:rows=list(book.active.values)
        finally:book.close()
        assert len(rows)==3 and rows[0]==('付款单编号','付款日期','供应商','结算账户','结算金额','结算号','明细备注')
        assert all(row[0]==f['import_number'] and row[1]=='2026-11-16' and row[2]=='QA Posting Supplier' and row[3]=='QA Purchase Posting Account' for row in rows[1:])
        assert sorted(row[4] for row in rows[1:])==[10,15]
    report=QA/'reports/payment-browser-evidence.json'
    evidence=json.loads(report.read_text(encoding='utf-8')) if report.exists() else dict(database_isolated=True,production_business_writes=0,all_system_features_accepted=False,stages={})
    evidence['stages'][action]=dict(payment=payment,verified=True,time=datetime.datetime.now().isoformat(),import_id=f.get('import_id'))
    report.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print('VERIFIED actual browser '+action+': same parent/line IDs, amounts, actor history, inventory, cash, supplier/customer balances and original-document settlements')

if __name__=='__main__':main()
