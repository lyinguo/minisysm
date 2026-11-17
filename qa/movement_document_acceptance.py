"""Real create -> transfer/count -> sale -> ordered reversal in isolated MySQL.

Product/warehouse/account fixtures are explicit SQL. Business documents and all
state transitions use actual HTTP; injected database failures test transactions.
"""
import argparse,copy,json,uuid,threading,concurrent.futures
from decimal import Decimal
from outbound_document_acceptance import OutboundDocumentSuite
from sale_return_cost_acceptance import owned_cost_mode
from acceptance import QA,read_state,sql,literal

class MovementSuite(OutboundDocumentSuite):
    def case(self,name,action):
        def traced():
            try:return action()
            except Exception:
                import traceback
                raise AssertionError(traceback.format_exc())
        return super().case(name,traced)
    def transfer_body(self,qty=4):
        destination=self.destination()
        return dict(frame=self.state['frame_id'],number='QADB'+uuid.uuid4().hex[:24],time='2026-11-15T10:00',data='QA actual transfer',items=[dict(goods=self.goods,attr='',unit='unit',warehouse=self.warehouse,storehouse=destination,nums=qty,price=100,batch='',mfd=None,serial='[]')])
    def count_body(self,qty=12):
        return dict(frame=self.state['frame_id'],number='QAPD'+uuid.uuid4().hex[:24],time='2026-11-15T10:00',data='QA actual count',items=[dict(goods=self.goods,attr='',unit='unit',warehouse=self.warehouse,counted=qty,price=2,batch='',mfd=None,serial='[]')])
    def doc(self,kind,identifier):return self.store('GET',('/transfer' if kind=='swap' else '/verify')+'/documents/'+identifier)
    def save_doc(self,kind,body):return self.store('POST',('/transfer' if kind=='swap' else '/verify')+'/documents',body)
    def mutation(self,kind,identifier,target=1,remove=False,version=None):
        version=version or self.doc(kind,identifier)['version']
        if kind=='swap':return self.request('POST','/transfer/documents/'+('delete' if remove else 'audit'),dict(ids=[identifier],versions={identifier:version},**({} if remove else dict(target=target))),service='store')
        return self.request('POST','/verify/documents/'+identifier+('/delete' if remove else '/audit'),dict(version=version,**({} if remove else dict(target=target))),service='store')
    def qty(self,warehouse):return Decimal(sql(self.state,'SELECT COALESCE(SUM(nums),0) FROM room WHERE goods='+literal(self.goods)+' AND warehouse='+literal(warehouse)+';'))
    def untouched_money(self):assert self.balance('customer',self.customer)==0 and self.balance('account',self.account)==100
    def sale_from(self,warehouse,qty=1,serial=None,batch='',mfd=None):
        b=self.body();b['time']='2026-11-16 10:00:00';b['items'][0].update(warehouse=warehouse,nums=qty,discount=1,batch=batch,mfd=mfd,serial=json.dumps(serial or []));return self.post_source(b)
    def run(self):
        for mode in ['base','ma','fifo']:
            def downstream(mode=mode):
                with owned_cost_mode(self.state,mode):
                    self.fixture(stock=0);receipt=self.incoming(10,2);body=self.transfer_body();target=body['items'][0]['storehouse'];identifier=self.save_doc('swap',body)
                    assert self.doc('swap',identifier)['header']['id']==identifier and self.qty(target)==0 and self.inventory()==10
                    assert self.mutation('swap',identifier).get('code')==10000
                    assert self.inventory()==6 and self.qty(target)==4 and self.movement_cost(identifier,'swapOut')==self.movement_cost(identifier,'swapEnter')==8
                    sale=self.sale_from(target,2);assert self.qty(target)==2 and self.movement_cost(sale,'sell')==4
                    before=self.doc('swap',identifier);assert self.mutation('swap',identifier,0).get('code')!=10000 and self.doc('swap',identifier)==before
                    assert self.post([sale],False).get('code')==10000 and self.qty(target)==4
                    assert self.mutation('swap',identifier,0).get('code')==10000 and self.inventory()==10 and self.qty(target)==0
                    assert self.mutation('swap',identifier,remove=True).get('code')==10000;self.audit(receipt,0);assert self.inventory()==0;self.untouched_money()
                    return ['Actual receipt10 -> HTTP-created transfer4 A6/B4 at cost8 -> actual destination sale2 cost4 -> upstream reverse blocked -> sale reverse -> transfer reverse A10/B0 -> receipt reverse0; '+mode]
            self.case('movement.transfer_sale_ordered_reverse_'+mode,downstream)
        def draft_edit():
            self.fixture();b=self.transfer_body(2);identifier=self.save_doc('swap',b);d=self.doc('swap',identifier);b.update(id=identifier,version=d['version']);b['items']=d['items'];b['items'][0]['nums']=3;b['items'].append({**b['items'][0],'id':None,'nums':1});self.save_doc('swap',b)
            assert len(self.doc('swap',identifier)['items'])==2 and self.inventory()==10
            assert self.request('POST','/transfer/documents',b,service='store').get('code')!=10000
            b['version']=self.doc('swap',identifier)['version'];b['items']=self.doc('swap',identifier)['items'][:1];self.save_doc('swap',b)
            assert len(self.doc('swap',identifier)['items'])==1;assert self.mutation('swap',identifier,remove=True).get('code')==10000
            assert sql(self.state,'SELECT COUNT(*) FROM swap_info WHERE pid='+literal(identifier)+';')=='0';return ['Actual versioned multi-line add/remove preserves existing line IDs, rejects stale edit and deletes all children without changing stock']
        self.case('movement.transfer_full_draft_edit_delete',draft_edit)
        def invalid():
            self.fixture();b=self.transfer_body();b['items'][0]['storehouse']=self.warehouse
            assert self.request('POST','/transfer/documents',b,service='store').get('code')!=10000
            b['items'][0]['storehouse']=self.destination();b['items'].append({**b['items'][0],'goods':uuid.uuid4().hex})
            before=sql(self.state,'SELECT COUNT(*) FROM goods;');assert self.request('POST','/transfer/add-transferList',b,service='store').get('code')!=10000
            assert sql(self.state,'SELECT COUNT(*) FROM goods;')==before and sql(self.state,'SELECT COUNT(*) FROM swap WHERE number='+literal(b['number'])+';')=='0'
            return ['Same-warehouse and last invalid product rejected atomically through canonical/legacy URL; no invented product or orphan header']
        self.case('movement.transfer_invalid_no_invented_goods',invalid)
        def shortage():
            self.fixture(stock=3);b=self.transfer_body(2);b['items'].append(copy.deepcopy(b['items'][0]));identifier=self.save_doc('swap',b);assert self.mutation('swap',identifier).get('code')!=10000
            assert self.inventory()==3 and self.qty(b['items'][0]['storehouse'])==0 and sql(self.state,'SELECT COUNT(*) FROM summary WHERE `class`='+literal(identifier)+';')=='0';return ['Last-line insufficient stock rolls back first line, both warehouses, all costs and posting proof']
        self.case('movement.transfer_last_line_posting_rollback',shortage)
        def race():
            self.fixture();b=self.transfer_body();barrier=threading.Barrier(2)
            def create(_):barrier.wait(timeout=10);return self.request('POST','/transfer/documents',b,service='store')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(create,range(2)))
            assert sum(x.get('code')==10000 for x in r)==1,str(r);identifier=next(x['data'] for x in r if x.get('code')==10000);v=self.doc('swap',identifier)['version'];barrier=threading.Barrier(2)
            def post(_):barrier.wait(timeout=10);return self.mutation('swap',identifier,version=v)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(post,range(2)))
            assert sum(x.get('code')==10000 for x in r)==1 and self.inventory()==6 and self.qty(b['items'][0]['storehouse'])==4,str(r)
            assert sql(self.state,"SELECT COUNT(*) FROM psi_warehouse_posting WHERE document_id="+literal(identifier)+';')=='1'
            return ['Concurrent same-number creates one UUID; same-version audits exactly one succeeds and stock moves once']
        self.case('movement.transfer_concurrent_number_and_audit',race)
        def report_interop():
            self.fixture();ids=[self.save_doc('swap',self.transfer_body(2)) for _ in range(2)];docs=[self.doc('swap',i) for i in ids];same='QADB'+uuid.uuid4().hex[:24];barrier=threading.Barrier(2)
            for d in docs:d['header']['number']=same;d['items'][0]['nums']=3
            def edit(pair):
                i,d=pair;barrier.wait(timeout=10);return self.request('PUT','/transfer/report-documents/swap/'+i,d,service='store')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(edit,zip(ids,docs)))
            assert sum(x.get('code')==10000 for x in r)==1,str(r)
            assert sql(self.state,'SELECT COUNT(*) FROM swap WHERE number='+literal(same)+';')=='1'
            for i,result in zip(ids,r):
                expected='3.0000' if result.get('code')==10000 else '2.0000';assert sql(self.state,'SELECT nums FROM swap_info WHERE pid='+literal(i)+';')==expected
            i=ids[0];sql(self.state,'UPDATE swap SET cse=1 WHERE id='+literal(i)+';');d=self.doc('swap',i);d['items'][0]['nums']=6
            assert self.request('PUT','/transfer/report-documents/swap/'+i,d,service='store').get('code')!=10000
            before=sql(self.state,'SELECT COUNT(*) FROM psi_inventory_count;');assert self.request('POST','/verify/inventoryPlus',[],service='store').get('code')!=10000
            assert sql(self.state,'SELECT COUNT(*) FROM psi_inventory_count;')==before and self.inventory()==10
            return ['Two real report edits to same transfer number serialize: one succeeds and loser detail update rolls back; report cannot bypass settled draft protection; old calculation-only count explicitly refuses without a false saved/success state']
        self.case('movement.report_interop_number_and_settlement_guards',report_interop)

        def counts():
            self.fixture();second=uuid.uuid4().hex;sql(self.state,'INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES('+','.join(literal(x) for x in [second,'QA Count Second','qa','QG'+second[:16],'0','unit',2,100,0,0,'{}'])+');')
            first=self.goods;self.goods=second;self.incoming(10);self.goods=first;b=self.count_body(12);b['items'].append({**b['items'][0],'goods':second,'counted':7});identifier=self.save_doc('count',b)
            assert self.inventory()==10 and all(Decimal(str(r['book_qty']))==10 for r in self.doc('count',identifier)['items'])
            assert self.mutation('count',identifier).get('code')==10000
            assert self.inventory()==12 and sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(second)+';')=='7.0000'
            d=self.doc('count',identifier);assert len(d['adjustments'])==2
            assert self.mutation('count',identifier,0).get('code')==10000 and self.inventory()==10
            assert sql(self.state,'SELECT SUM(nums) FROM room WHERE goods='+literal(second)+';')=='10.0000'
            assert not self.doc('count',identifier)['adjustments'];self.untouched_money();return ['Actual persisted mixed count book10/10 actual12/7 posts gain2 and loss3 together, independent goods unchanged; reverse restores both original10 with costs/proofs removed and cash/AR unchanged']
        self.case('movement.count_mixed_surplus_loss_and_reverse',counts)
        for qty in [0,10]:
            def zero(qty=qty):
                self.fixture();identifier=self.save_doc('count',self.count_body(qty));assert self.mutation('count',identifier).get('code')==10000 and self.inventory()==qty
                assert len(self.doc('count',identifier)['adjustments'])==(0 if qty==10 else 1)
                assert self.mutation('count',identifier,0).get('code')==10000 and self.inventory()==10
                assert self.mutation('count',identifier,remove=True).get('code')==10000;return ['Actual count'+str(qty)+' supports zero/full-loss or unchanged count; reverse10 and draft delete retains history']
            self.case('movement.count_actual_'+str(qty),zero)
        def expired():
            self.fixture();identifier=self.save_doc('count',self.count_body(12));self.incoming(1,2,'2026-11-16 10:00:00');before=self.doc('count',identifier)
            assert self.mutation('count',identifier).get('code')!=10000 and self.inventory()==11 and self.doc('count',identifier)==before
            return ['Actual receipt after saved count invalidates snapshot; no overwrite of new stock and no adjustment created']
        self.case('movement.count_expired_snapshot_refuses_overwrite',expired)
        def gain_sale():
            with owned_cost_mode(self.state,'fifo'):
                self.fixture(stock=0);identifier=self.save_doc('count',self.count_body(3));assert self.mutation('count',identifier).get('code')==10000 and self.inventory()==3
                sale=self.sale_from(self.warehouse,2);assert self.inventory()==1 and self.movement_cost(sale,'sell')==4
                assert self.mutation('count',identifier,0).get('code')!=10000 and self.inventory()==1 and self.doc('count',identifier)['header']['state']==1
                assert self.post([sale],False).get('code')==10000;assert self.mutation('count',identifier,0).get('code')==10000 and self.inventory()==0;self.untouched_money();return ['Actual zero-stock count gain3 -> sale2 at cost4 -> count reversal blocked until sale reversed -> count reversal restores0/cash100/AR0']
        self.case('movement.count_surplus_sale_and_reverse_dependencies',gain_sale)
        def own_adjustment():
            self.fixture();identifier=self.save_doc('count',self.count_body(12));assert self.mutation('count',identifier).get('code')==10000;link=self.doc('count',identifier)['adjustments'][0];doc=self.store('GET','/transfer/report-documents/entry/'+link['document_id'])
            assert self.request('POST','/transfer/report-documents/entry/'+link['document_id']+'/audit',dict(target=0,version=doc['version']),service='store').get('code')!=10000
            assert self.request('PUT','/otherin/examine',dict(ids=[link['document_id']],target=0,versions={link['document_id']:doc['version']}),service='store').get('code')!=10000
            assert self.inventory()==12;assert self.mutation('count',identifier,0).get('code')==10000;return ['Report and legacy inbound URLs cannot detach/reverse a count-owned adjustment; only owning count can reverse all effects']
        self.case('movement.count_adjustment_cannot_bypass_owner',own_adjustment)
        def late_failure():
            self.fixture();identifier=self.save_doc('count',self.count_body(7));trigger='qa_cnt_'+uuid.uuid4().hex[:16]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source='+literal(identifier)+" AND NEW.info='审核盘点并入账差异' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA count final history'; END IF; END$$\nDELIMITER ;\n")
            try:assert self.mutation('count',identifier).get('code')!=10000
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.inventory()==10 and self.doc('count',identifier)['header']['state']==0 and not self.doc('count',identifier)['adjustments']
            assert self.mutation('count',identifier).get('code')==10000 and self.inventory()==7;assert self.mutation('count',identifier,0).get('code')==10000
            return ['Real MySQL failure at final parent history rolls back generated loss document, stock, journals, proofs, links and state; same version retry succeeds and reverses']
        self.case('movement.count_last_history_failure_whole_transaction',late_failure)
        def count_race():
            self.fixture();identifier=self.save_doc('count',self.count_body(7));v=self.doc('count',identifier)['version'];barrier=threading.Barrier(2)
            def post(_):barrier.wait(timeout=10);return self.mutation('count',identifier,version=v)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:r=list(pool.map(post,range(2)))
            assert sum(x.get('code')==10000 for x in r)==1 and self.inventory()==7 and len(self.doc('count',identifier)['adjustments'])==1
            assert self.mutation('count',identifier,0).get('code')==10000 and self.inventory()==10
            return ['Two same-version count approvals cannot double-apply loss; exactly one adjustment and one stock effect, reverse restores10']
        self.case('movement.count_concurrent_audit_exactly_once',count_race)
        self.variants();self.extra();self.write_report()

    def variants(self):
        def serial():
            with owned_cost_mode(self.state,'fifo'):
                self.fixture(stock=0);sql(self.state,'UPDATE goods SET serial=1,batch=1 WHERE id='+literal(self.goods)+';');sn=['QA-SN-'+uuid.uuid4().hex for _ in range(2)]
                b=self.inbound(2);b['otherInListDetailInfoDTOList'][0].update(batch='QA-B',mfd='2026-11-01',serial=json.dumps(sn));receipt=self.store('POST','/otherin/add',b);self.audit(receipt,1)
                t=self.transfer_body(2);t['items'][0].update(batch='QA-B',mfd='2026-11-01',serial=json.dumps(sn));identifier=self.save_doc('swap',t);dest=t['items'][0]['storehouse'];assert self.mutation('swap',identifier).get('code')==10000
                sale=self.sale_from(dest,1,[sn[1]],'QA-B','2026-11-01');assert self.movement_cost(sale,'sell')==2;assert self.post([sale],False).get('code')==10000
                assert self.mutation('swap',identifier,0).get('code')==10000
                c=self.count_body(1);c['items'][0].update(batch='QA-B',mfd='2026-11-01',serial=json.dumps([sn[0]]));count=self.save_doc('count',c);assert self.mutation('count',count).get('code')==10000 and self.inventory()==1
                assert sql(self.state,'SELECT CAST(state AS SIGNED) FROM serial WHERE goods='+literal(self.goods)+' AND number='+literal(sn[1])+';')=='1'
                assert self.mutation('count',count,0).get('code')==10000 and self.inventory()==2;self.audit(receipt,0);assert self.inventory()==0
                return ['Real batch+serial receipt2 -> HTTP transfer both serials -> destination sale selected serial cost2 -> ordered reverse -> saved count detects missing serial and posts loss1 -> reverse restores original serial state/batch and original receipt reverse0']
        self.case('movement.batch_serial_transfer_sale_count_loss_reverse',serial)
        def serial_replace():
            with owned_cost_mode(self.state,'fifo'):
                self.fixture(stock=0);sql(self.state,'UPDATE goods SET serial=1 WHERE id='+literal(self.goods)+';');old='QA-OLD-'+uuid.uuid4().hex;new='QA-FOUND-'+uuid.uuid4().hex
                b=self.inbound(1);b['otherInListDetailInfoDTOList'][0]['serial']=json.dumps([old]);receipt=self.store('POST','/otherin/add',b);self.audit(receipt,1)
                c=self.count_body(1);c['items'][0].update(serial=json.dumps([new]),price=5);i=self.save_doc('count',c);result=self.mutation('count',i);assert result.get('code')==10000,str(result)
                assert self.inventory()==1 and len(self.doc('count',i)['adjustments'])==2
                sale=self.sale_from(self.warehouse,1,[new]);assert self.movement_cost(sale,'sell')==5 and self.inventory()==0
                assert self.mutation('count',i,0).get('code')!=10000;assert self.post([sale],False).get('code')==10000
                result=self.mutation('count',i,0);assert result.get('code')==10000,str(result);assert self.inventory()==1
                assert sql(self.state,'SELECT number,CAST(state AS SIGNED) FROM serial WHERE goods='+literal(self.goods)+' ORDER BY number;')==old+'\t0'
                self.audit(receipt,0);assert self.inventory()==0
                return ['Same total quantity but different physical serial: count posts missing old serial loss and found new serial gain at cost5; actual new serial sale costs5 and blocks parent reversal; ordered reverse restores original serial/cost and receipt reverse0']
        self.case('movement.serial_count_equal_quantity_replacement_sale_reverse',serial_replace)


    def extra(self):
        def edit_count():
            self.fixture();b=self.count_body(12);i=self.save_doc('count',b);d=self.doc('count',i);b.update(id=i,version=d['version'],items=d['items']);b['items'][0]['counted']=8;self.save_doc('count',b)
            assert self.request('POST','/verify/documents',b,service='store').get('code')!=10000
            assert self.mutation('count',i).get('code')==10000 and self.inventory()==8
            b['version']=self.doc('count',i)['version'];assert self.request('POST','/verify/documents',b,service='store').get('code')!=10000
            assert self.mutation('count',i,0).get('code')==10000 and self.inventory()==10
            assert self.mutation('count',i).get('code')==10000 and self.inventory()==8
            assert self.mutation('count',i,0).get('code')==10000 and self.inventory()==10
            return ['Persisted count edit12->8 retains book10; stale edit and posted edit refused; two full post/reverse cycles each8->10 with fresh versions']
        self.case('movement.count_versioned_edit_and_repeated_cycles',edit_count)
        def mixed_rollback():
            self.fixture();dest=self.destination();b=self.count_body(7);b['items'].append({**b['items'][0],'warehouse':dest,'counted':2});i=self.save_doc('count',b);trigger='qa_cnt_'+uuid.uuid4().hex[:16]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON entry_info FOR EACH ROW BEGIN IF NEW.goods='+literal(self.goods)+" THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA count surplus after loss'; END IF; END$$\nDELIMITER ;\n")
            try:assert self.mutation('count',i).get('code')!=10000
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.inventory()==10 and self.qty(dest)==0 and not self.doc('count',i)['adjustments']
            assert self.mutation('count',i).get('code')==10000 and self.inventory()==7 and self.qty(dest)==2
            trigger='qa_rev_'+uuid.uuid4().hex[:16]
            sql(self.state,'DELIMITER $$\nCREATE TRIGGER `'+trigger+'` BEFORE INSERT ON record FOR EACH ROW BEGIN IF NEW.source='+literal(i)+" AND NEW.info='反审核盘点并回滚差异' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='QA reverse final parent'; END IF; END$$\nDELIMITER ;\n")
            before=self.doc('count',i)
            try:assert self.mutation('count',i,0).get('code')!=10000
            finally:sql(self.state,'DROP TRIGGER IF EXISTS `'+trigger+'`;')
            assert self.doc('count',i)==before and self.inventory()==7 and self.qty(dest)==2
            assert self.mutation('count',i,0).get('code')==10000 and self.inventory()==10 and self.qty(dest)==0
            return ['Mixed count: actual surplus insert failure after loss posting restores both warehouses and leaves no partial documents; final reverse-history failure restores both posted adjustments; retry reverses all']
        self.case('movement.count_mixed_and_reverse_late_failures_atomic',mixed_rollback)
        def permissions():
            self.fixture();p=self.permissions();catalog=[('202','108','/transfer/query-transferList'),('203','108','/transfer/detail-transferInfo'),('204','108','/transfer/add-transferList'),('205','108','/transfer/modify-transfer'),('206','108','/transfer/batch-audit-transfer'),('207','108','/transfer/remove-transfer'),('179','117','/verify/inventoryPlus'),('180','117','/verify/inventoryReduce')]
            with p.catalog():
                for mid in ['108','117']:sql(self.state,"INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES("+','.join(literal(x) for x in [mid,'102','QA Movement','qa-movement-'+mid,0,0,'',0])+');')
                try:
                    for fid,mid,path in catalog:sql(self.state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(x) for x in [fid,mid,'QA Movement '+fid,'/j2-store'+path,0,'1'])+');')
                    p.role_fixture();p.token=p.ordinary
                    def grant(ids):
                        children=[]
                        for mid in ['108','117']:
                            functions=[dict(id=fid) for fid,m,path in catalog if m==mid and fid in ids]
                            if functions:children.append(dict(id=mid,fun=functions))
                        old=p.token;p.token=p.admin
                        try:assert p.request('PUT','/role/modify-role',dict(id=p.role,name=p.role_name,data='',root=json.dumps([dict(id='102',children=children)] if children else []),auth='{}')).get('code')==10000
                        finally:p.token=old
                    b=self.transfer_body();assert p.request('POST','/transfer/documents',b,service='store').get('code')==403
                    grant(['202','203','204','205','206','207','179','180']);r=p.request('POST','/transfer/documents',b,service='store');assert r.get('code')==10000,str(r);i=r['data'];assert sql(self.state,'SELECT `user` FROM swap WHERE id='+literal(i)+';')==p.user_id
                    c=self.count_body(10);r=p.request('POST','/verify/documents',c,service='store');assert r.get('code')==10000,str(r)
                    grant(['179']);assert p.request('GET','/verify/documents',service='store').get('code')==403
                    grant(['202','203','204','205','206','207','179','180']);sql(self.state,"UPDATE func_perm SET is_enable='0' WHERE id='204';")
                    assert p.request('POST','/transfer/documents',self.transfer_body(),service='store').get('code')==403
                    sql(self.state,"UPDATE func_perm SET is_enable='1' WHERE id='204';")
                    foreign=uuid.uuid4().hex;sql(self.state,'INSERT INTO frame(id,name) VALUES('+','.join(literal(x) for x in [foreign,'QA foreign'])+');');other=self.transfer_body();other['frame']=foreign
                    assert p.request('POST','/transfer/documents',other,service='store').get('code')==403
                    grant([]);assert p.request('GET','/transfer/documents',service='store').get('code')==403 and p.request('GET','/verify/documents',service='store').get('code')==403
                finally:
                    sql(self.state,'DELETE FROM func_perm WHERE id IN ('+','.join(literal(x[0]) for x in catalog)+");DELETE FROM menu WHERE id IN ('108','117');")
            return ['Actual role create/save grants take effect for signed ordinary actor; missing grant, revoke, disabled function and cross-organization create denied; count requires both surplus and loss grants, no cached-token bypass']
        self.case('movement.real_role_grant_revoke_disable_and_scope',permissions)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gateway',action='store_true');a=p.parse_args();MovementSuite.through_gateway=a.gateway;s=MovementSuite(read_state());s.run()
