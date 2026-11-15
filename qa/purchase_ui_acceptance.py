"""Real procurement query/data-scope acceptance and browser fixture SQL verification."""
import argparse
import json
import uuid
import urllib.request
import urllib.parse
import io
import zipfile
from decimal import Decimal
from purchase_revision_acceptance import PurchaseRevisionSuite
from acceptance import QA,read_state,sql,literal


class PurchaseUiSuite(PurchaseRevisionSuite):
    def login(self,user):
        client=json.loads((QA/'runtime/oauth-client.json').read_text(encoding='utf-8'))
        request=urllib.request.Request('http://127.0.0.1:18002/oauth/token',data=urllib.parse.urlencode(dict(grant_type='password',client_id=client['mgr-id'],client_secret=client['mgr-password'],username=user['user'],password=user['pwd'])).encode())
        with self.opener.open(request,timeout=20) as response: result=json.load(response)
        assert result.get('access_token') or result.get('token'),'Actual QA sign-in failed'
        return result.get('access_token') or result['token']

    def run(self):
        def associated():
            identifier=self.draft();number=sql(self.state,'SELECT number FROM buy WHERE id='+literal(identifier)+';')
            expense,kind,invoice,bill=[uuid.uuid4().hex for _ in range(4)]
            sql(self.state,'INSERT INTO iet(id,name,type,sort) VALUES('+','.join(literal(v) for v in [kind,'QA Purchase Expense',1,0])+');'+
                'INSERT INTO cost(id,type,`class`,time,iet,money,settle,state) VALUES('+','.join(literal(v) for v in [expense,'buy',identifier,'2026-11-15',kind,5,0,0])+');'+
                'INSERT INTO invoice(id,type,`class`,time,number,title,money) VALUES('+','.join(literal(v) for v in [invoice,'buy',identifier,'2026-11-15','QA Invoice '+invoice[:8],'QA Invoice Title',10])+');'+
                'INSERT INTO buy_bill(id,pid,type,source,time,money) VALUES('+','.join(literal(v) for v in [bill,identifier,'buy',identifier,'2026-11-15',30])+');')
            result=self.request('GET','/purchase-note/list?number='+number,service='purchase')
            assert result.get('code')==10000 and len(result['data']['rows'])==1
            row=result['data']['rows'][0]
            assert row['supplierName']=='QA Purchase Supplier' and row.get('frameName') and row.get('userName')
            assert Decimal(str(row['billMoney']))==30 and row['stockRecords']==0
            document=self.document(identifier)
            assert len(document['settlements'])==len(document['expenses'])==len(document['invoices'])==1
            assert document['settlements'][0]['sourceNumber']==number and Decimal(str(document['settlements'][0]['money']))==30
            assert document['expenses'][0]['expenseName']=='QA Purchase Expense' and Decimal(str(document['expenses'][0]['money']))==5
            assert document['invoices'][0]['title']=='QA Invoice Title'
            return ['SQL-only associated-record fixtures; actual list and complete read return names, settlement totals and correct expense/invoice records', 'These are query assertions, not procurement stock or financial posting acceptance']
        self.case('purchase.ui_real_names_and_associated_queries',associated)

        def scope():
            foreign,warehouse,supplier=[uuid.uuid4().hex for _ in range(3)]
            sql(self.state,'INSERT INTO frame(id,pid,name,sort) VALUES('+','.join(literal(v) for v in [foreign,'0','QA Other Purchase Org',0])+');'+
                'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [warehouse,'QA Branch Warehouse','QW'+warehouse[:16],foreign])+');'+
                'INSERT INTO supplier(id,name,py,number,frame,`user`,category) VALUES('+','.join(literal(v) for v in [supplier,'QA Branch Supplier','qa','QS'+supplier[:16],foreign,self.actor,'0'])+');')
            foreign_id,foreign_user,_=self.new_user(frame=foreign)
            own_id,own_user,_=self.new_user()
            admin=self.token
            try:
                self.token=self.login(foreign_user)
                body=self.body();body['purchaseNoteBuyDTO']['supplier']=supplier
                body['purchaseNoteInfoDTOS'][0].update(warehouse=warehouse,tax=13,discount=0,batch='',mfd=None,serial='[]')
                identifier=self.create(body)
                assert self.document(identifier)['header']['frame']==foreign
                self.token=admin
                edit=self.revision(identifier);edit['supplier']=supplier;edit['details'][0]['warehouse']=warehouse
                own_token=self.login(own_user)
                self.token=own_token
                assert self.request('GET','/purchase-note/document/'+identifier,service='purchase').get('code')==403
                listing=self.request('GET','/purchase-note/list?number='+body['purchaseNoteBuyDTO']['number'],service='purchase')
                assert listing.get('code')==10000 and isinstance(listing.get('data'),dict)
                assert not listing['data'].get('rows') and listing['data'].get('total')==0
                assert self.revise(edit).get('code')==403
                own=self.draft()
                assert self.document(own)['header']['frame']==self.state['frame_id']
                # Only this newly created QA account moves organizations; the same signed token is reused.
                self.token=admin
                self.success('PUT','/user/mod-user',dict(id=own_id,frame=foreign))
                self.token=own_token
                assert self.request('GET','/purchase-note/document/'+own,service='purchase').get('code')==403
                assert self.document(identifier)['header']['frame']==foreign
                self.token=admin
                assert self.revise(edit).get('code')==10000
                after=self.document(identifier)
                assert after['header']['frame']==foreign and after['header']['user']==foreign_id
                assert Decimal(str(after['items'][0]['nums']))==3
            finally:
                self.token=admin
            return ['Actual non-admin OAuth users create/read in their own organizations; foreign list/read/write denied', 'Moving only a new QA user changes data scope with its existing token; actual administrator can read/edit another organization without moving ownership', 'Function-level grants are a separate pending gate']
        self.case('purchase.ui_actual_organization_data_scopes',scope)

        def export():
            identifier=self.draft();number=self.document(identifier)['header']['number']
            assert self.state['purchase_port']==18023
            request=urllib.request.Request('http://127.0.0.1:18023/purchase-note/export/simple?ids='+identifier,headers={'Authorization':'Bearer '+self.token})
            with self.opener.open(request,timeout=30) as response: data=response.read()
            assert data[:2]==b'PK','Export did not return an actual XLSX archive'
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                assert any(name.startswith('xl/worksheets/') for name in archive.namelist())
                assert any(number.encode() in archive.read(name) for name in archive.namelist() if name.endswith('.xml')),'Export is missing the actual selected purchase number'
            (QA/'reports/purchase-ui-simple-export.xlsx').write_bytes(data)
            return ['Actual XLSX export archive contains worksheet data and the selected persisted purchase number']
        self.case('purchase.ui_actual_simple_export_content',export)

        def metadata():
            product=uuid.uuid4().hex;attribute=uuid.uuid4().hex
            sql(self.state,'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,batch,more) VALUES('+','.join(literal(v) for v in [product,'QA Batch Purchase Goods','qa','QG'+product[:16],'0','unit',100,120,0,0,1,'{}'])+');'+
                'INSERT INTO attr(id,pid,name,buy,sell) VALUES('+','.join(literal(v) for v in [attribute,product,'QA Attribute',100,120])+');')
            body=self.body();body['purchaseNoteInfoDTOS'][0].update(goods=product,batch='QA-B1',mfd='2026-11-01',serial='[]',discount=0,tax=13)
            identifier=self.create(body);edit=self.revision(identifier);edit['details'][0]['goods']=product
            edit['details'].append(dict(edit['details'][0],id=None,nums=2,attr='QA Attribute',batch='QA-B2',mfd='2026-11-02',serial='["QA-S1","QA-S2"]',source='0'))
            assert self.revise(edit).get('code')==10000
            document=self.document(identifier)
            assert len(document['items'])==2
            added=[item for item in document['items'] if item.get('batch')=='QA-B2']
            assert len(added)==1 and added[0]['attr']=='QA Attribute' and str(added[0]['mfd']).startswith('2026-11-02')
            assert json.loads(added[0]['serial'])==['QA-S1','QA-S2']
            assert sql(self.state,'SELECT COUNT(*) FROM room WHERE goods='+literal(product)+';')=='0'
            return ['Actual full-draft add persists selected attribute, batch, date and serial metadata; draft does not create stock']
        self.case('purchase.ui_new_line_metadata_persists',metadata)
        self.write_report()


fixture_path=QA/'runtime/purchase-browser-document.json'


def prepare():
    suite=PurchaseRevisionSuite(read_state());body=suite.body()
    body['purchaseNoteBuyDTO']['time']='2026-11-15 13:47:00'
    body['purchaseNoteInfoDTOS'][0].update(tax=13,discount=0,batch='',mfd=None,serial='[]')
    identifier=suite.create(body)
    fixture={key:getattr(suite,key) for key in ['goods','warehouse','supplier','actor']}
    fixture.update(database=suite.state['database'],id=identifier,number=body['purchaseNoteBuyDTO']['number'],file=body['purchaseNoteBuyDTO']['file'])
    fixture_path.write_text(json.dumps(fixture),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
    print('Prepared isolated procurement browser document: '+fixture['number'])


def verify(quantity):
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert fixture['database']==state['database']
    identifier=literal(fixture['id'])
    line=sql(state,'SELECT CONCAT(nums,\',\',total,\',\',tpt) FROM buy_info WHERE pid='+identifier+';')
    assert list(map(Decimal,line.split(',')))==list(map(Decimal,[str(quantity),str(quantity*100),str(quantity*113)]))
    header=sql(state,"SELECT CONCAT(total,',',actual,',',money,',',DATE_FORMAT(time,'%H:%i:%s')) FROM buy WHERE id="+identifier+';').split(',')
    assert list(map(Decimal,header[:3]))==list(map(Decimal,[str(quantity*100),str(quantity*113),'0'])) and header[3]=='13:47:00'
    assert sql(state,'SELECT `user` FROM buy WHERE id='+identifier+';')==fixture['actor']
    assert sql(state,'SELECT file FROM buy WHERE id='+identifier+';')==fixture['file']
    assert sql(state,'SELECT IF(account IS NULL AND people IS NULL,1,0) FROM buy WHERE id='+identifier+';')=='1'
    assert sql(state,'SELECT COUNT(*) FROM room WHERE goods='+literal(fixture['goods'])+';')=='0'
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(fixture['supplier'])+';'))==0
    for table in ['room_info','account_info']:
        assert sql(state,"SELECT COUNT(*) FROM "+table+" WHERE type='buy' AND `class`="+identifier+';')=='0'
    result=dict(case='purchase.browser_saved' if quantity==3 else 'purchase.browser_conflict_not_overwritten',quantity=quantity,status='verified',all_system_features_accepted=False,production_business_writes=0)
    (QA/('reports/purchase-browser-'+str(quantity)+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS browser procurement SQL: quantity='+str(quantity)+'; matching amounts, original creator/time/files, zero payment, no stock or payable movement')


def advance():
    state=read_state();fixture=json.loads(fixture_path.read_text(encoding='utf-8'))
    assert state['purchase_port']==18023 and fixture['database']==state['database']
    token=json.loads((QA/'runtime/browser-session.json').read_text(encoding='utf-8'))['token']
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(method,path,body=None):
        req=urllib.request.Request('http://127.0.0.1:18023'+path,method=method,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with opener.open(req,timeout=20) as response: result=json.load(response)
        assert result.get('code')==10000,'Actual concurrent editor request failed'
        return result['data']
    document=request('GET','/purchase-note/document/'+fixture['id'])
    body=dict(id=fixture['id'],version=document['version'],time=document['header']['time_text'],number=document['header']['number'],data='QA concurrent purchase revision',details=[dict(id=item['id'],goods=item['goods'],unit=item['unit'],warehouse=item['warehouse'],price=item['price'],nums=5,discount=0,tax=13,data=item.get('data')) for item in document['items']])
    request('POST','/purchase-note/revise',body)
    verify(5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare','verify-edit','advance-version','verify-conflict'],nargs='?',default='run')
    action=parser.parse_args().action
    if action=='run': PurchaseUiSuite(read_state()).run()
    elif action=='prepare': prepare()
    elif action=='advance-version': advance()
    else: verify(3 if action=='verify-edit' else 5)
