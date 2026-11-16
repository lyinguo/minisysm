"""Actual receipt preview, atomic customer settlement and safe reversal gates."""
import copy,json,uuid,concurrent.futures
from decimal import Decimal
from receipt_draft_acceptance import ReceiptDraftSuite
from receipt_trade_acceptance import ReceiptTradeSuite
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants
from acceptance import read_state,sql,literal,QA

class ReceiptSettlementSuite(ReceiptDraftSuite):
    def prepare_trade(self):
        flow=ReceiptTradeSuite(self.state);flow.run('prepare');self.token=flow.token;self.actor=flow.actor
        fixture=json.loads((QA/'runtime/receipt-trade-fixture.json').read_text(encoding='utf-8'))
        assert fixture['database']==self.state['database']
        for key in ['goods','warehouse','customer','account']:setattr(self,key,fixture[key])
        return fixture
    def preview_receipt(self,identifier):return self.request('GET','/fund/receipt/settlement-preview?id='+identifier,service='fund')
    def receipt_document(self,identifier):
        result=self.request('GET','/fund/receipt/document/'+identifier,service='fund');assert result.get('code')==10000,str(result);return result['data']
    def command(self,identifier):
        result=self.preview_receipt(identifier);assert result.get('code')==10000,str(result);plan=result['data']
        assert plan['receipt']==identifier and [Decimal(str(plan[key])) for key in ['cash','invoiceTotal','creditTotal','receivableNet']]==list(map(Decimal,['151','239','88','151']))
        return dict(id=identifier,status=1,version=plan['version'],allocations=plan['allocations'])
    def post_receipt(self,body):return self.request('POST','/fund/receipt/settle',body,service='fund')
    def balances(self,f,cash,receivable):
        assert self.inventory()==6 and self.balance('account',self.account)==cash and self.balance('customer',self.customer)==receivable
        assert Decimal(sql(self.state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0
    def run(self):
        def roundtrip():
            f=self.prepare_trade();command=self.command(f['receipt']);before=self.receipt_document(f['receipt'])
            assert self.preview_receipt(f['receipt'])['data']['version']==command['version'];self.balances(f,1171,151)
            assert self.receipt_document(f['receipt'])==before
            assert self.post_receipt(command).get('data')==1;self.balances(f,1322,0)
            posted=self.receipt_document(f['receipt']);assert posted['header']['examine']==1 and posted['header']['nucleus']==2
            assert self.post_receipt(dict(id=f['receipt'],status=1,version=posted['version'])).get('data')==0
            assert self.post_receipt(dict(id=f['receipt'],status=0,version=command['version'])).get('code')!=10000
            assert self.post_receipt(dict(id=f['receipt'],status=0,version=posted['version'])).get('data')==1;self.balances(f,1171,151)
            restored=self.receipt_document(f['receipt']);assert restored['header']['examine']==restored['header']['nucleus']==0 and restored['version']!=before['version']
            for table,where in [('account_info',"type='imy' AND `class`="),('imy_bill','pid='),('sell_bill',"type='imy' AND source="),('sre_bill',"type='imy' AND source="),('psi_receipt_posting','receipt_id=')]:
                assert sql(self.state,'SELECT COUNT(*) FROM '+table+' WHERE '+where+literal(f['receipt'])+';')=='0'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM sell WHERE id='+literal(f['sale'])+';')=='1'
            assert sql(self.state,'SELECT CAST(nucleus AS SIGNED) FROM sre WHERE id='+literal(f['sales_return'])+';')=='1'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(f['receipt'])+';')=='3'
            return ['Actual readonly239-88=151 plan, receipt closes cash1322/customer0, fresh same-target retry idempotent and stale reverse refused; explicit reverse restores1171/151 and both source partial statuses, removes only own journals/proof, preserves3 actor histories and changes version']
        self.case('receipt.settlement_actual_roundtrip_and_reviewed_versions',roundtrip)
        def concurrent_commands():
            f=self.prepare_trade();command=self.command(f['receipt'])
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.post_receipt(command),range(2)))
            assert sum(row.get('code')==10000 for row in results)==1;self.balances(f,1322,0)
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='imy' AND `class`="+literal(f['receipt'])+';')=='1'
            return ['Two actual concurrent submissions of identical reviewed receipt/source versions credit cash exactly once and leave one account journal']
        self.case('receipt.settlement_concurrent_single_credit',concurrent_commands)
        def storage():
            f=self.prepare_trade();command=self.command(f['receipt']);before=self.receipt_document(f['receipt']);trigger='qa_rct_post_'+uuid.uuid4().hex[:10]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON sre_bill FOR EACH ROW BEGIN IF NEW.type='imy' AND NEW.source="+literal(f['receipt'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA receipt offset insert fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_receipt(command).get('code')!=10000;self.balances(f,1171,151)
                assert self.receipt_document(f['receipt'])==before
                assert sql(self.state,"SELECT COUNT(*) FROM sell_bill WHERE type='imy' AND source="+literal(f['receipt'])+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_receipt(command).get('data')==1;self.balances(f,1322,0)
            return ['Actual late return-credit insertion failure rolls back cash credit, customer reduction, prior sales allocation/source state and histories/version; exact reviewed request retries']
        self.case('receipt.settlement_late_storage_rollback_retry',storage)
        def reverse_storage():
            f=self.prepare_trade();assert self.post_receipt(self.command(f['receipt'])).get('data')==1;before=self.receipt_document(f['receipt']);command=dict(id=f['receipt'],status=0,version=before['version']);trigger='qa_rct_reverse_'+uuid.uuid4().hex[:9]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE DELETE ON sre_bill FOR EACH ROW BEGIN IF OLD.type='imy' AND OLD.source="+literal(f['receipt'])+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA receipt offset reverse fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.post_receipt(command).get('code')!=10000;self.balances(f,1322,0);assert self.receipt_document(f['receipt'])==before
                assert sql(self.state,'SELECT COUNT(*) FROM psi_receipt_posting WHERE receipt_id='+literal(f['receipt'])+';')=='1'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.post_receipt(command).get('data')==1;self.balances(f,1171,151)
            return ['Actual late reverse deletion fault rolls back attempted cash withdrawal/customer restoration and earlier sales unallocation; original receipt proof/document/version remain intact and same reversal retries']
        self.case('receipt.settlement_reverse_storage_rollback_retry',reverse_storage)
        def finances():
            f=self.prepare_trade();command=self.command(f['receipt']);before=self.receipt_document(f['receipt'])
            sql(self.state,'UPDATE customer SET balance=150 WHERE id='+literal(self.customer)+';')
            try:
                assert self.post_receipt(command).get('code')!=10000
                assert self.balance('account',self.account)==1171 and self.receipt_document(f['receipt'])==before
            finally:sql(self.state,'UPDATE customer SET balance=151 WHERE id='+literal(self.customer)+';')
            period=uuid.uuid4().hex;sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-16','2026-11-16',self.actor])+');')
            try:assert self.post_receipt(command).get('code')!=10000;self.balances(f,1171,151);assert self.receipt_document(f['receipt'])==before
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            assert self.post_receipt(command).get('data')==1;posted=self.receipt_document(f['receipt']);reverse=dict(id=f['receipt'],status=0,version=posted['version'])
            sql(self.state,'UPDATE account SET balance=150 WHERE id='+literal(self.account)+';')
            try:
                assert self.post_receipt(reverse).get('code')!=10000
                assert self.balance('account',self.account)==150 and self.balance('customer',self.customer)==0 and self.receipt_document(f['receipt'])==posted
            finally:sql(self.state,'UPDATE account SET balance=1322 WHERE id='+literal(self.account)+';')
            assert self.post_receipt(reverse).get('data')==1;self.balances(f,1171,151)
            return ['Explicit QA insufficient receivable/closed-period fixtures block incoming posting atomically; after real posting, insufficient available account balance fixture blocks cash withdrawal/reverse without reopening AR, restore fixture then same reviewed reverse succeeds']
        self.case('receipt.settlement_receivable_period_and_reverse_funds',finances)
        def protocol():
            f=self.prepare_trade();command=self.command(f['receipt']);invalid=[]
            for key,value in [('version',None),('status',2),('allocations',[]),('allocations',command['allocations']*2)]:
                body=copy.deepcopy(command);body[key]=value;invalid.append(body)
            body=copy.deepcopy(command);body['allocations'][0]['version']='0'*64;invalid.append(body)
            body=copy.deepcopy(command);body['allocations'][0]['money']=-1;invalid.append(body)
            body=copy.deepcopy(command);body['allocations']=[dict(body['allocations'][0],money=151)];invalid.append(body)
            for body in invalid:assert self.post_receipt(body).get('code')!=10000
            assert self.request('PATCH','/fund/receipt/audit',dict(ids=[f['receipt']]),service='fund').get('code')!=10000
            self.balances(f,1171,151);assert self.receipt_document(f['receipt'])['version']==command['version']
            assert self.post_receipt(command).get('data')==1;self.balances(f,1322,0)
            return ['Missing/stale versions, invalid target/duplicate/empty/wrong-sign/unbalanced allocations and cash-only final settlement omitting return credit refuse; legacy audit toggle cannot bypass reviewed protocol, valid original plan succeeds']
        self.case('receipt.settlement_reviewed_allocation_and_credit_closure',protocol)
        def ordinary():
            f=self.prepare_trade();command=self.command(f['receipt']);helper=PaymentDocumentScopeSuite(self.state);user,token,role=helper.role_user();admin=self.token;self.token=token
            try:
                assert self.post_receipt(command).get('code')==403
                with qa_resource_grants(self.state,['/fund/receipt/audit','/fund/receipt/fundReceiptDetail'],[role]):
                    assert self.post_receipt(command).get('data')==1;self.balances(f,1322,0)
                    reverse=dict(id=f['receipt'],status=0,version=self.receipt_document(f['receipt'])['version'])
                assert self.post_receipt(reverse).get('code')==403;self.balances(f,1322,0)
                with qa_resource_grants(self.state,['/fund/receipt/audit'],[role]):assert self.post_receipt(reverse).get('data')==1;self.balances(f,1171,151)
            finally:self.token=admin
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='imy' AND source="+literal(f['receipt'])+' AND `user`='+literal(user)+';')=='2'
            return ['Actual ordinary signed finance operator posts/reverses only with live grant, same token immediately denied on revoke, both real operation histories attributed correctly and original balances restored']
        self.case('receipt.settlement_actual_ordinary_operator_and_revoke',ordinary)
        self.write_report()

if __name__=='__main__':ReceiptSettlementSuite(read_state()).run()
