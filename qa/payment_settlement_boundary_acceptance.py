"""Real settlement financial/period/downstream/reversal-storage boundaries."""
import uuid
from payment_settlement_posting_acceptance import PaymentPostingSuite
from acceptance import read_state,sql,literal

class PaymentBoundarySuite(PaymentPostingSuite):
    def run(self):
        def finances():
            f=self.prepare_chain();command=self.command(f['payment'])
            def unchanged():
                assert self.document(f['payment'])['version']==command['version']
                assert sql(self.state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(f['payment'])+';')=='0'
                assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(f['payment'])+';')=='0'
            sql(self.state,'UPDATE account SET balance=953 WHERE id='+literal(self.account)+';')
            try:assert self.post_payment(command).get('code')!=10000;assert self.balance('account',self.account)==953;unchanged()
            finally:sql(self.state,'UPDATE account SET balance=2125 WHERE id='+literal(self.account)+';')
            sql(self.state,'UPDATE supplier SET balance=953 WHERE id='+literal(self.supplier)+';')
            try:assert self.post_payment(command).get('code')!=10000;assert self.balance('account',self.account)==2125;unchanged()
            finally:sql(self.state,'UPDATE supplier SET balance=954 WHERE id='+literal(self.supplier)+';')
            period=uuid.uuid4().hex
            sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-16','2026-11-16',self.actor])+');')
            try:assert self.post_payment(command).get('code')!=10000;self.balances(2125,954);unchanged()
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            assert self.post_payment(command).get('data')==1;self.balances(1171,0)
            return ['Actual insufficient cash, insufficient supplier payable and closed-period fixtures reject same reviewed command without any journal/allocation/version changes; restored conditions permit original retry']
        self.case('payment.boundary_funds_payable_period_atomic',finances)

        def reverse_fault():
            f=self.prepare_chain();assert self.post_payment(self.command(f['payment'])).get('data')==1
            document=self.document(f['payment']);command=dict(id=f['payment'],status=0,version=document['version']);trigger='qa_pay_rev_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE DELETE ON bre_bill FOR EACH ROW BEGIN IF OLD.type='omy' AND OLD.source="+literal(f['payment'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA reverse late fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_payment(command).get('code')!=10000;self.balances(1171,0)
                assert self.document(f['payment'])==document
                assert sql(self.state,'SELECT COUNT(*) FROM psi_payment_posting WHERE payment_id='+literal(f['payment'])+';')=='1'
                assert all(sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM buy WHERE id='+literal(source)+';')=='2' for source in f['receipts'])
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_payment(command).get('data')==1;self.balances(2125,954)
            return ['Actual late return-credit deletion fault after attempted cash restoration rolls back entire reversal, source states/evidence/history unchanged; original reviewed reversal retries']
        self.case('payment.boundary_reverse_storage_rollback_retry',reverse_fault)

        def downstream():
            f=self.prepare_chain();assert self.post_payment(self.command(f['payment'])).get('data')==1
            document=self.document(f['payment']);command=dict(id=f['payment'],status=0,version=document['version']);invoice,kind,expense=[uuid.uuid4().hex for _ in range(3)]
            sql(self.state,'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'omy',f['payment'],'2026-11-15','QA'+invoice[:12],'QA Payment Invoice',1])+');')
            try:
                response=self.post_payment(command);assert response.get('code')!=10000,'Linked invoice allowed payment reversal'
                self.balances(1171,0);assert self.document(f['payment'])['version']==document['version']
            finally:sql(self.state,'DELETE FROM invoice WHERE id='+literal(invoice)+';')
            sql(self.state,'INSERT INTO iet(id,name,type,sort) VALUES('+','.join(literal(v) for v in [kind,'QA Payment Expense Kind',1,0])+');INSERT INTO cost(id,type,`class`,time,iet,money,settle,state) VALUES('+','.join(literal(v) for v in [expense,'omy',f['payment'],'2026-11-15',kind,1,0,0])+');')
            try:
                response=self.post_payment(command);assert response.get('code')!=10000,'Linked expense allowed payment reversal and left its source unapproved'
                self.balances(1171,0);assert self.document(f['payment'])['version']==document['version']
            finally:sql(self.state,'DELETE FROM cost WHERE id='+literal(expense)+';DELETE FROM iet WHERE id='+literal(kind)+';')
            assert self.post_payment(command).get('data')==1;self.balances(2125,954)
            return ['Explicit QA invoice and expense associations prevent real payment reversal until handled; removing only test associations permits same reviewed reverse command']
        self.case('payment.boundary_downstream_invoice_and_expense',downstream)
        self.write_report()

if __name__=='__main__':PaymentBoundarySuite(read_state()).run()
