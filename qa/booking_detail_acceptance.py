"""Actual full-order metadata and edit lifecycle, restricted to dedicated QA services."""
import argparse,json,uuid
from decimal import Decimal
from booking_audit_acceptance import OrderAuditSuite
from acceptance import read_state,sql,literal,QA

class OrderDetailSuite(OrderAuditSuite):
    def document(self,id):return self.request('GET','/purchase-order/document?id='+id,service='purchase')
    def run_detail(self):
        def names():
            self.fixture();id=self.order();head=self.document(id)['data']['header']
            assert head.get('peopleName')=='QA Booking Person','Detail omits actual related-person name'
            assert head.get('supplierName')=='QA Posting Supplier' and head.get('frameName') and head.get('userName')
            assert head['people']==self.person and head['supplier']==self.supplier and head['user']==self.actor
            self.unchanged();return ['Real names supplement unchanged reference IDs; query does not post stock or funds']
        self.case('booking.detail_actual_names_and_ids',names)
        def edit():
            self.fixture();body=self.order_body();line=body['purchaseOrderInfoDTOList'][0];line.update(price=1.0001,nums=.5,discount=10,tax=13)
            body['file']=json.dumps([dict(name='QA attachment metadata',url='qa-reference-only')])
            id=self.create_order(body);data=self.document(id)['data'];head=data['header'];item=data['items'][0]
            assert Decimal(str(item['total']))==Decimal('.4501') and Decimal(str(item['tpt']))==Decimal('.5086')
            body.update(id=id,total=head['total'],actual=head['actual'],file=head['file'],data='QA actual detail edit')
            line.update({key:item[key] for key in ['price','nums','discount','dsc','total','tax','tat','tpt']})
            result=self.request('PUT','/purchase-order/update',body,service='purchase');assert result.get('code')==10000,'Actual full-detail edit rejected'
            after=self.document(id)['data'];assert after['header']['data']=='QA actual detail edit' and after['header']['people']==self.person and after['header']['file']==body['file']
            for key in ['price','nums','discount','dsc','total','tax','tat','tpt']:assert Decimal(str(after['items'][0][key]))==Decimal(str(item[key])),key
            assert self.records(id)==2 and self.audit([id]).get('code')==10000 and self.audit([id],0).get('code')==10000
            self.unchanged();return ['Four-decimal discounted and taxed actual edit persists, rereads and approves/reverses without stock or funds changes']
        self.case('booking.detail_discount_precision_edit_audit',edit)
        def optional():
            self.fixture();body=self.order_body();body.update(people='',logistics='QA-OLD-TRACK');id=self.create_order(body)
            data=self.document(id)['data'];head=data['header'];item=data['items'][0]
            body.update(id=id,total=head['total'],actual=head['actual'],logistics='',data='',file='[]')
            body['purchaseOrderInfoDTOList'][0].update({key:item[key] for key in ['price','nums','discount','dsc','total','tax','tat','tpt']})
            assert self.request('PUT','/purchase-order/update',body,service='purchase').get('code')==10000
            after=self.document(id)['data']['header'];assert not after['people'] and not after['logistics'] and not after['data'] and after.get('peopleName') is None
            assert self.audit([id]).get('code')==10000;self.unchanged()
            return ['An order without optional related person/logistics can actually save and approve; blank inputs do not become fake IDs or carrier labels']
        self.case('booking.detail_optional_person_logistics',optional)
        self.write_report()

FIXTURE=QA/'runtime/booking-detail-browser.json'
def prepare():
    s=OrderDetailSuite(read_state());s.fixture();body=s.order_body();body['purchaseOrderInfoDTOList'][0].update(price=1.0001,nums=.5,discount=10,tax=13)
    id=s.create_order(body)
    FIXTURE.write_text(json.dumps(dict(database=s.state['database'],id=id,number=body['number'],actor=s.actor,goods=s.goods,warehouse=s.warehouse,supplier=s.supplier,people=s.person,account=s.account)),encoding='utf-8')
    (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=s.token)),encoding='utf-8')
    print('Prepared disposable actual detail order '+body['number'])
def verify(target):
    state=read_state();f=json.loads(FIXTURE.read_text());assert state['database']==f['database']
    head=json.loads(sql(state,"SELECT JSON_OBJECT('total',total,'actual',actual,'people',people,'supplier',supplier,'actor',`user`,'state',CAST(examine AS SIGNED),'data',data,'file',file,'logistics',logistics) FROM bor WHERE id="+literal(f['id'])+';'))
    assert Decimal(str(head['total']))==Decimal('.4001') and Decimal(str(head['actual']))==Decimal('.4521')
    assert head['people']==f['people'] and head['supplier']==f['supplier'] and head['actor']==f['actor'] and head['file']=='[]' and head['state']==target
    assert not head['logistics'],'Empty logistics was replaced by a carrier display label'
    assert sql(state,'SELECT CONCAT(discount,\':\',dsc,\':\',tat,\':\',tpt) FROM bor_info WHERE pid='+literal(f['id'])+';')=='20.00:0.1000:0.0520:0.4521'
    assert sql(state,"SELECT COUNT(*) FROM record WHERE type='bor' AND source="+literal(f['id'])+';')==('3' if target else '2')
    assert Decimal(sql(state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(f['goods'])+';'))==0
    assert Decimal(sql(state,'SELECT balance FROM supplier WHERE id='+literal(f['supplier'])+';'))==0 and Decimal(sql(state,'SELECT balance FROM account WHERE id='+literal(f['account'])+';'))==100
    (QA/('reports/booking-detail-browser-'+str(target)+'.json')).write_text(json.dumps(dict(status='verified',case='booking.browser_detail_edit_'+str(target),production_business_writes=0,all_system_features_accepted=False)))
    print('PASS actual browser edited discount20, net .4001, actual .4521, original references and stock/funds; approval='+str(target))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','prepare','verify-saved','verify-approved'],nargs='?',default='run');a=p.parse_args().action
    if a=='prepare':prepare()
    elif a.startswith('verify'):verify(1 if a=='verify-approved' else 0)
    else:OrderDetailSuite(read_state()).run_detail()
