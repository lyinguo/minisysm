"""Real deletion evidence and all-or-nothing deletion/history in the isolated DB."""
import uuid
from sale_posting_acceptance import SalePostingSuite
from acceptance import read_state,sql,literal

class SaleDeleteHistorySuite(SalePostingSuite):
    def remove(self,ids):return self.request('DELETE','/sale/form/deleteSales',ids,service='sale')
    def histories(self,identifier):return int(sql(self.state,"SELECT COUNT(*) FROM record WHERE type='sell' AND source="+literal(identifier)+';'))
    def run(self):
        def evidence():
            self.fixture();body=self.body();identifier=self.create(body);before=self.histories(identifier)
            assert self.remove([identifier]).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM sell WHERE id='+literal(identifier)+';SELECT COUNT(*) FROM sell_info WHERE pid='+literal(identifier)+';')=='0\n0'
            assert self.histories(identifier)==before+1,'Successful sale deletion omitted its operation evidence'
            assert sql(self.state,"SELECT COUNT(*) FROM record WHERE type='sell' AND source="+literal(identifier)+" AND info='删除销售单' AND `user`="+literal(self.actor)+';')=='1'
            assert sql(self.state,"SELECT COUNT(*) FROM `log` WHERE `user`="+literal(self.actor)+' AND info='+literal('删除销售单['+body['number']+']['+identifier+']')+';')=='1'
            assert self.inventory()==10 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            return ['Physical draft deletion retains previous history and appends exactly one actual actor/number/source record and log; actual stock/cash/receivable unchanged']
        self.case('sale.delete_signed_history_and_log_retained',evidence)
        def atomic():
            self.fixture();ids=[self.create(self.body()) for _ in range(2)]
            before={identifier:self.histories(identifier) for identifier in ids};trigger='qa_delete_history_'+uuid.uuid4().hex[:12]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.type='sell' AND NEW.source="+literal(ids[1])+" AND NEW.info='删除销售单' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA owned delete evidence failure'; END IF; END$$\nDELIMITER ;\n")
            try:
                assert self.remove(ids).get('code')!=10000,'Later delete-history storage failure was ignored'
                for identifier in ids:
                    assert sql(self.state,'SELECT COUNT(*) FROM sell WHERE id='+literal(identifier)+';SELECT COUNT(*) FROM sell_info WHERE pid='+literal(identifier)+';')=='1\n1'
                    assert self.histories(identifier)==before[identifier]
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.remove(ids).get('code')==10000
            for identifier in ids:
                assert sql(self.state,'SELECT COUNT(*) FROM sell WHERE id='+literal(identifier)+';SELECT COUNT(*) FROM sell_info WHERE pid='+literal(identifier)+';')=='0\n0'
                assert self.histories(identifier)==before[identifier]+1
            assert self.inventory()==10 and self.balance('account',self.account)==100 and self.balance('customer',self.customer)==0
            return ['Actual second owned history INSERT failure rolls back both deleted headers/details and first evidence; same request succeeds after trigger removal, one signed deletion per document; balances unchanged']
        self.case('sale.delete_later_history_failure_batch_atomic_retry',atomic)
        self.write_report()

if __name__=='__main__':SaleDeleteHistorySuite(read_state()).run()
