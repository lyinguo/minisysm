package com.zeroone.star.sale.service;

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

/** Atomic sales posting. Reversal uses the original movements, never today's unit configuration. */
@Service
public class SalePostingService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleDraftService drafts;
    private final SaleStockSummaryService summaries;
    public SalePostingService(JdbcTemplate db, SaleDocumentAccess access, SaleDraftService drafts,SaleStockSummaryService summaries) {
        this.db=db; this.access=access; this.drafts=drafts; this.summaries=summaries;
    }
    @PostConstruct public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_sale_posting (sale_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(32) NOT NULL,created_at DATETIME NOT NULL)");
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
        UserDTO actor=access.authorize("/sale/form/examine");
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(x->x==null || x.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同单据");
        drafts.lockWrites();
        List<String> ordered=new ArrayList<>(ids); Collections.sort(ordered);
        int changed=0;
        for(String id:ordered) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM sell WHERE id=? FOR UPDATE",id);
            if(found.size()!=1) throw new IllegalArgumentException("销售单不存在");
            Map<String,Object> head=found.get(0);
            access.requireFrame(actor,s(head.get("frame")));
            List<Map<String,Object>> lines=db.queryForList("SELECT * FROM sell_info WHERE pid=? ORDER BY id FOR UPDATE",id);
            boolean audited=n(head.get("examine"))==1;
            List<String> markers=db.queryForList("SELECT fingerprint FROM psi_sale_posting WHERE sale_id=? FOR UPDATE",String.class,id);
            if(audited==target) {
                if(audited && markers.isEmpty()) throw new IllegalStateException("该历史已审核单据缺少入账凭据，请先核对库存和资金，不能重复入账");
                continue;
            }
            if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)
                throw new IllegalArgumentException("单据日期已结账，不能审核或反审核");
            if(lines.isEmpty()) throw new IllegalArgumentException("销售单没有商品明细");
            // These product locks are shared with warehouse posting and also protect absent room rows.
            db.queryForList("SELECT id FROM goods WHERE id IN (SELECT goods FROM sell_info WHERE pid=?) ORDER BY id FOR UPDATE",id);
            if(target) {
                if(!markers.isEmpty()) throw new IllegalStateException("未审核单据存在入账凭据，请先核对数据");
                if(n(head.get("check"))!=1) throw new IllegalArgumentException("销售单未核对，不能审核");
                validateMoney(head,lines);
                validateReferences(head,false);
                for(Map<String,Object> line:lines) forwardStock(head,line);
                order(head,lines,true);
                money(head,true);
                int nucleus=d(head.get("money")).compareTo(d(head.get("actual")))==0 ? 2 : d(head.get("money")).signum()==0 ? 0:1;
                db.update("UPDATE sell SET examine=1,nucleus=? WHERE id=?",nucleus,id);
                db.update("INSERT INTO psi_sale_posting(sale_id,fingerprint,created_at) VALUES(?,?,CURRENT_TIMESTAMP)",id,fingerprint(head,lines));
            } else {
                if(markers.size()!=1 || !markers.get(0).equals(fingerprint(head,lines)))
                    throw new IllegalStateException("入账凭据缺失或单据入账后被修改，不能自动反审核");
                validateReferences(head,true);
                reverseStock(id);
                order(head,lines,false);
                money(head,false);
                db.update("UPDATE sell SET examine=0,nucleus=0 WHERE id=?",id);
                db.update("DELETE FROM psi_sale_posting WHERE sale_id=?",id);
            }
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
            String action=target ? "审核销售单":"反审核销售单";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'sell',?,?,?,?)",uid(),id,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),action+"["+id+"]");
            changed++;
        }
        return changed;
    }
    private void validateMoney(Map<String,Object> head,List<Map<String,Object>> lines) {
        BigDecimal actual=d(head.get("actual")), received=d(head.get("money"));
        if(actual.signum()<0 || received.signum()<0 || received.compareTo(actual)>0) throw new IllegalArgumentException("实收金额必须在零与实际金额之间");
        BigDecimal total=BigDecimal.ZERO,taxTotal=BigDecimal.ZERO;
        for(Map<String,Object> line:lines) { total=total.add(d(line.get("total"))); taxTotal=taxTotal.add(d(line.get("tpt"))); }
        if(total.compareTo(d(head.get("total")))!=0 || taxTotal.compareTo(actual)!=0) throw new IllegalArgumentException("单据金额与明细不一致，请重新保存并核对");
    }
    private void validateReferences(Map<String,Object> head,boolean reverse) {
        String id=s(head.get("id"));
        if(reverse && (count("SELECT COUNT(*) FROM sre WHERE source=?",id)>0
                || count("SELECT COUNT(*) FROM sre_info WHERE source IN (SELECT id FROM sell_info WHERE pid=?)",id)>0
                || count("SELECT COUNT(*) FROM bill_info WHERE mold='sell' AND source=?",id)>0
                || count("SELECT COUNT(*) FROM imy_bill WHERE type='sell' AND source=?",id)>0
                || count("SELECT COUNT(*) FROM sell_info WHERE pid=? AND COALESCE(retreat,0)>0",id)>0
                || count("SELECT COUNT(*) FROM sell_bill WHERE pid=? AND NOT(type='sell' AND source=?)",id,id)>0
                || count("SELECT COUNT(*) FROM invoice WHERE type='sell' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='sell' AND `class`=?)",id)>0))
            throw new IllegalArgumentException("存在退货、核销、发票或费用结算引用，请先处理关联单据");
        if(count("SELECT COUNT(*) FROM cost WHERE type='sell' AND `class`=? AND COALESCE(settle,0)<>0",id)>0)
            throw new IllegalArgumentException("单据费用已经结算，不能反向修改");
    }
    public void requireDeletable(String id) {
        Map<String,Object> head=db.queryForMap("SELECT * FROM sell WHERE id=? FOR UPDATE",id);
        if(n(head.get("check"))!=0 || n(head.get("examine"))!=0 || n(head.get("nucleus"))!=0)
            throw new IllegalArgumentException("已核对、审核或核销的销售单不能删除，请先处理单据状态");
        if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0) throw new IllegalArgumentException("已结账期间的销售单不能删除");
        validateReferences(head,true);
        if(count("SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id=?",id)>0
                || count("SELECT COUNT(*) FROM room_info WHERE type='sell' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM serve_info WHERE type='sell' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM account_info WHERE type='sell' AND `class`=?",id)>0
                || count("SELECT COUNT(*) FROM sell_bill WHERE pid=?",id)>0
                || count("SELECT COUNT(*) FROM cost WHERE type='sell' AND `class`=?",id)>0)
            throw new IllegalArgumentException("销售单存在库存、资金、费用或核销凭据，不能删除");
    }
    private void order(Map<String,Object> head,List<Map<String,Object>> lines,boolean forward) {
        String source=s(head.get("source"));
        if(source.isEmpty() || "0".equals(source)) {
            if(lines.stream().anyMatch(row->!s(row.get("source")).isEmpty() && !"0".equals(s(row.get("source"))))) throw new IllegalArgumentException("商品明细关联了订单但单据来源为空");
            return;
        }
        // MySQL TINYINT(1) is otherwise returned as Boolean, collapsing states 2/3 to 1.
        List<Map<String,Object>> orders=db.queryForList("SELECT s.*,CAST(s.examine AS SIGNED) AS approval_state,CAST(s.state AS SIGNED) AS execution_state FROM sor s WHERE s.id=? FOR UPDATE",source);
        if(orders.size()!=1 || n(orders.get(0).get("approval_state"))!=1
                || orders.get(0).get("execution_state")==null || n(orders.get(0).get("execution_state"))<0 || n(orders.get(0).get("execution_state"))>2
                || !s(head.get("frame")).equals(s(orders.get(0).get("frame"))) || !s(head.get("customer")).equals(s(orders.get(0).get("customer"))))
            throw new IllegalArgumentException("来源订单不存在、未审核、已关闭或客户组织不匹配");
        for(Map<String,Object> line:lines) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM sor_info WHERE id=? AND pid=? FOR UPDATE",line.get("source"),source);
            if(found.size()!=1) throw new IllegalArgumentException("来源订单明细不存在");
            Map<String,Object> original=found.get(0);
            for(String field:Arrays.asList("goods","attr","unit")) if(!s(line.get(field)).equals(s(original.get(field)))) throw new IllegalArgumentException("商品、属性或单位与来源订单不一致");
            BigDecimal delta=d(line.get("nums")); if(!forward) delta=delta.negate();
            if(db.update("UPDATE sor_info SET handle=COALESCE(handle,0)+? WHERE id=? AND COALESCE(handle,0)+? BETWEEN 0 AND nums",delta,line.get("source"),delta)!=1)
                throw new IllegalArgumentException("出库数量超过订单剩余数量，或已出库数量不足以反审核");
        }
        int state=count("SELECT COUNT(*) FROM sor_info WHERE pid=? AND COALESCE(handle,0)<nums",source)==0 ? 2
                : count("SELECT COUNT(*) FROM sor_info WHERE pid=? AND COALESCE(handle,0)>0",source)>0 ? 1:0;
        db.update("UPDATE sor SET state=? WHERE id=?",state,source);
    }
    private void money(Map<String,Object> head,boolean forward) {
        String id=s(head.get("id")),customer=s(head.get("customer")),account=s(head.get("account"));
        List<Map<String,Object>> customers=db.queryForList("SELECT id,frame FROM customer WHERE id=? FOR UPDATE",customer);
        if(customers.size()!=1) throw new IllegalArgumentException("客户不存在");
        BigDecimal received=d(head.get("money")), outstanding=d(head.get("actual")).subtract(received);
        if(received.signum()>0) {
            List<Map<String,Object>> accounts=db.queryForList("SELECT id,frame,balance FROM account WHERE id=? FOR UPDATE",account);
            if(accounts.size()!=1) throw new IllegalArgumentException("结算账户不存在");
            String accountFrame=s(accounts.get(0).get("frame"));
            if(!"0".equals(accountFrame) && !s(head.get("frame")).equals(accountFrame)) throw new IllegalArgumentException("结算账户与单据组织不一致");
            if(!forward && d(accounts.get(0).get("balance")).compareTo(received)<0) throw new IllegalStateException("账户余额不足以撤销本次收款");
            if(!forward && (count("SELECT COUNT(*) FROM account_info WHERE type='sell' AND `class`=? AND pid=? AND money=? AND direction=1",id,account,received)!=1
                    || count("SELECT COUNT(*) FROM sell_bill WHERE pid=? AND type='sell' AND source=? AND money=?",id,id,received)!=1))
                throw new IllegalStateException("收款流水与入账凭据不一致，不能自动反审核");
            db.update("UPDATE account SET balance=COALESCE(balance,0)+? WHERE id=?",forward ? received:received.negate(),account);
            if(forward) {
                db.update("INSERT INTO account_info(id,pid,type,`class`,time,direction,money) VALUES(?,?,'sell',?,?,1,?)",uid(),account,id,head.get("time"),received);
                db.update("INSERT INTO sell_bill(id,pid,type,source,time,money) VALUES(?,?,'sell',?,?,?)",uid(),id,id,head.get("time"),received);
            } else {
                db.update("DELETE FROM account_info WHERE type='sell' AND `class`=?",id);
                db.update("DELETE FROM sell_bill WHERE pid=? AND type='sell' AND source=?",id,id);
            }
        }
        db.update("UPDATE customer SET balance=COALESCE(balance,0)+? WHERE id=?",forward ? outstanding:outstanding.negate(),customer);
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
        BigDecimal qty=d(line.get("nums")).multiply(radix(product,s(line.get("unit"))));
        if(qty.signum()<=0 || qty.scale()>4 && qty.stripTrailingZeros().scale()>4) throw new IllegalArgumentException("基础数量必须为正数且最多4位小数");
        BigDecimal price=d(line.get("price")).multiply(d(line.get("nums"))).divide(qty,4,RoundingMode.HALF_UP);
        if(n(product.get("type"))==1) {
            List<String> services=db.queryForList("SELECT id FROM serve WHERE goods=? AND COALESCE(attr,'')=? FOR UPDATE",String.class,goods,attr);
            if(services.size()>1) throw new IllegalStateException("服务累计记录重复");
            String service=services.isEmpty() ? uid():services.get(0);
            if(services.isEmpty()) db.update("INSERT INTO serve(id,goods,attr,nums) VALUES(?,?,?,0)",service,goods,attr);
            db.update("UPDATE serve SET nums=nums+? WHERE id=?",qty,service);
            db.update("INSERT INTO serve_info(id,pid,type,`class`,info,time,price,nums) VALUES(?,?,'sell',?,?,?,?,?)",uid(),service,id,line.get("id"),head.get("time"),price,qty);
            return;
        }
        String warehouse=s(line.get("warehouse"));
        if(count("SELECT COUNT(*) FROM warehouse WHERE id=? AND frame IN ('0',?)",warehouse,head.get("frame"))!=1) throw new IllegalArgumentException("仓库不存在或与单据组织不一致");
        List<Map<String,Object>> rooms=db.queryForList("SELECT * FROM room WHERE goods=? AND warehouse=? AND COALESCE(attr,'')=? FOR UPDATE",goods,warehouse,attr);
        if(rooms.size()!=1 || d(rooms.get(0).get("nums")).compareTo(qty)<0) throw new IllegalStateException("仓库库存不足或记录重复");
        String room=s(rooms.get(0).get("id")),batch="";
        if(n(product.get("batch"))==1 || !s(line.get("batch")).isEmpty()) {
            List<Map<String,Object>> batches=db.queryForList("SELECT * FROM batch WHERE room=? AND number=? AND time=? FOR UPDATE",room,line.get("batch"),line.get("mfd"));
            if(batches.size()!=1 || d(batches.get(0).get("nums")).compareTo(qty)<0) throw new IllegalStateException("批次库存不足或生产日期不匹配");
            batch=s(batches.get(0).get("id"));
            db.update("UPDATE batch SET nums=nums-? WHERE id=?",qty,batch);
            db.update("INSERT INTO batch_info(id,pid,type,`class`,info,direction,nums) VALUES(?,?,'sell',?,?,0,?)",uid(),batch,id,line.get("id"),qty);
        }
        if(n(product.get("serial"))==1 || !s(line.get("serial")).isEmpty() && !"[]".equals(s(line.get("serial")))) {
            JSONArray values;
            try { values=new JSONArray(s(line.get("serial"))); } catch(Exception e) { throw new IllegalArgumentException("序列号必须是JSON数组"); }
            Set<String> serials=new HashSet<>();
            for(Object value:values) {
                String number=value instanceof JSONObject ? ((JSONObject)value).getStr("number"):s(value);
                if(number==null || number.trim().isEmpty() || !serials.add(number.trim())) throw new IllegalArgumentException("序列号为空或重复");
                List<Map<String,Object>> rows=db.queryForList("SELECT * FROM serial WHERE goods=? AND number=? FOR UPDATE",goods,number.trim());
                if(rows.size()!=1 || n(rows.get(0).get("state"))!=0 || !room.equals(s(rows.get(0).get("room"))) || !batch.equals(s(rows.get(0).get("batch"))))
                    throw new IllegalArgumentException("序列号状态、仓库或批次不匹配");
                String serial=s(rows.get(0).get("id"));
                db.update("UPDATE serial SET state=1 WHERE id=?",serial);
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,'sell',?,?)",uid(),serial,id,line.get("id"));
            }
            if(qty.compareTo(BigDecimal.valueOf(serials.size()))!=0) throw new IllegalArgumentException("序列号数量与基础数量不一致");
        }
        db.update("UPDATE room SET nums=nums-? WHERE id=?",qty,room);
        String ledger=uid();
        db.update("INSERT INTO room_info(id,pid,type,`class`,info,time,direction,price,nums) VALUES(?,?,'sell',?,?,?,0,?,?)",ledger,room,id,line.get("id"),head.get("time"),price,qty);
        summaries.add(head,line,ledger,qty,price);
    }
    private void reverseStock(String id) {
        summaries.remove(id);
        for(Map<String,Object> row:db.queryForList("SELECT * FROM room_info WHERE type='sell' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE room SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1) throw new IllegalStateException("原库存记录不存在");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM batch_info WHERE type='sell' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE batch SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1) throw new IllegalStateException("原批次记录不存在");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serial_info WHERE type='sell' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE serial SET state=0 WHERE id=? AND state=1",row.get("pid"))!=1) throw new IllegalStateException("序列号已被后续业务修改");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serve_info WHERE type='sell' AND `class`=? FOR UPDATE",id))
            if(db.update("UPDATE serve SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1) throw new IllegalStateException("服务累计数量与原流水不一致");
        for(String table:Arrays.asList("room_info","batch_info","serial_info","serve_info")) db.update("DELETE FROM "+table+" WHERE type='sell' AND `class`=?",id);
    }
}
