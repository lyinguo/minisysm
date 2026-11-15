package com.zeroone.star.purchase.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;
import javax.annotation.PostConstruct;
import java.math.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Atomic procurement posting. Reversal uses the original movements and quantity. */
@Service
public class PurchasePostingService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseStockSummaryService summaries;
    public PurchasePostingService(JdbcTemplate db, PurchaseDocumentAccess access, PurchaseStockSummaryService summaries) {
        this.db=db; this.access=access; this.summaries=summaries;
    }
    @PostConstruct public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_purchase_posting (purchase_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(32) NOT NULL,created_at DATETIME NOT NULL)");
    }
    private static String uid() { return UUID.randomUUID().toString().replace("-",""); }
    private static String s(Object v) { return v==null ? "" : v.toString(); }
    private static int n(Object v) { return v instanceof Boolean ? ((Boolean)v ? 1:0) : v==null ? 0 : ((Number)v).intValue(); }
    private static BigDecimal d(Object v) { return v==null ? BigDecimal.ZERO : new BigDecimal(v.toString()); }
    private int count(String sql,Object... args) { return db.queryForObject(sql,Integer.class,args); }
    private String fingerprint(Map<String,Object> head,List<Map<String,Object>> lines) {
        Map<String,Object> immutable=new LinkedHashMap<>(head);
        immutable.remove("examine"); immutable.remove("nucleus");
        return DigestUtils.md5DigestAsHex((immutable.toString()+lines.toString()).getBytes(StandardCharsets.UTF_8));
    }
    @Transactional(rollbackFor=Exception.class)
    public int post(List<String> ids,boolean target) {
        UserDTO actor=access.authorize("/purchase-note/audit");
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(x->x==null || x.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同单据");
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('buy') ON DUPLICATE KEY UPDATE scope='buy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        List<String> ordered=new ArrayList<>(ids); Collections.sort(ordered);
        int changed=0;
        for(String id:ordered) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM buy WHERE id=? FOR UPDATE",id);
            if(found.size()!=1) throw new IllegalArgumentException("采购单不存在");
            Map<String,Object> head=found.get(0);
            access.requireFrame(actor,s(head.get("frame")));
            List<Map<String,Object>> lines=db.queryForList("SELECT * FROM buy_info WHERE pid=? ORDER BY id FOR UPDATE",id);
            boolean audited=n(head.get("examine"))==1;
            List<String> markers=db.queryForList("SELECT fingerprint FROM psi_purchase_posting WHERE purchase_id=? FOR UPDATE",String.class,id);
            if(audited==target) {
                if(audited && markers.isEmpty()) throw new IllegalStateException("该历史已审核单据缺少入账凭据，请先核对库存和资金，不能重复入账");
                continue;
            }
            if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)
                throw new IllegalArgumentException("单据日期已结账，不能审核或反审核");
            if(lines.isEmpty()) throw new IllegalArgumentException("采购单没有商品明细");
            // These product locks are shared with warehouse posting and also protect absent room rows.
            db.queryForList("SELECT id FROM goods WHERE id IN (SELECT goods FROM buy_info WHERE pid=?) ORDER BY id FOR UPDATE",id);
            if(target) {
                if(!markers.isEmpty()) throw new IllegalStateException("未审核单据存在入账凭据，请先核对数据");
                if(n(head.get("check"))!=1) throw new IllegalArgumentException("采购单未核对，不能审核");
                validateMoney(head,lines);
                validateReferences(head,false);
                for(Map<String,Object> line:lines) forwardStock(head,line);
                order(head,lines,true);
                money(head,true);
                int nucleus=d(head.get("money")).compareTo(d(head.get("actual")))==0 ? 2 : d(head.get("money")).signum()==0 ? 0:1;
                db.update("UPDATE buy SET examine=1,nucleus=? WHERE id=?",nucleus,id);
                db.update("INSERT INTO psi_purchase_posting(purchase_id,fingerprint,created_at) VALUES(?,?,CURRENT_TIMESTAMP)",id,fingerprint(head,lines));
            } else {
                if(markers.size()!=1 || !markers.get(0).equals(fingerprint(head,lines)))
                    throw new IllegalStateException("入账凭据缺失或单据入账后被修改，不能自动反审核");
                validateReferences(head,true);
                requireOriginalMovements(head,lines);
                reverseStock(id);
                order(head,lines,false);
                money(head,false);
                db.update("UPDATE buy SET examine=0,nucleus=0 WHERE id=?",id);
                db.update("DELETE FROM psi_purchase_posting WHERE purchase_id=?",id);
            }
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
            String action=target ? "审核采购单":"反审核采购单";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'buy',?,?,?,?)",uid(),id,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),action+"["+id+"]");
            changed++;
        }
        return changed;
    }
    private void validateMoney(Map<String,Object> head,List<Map<String,Object>> lines) {
        BigDecimal actual=d(head.get("actual")), received=d(head.get("money"));
        if(actual.signum()<0 || received.signum()<0 || received.compareTo(actual)>0) throw new IllegalArgumentException("实付金额必须在零与实际金额之间");
        BigDecimal total=BigDecimal.ZERO,taxTotal=BigDecimal.ZERO;
        for(Map<String,Object> line:lines) {
            BigDecimal gross=d(line.get("price")).multiply(d(line.get("nums"))).setScale(4,RoundingMode.HALF_UP);
            BigDecimal deduction=d(line.get("dsc")),net=d(line.get("total")),tax=d(line.get("tax")),taxAmount=d(line.get("tat"));
            if(d(line.get("price")).signum()<0 || d(line.get("nums")).signum()<=0 || deduction.signum()<0 || deduction.compareTo(gross)>0
                    || gross.subtract(deduction).compareTo(net)!=0 || tax.signum()<0 || tax.compareTo(new BigDecimal("100"))>0 || taxAmount.signum()<0
                    || net.add(taxAmount).compareTo(d(line.get("tpt")))!=0)
                throw new IllegalArgumentException("采购明细数量、折扣或金额无效，请重新保存并核对");
            BigDecimal percentTax=net.multiply(tax).movePointLeft(2).setScale(4,RoundingMode.HALF_UP);
            BigDecimal legacyTax=net.multiply(tax).setScale(4,RoundingMode.HALF_UP);
            if(percentTax.compareTo(taxAmount)!=0 && !(tax.compareTo(BigDecimal.ONE)<=0 && legacyTax.compareTo(taxAmount)==0))
                throw new IllegalArgumentException("采购明细税额与税率不一致");
            total=total.add(net);taxTotal=taxTotal.add(d(line.get("tpt")));
        }
        if(total.compareTo(d(head.get("total")))!=0 || taxTotal.compareTo(actual)!=0) throw new IllegalArgumentException("单据金额与明细不一致，请重新保存并核对");
    }
    private void validateReferences(Map<String,Object> head,boolean reverse) {
        String id=s(head.get("id"));
        if(reverse && (count("SELECT COUNT(*) FROM bre WHERE source=?",id)>0
                || count("SELECT COUNT(*) FROM bre_info WHERE source IN (SELECT id FROM buy_info WHERE pid=?)",id)>0
                || count("SELECT COUNT(*) FROM bill_info WHERE mold='buy' AND source=?",id)>0
                || count("SELECT COUNT(*) FROM omy_bill WHERE type='buy' AND source=?",id)>0
                || count("SELECT COUNT(*) FROM buy_info WHERE pid=? AND COALESCE(retreat,0)>0",id)>0
                || count("SELECT COUNT(*) FROM buy_bill WHERE pid=? AND NOT(type='buy' AND source=?)",id,id)>0
                || count("SELECT COUNT(*) FROM invoice WHERE type='buy' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='buy' AND `class`=?)",id)>0))
            throw new IllegalArgumentException("存在退货、核销、发票或费用结算引用，请先处理关联单据");
        if(count("SELECT COUNT(*) FROM cost WHERE type='buy' AND `class`=? AND COALESCE(settle,0)<>0",id)>0)
            throw new IllegalArgumentException("单据费用已经结算，不能反向修改");
    }
    public void requireDeletable(String id) {
        Map<String,Object> head=db.queryForMap("SELECT * FROM buy WHERE id=? FOR UPDATE",id);
        if(n(head.get("check"))!=0 || n(head.get("examine"))!=0 || n(head.get("nucleus"))!=0)
            throw new IllegalArgumentException("已核对、审核或核销的采购单不能删除，请先处理单据状态");
        if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0) throw new IllegalArgumentException("已结账期间的采购单不能删除");
        validateReferences(head,true);
        if(count("SELECT COUNT(*) FROM psi_purchase_posting WHERE purchase_id=?",id)>0
                || count("SELECT COUNT(*) FROM room_info WHERE type='buy' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM serve_info WHERE type='buy' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM account_info WHERE type='buy' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM buy_bill WHERE pid=?",id)>0
                || count("SELECT COUNT(*) FROM cost WHERE type='buy' AND `class`=?",id)>0)
            throw new IllegalArgumentException("采购单存在库存、资金、费用或核销凭据，不能删除");
    }
    private void order(Map<String,Object> head,List<Map<String,Object>> lines,boolean forward) {
        String source=s(head.get("source"));
        if(source.isEmpty() || "0".equals(source)) {
            if(lines.stream().anyMatch(row->!s(row.get("source")).isEmpty() && !"0".equals(s(row.get("source"))))) throw new IllegalArgumentException("商品明细关联了订单但单据来源为空");
            return;
        }
        List<Map<String,Object>> orders=db.queryForList("SELECT b.*,CAST(b.state AS SIGNED) AS source_state FROM bor b WHERE b.id=? FOR UPDATE",source);
        if(orders.size()!=1 || n(orders.get(0).get("examine"))!=1 || n(orders.get(0).get("source_state"))==3
                || !s(head.get("frame")).equals(s(orders.get(0).get("frame"))) || !s(head.get("supplier")).equals(s(orders.get(0).get("supplier"))))
            throw new IllegalArgumentException("来源订单不存在、未审核、已关闭或供应商组织不匹配");
        for(Map<String,Object> line:lines) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM bor_info WHERE id=? AND pid=? FOR UPDATE",line.get("source"),source);
            if(found.size()!=1) throw new IllegalArgumentException("来源订单明细不存在");
            Map<String,Object> original=found.get(0);
            for(String field:Arrays.asList("goods","attr","unit")) if(!s(line.get(field)).equals(s(original.get(field)))) throw new IllegalArgumentException("商品、属性或单位与来源订单不一致");
            BigDecimal delta=d(line.get("nums")); if(!forward) delta=delta.negate();
            if(db.update("UPDATE bor_info SET handle=COALESCE(handle,0)+? WHERE id=? AND COALESCE(handle,0)+? BETWEEN 0 AND nums",delta,line.get("source"),delta)!=1)
                throw new IllegalArgumentException("入库数量超过订单剩余数量，或已入库数量不足以反审核");
        }
        int state=count("SELECT COUNT(*) FROM bor_info WHERE pid=? AND COALESCE(handle,0)<nums",source)==0 ? 2
                : count("SELECT COUNT(*) FROM bor_info WHERE pid=? AND COALESCE(handle,0)>0",source)>0 ? 1:0;
        db.update("UPDATE bor SET state=? WHERE id=?",state,source);
    }
    private void money(Map<String,Object> head,boolean forward) {
        String id=s(head.get("id")),supplier=s(head.get("supplier")),account=s(head.get("account"));
        List<Map<String,Object>> suppliers=db.queryForList("SELECT id,frame FROM supplier WHERE id=? FOR UPDATE",supplier);
        if(suppliers.size()!=1) throw new IllegalArgumentException("供应商不存在");
        BigDecimal received=d(head.get("money")), outstanding=d(head.get("actual")).subtract(received);
        if(received.signum()>0) {
            List<Map<String,Object>> accounts=db.queryForList("SELECT id,frame,balance FROM account WHERE id=? FOR UPDATE",account);
            if(accounts.size()!=1) throw new IllegalArgumentException("结算账户不存在");
            String accountFrame=s(accounts.get(0).get("frame"));
            if(!"0".equals(accountFrame) && !s(head.get("frame")).equals(accountFrame)) throw new IllegalArgumentException("结算账户与单据组织不一致");
            if(forward && d(accounts.get(0).get("balance")).compareTo(received)<0) throw new IllegalStateException("账户余额不足以支付本次采购");
            if(!forward && (count("SELECT COUNT(*) FROM account_info WHERE type='buy' AND `class`=? AND pid=? AND money=? AND direction=0",id,account,received)!=1
                    || count("SELECT COUNT(*) FROM buy_bill WHERE pid=? AND type='buy' AND source=? AND money=?",id,id,received)!=1))
                throw new IllegalStateException("付款流水与入账凭据不一致，不能自动反审核");
            db.update("UPDATE account SET balance=COALESCE(balance,0)+? WHERE id=?",forward ? received.negate():received,account);
            if(forward) {
                db.update("INSERT INTO account_info(id,pid,type,`class`,time,direction,money) VALUES(?,?,'buy',?,?,0,?)",uid(),account,id,head.get("time"),received);
                db.update("INSERT INTO buy_bill(id,pid,type,source,time,money) VALUES(?,?,'buy',?,?,?)",uid(),id,id,head.get("time"),received);
            } else {
                db.update("DELETE FROM account_info WHERE type='buy' AND `class`=?",id);
                db.update("DELETE FROM buy_bill WHERE pid=? AND type='buy' AND source=?",id,id);
            }
        }
        String supplierFrame=s(suppliers.get(0).get("frame"));
        if(!"0".equals(supplierFrame) && !s(head.get("frame")).equals(supplierFrame)) throw new IllegalArgumentException("供应商与单据组织不一致");
        db.update("UPDATE supplier SET balance=COALESCE(balance,0)+? WHERE id=?",forward ? outstanding:outstanding.negate(),supplier);
    }
    private BigDecimal radix(Map<String,Object> product,String unit) {
        if(!"-1".equals(s(product.get("unit")))) {
            if(!s(product.get("unit")).equals(unit)) throw new IllegalArgumentException("商品单位不匹配");
            return BigDecimal.ONE;
        }
        JSONArray units;
        try { units=new JSONArray(s(product.get("units"))); } catch(Exception e) { throw new IllegalArgumentException("商品多单位配置无效"); }
        if(units.isEmpty()) throw new IllegalArgumentException("商品多单位配置为空");
        BigDecimal factor=BigDecimal.ONE;
        if(unit.equals(units.getJSONObject(0).getStr("source"))) return factor;
        for(Object entry:units) {
            JSONObject item=new JSONObject(entry);
            factor=factor.multiply(d(item.get("nums")));
            if(factor.signum()<=0) throw new IllegalArgumentException("单位换算率必须大于零");
            if(unit.equals(item.getStr("name"))) return factor;
        }
        throw new IllegalArgumentException("单位不存在于商品多单位配置");
    }
    private void forwardStock(Map<String,Object> head,Map<String,Object> line) {
        String id=s(head.get("id")), goods=s(line.get("goods")), attr=s(line.get("attr"));
        List<Map<String,Object>> products=db.queryForList("SELECT * FROM goods WHERE id=? FOR UPDATE",goods);
        if(products.size()!=1) throw new IllegalArgumentException("商品不存在");
        Map<String,Object> product=products.get(0);
        if(!attr.isEmpty() && count("SELECT COUNT(*) FROM attr WHERE pid=? AND name=?",goods,attr)!=1)
            throw new IllegalArgumentException("商品辅助属性不存在或重复");
        BigDecimal qty=d(line.get("nums")).multiply(radix(product,s(line.get("unit"))));
        if(qty.signum()<=0 || qty.scale()>4 && qty.stripTrailingZeros().scale()>4) throw new IllegalArgumentException("基础数量必须为正数且最多4位小数");
        BigDecimal price=d(line.get("total")).divide(qty,4,RoundingMode.HALF_UP);
        if(n(product.get("type"))==1) {
            List<String> services=db.queryForList("SELECT id FROM serve WHERE goods=? AND COALESCE(attr,'')=? FOR UPDATE",String.class,goods,attr);
            if(services.size()>1) throw new IllegalStateException("服务累计记录重复");
            String service=services.isEmpty() ? uid():services.get(0);
            if(services.isEmpty()) db.update("INSERT INTO serve(id,goods,attr,nums) VALUES(?,?,?,0)",service,goods,attr);
            db.update("UPDATE serve SET nums=nums+? WHERE id=?",qty,service);
            db.update("INSERT INTO serve_info(id,pid,type,`class`,info,time,price,nums) VALUES(?,?,'buy',?,?,?,?,?)",uid(),service,id,line.get("id"),head.get("time"),price,qty);
            return;
        }
        String warehouse=s(line.get("warehouse"));
        if(count("SELECT COUNT(*) FROM warehouse WHERE id=? AND frame IN ('0',?)",warehouse,head.get("frame"))!=1) throw new IllegalArgumentException("仓库不存在或与单据组织不一致");
        List<Map<String,Object>> rooms=db.queryForList("SELECT * FROM room WHERE goods=? AND warehouse=? AND COALESCE(attr,'')=? FOR UPDATE",goods,warehouse,attr);
        if(rooms.size()>1) throw new IllegalStateException("仓库库存记录重复");
        String room=rooms.isEmpty() ? uid():s(rooms.get(0).get("id")),batch="";
        if(rooms.isEmpty()) db.update("INSERT INTO room(id,warehouse,goods,attr,nums) VALUES(?,?,?,?,0)",room,warehouse,goods,attr);
        if(n(product.get("batch"))==1 || !s(line.get("batch")).isEmpty()) {
            if(s(line.get("batch")).isEmpty() || line.get("mfd")==null) throw new IllegalArgumentException("批次商品必须填写批次号和生产日期");
            List<Map<String,Object>> batches=db.queryForList("SELECT * FROM batch WHERE room=? AND number=? FOR UPDATE",room,line.get("batch"));
            if(batches.size()>1) throw new IllegalStateException("批次库存记录重复");
            if(batches.isEmpty()) {
                batch=uid();
                db.update("INSERT INTO batch(id,room,warehouse,goods,number,time,nums) VALUES(?,?,?,?,?,?,0)",batch,room,warehouse,goods,line.get("batch"),line.get("mfd"));
            } else {
                if(!s(batches.get(0).get("time")).equals(s(line.get("mfd")))) throw new IllegalArgumentException("相同批次的生产日期不一致");
                batch=s(batches.get(0).get("id"));
            }
            db.update("UPDATE batch SET nums=nums+? WHERE id=?",qty,batch);
            db.update("INSERT INTO batch_info(id,pid,type,`class`,info,direction,nums) VALUES(?,?,'buy',?,?,1,?)",uid(),batch,id,line.get("id"),qty);
        }
        if(n(product.get("serial"))==1 || !s(line.get("serial")).isEmpty() && !"[]".equals(s(line.get("serial")))) {
            JSONArray values;
            try { values=new JSONArray(s(line.get("serial"))); } catch(Exception e) { throw new IllegalArgumentException("序列号必须是JSON数组"); }
            Set<String> serials=new HashSet<>();
            for(Object value:values) {
                String number=value instanceof JSONObject ? ((JSONObject)value).getStr("number"):s(value);
                if(number==null || number.trim().isEmpty() || !serials.add(number.trim())) throw new IllegalArgumentException("序列号为空或重复");
                List<Map<String,Object>> rows=db.queryForList("SELECT * FROM serial WHERE goods=? AND number=? FOR UPDATE",goods,number.trim());
                if(!rows.isEmpty()) throw new IllegalArgumentException("商品序列号已存在");
                String serial=uid();
                db.update("INSERT INTO serial(id,room,warehouse,batch,goods,number,state) VALUES(?,?,?,?,?,?,0)",serial,room,warehouse,batch,goods,number.trim());
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,'buy',?,?)",uid(),serial,id,line.get("id"));
            }
            if(qty.compareTo(BigDecimal.valueOf(serials.size()))!=0) throw new IllegalArgumentException("序列号数量与基础数量不一致");
        }
        db.update("UPDATE room SET nums=nums+? WHERE id=?",qty,room);
        String ledger=uid();
        db.update("INSERT INTO room_info(id,pid,type,`class`,info,time,direction,price,nums) VALUES(?,?,'buy',?,?,?,1,?,?)",ledger,room,id,line.get("id"),head.get("time"),price,qty);
        summaries.add(head,line,ledger,qty,price);
    }
    private void reverseStock(String id) {
        summaries.remove(id);
        for(Map<String,Object> row:db.queryForList("SELECT * FROM room_info WHERE type='buy' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE room SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1) throw new IllegalStateException("库存已被使用或原库存记录不存在，不能反审核");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM batch_info WHERE type='buy' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE batch SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1) throw new IllegalStateException("批次库存已被使用，不能反审核");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serial_info WHERE type='buy' AND `class`=? FOR UPDATE",id)) {
            if(count("SELECT COUNT(*) FROM serial_info WHERE pid=? AND NOT(type='buy' AND `class`=?)",row.get("pid"),id)>0)
                throw new IllegalStateException("序列号已被后续业务使用，不能反审核");
            if(count("SELECT COUNT(*) FROM serial s JOIN room_info r ON r.pid=s.room WHERE s.id=? AND r.type='buy' AND r.`class`=? AND r.info=?",row.get("pid"),id,row.get("info"))!=1)
                throw new IllegalStateException("序列号位置与原采购入库不一致");
            if(db.update("DELETE FROM serial WHERE id=? AND state=0",row.get("pid"))!=1) throw new IllegalStateException("序列号已被后续业务修改");
        }
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serve_info WHERE type='buy' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE serve SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1) throw new IllegalStateException("服务累计数量与原流水不一致");
        for(String table:Arrays.asList("room_info","batch_info","serial_info","serve_info")) db.update("DELETE FROM "+table+" WHERE type='buy' AND `class`=?",id);
    }
    private void requireOriginalMovements(Map<String,Object> head,List<Map<String,Object>> lines) {
        String id=s(head.get("id"));
        for(Map<String,Object> line:lines) {
            int rooms=count("SELECT COUNT(*) FROM room_info WHERE type='buy' AND `class`=? AND info=? AND direction=1 AND nums>0",id,line.get("id"));
            int services=count("SELECT COUNT(*) FROM serve_info WHERE type='buy' AND `class`=? AND info=? AND nums>0",id,line.get("id"));
            if(rooms+services!=1) throw new IllegalStateException("原入库流水缺失或重复，不能自动反审核");
            if(rooms==1 && count("SELECT COUNT(*) FROM summary s JOIN room_info r ON r.id=s.pid WHERE s.type='buy' AND s.`class`=? AND s.info=? AND s.direction=1 AND s.nums=r.nums",id,line.get("id"))!=1)
                throw new IllegalStateException("原入库报表流水不一致，不能自动反审核");
        }
    }
}
