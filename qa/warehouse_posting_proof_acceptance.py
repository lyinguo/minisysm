"""Actual warehouse/source/cost reversal guards; all fixtures use the isolated DB."""
import argparse,json,uuid,threading,concurrent.futures
from decimal import Decimal
from sale_posting_acceptance import SalePostingSuite
from sale_return_cost_acceptance import owned_cost_mode
from acceptance import read_state,sql,literal

class WarehouseProofSuite(SalePostingSuite):
    def incoming(self,quantity=4,price=2,time='2026-11-14 10:00:00'):
        body=self.inbound(quantity);body['time']=time;body['total']=quantity*price
        body['otherInListDetailInfoDTOList'][0].update(price=price,total=quantity*price)
        identifier=self.store('POST','/otherin/add',body);self.audit(identifier,1);return identifier
    def command(self,identifier,target):
        return self.request('POST','/transfer/report-documents/entry/'+identifier+'/audit',dict(target=target,version=self.detail(identifier)['version']),service='store')
    def snapshot(self,identifier):
        return dict(document=self.detail(identifier),stock=str(self.inventory()),cash=str(self.balance('account',self.account)),ar=str(self.balance('customer',self.customer)),counts=sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(identifier)+';SELECT COUNT(*) FROM room_info WHERE `class`='+literal(identifier)+';SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+';'))
    def run(self,baseline=False):
        def consumed():
            with owned_cost_mode(self.state,'fifo'):
                self.fixture(stock=0);original=self.incoming(10)
                sale=self.draft(qty=3);assert self.post([sale]).get('code')==10000
                replacement=self.incoming(10,8,'2026-11-16 10:00:00');before=self.snapshot(original)
                assert self.inventory()==17
                result=self.command(original,0)
                assert result.get('code')!=10000,'Consumed FIFO inbound was reversed after replenishment made quantity sufficient'
                assert self.snapshot(original)==before
                assert self.post([sale],False).get('code')==10000
                self.audit(original,0);self.audit(replacement,0)
                assert self.inventory()==0 and self.balance('customer',self.customer)==0
                assert sql(self.state,'SELECT COUNT(*) FROM fifo WHERE `in` NOT IN (SELECT id FROM summary) OR `out` NOT IN (SELECT id FROM summary);')=='0'
                return ['Actual inbound10→sale3→restock10 refuses original consumed layer reversal with all states/balances/journals unchanged; reversing sale first permits both receipts reversal, stock0 and no orphan FIFO']
        self.case('warehouse.proof_consumed_inbound_restock_and_dependency_unwind',consumed)
        def closed():
            self.fixture(stock=0);identifier=self.incoming();other,_=self.create_inbound(2);period=uuid.uuid4().hex
            sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+literal(period)+",'2026-11-14',NOW(),"+literal(self.actor)+');')
            try:
                before=self.snapshot(identifier)
                assert self.command(identifier,0).get('code')!=10000,'Closed warehouse receipt reversed'
                assert self.command(other,1).get('code')!=10000,'Closed warehouse draft posted'
                assert self.snapshot(identifier)==before and self.detail(other)['header']['examine']==0
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            self.audit(identifier,0);assert self.inventory()==0
            return ['Owned explicit period fixture blocks actual receipt posting and reversal without movements; reopening permits original reversal; does not claim closing UI lifecycle']
        self.case('warehouse.proof_closed_period_both_directions',closed)
        def legacy():
            self.fixture(stock=0);identifier,_=self.create_inbound();self.incoming(10)
            sql(self.state,'UPDATE entry SET examine=1 WHERE id='+literal(identifier)+';');before=self.snapshot(identifier)
            assert self.command(identifier,1).get('code')!=10000,'Bare legacy approved flag reported proven posting'
            assert self.command(identifier,0).get('code')!=10000,'Bare legacy approved flag created a fictitious reversal'
            assert self.snapshot(identifier)==before
            return ['Explicit owned legacy approved-flag fixture without posting proof cannot report proven success or subtract another receipt stock; all original data unchanged']
        self.case('warehouse.proof_legacy_flag_without_posting_refused',legacy)
        def changed():
            self.fixture(stock=0);identifier=self.incoming()
            sql(self.state,'UPDATE entry_info SET nums=2,total=4 WHERE pid='+literal(identifier)+';')
            try:
                before=self.snapshot(identifier)
                assert self.command(identifier,0).get('code')!=10000,'Reversal used edited quantity instead of original posting'
                assert self.snapshot(identifier)==before
            finally:sql(self.state,'UPDATE entry_info SET nums=4,total=8 WHERE pid='+literal(identifier)+';')
            self.audit(identifier,0);assert self.inventory()==0
            return ['Explicit owned post-entry line corruption refuses reversal atomically; restoring exact original row permits original quantity4 reversal']
        self.case('warehouse.proof_changed_posted_document_refused',changed)
        def missing_journal():
            self.fixture(stock=0);identifier=self.incoming()
            row=json.loads(sql(self.state,"SELECT JSON_OBJECT('id',id,'pid',pid,'type',type,'class',`class`,'info',info,'time',DATE_FORMAT(time,'%Y-%m-%d %H:%i:%s'),'direction',CAST(direction AS SIGNED),'price',price,'nums',nums) FROM room_info WHERE `class`="+literal(identifier)+';'))
            sql(self.state,'DELETE FROM room_info WHERE id='+literal(row['id'])+';')
            try:
                before=self.snapshot(identifier)
                assert self.command(identifier,0).get('code')!=10000,'Missing original room journal was silently reversed'
                assert self.snapshot(identifier)==before
            finally:
                if self.detail(identifier)['header']['examine']==1:sql(self.state,'INSERT INTO room_info('+','.join('`'+key+'`' for key in row)+') VALUES('+','.join(literal(value) for value in row.values())+');')
            self.audit(identifier,0);assert self.inventory()==0
            return ['Missing owned original journal rejects reversal with inventory/state unchanged; exact journal repair permits reversal; no synthetic automatic history backfill']
        self.case('warehouse.proof_missing_original_journal_refused',missing_journal)
        def costs():
            for mode,value in [('base','19'),('ma','9.4'),('fifo','13')]:
                with owned_cost_mode(self.state,mode):
                    self.fixture(stock=0);self.incoming(3,2);self.incoming(2,8,'2026-11-14 11:00:00')
                    sale=self.draft(qty=4);assert self.post([sale]).get('code')==10000
                    later=self.incoming(1,5,'2026-11-16 10:00:00')
                    row=json.loads(sql(self.state,'SELECT JSON_OBJECT(\'exist\',exist,\'balance\',balance) FROM summary WHERE `class`='+literal(later)+';'))
                    assert Decimal(str(json.loads(row['exist'])[1]))==2
                    actual=Decimal(str(json.loads(row['balance'])[1]));assert actual==Decimal(value),mode+' warehouse report value '+str(actual)+' != '+value
            return ['Actual differently priced receipts→sale→later receipt produce stock2 and chronological report value19/base,9.4/MA,13/FIFO; cost definitions are explicit isolated SQL fixtures restored after each mode']
        self.case('warehouse.proof_cross_service_cost_report_replay',costs)
        if not baseline:
            def proof_write_fault():
                self.fixture(stock=0);identifier,_=self.create_inbound();before=self.snapshot(identifier);trigger='qa_proof_insert_'+uuid.uuid4().hex[:12]
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON psi_warehouse_posting FOR EACH ROW BEGIN IF NEW.document_id="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA owned warehouse proof insert failure'; END IF; END$$\nDELIMITER ;\n")
                try:
                    assert self.command(identifier,1).get('code')!=10000
                    assert self.snapshot(identifier)==before
                    assert sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';')=='0'
                finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
                self.audit(identifier,1);assert self.inventory()==4
                history=self.snapshot(identifier)['counts'];self.audit(identifier,1);assert self.snapshot(identifier)['counts']==history
                self.audit(identifier,0);assert self.inventory()==0
                return ['Actual late proof INSERT failure rolls back new room, journals, report, status and history; exact request retries, repetition does not double-post, final reversal restores0']
            self.case('warehouse.proof_storage_failure_atomic_and_retry',proof_write_fault)
            def reverse_fault():
                self.fixture(stock=0);identifier=self.incoming();before=self.snapshot(identifier);trigger='qa_proof_delete_'+uuid.uuid4().hex[:12]
                sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE DELETE ON psi_warehouse_posting FOR EACH ROW BEGIN IF OLD.document_id="+literal(identifier)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA owned warehouse proof remove failure'; END IF; END$$\nDELIMITER ;\n")
                try:
                    assert self.command(identifier,0).get('code')!=10000
                    assert self.snapshot(identifier)==before
                    assert sql(self.state,'SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id='+literal(identifier)+';')=='1'
                finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
                self.audit(identifier,0);assert self.inventory()==0
                return ['Actual late proof DELETE failure rolls back stock reduction, deleted source journals/report, proof and operation history; retry after fault removal restores0']
            self.case('warehouse.proof_reverse_late_storage_failure_atomic',reverse_fault)
            def competing_sale():
                with owned_cost_mode(self.state,'fifo'):
                    self.fixture(stock=0);original=self.incoming(10);self.incoming(10,8,'2026-11-16 10:00:00')
                    body=self.body();body['time']='2026-11-16 13:00:00';body['items'][0].update(nums=3,discount=1)
                    sale=self.create(body);self.sale('POST','/sale/form/check?check=true',[sale]);barrier=threading.Barrier(2)
                    version=self.detail(original)['version']
                    def reverse():
                        barrier.wait();return self.request('POST','/transfer/report-documents/entry/'+original+'/audit',dict(target=0,version=version),service='store')
                    def sell():barrier.wait();return self.post([sale])
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                        left=pool.submit(reverse);right=pool.submit(sell);reversed_result,sold_result=left.result(),right.result()
                    assert sold_result.get('code')==10000,str(sold_result)
                    cost=Decimal(sql(self.state,"SELECT bct FROM summary WHERE type='sell' AND `class`="+literal(sale)+';'))
                    if reversed_result.get('code')==10000:assert self.inventory()==7 and cost==24
                    else:assert self.inventory()==17 and cost==6 and self.detail(original)['header']['examine']==1
                    assert self.balance('customer',self.customer)==339 and self.balance('account',self.account)==100
                    assert sql(self.state,'SELECT COUNT(*) FROM fifo WHERE `in` NOT IN (SELECT id FROM summary) OR `out` NOT IN (SELECT id FROM summary);')=='0'
                    return ['Actual concurrent warehouse reversal and sale serialize through shared goods locks: reversal first yields stock7/cost24, sale first retains source and stock17/cost6; AR339, no orphan FIFO']
            self.case('warehouse.proof_reverse_vs_actual_sale_cost_consistency',competing_sale)
            def service_source():
                self.fixture(stock=0);sql(self.state,'UPDATE goods SET type=1 WHERE id='+literal(self.goods)+';');original=self.incoming()
                sale=self.draft(qty=2);assert self.post([sale]).get('code')==10000
                replacement=self.incoming(4,2,'2026-11-16 10:00:00')
                assert Decimal(sql(self.state,'SELECT nums FROM serve WHERE goods='+literal(self.goods)+';'))==10
                assert self.command(original,0).get('code')==10000,'Independent service cumulative receipt could not be reversed'
                assert self.post([sale],False).get('code')==10000
                self.audit(replacement,0)
                assert Decimal(sql(self.state,'SELECT nums FROM serve WHERE goods='+literal(self.goods)+';'))==0
                assert self.inventory()==0 and self.balance('customer',self.customer)==0
                return ['Actual service receipt4→sale2→receipt4 yields cumulative10, physical0; reversing independent receipt4 leaves6, reversing sale2 and final receipt4 restores cumulative0/physical0/AR0']
            self.case('warehouse.proof_service_cumulative_independent_reversal',service_source)
            def independent_warehouse():
                with owned_cost_mode(self.state,'fifo'):
                    self.fixture(stock=0);original=self.incoming();other=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [other,'QA Independent Warehouse','QA'+other[:18],self.state['frame_id']])+');')
                    body=self.inbound();body['time']='2026-11-15 10:00:00';body['otherInListDetailInfoDTOList'][0]['warehouse']=other
                    second=self.store('POST','/otherin/add',body);self.audit(second,1)
                    body=self.body();body['time']='2026-11-16 10:00:00';body['items'][0].update(nums=1,discount=1,warehouse=other)
                    sale=self.create(body);self.sale('POST','/sale/form/check?check=true',[sale]);assert self.post([sale]).get('code')==10000
                    assert self.command(original,0).get('code')==10000,'Unrelated independent warehouse sale blocked an unused source'
                    assert self.inventory()==0 and Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(other)+';'))==3
                    assert self.post([sale],False).get('code')==10000;self.audit(second,0)
                    assert self.balance('customer',self.customer)==0
                    assert sql(self.state,'SELECT COUNT(*) FROM fifo WHERE `in` NOT IN (SELECT id FROM summary) OR `out` NOT IN (SELECT id FROM summary);')=='0'
                    return ['Actual independent-warehouse FIFO scope permits unused warehouse-A receipt reversal while warehouse-B sale remains posted; its original source/cost survives replay, final dependent reversal restores0 without orphan FIFO']
            self.case('warehouse.proof_independent_warehouse_scope_allows_reversal',independent_warehouse)
        self.write_report()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args();WarehouseProofSuite(read_state()).run(args.baseline)
