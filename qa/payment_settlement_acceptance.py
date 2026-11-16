"""Actual supplier settlement preparation on a complete purchasing/sales/return chain."""
import json,re,uuid
from decimal import Decimal
from trade_flow_acceptance import TradeFlowSuite
from payment_draft_acceptance import PaymentDraftSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants,authority
from acceptance import read_state,sql,literal,QA

class SettlementPreviewSuite(PaymentDraftSuite):
    def prepare_chain(self):
        flow=TradeFlowSuite(self.state);flow.run('prepare')
        fixture=json.loads((QA/'runtime/trade-flow-fixture.json').read_text(encoding='utf-8'))
        assert fixture['database']==self.state['database']
        for key in ['goods','warehouse','supplier','account']:setattr(self,key,fixture[key])
        return fixture
    def preview(self,identifier):return self.request('GET','/payment-order/settlement-preview?id='+identifier,service='payment')
    def preview_cases(self):
        def actual_plan():
            f=self.prepare_chain();before=sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(f['payment'])+';')
            first=self.preview(f['payment']);assert first.get('code')==10000,'Real supplier settlement preview failed'
            data=first['data'];assert data['payment']==f['payment'] and re.fullmatch('[0-9a-f]{64}',data['version'])
            assert [Decimal(str(data[k])) for k in ['cash','invoiceTotal','creditTotal','payableNet']]==list(map(Decimal,['954','1130','176','954']))
            allocations=data['allocations'];assert len(allocations)==3
            assert {row['id'] for row in allocations if row['type']=='buy'}==set(f['receipts'])
            assert [row['id'] for row in allocations if row['type']=='bre']==[f['purchase_return']]
            assert sum(Decimal(str(row['money'])) for row in allocations)==954
            assert next(Decimal(str(row['money'])) for row in allocations if row['type']=='bre')==-176
            assert all(re.fullmatch('[0-9a-f]{64}',row['version']) for row in allocations)
            assert self.preview(f['payment'])['data']==data
            assert self.inventory()==6 and self.balance('account',self.account)==2125 and self.balance('supplier',self.supplier)==954
            assert sql(self.state,'SELECT COUNT(*) FROM omy_bill WHERE pid='+literal(f['payment'])+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM account_info WHERE type='omy' AND `class`="+literal(f['payment'])+';')=='0'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='omy' AND source="+literal(f['payment'])+';')==before
            return ['Complete actual trade chain produces reviewable purchases1130 minus return-credit176 = cash954; original2 receipts+return identities and SHA256 versions included; repeated preview writes no allocation/funds/history and stock6/cash2125/payable954 remain']
        self.case('payment.settlement_preview_actual_integrated_allocation',actual_plan)
        def live_grants():
            f=self.prepare_chain();role=self.success('POST','/role/add-role',dict(name='QA Finance Plan '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');_,username,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,username);admin=self.token
            try:
                self.token=token;assert self.preview(f['payment']).get('code')==403
                with qa_resource_grants(self.state,['/payment-order/modify-examine-status'],[authority(role,keyword)]):assert self.preview(f['payment']).get('code')==10000
                assert self.preview(f['payment']).get('code')==403
            finally:self.token=admin
            assert self.balance('account',self.account)==2125 and self.balance('supplier',self.supplier)==954
            return ['Actual ordinary OAuth finance role needs live settlement approval grant; same token loses access after revoke; preview has no financial changes']
        self.case('payment.settlement_preview_live_grants',live_grants)
        def inconsistent_source():
            f=self.prepare_chain();identifier=f['receipts'][0]
            try:
                sql(self.state,'UPDATE buy SET nucleus=2 WHERE id='+literal(identifier)+';')
                assert self.preview(f['payment']).get('code')!=10000,'Inconsistent source state accepted as reviewed settlement'
            finally:sql(self.state,'UPDATE buy SET nucleus=0 WHERE id='+literal(identifier)+';')
            assert self.preview(f['payment']).get('code')==10000
            assert self.inventory()==6 and self.balance('account',self.account)==2125 and self.balance('supplier',self.supplier)==954
            return ['Explicit owned QA source-state corruption is refused instead of guessing or hiding unpaid documents; restoring source permits actual read-only preparation']
        self.case('payment.settlement_preview_source_consistency',inconsistent_source)
        self.write_report()

if __name__=='__main__':SettlementPreviewSuite(read_state()).preview_cases()
