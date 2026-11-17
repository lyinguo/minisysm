"""Actual warehouse costs across receipts, non-sale issues and transfers.

Only draft extry/swap fixtures are inserted by SQL: this does not accept their
legacy create endpoints. Posting/reversal and every cost assertion use actual
HTTP services and persistent journals in the dedicated QA database.
"""
import argparse,json,uuid
from decimal import Decimal
from warehouse_posting_proof_acceptance import WarehouseProofSuite
from sale_return_cost_acceptance import owned_cost_mode
from sale_return_posting_acceptance import SaleReturnPostingSuite
from acceptance import read_state,sql,literal

class WarehouseCostFlowSuite(WarehouseProofSuite,SaleReturnPostingSuite):
    def document(self,kind,quantity=4,price=100,destination=None,serials=None,time='2026-11-15 10:00:00',warehouse=None,attr='',batch='',mfd=None):
        assert kind in ['extry','swap'];identifier,line=[uuid.uuid4().hex for _ in range(2)]
        fields=['id','frame','time','number','total','cost','examine','cse','user','file','more']
        values=[identifier,self.state['frame_id'],time,'QACOST'+uuid.uuid4().hex[:24],quantity*price,0,0,3,self.actor,'[]','{}']
        if kind=='extry':fields+=['customer','type','check'];values += ['',0,0]
        sql(self.state,'INSERT INTO '+kind+'('+','.join('`'+f+'`' for f in fields)+') VALUES('+','.join(literal(v) for v in values)+');')
        fields=['id','pid','goods','attr','unit','warehouse','price','nums','total','serial','batch','mfd'];values=[line,identifier,self.goods,attr,'unit',warehouse or self.warehouse,price,quantity,quantity*price,json.dumps(serials or []),batch,mfd]
        if kind=='swap':fields.append('storehouse');values.append(destination)
        sql(self.state,'INSERT INTO '+kind+'_info('+','.join('`'+f+'`' for f in fields)+') VALUES('+','.join(literal(v) for v in values)+');')
        return identifier
    def action(self,kind,identifier,target):
        doc=self.store('GET','/transfer/report-documents/'+kind+'/'+identifier)
        return self.request('POST','/transfer/report-documents/'+kind+'/'+identifier+'/audit',dict(target=target,version=doc['version']),service='store')
    def movement_cost(self,identifier,kind):return Decimal(sql(self.state,'SELECT SUM(bct) FROM summary WHERE `class`='+literal(identifier)+' AND type='+literal(kind)+';'))
    def destination(self):
        identifier=uuid.uuid4().hex
        sql(self.state,'INSERT INTO warehouse(id,name,number,frame) VALUES('+','.join(literal(v) for v in [identifier,'QA Cost Destination','QW'+identifier[:16],self.state['frame_id']])+');');return identifier
    def run(self):
        for mode,expected in [('base','8'),('ma','17.6'),('fifo','14')]:
            def outbound(mode=mode,expected=expected):
                with owned_cost_mode(self.state,mode):
                    self.fixture(stock=0);self.incoming(3,2);self.incoming(2,8,'2026-11-14 11:00:00')
                    identifier=self.document('extry');result=self.action('extry',identifier,1);assert result.get('code')==10000,str(result)
                    actual=self.movement_cost(identifier,'extry');assert actual==Decimal(expected),'Actual '+mode+' issue cost='+str(actual)+'; expected='+expected+' (draft estimate100 must not override actual cost)'
                    detail=self.store('GET','/transfer/report-documents/extry/'+identifier);assert Decimal(str(detail['header']['actualCost']))==Decimal(expected) and detail['header']['total']==400
                    assert sum(Decimal(str(row['actualCost'])) for row in detail['items'])==Decimal(expected)
                    assert self.inventory()==1;assert self.action('extry',identifier,0).get('code')==10000 and self.inventory()==5
                    return ['Actual receipts3x2+2x8 -> non-sale issue4 at intentionally wrong estimate100; '+mode+' authoritative cost'+expected+', stock5->1->5']
            self.case('warehouse.cost_issue_'+mode,outbound)
            def transfer(mode=mode,expected=expected):
                with owned_cost_mode(self.state,mode):
                    self.fixture(stock=0);self.incoming(3,2);self.incoming(2,8,'2026-11-14 11:00:00');destination=self.destination()
                    identifier=self.document('swap',destination=destination);result=self.action('swap',identifier,1);assert result.get('code')==10000,str(result)
                    outgoing=self.movement_cost(identifier,'swapOut');incoming=self.movement_cost(identifier,'swapEnter')
                    assert outgoing==incoming==Decimal(expected),'Transfer '+mode+' out/in='+str(outgoing)+'/'+str(incoming)+' expected='+expected
                    assert Decimal(str(self.store('GET','/transfer/report-documents/swap/'+identifier)['header']['actualCost']))==Decimal(expected)
                    assert self.inventory()==1 and Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(destination)+';'))==4
                    assert self.action('swap',identifier,0).get('code')==10000 and self.inventory()==5
                    return ['Actual A->B transfer4 conserves exact source issue cost'+expected+' in both legs and quantity5; reversal restores A5/B0']
            self.case('warehouse.cost_transfer_'+mode,transfer)
        for mode in ['base','ma']:
            def downstream(mode=mode):
                with owned_cost_mode(self.state,mode):
                    self.fixture(stock=0);self.incoming(10,2);destination=self.destination();transfer=self.document('swap',quantity=4,price=2,destination=destination)
                    assert self.action('swap',transfer,1).get('code')==10000
                    issue=self.document('extry',quantity=1,price=2,warehouse=destination,time='2026-11-16 10:00:00');assert self.action('extry',issue,1).get('code')==10000
                    body=self.inbound(5);body['time']='2026-11-17 01:00:00';body['otherInListDetailInfoDTOList'][0]['warehouse']=destination
                    replacement=self.store('POST','/otherin/add',body);self.audit(replacement,1)
                    before=sql(self.state,'SELECT warehouse,nums FROM room WHERE goods='+literal(self.goods)+' ORDER BY warehouse;')
                    assert self.action('swap',transfer,0).get('code')!=10000,'Consumed destination transfer reversed merely because restock made quantity sufficient'
                    assert sql(self.state,'SELECT warehouse,nums FROM room WHERE goods='+literal(self.goods)+' ORDER BY warehouse;')==before
                    self.audit(replacement,0);assert self.action('extry',issue,0).get('code')==10000;assert self.action('swap',transfer,0).get('code')==10000 and self.inventory()==10
                    return ['Actual transfer4 -> destination issue1 -> restock5 cannot reverse consumed transfer under '+mode+' despite sufficient B8; unwind downstream first restores A10/B0']
            self.case('warehouse.cost_transfer_consumed_destination_'+mode,downstream)
        self.serial_checks();self.write_report()
    def matrix(self):
        rules=['def','attr','batch','attr_batch']
        expected_ma={True:['72.5333','68.8','48.8','17.6'],False:['87.5294','90.6667','74','69.7143']}
        expected_fifo={True:['80','120','80','14'],False:['140','160','140','104']}
        for mode in ['base','ma','fifo']:
            for branch in [True,False]:
                for index,rule in enumerate(rules):
                    def scenario(mode=mode,branch=branch,rule=rule,index=index):
                        with owned_cost_mode(self.state,mode,branch=branch,rule=rule):
                            self.fixture(stock=0);destination=self.destination();sql(self.state,'UPDATE goods SET batch=1 WHERE id='+literal(self.goods)+';')
                            for attr in ['red','blue']:sql(self.state,'INSERT INTO attr(id,pid,name,buy,sell) VALUES('+','.join(literal(v) for v in [uuid.uuid4().hex,self.goods,attr,2,100])+');')
                            def received(qty,price,warehouse,attr,batch,time):
                                body=self.inbound(qty);body['time']='2026-11-14 '+time;body['otherInListDetailInfoDTOList'][0].update(price=price,total=qty*price,warehouse=warehouse,attr=attr,batch=batch,mfd='2026-11-01')
                                identifier=self.store('POST','/otherin/add',body);self.audit(identifier,1);return identifier
                            received(2,50,destination,'red','A','08:00:00')
                            received(5,20,self.warehouse,'blue','A','09:00:00')
                            received(5,30,self.warehouse,'red','B','09:30:00')
                            received(3,2,self.warehouse,'red','A','10:00:00')
                            received(2,8,self.warehouse,'red','A','11:00:00')
                            identifier=self.document('swap',destination=destination,attr='red',batch='A',mfd='2026-11-01');result=self.action('swap',identifier,1);assert result.get('code')==10000,str(result)
                            expected=Decimal('8' if mode=='base' else (expected_ma if mode=='ma' else expected_fifo)[branch][index])
                            assert self.movement_cost(identifier,'swapOut')==self.movement_cost(identifier,'swapEnter')==expected,(mode,branch,rule,expected)
                            assert self.inventory()==11
                            assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(destination)+';'))==6
                            assert sql(self.state,'SELECT SUM(CASE WHEN direction=1 THEN bct ELSE -bct END) FROM summary WHERE goods='+literal(self.goods)+';')=='372.0000'
                            assert self.action('swap',identifier,0).get('code')==10000 and self.inventory()==15
                            return ['Actual mixed red/blue and A/B batch receipts with prior destination stock: '+mode+'/'+rule+'/branch='+str(branch)+' transfer source/destination exact'+str(expected)+', physical17 and value372 conserved; reverse restores A15/B2']
                    self.case('warehouse.cost_scope_'+mode+'_'+rule+('_branch' if branch else '_global'),scenario)
        self.write_report()
    def serial_checks(self):
        for kind in ['extry','swap']:
            def serial_source(kind=kind):
                with owned_cost_mode(self.state,'fifo'):
                    self.fixture(stock=0);sql(self.state,'UPDATE goods SET serial=1 WHERE id='+literal(self.goods)+';')
                    serials=['QA-CHEAP-'+uuid.uuid4().hex,'QA-HIGH-'+uuid.uuid4().hex];receipts=[]
                    for index,price in enumerate([2,8]):
                        body=self.inbound(1);body['time']='2026-11-14 '+('10' if index==0 else '11')+':00:00';body['otherInListDetailInfoDTOList'][0].update(price=price,total=price,serial=json.dumps([serials[index]]))
                        receipt=self.store('POST','/otherin/add',body);self.audit(receipt,1);receipts.append(receipt)
                    destination=self.destination() if kind=='swap' else None
                    identifier=self.document(kind,quantity=1,price=100,destination=destination,serials=[serials[1]])
                    assert self.action(kind,identifier,1).get('code')==10000
                    source_kind='swapOut' if kind=='swap' else 'extry'
                    assert self.movement_cost(identifier,source_kind)==8
                    origins=sql(self.state,'SELECT si.`class` FROM fifo f JOIN summary so ON so.id=f.`out` JOIN summary si ON si.id=f.`in` WHERE so.`class`='+literal(identifier)+' AND so.type='+literal(source_kind)+';')
                    assert origins==receipts[1],'FIFO journal points to another serial receipt: '+origins
                    if kind=='swap':
                        assert self.movement_cost(identifier,'swapEnter')==8,'Transfer replaced the selected serial original cost'
                        body=self.body();body['time']='2026-11-16 10:00:00';body['items'][0].update(nums=1,warehouse=destination,serial=json.dumps([serials[1]]),discount=1)
                        sale=self.create(body);self.sale('POST','/sale/form/check?check=true',[sale]);assert self.post([sale]).get('code')==10000
                        assert self.movement_cost(sale,'sell')==8,'Sale after transfer lost selected serial original cost'
                        assert self.post([sale],False).get('code')==10000
                    assert self.action(kind,identifier,0).get('code')==10000
                    self.audit(receipts[1],0);self.audit(receipts[0],0);assert self.inventory()==0
                    return ['Actual two serial receipts cost2 and8, explicitly select expensive serial; '+kind+' cost8 and FIFO points to correct source; transfer preserves serial cost through actual sale and ordered reversal0']
            self.case('warehouse.cost_serial_source_'+kind,serial_source)
    def mixed_serial(self,return_flow=False,return_both=False):
        def scenario():
            with owned_cost_mode(self.state,'fifo'):
                self.fixture(stock=0);sql(self.state,'UPDATE goods SET serial=1 WHERE id='+literal(self.goods)+';')
                serials=['QA-MIX-LOW-'+uuid.uuid4().hex,'QA-MIX-HIGH-'+uuid.uuid4().hex];receipts=[]
                for index,price in enumerate([2,8]):
                    body=self.inbound(1);body['time']='2026-11-14 '+str(10+index)+':00:00';body['otherInListDetailInfoDTOList'][0].update(price=price,total=price,serial=json.dumps([serials[index]]))
                    receipt=self.store('POST','/otherin/add',body);self.audit(receipt,1);receipts.append(receipt)
                destination=self.destination();identifier=self.document('swap',quantity=2,price=100,destination=destination,serials=serials)
                assert self.action('swap',identifier,1).get('code')==10000
                assert self.movement_cost(identifier,'swapOut')==self.movement_cost(identifier,'swapEnter')==10
                selected=serials if return_both else [serials[1]];expected=10 if return_both else 8
                body=self.body();body['time']='2026-11-16 10:00:00';body['items'][0].update(nums=len(selected),warehouse=destination,serial=json.dumps(selected),discount=1)
                sale=self.create(body);self.sale('POST','/sale/form/check?check=true',[sale]);assert self.post([sale]).get('code')==10000
                assert self.movement_cost(sale,'sell')==expected,'Transferred serial sale lost original individual cost'
                if return_flow:
                    returned=self.return_body(sale,len(selected));returned['salesReturnOrderInfos'][0].update(warehouse=destination,serial=json.dumps(selected))
                    result=self.add_return(returned);assert result.get('code')==10000,str(result);return_id=result['data']
                    assert self.review([return_id],versions=self.versions([return_id])).get('code')==10000
                    result=self.post_return([return_id],versions=self.versions([return_id]));assert result.get('code')==10000,str(result)
                    assert self.movement_cost(return_id,'sre')==expected,'Return after mixed serial transfer lost original issue cost'+str(expected)
                    assert self.balance('customer',self.customer)==0 and self.balance('account',self.account)==100
                    assert Decimal(sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(destination)+';'))==2
                    if return_both:
                        later=self.body();later['time']='2026-11-16 13:00:00';later['items'][0].update(nums=1,warehouse=destination,serial=json.dumps([serials[1]]),discount=1)
                        resold=self.post_source(later);assert self.movement_cost(resold,'sell')==8,'Return averaged original serial values before subsequent resale'
                        assert self.post_return([return_id],status=0,versions=self.versions([return_id])).get('code')!=10000
                        assert self.post([resold],False).get('code')==10000
                    assert self.post_return([return_id],status=0,versions=self.versions([return_id])).get('code')==10000
                    assert self.post([sale],False).get('code')!=10000,'Source sale reversed while a return draft still references it'
                    assert self.review([return_id],status=0,versions=self.versions([return_id])).get('code')==10000
                    assert self.remove_return(return_id,self.return_doc(return_id)['version']).get('code')==10000
                result=self.post([sale],False);assert result.get('code')==10000,str(result)
                result=self.action('swap',identifier,0);assert result.get('code')==10000,str(result)
                self.audit(receipts[1],0);self.audit(receipts[0],0);assert self.inventory()==0 and self.balance('customer',self.customer)==0
                return ['Actual cost2 and8 serials move together in one transfer cost10; selected serial issue and return preserve original total'+str(expected)+'; '+('actual return restores destination quantity2 and zero receivable; ' if return_flow else '')+('subsequent expensive serial resale still costs8 and blocks return reversal until unwound; ' if return_both else '')+'ordered reverse restores stock0/AR0']
        self.case('warehouse.cost_serial_transfer_'+('multi_return_resale_original_values' if return_both else 'return_preserves_original_cost' if return_flow else 'preserves_individual_values'),scenario);self.write_report()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--serial-only',action='store_true');p.add_argument('--matrix',action='store_true');p.add_argument('--mixed-serial',action='store_true');p.add_argument('--serial-return',action='store_true');p.add_argument('--serial-return-both',action='store_true');a=p.parse_args();s=WarehouseCostFlowSuite(read_state())
    if a.serial_only:s.serial_checks();s.write_report()
    elif a.matrix:s.matrix()
    elif a.mixed_serial:s.mixed_serial()
    elif a.serial_return:s.mixed_serial(return_flow=True)
    elif a.serial_return_both:s.mixed_serial(return_flow=True,return_both=True)
    else:s.run()
