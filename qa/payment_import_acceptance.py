"""Real reviewed complete-draft import, grouping and batch transaction gates."""
import copy
import uuid
import re
from payment_document_scope_acceptance import PaymentDocumentScopeSuite
from resource_fixture import qa_resource_grants
from acceptance import read_state,sql,literal

class PaymentImportSuite(PaymentDocumentScopeSuite):
    def rows(self):
        self.fixture();supplier=sql(self.state,'SELECT number FROM supplier WHERE id='+literal(self.supplier)+';');account=sql(self.state,'SELECT number FROM account WHERE id='+literal(self.account)+';')
        first='QAIMP'+uuid.uuid4().hex[:24];second='QAIMP'+uuid.uuid4().hex[:24]
        rows=[dict(number=first,date='2026-11-15',supplierNumber=supplier,accountNumber=account,money=10,settle='QA bank',remark='QA complete import',lineRemark='QA first')]
        rows.append(dict(rows[0],money=15,lineRemark='QA second'));rows.append(dict(rows[0],number=second,money=20,lineRemark='QA third'))
        return rows
    def preview_import(self,rows):return self.request('POST','/payment-order/import-preview',dict(rows=rows),service='payment')
    def import_rows(self,rows,version):return self.request('POST','/payment-order/addmore',dict(rows=rows,version=version),service='payment')
    def prepared(self,rows):
        response=self.preview_import(rows);assert response.get('code')==10000,str(response);return response['data']
    def absent(self,rows):
        assert all(self.count_payment(row['number'])==0 for row in rows)
        assert sql(self.state,'SELECT COUNT(*) FROM omy_info WHERE account='+literal(self.account)+';')=='0';self.unchanged()
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
            assert all(self.count_payment(row['number'])==1 for row in rows);self.unchanged()
            return ['Actual three template rows group into two complete real drafts with correct totals/parent IDs/actor and no funds; repeated readonly preview stable, duplicate commit cannot create extra drafts']
        self.case('payment.import_complete_grouped_drafts',grouping)

        def invalid():
            rows=self.rows();plan=self.prepared(rows)
            for field,value in [('supplierNumber','missing'),('accountNumber','missing'),('money',-1),('money','0.00001'),('date','bad'),('remark','different header')]:
                bad=copy.deepcopy(rows);bad[1][field]=value
                assert self.preview_import(bad).get('code')!=10000
                assert self.import_rows(bad,plan['version']).get('code')!=10000;self.absent(rows)
            assert self.import_rows(rows,None).get('code')!=10000;self.absent(rows)
            response=self.request('POST','/payment-order/addmore',[dict(account=self.account,money=10,settle='QA orphan')],service='payment')
            assert response.get('code')!=10000;self.absent(rows)
            return ['Unknown master codes, inconsistent same-number header, invalid money/date, missing reviewed version and old unattached-row payload cannot persist partial or orphan rows']
        self.case('payment.import_invalid_batch_and_legacy_orphan_denied',invalid)

        def stale():
            rows=self.rows();plan=self.prepared(rows);changed=copy.deepcopy(rows);changed[0]['money']=11
            assert self.import_rows(changed,plan['version']).get('code')!=10000;self.absent(rows)
            original=rows[0]['accountNumber'];sql(self.state,'UPDATE account SET number='+literal('QA_CHANGED'+uuid.uuid4().hex[:12])+' WHERE id='+literal(self.account)+';')
            try:assert self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
            finally:sql(self.state,'UPDATE account SET number='+literal(original)+' WHERE id='+literal(self.account)+';')
            assert self.import_rows(rows,plan['version']).get('code')==10000;self.unchanged()
            return ['Changed reviewed input or account code refuses without any draft; restoring unchanged master data permits exact original reviewed batch retry']
        self.case('payment.import_reviewed_input_and_master_revalidation',stale)

        def storage():
            rows=self.rows();plan=self.prepared(rows);marker=rows[-1]['lineRemark'];trigger='qa_imp_'+uuid.uuid4().hex[:12]
            sql(self.state,"DELIMITER $$\nCREATE TRIGGER `"+trigger+"` BEFORE INSERT ON omy_info FOR EACH ROW BEGIN IF NEW.account="+literal(self.account)+' AND NEW.data='+literal(marker)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA whole import fault'; END IF; END$$\nDELIMITER ;")
            try:
                assert self.import_rows(rows,plan['version']).get('code')!=10000;self.absent(rows)
                assert sql(self.state,"SELECT COUNT(*) FROM `log` WHERE info LIKE "+literal('%'+rows[0]['number']+'%')+';')=='0'
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.import_rows(rows,plan['version']).get('code')==10000;self.unchanged()
            return ['Actual second-document detail insert failure rolls back first complete document, both headers/details and history/log; same reviewed batch retries after fault removal']
        self.case('payment.import_entire_batch_storage_rollback',storage)

        def grants():
            rows=self.rows();user,token,role=self.role_user();admin=self.token;self.token=token
            try:
                assert self.preview_import(rows).get('code')==403
                with qa_resource_grants(self.state,['/payment-order/addmore'],[role]):
                    assert self.preview_import(rows).get('code')==403
                    with qa_resource_grants(self.state,['/payment-order/add'],[role]):
                        plan=self.prepared(rows);response=self.import_rows(rows,plan['version']);assert response.get('code')==10000
                        assert all(sql(self.state,'SELECT `user` FROM omy WHERE id='+literal(identifier)+';')==user for identifier in response['data']['ids'])
                assert self.preview_import(rows).get('code')==403
            finally:self.token=admin
            self.unchanged()
            return ['Actual ordinary OAuth requires current import and creation grants; complete drafts record actual operator, same token loses revoked import access']
        self.case('payment.import_actual_live_grants',grants)
        self.write_report()

if __name__=='__main__':PaymentImportSuite(read_state()).run()
