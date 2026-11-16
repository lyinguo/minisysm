"""Real reviewed complete-draft import, grouping and batch transaction gates."""
import copy
import uuid
import re
import concurrent.futures
from receipt_document_scope_acceptance import ReceiptDocumentScopeSuite
from resource_fixture import qa_database_resource_grants as qa_resource_grants
from acceptance import read_state,sql,literal

class ReceiptImportSuite(ReceiptDocumentScopeSuite):
    def rows(self):
        self.fixture(stock=0);customer=sql(self.state,'SELECT number FROM customer WHERE id='+literal(self.customer)+';');account=sql(self.state,'SELECT number FROM account WHERE id='+literal(self.account)+';')
        first='QAIMP'+uuid.uuid4().hex[:24];second='QAIMP'+uuid.uuid4().hex[:24]
        rows=[dict(number=first,date='2026-11-16 14:00:00',customerNumber=customer,accountNumber=account,money=10,settle='QA bank',remark='QA complete import',lineRemark='QA first')]
        rows.append(dict(rows[0],money=15,lineRemark='QA second'));rows.append(dict(rows[0],number=second,money=20,lineRemark='QA third'))
        return rows
    def preview_import(self,rows):return self.request('POST','/fund/receipt/import-preview',dict(rows=rows),service='fund')
    def import_rows(self,rows,version):return self.request('POST','/fund/receipt/import-confirm',dict(rows=rows,version=version),service='fund')
    def prepared(self,rows):
        response=self.preview_import(rows);assert response.get('code')==10000,str(response);return response['data']
    def absent(self,rows):
        assert all(self.count_receipt(row['number'])==0 for row in rows)
        assert sql(self.state,'SELECT COUNT(*) FROM imy_info WHERE account='+literal(self.account)+';')=='0';self.unchanged_receipt()
    def run(self):
        def grouping():
            rows=self.rows();plan=self.prepared(rows);self.absent(rows)
            assert plan['documentCount']==2 and plan['lineCount']==3 and plan['cash']==45
            assert re.fullmatch('[0-9a-f]{64}',plan['version']) and self.prepared(rows)==plan
            response=self.import_rows(rows,plan['version']);assert response.get('code')==10000,str(response)
            ids=response['data']['ids'];assert len(ids)==2 and response['data']['cash']==45
            first,second=[self.document(identifier) for identifier in ids]
            assert first['header']['total']==25 and len(first['items'])==2 and second['header']['total']==20 and len(second['items'])==1
            for document in [first,second]:
                assert document['header']['frame']==self.state['frame_id'] and document['header']['user']==self.actor
                assert document['header']['examine']==document['header']['nucleus']==0
                assert all(row['pid']==document['header']['id'] for row in document['items'])
            assert self.import_rows(rows,plan['version']).get('code')!=10000
            assert all(self.count_receipt(row['number'])==1 for row in rows);self.unchanged_receipt()
            return ['Actual three template rows group into two complete real drafts with correct totals/parent IDs/actor and no funds; repeated readonly preview stable, duplicate commit cannot create extra drafts']
        self.case('receipt.import_complete_grouped_drafts',grouping)

        def invalid():
            rows=self.rows();plan=self.prepared(rows)
            for field,value in [('customerNumber','missing'),('accountNumber','missing'),('money',-1),('money','0.00001'),('date','bad'),('remark','different header')]:
                bad=copy.deepcopy(rows);bad[1][field]=value
                assert self.preview_import(bad).get('code')!=10000
                assert self.import_rows(bad,plan['version']).get('code')!=10000;self.absent(rows)
            assert self.import_rows(rows,None).get('code')!=10000;self.absent(rows)
            response=self.request('POST','/fund/receipt/import-confirm',[dict(account=self.account,money=10,settle='QA orphan')],service='fund')
            assert response.get('code')!=10000;self.absent(rows)
            return ['Unknown master codes, inconsistent same-number header, invalid money/date, missing reviewed version and old unattached-row payload cannot persist partial or orphan rows']
        self.case('receipt.import_invalid_batch_and_legacy_orphan_denied',invalid)

        def stale():
            rows=self.rows();plan=self.prepared(rows);changed=copy.deepcopy(rows);changed[0]['money']=11
            assert self.import_rows(changed,plan['version']).get('code')!=10000;self.absent(rows)
            original=rows[0]['accountNumber'];sql(self.state,'UPDATE account SET number='+literal('QA_CHANGED'+uuid.uuid4().hex[:12])+' WHERE id='+literal(self.account)+';')
            try:assert self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
            finally:sql(self.state,'UPDATE account SET number='+literal(original)+' WHERE id='+literal(self.account)+';')
            assert self.import_rows(rows,plan['version']).get('code')==10000;self.unchanged_receipt()
            return ['Changed reviewed input or account code refuses without any draft; restoring unchanged master data permits exact original reviewed batch retry']
        self.case('receipt.import_reviewed_input_and_master_revalidation',stale)

        def storage():
            rows=self.rows();plan=self.prepared(rows);marker=rows[-1]['lineRemark'];trigger='qa_imp_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON imy_info FOR EACH ROW BEGIN IF NEW.account="+literal(self.account)+' AND NEW.data='+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA whole import fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
                assert sql(self.state,"SELECT COUNT(*) FROM `log` WHERE info LIKE "+literal('%'+rows[0]['number']+'%')+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.import_rows(rows,plan['version']).get('code')==10000;self.unchanged_receipt()
            return ['Actual second-document detail insert failure rolls back first complete document, both headers/details and history/log; same reviewed batch retries after fault removal']
        self.case('receipt.import_entire_batch_storage_rollback',storage)

        def grants():
            rows=self.rows();user,token,role=self.role_user();admin=self.token;self.token=token
            try:
                assert self.preview_import(rows).get('code')==403
                with qa_resource_grants(self.state,['/fund/receipt/import'],[role]):
                    assert self.preview_import(rows).get('code')==403
                    with qa_resource_grants(self.state,['/fund/receipt/add'],[role]):
                        plan=self.prepared(rows);response=self.import_rows(rows,plan['version']);assert response.get('code')==10000
                        assert all(sql(self.state,'SELECT `user` FROM imy WHERE id='+literal(identifier)+';')==user for identifier in response['data']['ids'])
                assert self.preview_import(rows).get('code')==403
            finally:self.token=admin
            self.unchanged_receipt()
            return ['Actual ordinary OAuth requires current import and creation grants; complete drafts record actual operator, same token loses revoked import access']
        self.case('receipt.import_actual_live_grants',grants)
        def competing():
            rows=self.rows();plan=self.prepared(rows)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.import_rows(rows,plan['version']),range(2)))
            assert sum(result.get('code')==10000 for result in results)==1
            assert all(self.count_receipt(row['number'])==1 for row in rows)
            assert sql(self.state,'SELECT COUNT(*) FROM imy_info WHERE account='+literal(self.account)+';')=='3'
            self.unchanged_receipt();return ['Two real simultaneous confirmations of one reviewed two-document batch commit exactly one complete batch, without duplicates, orphan details or funds']
        self.case('receipt.import_concurrent_reviewed_batch_single_commit',competing)
        def period_and_actor():
            rows=self.rows();plan=self.prepared(rows);period=uuid.uuid4().hex
            sql(self.state,'INSERT INTO period(id,date,time,`user`) VALUES('+','.join(literal(value) for value in [period,'2026-11-16','2026-11-16',self.actor])+');')
            try:
                assert self.preview_import(rows).get('code')!=10000 and self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
            finally:sql(self.state,'DELETE FROM period WHERE id='+literal(period)+';')
            original=self.token;user_id,user,_=self.new_user()
            sql(self.state,"UPDATE `user` SET role='0' WHERE id="+literal(user_id)+';')
            from purchase_ui_acceptance import PurchaseUiSuite
            try:
                self.token=PurchaseUiSuite.login(self,user)
                assert self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
                own=self.prepared(rows);assert own['version']!=plan['version']
                result=self.import_rows(rows,own['version']);assert result.get('code')==10000
                assert all(sql(self.state,'SELECT `user` FROM imy WHERE id='+literal(identifier)+';')==user_id for identifier in result['data']['ids'])
            finally:self.token=original
            self.unchanged_receipt();return ['A period closed after preview refuses the whole import; another fresh explicitly prepared QA administrator must obtain its own real reviewed version and resulting drafts record that actual actor']
        self.case('receipt.import_closed_period_and_actual_reviewer_binding',period_and_actor)
        def bounds_and_scope():
            rows=self.rows();frame=uuid.uuid4().hex
            sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Receipt Import Foreign');")
            for table,identifier in [('customer',self.customer),('account',self.account)]:
                sql(self.state,'UPDATE '+table+' SET frame='+literal(frame)+' WHERE id='+literal(identifier)+';')
                try:assert self.preview_import(rows).get('code')!=10000;self.absent(rows)
                finally:sql(self.state,'UPDATE '+table+' SET frame='+literal(self.state['frame_id'])+' WHERE id='+literal(identifier)+';')
            assert self.preview_import([dict(rows[0]) for _ in range(1001)]).get('code')!=10000
            assert self.preview_import([dict(rows[0]) for _ in range(201)]).get('code')!=10000
            self.absent(rows);return ['Actual foreign customer/account business codes refuse even for admin creating in its own organization; >1000 batch rows or >200 rows per document cannot persist anything']
        self.case('receipt.import_reference_org_and_size_limits',bounds_and_scope)
        self.write_report()

if __name__=='__main__':ReceiptImportSuite(read_state()).run()
