"""Real UUID legacy inbound endpoints; no business writes on normal services."""
import argparse,uuid,json
from stock_role_integration_acceptance import StockRoleSuite,ENTRY
from acceptance import QA,read_state,sql,literal

class InboundLegacySuite(StockRoleSuite):
    def command(self,identifier,target=None):
        body=dict(ids=[identifier],versions={identifier:self.detail(identifier)['version']})
        if target is not None:body['target']=target
        return body
    def mutate(self,action,body):
        return self.request('DELETE' if action=='delete' else 'PUT','/otherin/'+action,body,service='store')
    def run(self,baseline=False):
        with self.catalog():
            def check_uuid():
                self.fixture(stock=0);identifier,_=self.create_inbound();result=self.mutate('check',self.command(identifier,1))
                assert result.get('code')==10000,str(result)
                assert sql(self.state,'SELECT CAST(`check` AS SIGNED) FROM entry WHERE id='+literal(identifier)+';')=='1'
                assert self.inventory()==0
                return ['Actual UUID command checks persisted draft without changing stock']
            self.case('inbound.legacy_uuid_explicit_check',check_uuid)
            def audit_uuid():
                self.fixture(stock=0);identifier,_=self.create_inbound();result=self.mutate('examine',self.command(identifier,1))
                assert result.get('code')==10000,str(result)
                assert self.inventory()==4
                assert self.mutate('examine',self.command(identifier,0)).get('code')==10000
                assert self.inventory()==0
                return ['Actual UUID explicit audit/reverse uses real stock and original proof, restores0']
            self.case('inbound.legacy_uuid_post_reverse',audit_uuid)
            def delete_uuid():
                self.fixture(stock=0);identifier,_=self.create_inbound();before=int(sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+';'))
                result=self.mutate('delete',self.command(identifier));assert result.get('code')==10000,str(result)
                assert sql(self.state,'SELECT COUNT(*) FROM entry WHERE id='+literal(identifier)+';SELECT COUNT(*) FROM entry_info WHERE pid='+literal(identifier)+';')=='0\n0'
                assert int(sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+';'))==before+1
                assert self.inventory()==0
                return ['Actual UUID physical draft deletion removes all lines, retains original history and appends signed deletion evidence; stock0']
            self.case('inbound.legacy_uuid_delete_history',delete_uuid)
            def denied_detail():
                self.fixture(stock=0);identifier,_=self.create_inbound();self.role_fixture();self.token=self.ordinary
                try:
                    result=self.request('GET','/otherin/detail?id='+identifier,service='store')
                    assert result.get('code')==403,'Legacy detail ignores missing function grant: '+str(result.get('code'))
                    return ['Actual ungranted ordinary OAuth actor cannot use old detail endpoint to bypass183']
                finally:self.token=self.admin;self.select([])
            self.case('inbound.legacy_detail_requires_function',denied_detail)
            def denied_list():
                self.fixture(stock=0);_,payload=self.create_inbound();self.role_fixture();self.token=self.ordinary
                try:
                    result=self.request('GET','/otherin?number='+payload['number'],service='store')
                    assert result.get('code')==403,'Legacy list did not check182 before querying: '+str(result.get('code'))
                    return ['Actual ungranted ordinary OAuth actor cannot bypass182 through old list']
                finally:self.token=self.admin;self.select([])
            self.case('inbound.legacy_list_requires_function',denied_list)
            if not baseline:
                def checked_lifecycle():
                    self.fixture(stock=0);identifier,payload=self.create_inbound()
                    original=self.command(identifier,1);assert self.mutate('check',original).get('code')==10000
                    checked=self.detail(identifier);count=sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+';')
                    assert self.mutate('check',self.command(identifier,1)).get('code')==10000
                    assert sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+';')==count
                    assert self.mutate('check',original).get('code')!=10000
                    payload.update(id=identifier,version=checked['version'])
                    assert self.request('PUT','/otherin/update',payload,service='store').get('code')!=10000
                    assert self.request('PUT','/transfer/report-documents/entry/'+identifier,checked,service='store').get('code')!=10000
                    assert self.mutate('examine',self.command(identifier,1)).get('code')==10000
                    assert self.inventory()==4
                    assert self.mutate('check',self.command(identifier,0)).get('code')!=10000
                    assert self.mutate('delete',self.command(identifier)).get('code')!=10000
                    assert self.mutate('examine',self.command(identifier,0)).get('code')==10000
                    assert self.inventory()==0
                    assert self.mutate('check',self.command(identifier,0)).get('code')==10000
                    assert self.mutate('delete',self.command(identifier)).get('code')==10000
                    return ['Real draft -> check -> audit -> reverse -> uncheck -> physical delete; edits blocked while checked; fresh repeat check adds no history; stale command rejected; stock0->4->0']
                self.case('inbound.checked_cross_entry_lifecycle',checked_lifecycle)
                def protocol():
                    self.fixture(stock=0);identifier,_=self.create_inbound();original=self.detail(identifier)
                    valid=self.command(identifier,1);invalid=[{},dict(valid,target=None),dict(valid,target=1.5),dict(valid,target='1'),dict(valid,ids=[123]),dict(valid,ids=[identifier,identifier]),dict(valid,versions={})]
                    for body in invalid:assert self.mutate('check',body).get('code')!=10000,str(body)
                    assert self.detail(identifier)['version']==original['version'] and self.inventory()==0
                    return ['Actual HTTP rejects absent target/version, fractional/string target, numeric/duplicate IDs; draft and stock unchanged']
                self.case('inbound.explicit_protocol_no_coercion',protocol)
                def batch_atomic():
                    self.fixture(stock=0);first,_=self.create_inbound();second,_=self.create_inbound();stale=self.command(second,1)
                    assert self.mutate('check',stale).get('code')==10000
                    body=self.command(first,1);body['ids'].append(second);body['versions'].update(stale['versions'])
                    before=self.detail(first)['version'];assert self.mutate('check',body).get('code')!=10000
                    assert self.detail(first)['version']==before and self.inventory()==0
                    delete=self.command(first);delete['ids'].append(second);delete['versions'].update(self.command(second)['versions'])
                    assert self.mutate('delete',delete).get('code')!=10000
                    assert sql(self.state,'SELECT COUNT(*) FROM entry WHERE id IN ('+literal(first)+','+literal(second)+');')=='2'
                    assert self.mutate('check',self.command(second,0)).get('code')==10000
                    delete=self.command(first);delete['ids'].append(second);delete['versions'].update(self.command(second)['versions'])
                    assert self.mutate('delete',delete).get('code')==10000
                    assert sql(self.state,'SELECT COUNT(*) FROM entry_info WHERE pid IN ('+literal(first)+','+literal(second)+');')=='0'
                    return ['Multi-document stale check and checked deletion reject entire batch; after uncheck both headers/children are atomically deleted']
                self.case('inbound.batch_versions_and_delete_atomicity',batch_atomic)
                def scoped_reads():
                    self.fixture(stock=0);identifier,payload=self.create_inbound();self.role_fixture();self.select(['182','183']);self.token=self.ordinary
                    foreign=uuid.uuid4().hex
                    sql(self.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(foreign)+",'0','QA Inbound Foreign');")
                    try:
                        response=self.request('GET','/otherin?number='+payload['number']+'&startTime=2026-11-14&endTime=2026-11-14&frame='+foreign,service='store')
                        assert response.get('code')==10000,str(response)
                        assert [r['id'] for r in response['data']['rows']]==[identifier], 'Expected own dated document: '+str(response)
                        detail=self.request('GET','/otherin/detail?id='+identifier,service='store');assert detail.get('code')==10000,str(detail)
                        assert detail['data']['header']['cse']==3 and type(detail['data']['header']['type']) is int and detail['data']['header']['type']==0,'Numeric fee/type states must not become JSON booleans'
                        assert len(detail['data']['items'])==1 and detail['data']['version']==self.detail_as_admin(identifier)['version'], 'Detail incomplete or inconsistent version: '+str(detail)
                        sql(self.state,'UPDATE entry SET frame='+literal(foreign)+' WHERE id='+literal(identifier)+';')
                        refused=self.request('GET','/otherin/detail?id='+identifier,service='store');assert refused.get('code')==403,str(refused)
                        hidden=self.request('GET','/otherin?number='+payload['number'],service='store');assert hidden['data']['total']==0,str(hidden)
                        return ['Real182/183 independently granted via C1: dated list and full detail work; query frame cannot override signed org; foreign document excluded and detail403']
                    finally:self.token=self.admin;sql(self.state,'UPDATE entry SET frame='+literal(self.state['frame_id'])+' WHERE id='+literal(identifier)+';');self.select([])
                self.case('inbound.authorized_dates_details_and_org_scope',scoped_reads)
                def late_delete_failure():
                    self.fixture(stock=0);identifier,_=self.create_inbound();command=self.command(identifier);before=self.detail(identifier);trigger='qa_in_delete_'+uuid.uuid4().hex[:12]
                    sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+"` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source="+literal(identifier)+" AND NEW.info='删除入库草稿' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA owned deletion rollback'; END IF; END$$\nDELIMITER ;\n")
                    try:assert self.mutate('delete',command).get('code')!=10000
                    finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
                    assert self.detail(identifier)['version']==before['version'] and len(self.detail(identifier)['items'])==1
                    assert self.mutate('delete',command).get('code')==10000 and self.inventory()==0
                    return ['Real MySQL late history INSERT failure rolls header/children deletion back; identical original version succeeds after removing owned trigger']
                self.case('inbound.physical_delete_late_failure_rolls_back',late_delete_failure)
                def only_action_grants():
                    self.fixture(stock=0);identifier,_=self.create_inbound();self.role_fixture()
                    try:
                        self.select(['184']);self.token=self.ordinary
                        options=self.request('GET','/otherin/options',service='store');assert options.get('code')==10000,str(options)
                        assert any(row['id']==self.warehouse and row.get('number') for row in options['data']['warehouses'])
                        for grant,action,target in [('187','check',1),('188','examine',1),('188','examine',0),('187','check',0),('185','delete',None)]:
                            self.token=self.admin;body=self.command(identifier,target);self.select([grant]);self.token=self.ordinary
                            result=self.mutate(action,body);assert result.get('code')==10000,str(result)
                        assert self.inventory()==0
                        assert sql(self.state,'SELECT COUNT(*) FROM record WHERE source='+literal(identifier)+' AND `user`='+literal(self.user_id)+';')=='5'
                        return ['Same actual ordinary account needs only187/188/185 for its command; no hidden detail183/edit186 grant; signed history five operations, stock restored0']
                    finally:self.token=self.admin;self.select([])
                self.case('inbound.commands_no_hidden_read_edit_grants',only_action_grants)
        self.write_report()

    def detail_as_admin(self,identifier):
        previous=self.token;self.token=self.admin
        try:return self.detail(identifier)
        finally:self.token=previous

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');parser.add_argument('--gateway',action='store_true');args=parser.parse_args();InboundLegacySuite(read_state(),args.gateway).run(args.baseline)
