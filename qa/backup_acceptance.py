"""Real authorized SQL download and restore into a new disposable QA database."""
import argparse
import hashlib
import json
import re
import uuid
import urllib.request
from purchase_posting_acceptance import PurchasePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from acceptance import QA,read_state,sql,literal,integrity


class BackupSuite(PurchasePostingSuite):
    def backup(self,path='download',token=None):
        assert self.state['homepage_port']==18025
        request=urllib.request.Request('http://127.0.0.1:18025/homepage/system/backup/'+path,headers={'Authorization':'Bearer '+(self.token if token is None else token)})
        with self.opener.open(request,timeout=150) as response:
            return response.read(),dict(response.headers)

    def table_counts(self,state):
        tables=sql(state,"SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name;").splitlines()
        assert tables and all(re.fullmatch('[A-Za-z0-9_]+',table) for table in tables)
        statement=' UNION ALL '.join('SELECT '+literal(table)+',COUNT(*) FROM `'+table+'`' for table in tables)+';'
        return sql(state,statement)

    def business(self,state,identifier):
        return sql(state,'SELECT CONCAT(examine,\':\',total,\':\',actual) FROM buy WHERE id='+literal(identifier)+';'+
            'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(self.warehouse)+';'+
            'SELECT balance FROM account WHERE id='+literal(self.account)+';'+
            'SELECT balance FROM supplier WHERE id='+literal(self.supplier)+';')

    def attachments(self,state):
        result={}
        for table,parent in [('psi_bor_attachment','order_id'),('psi_buy_attachment','purchase_id')]:
            result[table]=sql(state,'SELECT id,'+parent+',name,file_size,sha256,SHA2(body,256),user_id,created_at,removed_at,removed_by FROM '+table+' ORDER BY id;')
        return result

    def run(self):
        def permissions():
            _,user,_=self.new_user();token=PurchaseUiSuite.login(self,user)
            for path in ['status','download']:
                assert json.loads(self.backup(path,token)[0]).get('code')==403,'Non-admin could access full backup'
                assert json.loads(self.backup(path,'')[0]).get('code')==401,'Unsigned backup request accepted'
            return ['Real OAuth non-admin and unsigned requests cannot query backup status or download the database']
        self.case('backup.actual_admin_only',permissions)

        def status():
            result=json.loads(self.backup('status')[0]);assert result.get('code')==10000,result.get('message','Status failed')
            assert result['data']['database']==self.state['database'] and result['data']['tables']>0
            return ['Actual admin status identifies the QA datasource and verifies Docker MySQL server identity']
        self.case('backup.actual_environment_status',status)

        def revoked():
            # Only the newly created QA actor loses its fixture admin role.
            sql(self.state,'UPDATE `user` SET role='+literal(self.state['role_id'])+' WHERE id='+literal(self.actor)+';')
            try:
                for path in ['status','download']:assert json.loads(self.backup(path)[0]).get('code')==403
            finally:sql(self.state,"UPDATE `user` SET role='0' WHERE id="+literal(self.actor)+';')
            assert json.loads(self.backup('status')[0]).get('code')==10000
            return ['The same signed token immediately loses backup access when its current database admin role is removed; only the new QA actor is changed and restored']
        self.case('backup.live_admin_revocation',revoked)

        def restore():
            self.fixture();identifier=self.create_document(paid=25)
            # Actual uploads ensure this standalone restore suite contains both new binary tables.
            from purchase_attachment_acceptance import PurchaseAttachmentSuite
            from booking_attachment_acceptance import AttachmentSuite
            uploaded=PurchaseAttachmentSuite.upload(self,identifier,version=self.document(identifier)['version'],data=b'QA backup receipt\x00\xff',name='QA backup receipt.txt')
            assert uploaded.get('code')==10000
            order_files=AttachmentSuite(self.state);order=order_files.fresh();item=order_files.added(order,data=b'QA backup order\x00\xff',name='QA backup order.txt')
            assert order_files.remove(order,item['id']).get('code')==10000
            assert self.check([identifier]).get('code')==10000 and self.post([identifier]).get('code')==10000
            marker='qa_backup_'+uuid.uuid4().hex[:12];trigger=marker+'_trg'
            sql(self.state,'CREATE TABLE `'+marker+'` (id INT PRIMARY KEY,txt TEXT,amount DECIMAL(16,4),bytes LONGBLOB) ENGINE=InnoDB;'+
                'CREATE TRIGGER `'+trigger+'` BEFORE INSERT ON `'+marker+'` FOR EACH ROW SET NEW.amount=NEW.amount+1;'+
                'INSERT INTO `'+marker+'` VALUES(1,'+literal('QA备份 中文 quote\' slash\\ newline\n')+',12.3456,0x0001FF5C);')
            restored='psi_qa_'+uuid.uuid4().hex[:12];created=False
            try:
                before=self.business(self.state,identifier);counts=self.table_counts(self.state)
                attachment_before=self.attachments(self.state);assert all(attachment_before.values())
                marker_before=sql(self.state,'SELECT HEX(txt),amount,HEX(bytes) FROM `'+marker+'`;')
                data,headers=self.backup()
                assert data.startswith(b'-- MySQL dump') and b'CREATE TABLE' in data
                digest=next((value for key,value in headers.items() if key.lower()=='x-backup-sha256'),None)
                assert digest==hashlib.sha256(data).hexdigest(),'Backup integrity header mismatch'
                text=data.decode('utf-8');assert not re.search(r'(?im)^\s*(?:USE\s|CREATE\s+DATABASE|DROP\s+DATABASE)',text),'Dump would select or overwrite another database'
                (QA/'runtime/backup-acceptance.sql').write_bytes(data)
                assert re.fullmatch('psi_qa_[0-9a-f]{12}',restored) and restored!=self.state['database']
                integrity.query(self.state['container'],None,'CREATE DATABASE `'+restored+'` CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci;');created=True
                target=dict(self.state,database=restored)
                sql(target,text)
                assert self.table_counts(target)==counts,'Restored table set/counts differ from actual backup source'
                assert self.business(target,identifier)==before,'Restored real stock/cash/payable/document state differs'
                assert self.attachments(target)==attachment_before,'Restored attachment bytes/metadata/operators/removal flags differ'
                assert sql(target,'SELECT HEX(txt),amount,HEX(bytes) FROM `'+marker+'`;')==marker_before,'Unicode/binary/decimal values not restored exactly'
                assert sql(target,'SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema=DATABASE() AND trigger_name='+literal(trigger)+';')=='1'
                sql(target,'INSERT INTO `'+marker+'` VALUES(2,\'restored trigger\',1,0xFF);')
                assert sql(target,'SELECT amount FROM `'+marker+'` WHERE id=2;')=='2.0000','Restored trigger is not functional'
                assert self.business(self.state,identifier)==before and self.table_counts(self.state)==counts,'Backup or restore modified the source'
                return ['Actual SQL file and SHA256 valid; restored all base-table counts into a new isolated database', 'Both actual-uploaded attachment tables preserve every binary SHA256, metadata, operator and logical-removal flag', 'Real audited purchase stock/cash/payable state and exact Unicode/binary/decimal content preserved; restored trigger executes; original source unchanged']
            finally:
                if created:
                    assert re.fullmatch('psi_qa_[0-9a-f]{12}',restored) and restored!=self.state['database']
                    integrity.query(self.state['container'],None,'DROP DATABASE `'+restored+'`;')
                sql(self.state,'DROP TABLE IF EXISTS `'+marker+'`;')
        self.case('backup.real_download_and_independent_restore',restore)
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','unavailable'],nargs='?',default='run')
    action=parser.parse_args().action
    if action=='prepare':
        suite=BackupSuite(read_state());(QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8');print('Prepared actual isolated administrator browser session')
    elif action=='unavailable':
        suite=BackupSuite(read_state())
        def unavailable():
            for path in ['status','download']:
                result=json.loads(suite.backup(path)[0]);assert result.get('code')==503 and '备份工具执行失败' in result.get('message','')
            return ['Actual missing QA backup container produces actionable failure for status/download, never a successful SQL file']
        suite.case('backup.actual_tool_failure',unavailable);suite.write_report()
    else:BackupSuite(read_state()).run()
