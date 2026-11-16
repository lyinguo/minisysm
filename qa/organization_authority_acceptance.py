"""Actual legacy authority-label collision tests; only new isolated QA identities/data."""
import argparse,copy,json,uuid
from acceptance import QA,Suite,read_state,sql,literal,authenticate_registered_login
from purchase_ui_acceptance import PurchaseUiSuite
from purchase_posting_acceptance import PurchasePostingSuite
from sale_posting_acceptance import SalePostingSuite
from payment_document_acceptance import PaymentDocumentSuite
from receipt_document_acceptance import ReceiptDocumentSuite
from resource_fixture import qa_database_resource_grants

DEFINITIONS={
    'sale':(SalePostingSuite,'sell',['/sale/form/getSaleDetail','/sale/form/getSaleList','/sale/form/updateSale','/sale/form/deleteSales']),
    'purchase':(PurchasePostingSuite,'buy',['/j3-purchase/purchase-note/info','/j3-purchase/purchase-note/list','/j3-purchase/purchase-note/revise','/j3-purchase/purchase-note/delete']),
    'payment':(PaymentDocumentSuite,'omy',['/payment-order/query-by-id/{id}','/payment-order/query-all','/payment-order/modify','/payment-order/remove']),
    'fund':(ReceiptDocumentSuite,'imy',['/fund/receipt/fundReceiptDetail','/fund/receipt/fundReceiptList','/fund/receipt/update','/fund/receipt/remove'])}

def construct(base,state,gateway):
    class ActorSuite(base):
        def __init__(self,state):
            self.through_gateway=gateway
            super().__init__(state)
        def request(self,method,path,body=None,service='c1'):
            if gateway and service in ('c1','sale','purchase','payment','fund'):
                if service=='purchase':path='/j3-purchase'+path
                service='gateway'
            return super().request(method,path,body,service)
    return ActorSuite(state)

def verify(service,gateway=False):
    base,table,resources=DEFINITIONS[service];suite=construct(base,read_state(),gateway)
    if service=='fund':suite.fixture(stock=0)
    else:suite.fixture()
    def create():
        if service=='sale':return suite.create(suite.body())
        if service=='purchase':return suite.create_document()
        if service=='payment':return suite.create_payment(suite.body())
        return suite.create_receipt(suite.receipt_body())
    def read(identifier):
        prefix={'sale':'/sale/form','purchase':'/purchase-note','payment':'/payment-order','fund':'/fund/receipt'}[service]
        return suite.request('GET',prefix+'/document/'+identifier,service=service)
    def listing(number):
        path={'sale':'/sale/form/getSaleList','purchase':'/purchase-note/list','payment':'/payment-order/documents','fund':'/fund/receipt/documents'}[service]
        return suite.request('GET',path+'?pageIndex=1&pageSize=10&number='+number,service=service)
    def revision(document):
        if service in ('payment','fund'):return suite.revision(document)
        if service=='purchase':
            line=document['items'][0]['id']
            return dict(id=document['header']['id'],version=document['version'],supplier=suite.supplier,time='2026-11-15 13:47:00',number=document['header']['number'],actual=339,money=0,account='',people='',file='',data='QA scope edit',examine=0,checkStatus=0,
                details=[dict(id=line,goods=suite.goods,unit='unit',warehouse=suite.warehouse,price=100,nums=3,discount=0,tax=13,data='QA scope edit',retreat=0)])
        body=copy.deepcopy(document['header']);body.update(time=body.pop('timeEpoch'),version=document['version'],items=document['items'],data='QA scope edit');return body
    def edit(identifier,document):
        body=revision(document)
        if service=='sale':return suite.request('PUT','/sale/form/updateSale',body,service=service)
        if service=='purchase':return suite.request('POST','/purchase-note/revise',body,service=service)
        return suite.edit(identifier,body)
    def remove(identifier,document):
        if service=='sale':return suite.request('DELETE','/sale/form/deleteSales',[identifier],service=service)
        if service=='purchase':return suite.request('POST','/purchase-note/delete',[identifier],service=service)
        return suite.remove(identifier,document['version'])
    own,foreign=create(),create();frame=uuid.uuid4().hex
    sql(suite.state,'INSERT INTO frame(id,pid,name) VALUES('+literal(frame)+",'0','QA Authority Other Org');UPDATE "+table+' SET frame='+literal(frame)+' WHERE id='+literal(foreign)+';')
    initial=read(foreign);assert initial.get('code')==10000
    foreign_doc=initial['data'];own_doc=read(own)['data'];number=foreign_doc['header']['number']
    admin=suite.token;name='QA Authority Collision '+uuid.uuid4().hex[:7]
    role=suite.success('POST','/role/add-role',dict(name=name,data='',root='[]',auth='{}'))
    keyword=sql(suite.state,'SELECT keyword FROM role WHERE id='+literal(role)+';')
    user_id,user,_=suite.new_user(role=role)
    def balance_snapshot():
        party='customer' if service in ('sale','fund') else 'supplier'
        identifier=getattr(suite,party)
        return sql(suite.state,'SELECT balance FROM account WHERE id='+literal(suite.account)+';SELECT balance FROM '+party+' WHERE id='+literal(identifier)+';SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(suite.goods)+';')
    before=balance_snapshot()
    try:
        with qa_database_resource_grants(suite.state,resources,[keyword]) as functions:
            # Explicit owned legacy-config fixture; never modify normal/existing roles.
            sql(suite.state,"UPDATE role SET keyword='ROLE_ADMIN' WHERE id="+literal(role)+';')
            ordinary=authenticate_registered_login(suite.state,user['user'],user['pwd'],suite.opener) if gateway else PurchaseUiSuite.login(suite,user)
            suite.token=ordinary
            assert read(own).get('code')==10000,'Own authorized document was denied'
            foreign_response=read(foreign)
            assert foreign_response.get('code')==403,'Nonzero role with ROLE_ADMIN label leaked foreign '+service+' detail: code='+str(foreign_response.get('code'))
            page=listing(number);assert page.get('code')==10000 and page['data']['total']==0,'Foreign organization list leaked'
            assert edit(foreign,foreign_doc).get('code')==403,'Foreign edit was not denied'
            assert remove(foreign,foreign_doc).get('code')==403,'Foreign delete was not denied'
            suite.token=admin;assert read(foreign)['data']==foreign_doc
            assert suite.request('PUT','/user/mod-user',dict(id=user_id,frame=frame)).get('code')==10000
            suite.token=ordinary
            assert read(foreign).get('code')==10000 and read(own).get('code')==403,'Old JWT organization overrode current DB membership'
            suite.token=admin
            assert suite.request('PUT','/user/mod-user',dict(id=user_id,frame=suite.state['frame_id'])).get('code')==10000
            suite.token=ordinary
            sql(suite.state,"UPDATE func_perm SET is_enable='0' WHERE id="+literal(functions[resources[0]])+';')
            assert read(own).get('code')==403,'ROLE_ADMIN keyword bypassed a disabled function'
            sql(suite.state,"UPDATE func_perm SET is_enable='1' WHERE id="+literal(functions[resources[0]])+';')
            assert edit(own,own_doc).get('code')==10000,'Authorized ordinary edit was incorrectly disabled'
            changed=read(own);assert changed.get('code')==10000
            assert remove(own,changed['data']).get('code')==10000,'Authorized ordinary deletion was incorrectly disabled'
            assert balance_snapshot()==before,'Draft permission checks changed actual cash/party/stock'
            suite.token=admin;assert read(foreign)['data']==foreign_doc
            assert sql(suite.state,'SELECT COUNT(*) FROM '+table+' WHERE id='+literal(own)+';')=='0'
            assert sql(suite.state,"SELECT COUNT(*) FROM record WHERE type="+literal(table)+' AND source='+literal(own)+' AND `user`='+literal(user_id)+';')=='2'
    finally:
        suite.token=admin
        sql(suite.state,'UPDATE role SET keyword='+literal(keyword)+',root=\'[]\' WHERE id='+literal(role)+';UPDATE `user` SET frame='+literal(suite.state['frame_id'])+' WHERE id='+literal(user_id)+';')
    return ['Actual OAuth user with nonzero role and explicit legacy ROLE_ADMIN label stays organization-scoped; current DB organization changes apply to same token',
        'Foreign list/detail/edit/delete refuse without mutations; own granted edit/delete persist with signed histories; no stock/cash/party changes; role/catalog fixtures restored']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--gateway',action='store_true');args=parser.parse_args()
    reporter=Suite.__new__(Suite);reporter.results=[]
    for service in DEFINITIONS:reporter.case('organization.authority_label_'+service+('_through_gateway' if args.gateway else ''),lambda service=service:verify(service,args.gateway))
    reporter.write_report()
