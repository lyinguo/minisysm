"""Real procurement order deletion; only disposable dedicated QA fixtures."""
import uuid, concurrent.futures
from booking_receive_acceptance import ReceiveSuite
from acceptance import read_state,sql,literal
from resource_fixture import qa_resource_grants
from purchase_ui_acceptance import PurchaseUiSuite

class OrderDeleteSuite(ReceiveSuite):
    def delete_order(self,ids):return self.request('DELETE','/purchase-order/delete',ids,service='purchase')
    def exists(self,id):return int(sql(self.state,'SELECT COUNT(*) FROM bor WHERE id='+literal(id)+';'))
    def intact(self,id):assert self.exists(id)==1 and int(sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(id)+';'))>0
    def run(self,baseline=False):
        def ordinary():
            self.setup(False);id=self.source;before=self.records(id)
            assert self.delete_order([id]).get('code')==10000 and self.exists(id)==0
            assert sql(self.state,'SELECT COUNT(*) FROM bor_info WHERE pid='+literal(id)+';')=='0'
            assert self.records(id)==before+1,'Missing deletion history'
            self.unchanged();return ['Actual free order and details physically deleted; creator history preserved plus actual deletion actor; stock/cash/payable unchanged']
        self.case('booking.delete_free_draft_history',ordinary)
        def states():
            for approved,state in [(True,0),(False,1),(False,2),(False,3)]:
                self.setup(approved);id=self.source
                if state:sql(self.state,'UPDATE bor SET state='+str(state)+' WHERE id='+literal(id)+';')
                assert self.delete_order([id]).get('code')!=10000,'Approved/executed/closed order was deleted'
                self.intact(id);self.unchanged()
            return ['Actual approved order and owned SQL state1/2/3 fixtures reject deletion; all details remain']
        self.case('booking.delete_approved_executed_closed_denied',states)
        def downstream():
            self.setup();id=self.source;receipt=self.create_receipt(self.receive_body())
            # Damaged legacy approval flag must not hide real downstream links.
            sql(self.state,'UPDATE bor SET examine=0 WHERE id='+literal(id)+';')
            assert self.delete_order([id]).get('code')!=10000,'Order with real generated receipt was deleted'
            self.intact(id);assert self.count_receipts()==1;self.unchanged()
            # Prove line-only historical linkage protects independently of header source.
            sql(self.state,"UPDATE buy SET source='0' WHERE id="+literal(receipt)+';')
            assert self.delete_order([id]).get('code')!=10000;self.intact(id)
            return ['Actual generated receipt protects source order even with corrupt approval flag or header source; real line references remain protected']
        self.case('booking.delete_real_downstream_guard',downstream)
        def legacy_references():
            self.setup();id=self.source;receipt=self.create_receipt(self.receive_body());number=sql(self.state,'SELECT number FROM bor WHERE id='+literal(id)+';')
            sql(self.state,'UPDATE bor SET examine=0 WHERE id='+literal(id)+';UPDATE buy SET source='+literal(number)+' WHERE id='+literal(receipt)+";UPDATE buy_info SET source='0' WHERE pid="+literal(receipt)+';')
            assert self.delete_order([id]).get('code')!=10000;self.intact(id)
            self.setup(False);id=self.source;sql(self.state,'UPDATE bor_info SET handle=1 WHERE pid='+literal(id)+';')
            assert self.delete_order([id]).get('code')!=10000;self.intact(id)
            self.setup(False);id=self.source;invoice=uuid.uuid4().hex
            sql(self.state,'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'bor',id,'2026-11-15','QA-'+invoice[:16],'QA Order Ref',1])+');')
            assert self.delete_order([id]).get('code')!=10000;self.intact(id);self.unchanged()
            return ['Owned legacy number-only receipt reference, nonzero handled quantity with zero flags, and SQL generic invoice link independently block deletion; not invoice lifecycle acceptance']
        self.case('booking.delete_legacy_reference_guards',legacy_references)
        def invalid_batch():
            self.setup(False);id=self.source
            for ids in [[],[id,id],[''],[id,'zz'+uuid.uuid4().hex[:30]],[id,None]]:
                assert self.delete_order(ids).get('code')!=10000,'Invalid/missing batch accepted'
                self.intact(id)
            self.unchanged();return ['Empty/duplicate/null/missing IDs reject without partially deleting valid batch members']
        self.case('booking.delete_invalid_batch_atomic',invalid_batch)
        def period():
            self.setup(False);id=self.source;period=uuid.uuid4().hex
            try:
                sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(v) for v in [period,'2026-11-15','2026-11-15',self.actor])+');')
                assert self.delete_order([id]).get('code')!=10000;self.intact(id)
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            assert self.delete_order([id]).get('code')==10000
            return ['Owned closed-period fixture prevents deletion; after removing only that fixture free draft can be deleted']
        self.case('booking.delete_closed_period',period)
        def fault():
            self.setup(False);first=self.source;second=self.create_order(self.order_body());before=self.records(first);trigger='qa_bord_'+uuid.uuid4().hex[:12]
            # Fail a later header deletion after earlier members/details were removed.
            failing=max(first,second)
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE DELETE ON bor FOR EACH ROW BEGIN IF OLD.id="+literal(failing)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA order delete failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.delete_order([first,second]).get('code')!=10000
                self.intact(first);self.intact(second);assert self.records(first)==before
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.delete_order([first,second]).get('code')==10000 and self.exists(first)==self.exists(second)==0
            self.unchanged();return ['Real later-member MySQL header delete failure rolls back all headers/details/history; same-request retry succeeds']
        self.case('booking.delete_storage_batch_rollback',fault)
        def history_fault():
            self.setup(False);id=self.source;before=self.records(id);trigger='qa_bordh_'+uuid.uuid4().hex[:11]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='bor' AND NEW.source="+literal(id)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA delete history failure'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.delete_order([id]).get('code')!=10000;self.intact(id);assert self.records(id)==before
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.delete_order([id]).get('code')==10000 and self.exists(id)==0 and self.records(id)==before+1
            return ['Real deletion-history insert failure restores already removed header/details and all history; retry deletes once']
        self.case('booking.delete_history_failure_atomic',history_fault)
        def auth():
            self.setup(False);first=self.source;second=self.create_order(self.order_body())
            role=self.success('POST','/role/add-role',dict(name='QA Order Delete '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'));keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);admin=self.token;self.token=PurchaseUiSuite.login(self,user)
            try:
                assert self.delete_order([first]).get('code')==403;self.intact(first)
                with qa_resource_grants(self.state,['/purchase-order/delete'],[keyword]):
                    assert self.delete_order([first]).get('code')==10000
                    assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(first)+' AND `user`='+literal(actor)+';')=='1'
                    other=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(other)+",'0','QA Foreign Order Delete');"+'UPDATE `user` SET frame='+literal(other)+' WHERE id='+literal(actor)+';')
                    assert self.delete_order([second]).get('code')==403;self.intact(second)
                assert self.delete_order([second]).get('code')==403
            finally:self.token=admin
            return ['Real OAuth role needs delete grant, deletion records actual actor, live frame change and revoked permission immediately reject']
        self.case('booking.delete_actual_permission_scope',auth)
        if not baseline:
            def concurrent_delete():
                self.setup(False);id=self.source
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.delete_order([id]),range(2)))
                assert sum(r.get('code')==10000 for r in results)==1 and self.exists(id)==0 and self.records(id)==2
                self.unchanged();return ['Simultaneous actual deletes commit once with exactly one deletion history']
            self.case('booking.delete_concurrent_once',concurrent_delete)
            def race():
                self.setup(False);id=self.source
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    deletion=pool.submit(self.delete_order,[id]);approval=pool.submit(self.audit,[id]);deleted,approved=deletion.result(),approval.result()
                if deleted.get('code')==10000:assert approved.get('code')!=10000 and self.exists(id)==0
                else:assert approved.get('code')==10000;self.intact(id);assert self.state_of(id)=='1'
                self.unchanged();return ['Actual deletion versus approval serializes: removed draft or intact approved order, never approved orphan']
            self.case('booking.delete_race_order_approval',race)
        self.write_report()

if __name__=='__main__':
    import sys
    OrderDeleteSuite(read_state()).run(len(sys.argv)>1 and sys.argv[1]=='baseline')
