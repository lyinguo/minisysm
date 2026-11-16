"""Actual procurement return-source gates; no return save/stock/refund completion claim."""
import argparse
import uuid
import json
from decimal import Decimal
from purchase_posting_acceptance import PurchasePostingSuite
from purchase_ui_acceptance import PurchaseUiSuite
from resource_fixture import qa_resource_grants,authority
from acceptance import read_state,sql,literal


class PurchaseReturnPreviewSuite(PurchasePostingSuite):
    resource='/purchase-note/getBuildBre'
    def preview(self,identifier):
        return self.request('GET',self.resource+'?id='+identifier,service='purchase')
    def posted(self):
        self.fixture();identifier=self.create_document(paid=25)
        assert self.check([identifier]).get('code')==10000
        assert self.post([identifier]).get('code')==10000
        return identifier
    def unchanged(self):
        assert self.inventory()==2 and self.balance('account',self.account)==75 and self.balance('supplier',self.supplier)==201
    def linked_fixture(self,source,quantity,approval=0):
        """Explicit QA legacy return state; not a real return save/audit proof."""
        identifier,line=uuid.uuid4().hex,uuid.uuid4().hex
        original=sql(self.state,'SELECT id FROM buy_info WHERE pid='+literal(source)+' LIMIT 1;')
        sql(self.state,'INSERT INTO bre(id,source,frame,supplier,time,number,total,actual,money,cost,examine,nucleus,cse,invoice,`check`,`user`) SELECT '+
            literal(identifier)+',id,frame,supplier,time,'+literal('QABR'+identifier[:20])+',0,0,0,0,'+str(approval)+',0,3,3,0,'+literal(self.actor)+' FROM buy WHERE id='+literal(source)+';'+
            'INSERT INTO bre_info(id,pid,source,goods,attr,unit,warehouse,batch,mfd,price,nums,total,tpt,serial) SELECT '+literal(line)+','+literal(identifier)+',id,goods,attr,unit,warehouse,batch,mfd,price,'+literal(quantity)+",0,0,'[]' FROM buy_info WHERE id="+literal(original)+';')
        return identifier,line,original
    def baseline(self):
        def source_defaults():
            source=self.posted();result=self.preview(source)
            assert result.get('code')==10000
            data=result['data'];document=self.document(source)
            assert data.get('source')==source and data.get('sourceVersion')==document['version'], 'Return preview lacks canonical actual source/version'
            assert not data.get('id') and data.get('number')=='' and data.get('money')==0 and data.get('examine')==0 and data.get('check')==0
            assert data['frame']==self.state['frame_id'] and data['supplier']==self.supplier and data['user']==self.actor
            item=data['items'][0];assert item['source']==document['items'][0]['id'] and item['available']==2
            assert item['goods']==self.goods and item['warehouse']==self.warehouse
            self.unchanged();return ['Actual posted receipt preview has canonical source/version, correct supplier/organization/original detail and fresh unposted defaults, no stock/funds effects']
        self.case('purchase.return_preview_actual_source_defaults',source_defaults)
        def unposted():
            self.fixture();identifier=self.create_document()
            assert self.preview(identifier).get('code')!=10000,'Unposted purchase accepted as a return source'
            assert self.inventory()==0 and self.balance('account',self.account)==100
            return ['Actual unposted draft cannot generate procurement-return data']
        self.case('purchase.return_preview_requires_actual_posting',unposted)
        def forged_approval():
            self.fixture();identifier=self.create_document()
            sql(self.state,'UPDATE buy SET examine=1 WHERE id='+literal(identifier)+';')
            assert self.preview(identifier).get('code')!=10000,'Approval flag without actual receipt posting accepted'
            assert self.inventory()==0 and self.balance('account',self.account)==100
            return ['Explicit owned approval-flag fixture without posting proof is refused, not treated as actual stock receipt']
        self.case('purchase.return_preview_requires_posting_proof',forged_approval)
        def pending_quantity():
            source=self.posted();self.linked_fixture(source,.5)
            result=self.preview(source);assert result.get('code')==10000
            item=result['data'].get('items',[{}])[0]
            assert Decimal(str(item.get('available',-1)))==Decimal('1.5') and Decimal(str(item.get('reserved',-1)))==Decimal('.5'),'Pending return reservation ignored'
            self.unchanged();return ['Explicit half-unit pending legacy fixture reserves source quantity; preview reports1.5 without posting inventory or funds']
        self.case('purchase.return_preview_pending_quantity_reservation',pending_quantity)
        def fully_returned():
            source=self.posted();_,_,original=self.linked_fixture(source,2,1)
            sql(self.state,'UPDATE buy_info SET retreat=2 WHERE id='+literal(original)+';')
            assert self.preview(source).get('code')!=10000,'Fully returned purchase still offers original quantities'
            self.unchanged();return ['Explicit consistent fully-returned source state refuses another return preview; not a return-posting completion claim']
        self.case('purchase.return_preview_no_remaining_quantity',fully_returned)
        self.write_report()

    def sale_from_receipt(self,quantity=1,serial=None,time=None):
        from sale_posting_acceptance import SalePostingSuite
        sale=SalePostingSuite(self.state);sale.goods=self.goods;sale.warehouse=self.warehouse
        body=sale.body();body['items'][0].update(nums=quantity,discount=1,serial=json.dumps(serial or []))
        if time is not None: body['time']=time
        identifier=sale.create(body)
        assert sale.request('POST','/sale/form/check?check=true',[identifier],service='sale').get('code')==10000
        assert sale.post([identifier]).get('code')==10000
        return sale,identifier

    def extended(self):
        def partial_amounts():
            source=self.posted();_,_,line=self.linked_fixture(source,.5,1);self.linked_fixture(source,.25)
            sql(self.state,'UPDATE buy_info SET retreat=.5 WHERE id='+literal(line)+';')
            result=self.preview(source);assert result.get('code')==10000
            data=result['data'];item=data['items'][0]
            assert [Decimal(str(item[key])) for key in ['sourceQuantity','returned','reserved','available','stockQuantity','total','tat','tpt']]==list(map(Decimal,['2','.5','.25','1.25','2','125','16.25','141.25']))
            old=data['purchaseNoteBuilInfoDTOS'][0]
            assert old['source']==line and not old.get('id') and not old.get('pid') and Decimal(str(old['nums']))==Decimal('1.25')
            self.unchanged();return ['Explicit approved/pending legacy quantity fixtures give source remaining1.25 and proportional net125/tax16.25/gross141.25; legacy response also uses correct original detail identity without reusing persisted IDs']
        self.case('purchase.return_preview_partial_amounts_and_legacy_identity',partial_amounts)

        def bad_links():
            source=self.posted();_,line,_=self.linked_fixture(source,.5)
            other=uuid.uuid4().hex
            sql(self.state,'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) SELECT '+literal(other)+",'QA Existing Other Product',py,"+literal('QG'+other[:16])+',category,unit,buy,sell,0,type,more FROM goods WHERE id='+literal(self.goods)+';'+
                'UPDATE bre_info SET goods='+literal(other)+' WHERE id='+literal(line)+';')
            assert self.preview(source).get('code')!=10000
            self.unchanged()
            source=self.posted();self.linked_fixture(source,.5,1)
            assert self.preview(source).get('code')!=10000
            self.unchanged();return ['Explicit linked wrong-product fixture and approved-return/source-counter mismatch both refuse source estimates, without hiding invalid associations']
        self.case('purchase.return_preview_link_and_counter_integrity',bad_links)

        def actual_consumption():
            source=self.posted();self.sale_from_receipt(1)
            before=self.document(source)['version'];result=self.preview(source);assert result.get('code')==10000
            item=result['data']['items'][0]
            assert item['available']==2 and item['stockQuantity']==1 and item['stockBase']==1
            assert self.document(source)['version']==before
            assert self.inventory()==1 and self.balance('account',self.account)==75 and self.balance('supplier',self.supplier)==201
            return ['Actual sale consumes one of two received units; preview distinguishes source allowance2 from physical stock1 and does not mutate original source version or balances']
        self.case('purchase.return_preview_actual_stock_is_not_source_allowance',actual_consumption)

        def original_units():
            self.fixture();sql(self.state,"UPDATE goods SET unit='-1',units="+literal(json.dumps([dict(source='unit',name='box',nums=5)]))+' WHERE id='+literal(self.goods)+';')
            body=self.body();body['purchaseNoteBuyDTO'].update(total=100,actual=113,money=25,account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(unit='box',nums=1,discount=0,tax=13,total=100,tat=13,tpt=113,batch='',mfd=None,serial='[]')
            source=self.create(body);assert self.check([source]).get('code')==10000 and self.post([source]).get('code')==10000
            sql(self.state,'UPDATE goods SET units='+literal(json.dumps([dict(source='unit',name='box',nums=10)]))+' WHERE id='+literal(self.goods)+';')
            result=self.preview(source);assert result.get('code')==10000
            item=result['data']['items'][0];assert item['sourceBaseQuantity']==5 and item['stockBase']==5 and item['stockQuantity']==1 and item['unit']=='box'
            assert self.inventory()==5 and self.balance('account',self.account)==75 and self.balance('supplier',self.supplier)==88
            return ['Actual one-box receipt at five base units remains stockQuantity1 after explicit owned current conversion change to ten; original receipt conversion is used instead of current configuration']
        self.case('purchase.return_preview_original_receipt_unit_conversion',original_units)

        def actual_serials():
            self.fixture();sql(self.state,'UPDATE goods SET serial=1 WHERE id='+literal(self.goods)+';')
            body=self.body();body['purchaseNoteBuyDTO'].update(money=25,account=self.account)
            body['purchaseNoteInfoDTOS'][0].update(discount=0,tax=13,batch='',mfd=None,serial=json.dumps(['QA-PR-A','QA-PR-B']))
            source=self.create(body);assert self.check([source]).get('code')==10000 and self.post([source]).get('code')==10000
            self.sale_from_receipt(1,['QA-PR-A'])
            result=self.preview(source);assert result.get('code')==10000
            item=result['data']['items'][0];assert item['serialRequired'] is True and item['availableSerials']==['QA-PR-B'] and item['serial']=='[]'
            assert item['stockQuantity']==1 and item['available']==2
            assert self.inventory()==1 and self.balance('account',self.account)==75 and self.balance('supplier',self.supplier)==201
            return ['Actual original serial purchase and sale exclude sold serialA while offering only still-stocked originalB; selected return serials remain empty until an explicit user choice']
        self.case('purchase.return_preview_actual_original_serial_options',actual_serials)

        def service():
            self.fixture();sql(self.state,'UPDATE goods SET type=1 WHERE id='+literal(self.goods)+';')
            source=self.create_document(paid=25);assert self.check([source]).get('code')==10000 and self.post([source]).get('code')==10000
            result=self.preview(source);assert result.get('code')==10000
            item=result['data']['items'][0];assert item['service'] is True and item.get('stockBase') is None and item.get('stockQuantity') is None and item['available']==2
            assert self.inventory()==0 and self.balance('account',self.account)==75 and self.balance('supplier',self.supplier)==201
            return ['Actual service purchase retains original source quantity and service receipt identity, never inventing warehouse stock']
        self.case('purchase.return_preview_actual_service_source',service)

        def live_scope():
            own=self.posted();foreign=uuid.uuid4().hex
            self.fixture();sql(self.state,"INSERT INTO frame(id,pid,name,sort) VALUES("+literal(foreign)+",'0','QA Purchase Return Foreign',0);")
            for table,identifier in [('warehouse',self.warehouse),('supplier',self.supplier),('account',self.account)]:sql(self.state,'UPDATE '+table+' SET frame='+literal(foreign)+' WHERE id='+literal(identifier)+';')
            self.success('PUT','/user/mod-user',dict(id=self.actor,frame=foreign))
            try:
                other=self.create_document(paid=25);assert self.check([other]).get('code')==10000 and self.post([other]).get('code')==10000
            finally:self.success('PUT','/user/mod-user',dict(id=self.actor,frame=self.state['frame_id']))
            role=self.success('POST','/role/add-role',dict(name='QA Return Source '+uuid.uuid4().hex[:8],data='',root='[]',auth='{}'))
            keyword=sql(self.state,'SELECT keyword FROM role WHERE id='+literal(role)+';');actor,user,_=self.new_user(role=role);token=PurchaseUiSuite.login(self,user);admin=self.token
            try:
                self.token=token;assert self.preview(own).get('code')==403
                with qa_resource_grants(self.state,[self.resource],[authority(role,keyword)]):
                    assert self.preview(own).get('code')==10000 and self.preview(own)['data']['user']==actor
                    assert self.preview(other).get('code')==403
                assert self.preview(own).get('code')==403
            finally:self.token=admin
            self.unchanged();return ['Actual new OAuth role requires live return-source grant, sees its own organization only and current operator identity; same token is immediately refused after grant restoration; foreign source was actually created and posted with a new fixture actor organization']
        self.case('purchase.return_preview_live_oauth_and_organization',live_scope)
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['baseline','extended'])
    action=parser.parse_args().action;suite=PurchaseReturnPreviewSuite(read_state())
    if action=='baseline':suite.baseline()
    else:suite.extended()
