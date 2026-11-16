package com.zeroone.star.sale.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.math.*;
import java.util.*;
import javax.annotation.PostConstruct;

/** Replays stock report balances in business-time order, including backdated sales. Caller holds goods locks. */
@Service
public class SaleStockSummaryService {
    private final JdbcTemplate db;
    public SaleStockSummaryService(JdbcTemplate db) { this.db=db; }
    @PostConstruct public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_stock_posting_order (sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE)");
    }
    private static String id() { return UUID.randomUUID().toString().replace("-",""); }
    private static String s(Object value) { return value==null ? "":value.toString(); }
    private static BigDecimal d(Object value) { return value==null ? BigDecimal.ZERO:new BigDecimal(value.toString()); }
    private static int n(Object value) { return value instanceof Boolean ? ((Boolean)value ? 1:0):value==null ? 0:((Number)value).intValue(); }
    private static class Balance { BigDecimal quantity=BigDecimal.ZERO,value=BigDecimal.ZERO; }
    private static class Layer {
        String id; BigDecimal available,value;
        Layer(String id,BigDecimal available,BigDecimal value) { this.id=id;this.available=available;this.value=value; }
    }
    private static String key(Object... values) { return new JSONArray(Arrays.asList(values)).toString(); }
    private List<String> keys(Map<String,Object> row,String rule) {
        String goods=s(row.get("goods")),warehouse=s(row.get("warehouse"));
        String attr=rule.contains("attr") ? s(row.get("attr")):"";
        String batch=rule.contains("batch") ? s(row.get("batch")):"";
        String mfd=rule.contains("batch") ? s(row.get("mfd")):"";
        return Arrays.asList(key(goods),key(goods,warehouse),key(goods,attr,batch,mfd),key(goods,warehouse,attr,batch,mfd));
    }
    public void add(Map<String,Object> head,Map<String,Object> line,String ledger,BigDecimal quantity,BigDecimal price) {
        String summary=id();
        db.update("INSERT INTO summary(id,pid,type,`class`,info,time,goods,attr,warehouse,batch,mfd,serial,direction,price,nums,uct,bct,exist,balance,handle) VALUES(?,?,'sell',?,?,?,?,?,?,?,?,?,0,?,?,0,0,'[0,0,0,0]','[0,0,0,0]',0)",
                summary,ledger,head.get("id"),line.get("id"),head.get("time"),line.get("goods"),line.get("attr"),line.get("warehouse"),line.get("batch"),line.get("mfd"),line.get("serial"),price,quantity);
        db.update("INSERT INTO psi_stock_posting_order(movement_id) VALUES(?)",summary);
        rebuild(s(line.get("goods")));
    }
    public void remove(String sale) {
        List<String> goods=db.queryForList("SELECT DISTINCT goods FROM summary WHERE type='sell' AND `class`=?",String.class,sale);
        for(String product:goods) clearFifo(product);
        db.update("DELETE FROM psi_stock_posting_order WHERE movement_id IN (SELECT id FROM summary WHERE type='sell' AND `class`=?)",sale);
        db.update("DELETE FROM summary WHERE type='sell' AND `class`=?",sale);
        for(String product:goods) rebuild(product);
    }
    /** Returned inventory carries the exact original issue value, including final rounding residue. */
    public void addReturn(Map<String,Object> head,Map<String,Object> line,String ledger,BigDecimal quantity,BigDecimal value){
        String summary=id();BigDecimal cost=value.divide(quantity,4,RoundingMode.HALF_UP);
        db.update("INSERT INTO summary(id,pid,type,`class`,info,time,goods,attr,warehouse,batch,mfd,serial,direction,price,nums,uct,bct,exist,balance,handle) VALUES(?,?,'sre',?,?,?,?,?,?,?,?,?,1,?,?,?,?,'[0,0,0,0]','[0,0,0,0]',0)",
            summary,ledger,head.get("id"),line.get("id"),head.get("time"),line.get("goods"),line.get("attr"),line.get("warehouse"),line.get("batch"),line.get("mfd"),line.get("serial"),cost,quantity,cost,value);
        db.update("INSERT INTO psi_stock_posting_order(movement_id) VALUES(?)",summary);rebuild(s(line.get("goods")));
    }
    public void removeReturn(String identifier){
        if(db.queryForObject("SELECT COUNT(*) FROM fifo WHERE `in` IN (SELECT id FROM summary WHERE type='sre' AND `class`=?)",Integer.class,identifier)>0)
            throw new IllegalStateException("退货成本层已被后续出库使用，请先处理后续单据");
        List<String> goods=db.queryForList("SELECT DISTINCT goods FROM summary WHERE type='sre' AND `class`=?",String.class,identifier);
        for(String product:goods)clearFifo(product);
        db.update("DELETE FROM psi_stock_posting_order WHERE movement_id IN (SELECT id FROM summary WHERE type='sre' AND `class`=?)",identifier);
        db.update("DELETE FROM summary WHERE type='sre' AND `class`=?",identifier);
        for(String product:goods)rebuild(product);
    }
    private void clearFifo(String goods) {
        db.update("DELETE FROM fifo WHERE `out` IN (SELECT id FROM summary WHERE goods=?) OR `in` IN (SELECT id FROM summary WHERE goods=?)",goods,goods);
    }
    private List<String> serials(Object value) {
        if(s(value).isEmpty()) return Collections.emptyList();
        JSONArray array=new JSONArray(s(value));
        List<String> result=new ArrayList<>();
        for(Object item:array) result.add(item instanceof JSONObject ? ((JSONObject)item).getStr("number"):s(item));
        return result;
    }
    public void rebuild(String goods) {
        List<String> settings=db.queryForList("SELECT info FROM sys WHERE name='fun'",String.class);
        if(settings.size()>1) throw new IllegalStateException("成本配置重复，请先整理系统参数");
        JSONObject fun=settings.isEmpty() ? new JSONObject():new JSONObject(settings.get(0));
        String valuation=fun.getStr("valuation","base"),rule=fun.getStr("rule","def");
        if("balance".equals(rule)) rule="def";
        if("aab".equals(rule)) rule="attr_batch";
        if(!Arrays.asList("base","ma","fifo").contains(valuation) || !Arrays.asList("def","attr","batch","attr_batch").contains(rule))
            throw new IllegalArgumentException("成本计价方法或规则配置无效");
        boolean branch=fun.getBool("branch",false);
        Map<String,Object> product=db.queryForMap("SELECT buy FROM goods WHERE id=?",goods);
        Map<String,BigDecimal> prices=new HashMap<>();
        for(Map<String,Object> attr:db.queryForList("SELECT name,buy FROM attr WHERE pid=?",goods)) prices.put(s(attr.get("name")),d(attr.get("buy")));
        String closedDate=s(db.queryForObject("SELECT MAX(date) FROM period",java.sql.Date.class));
        List<Map<String,Object>> movements=db.queryForList("SELECT s.*,CASE WHEN s.type='buy' THEN (SELECT total FROM buy_info WHERE id=s.info AND pid=s.`class`) END AS purchase_net,CASE WHEN s.type='bre' THEN (SELECT total FROM bre_info WHERE id=s.info AND pid=s.`class`) END AS purchase_return_net,DATE_FORMAT(s.time,'%Y-%m-%d') AS posting_date FROM summary s LEFT JOIN psi_stock_posting_order o ON o.movement_id=s.id WHERE s.goods=? ORDER BY s.time,COALESCE(o.sequence,0),s.id FOR UPDATE",goods);
        clearFifo(goods);
        db.update("UPDATE summary SET handle=0 WHERE goods=?",goods);
        Map<String,Balance> balances=new HashMap<>();
        Map<String,Deque<Layer>> layers=new HashMap<>();
        Map<String,BigDecimal> serialCosts=new HashMap<>();
        for(Map<String,Object> row:movements) {
            String type=s(row.get("type")),identifier=s(row.get("id"));
            boolean incoming=n(row.get("direction"))==1;
            boolean closed=!closedDate.isEmpty() && closedDate.compareTo(s(row.get("posting_date")))>=0;
            BigDecimal quantity=d(row.get("nums"));
            if(quantity.signum()<=0) throw new IllegalStateException("历史收发记录数量无效");
            List<String> scopes=keys(row,rule);
            String selected=scopes.get(branch ? 3:2);
            Balance previous=balances.computeIfAbsent(selected,k->new Balance());
            BigDecimal purchase=prices.getOrDefault(s(row.get("attr")),d(product.get("buy")));
            BigDecimal cost=purchase,exactValue=null;
            boolean fixed=Arrays.asList("buy","bre","entry","extry","swapOut","swapEnter").contains(type);
            if("base".equals(valuation)) cost=fixed ? d(row.get("price")):purchase;
            else if("ma".equals(valuation)) cost=fixed ? d(row.get("price")):previous.quantity.signum()>0 ? previous.value.divide(previous.quantity,8,RoundingMode.HALF_UP):purchase;
            if(incoming && "buy".equals(type) && row.get("purchase_net")!=null) exactValue=d(row.get("purchase_net"));
            // Preserve source return net before rounded unit prices; FIFO below computes its own layer value.
            if(!incoming && "bre".equals(type) && row.get("purchase_return_net")!=null) exactValue=d(row.get("purchase_return_net"));
            if("ma".equals(valuation) && !fixed && !incoming && previous.quantity.signum()>0)
                exactValue=previous.value.multiply(quantity).divide(previous.quantity,4,RoundingMode.HALF_UP);
            Deque<Layer> queue=layers.computeIfAbsent(selected,k->new ArrayDeque<>());
            if("fifo".equals(valuation)) {
                if(incoming) cost=Arrays.asList("buy","entry","swapEnter").contains(type) ? d(row.get("price")):purchase;
                else {
                    BigDecimal remaining=quantity,total=BigDecimal.ZERO;
                    while(remaining.signum()>0 && !queue.isEmpty()) {
                        Layer layer=queue.peek();
                        BigDecimal used=remaining.min(layer.available);
                        BigDecimal usedValue=used.compareTo(layer.available)==0 ? layer.value:layer.value.multiply(used).divide(layer.available,4,RoundingMode.HALF_UP);
                        total=total.add(usedValue); layer.value=layer.value.subtract(usedValue); remaining=remaining.subtract(used); layer.available=layer.available.subtract(used);
                        db.update("INSERT INTO fifo(id,`out`,`in`,handle) VALUES(?,?,?,?)",id(),identifier,layer.id,used);
                        db.update("UPDATE summary SET handle=handle+? WHERE id=?",used,layer.id);
                        if(layer.available.signum()==0) queue.remove();
                    }
                    // Legacy opening balances may precede the available movement history.
                    exactValue=total.add(remaining.multiply(purchase)).setScale(4,RoundingMode.HALF_UP);
                    cost=exactValue.divide(quantity,8,RoundingMode.HALF_UP);
                }
            }
            List<String> serials=serials(row.get("serial"));
            if(!serials.isEmpty()) {
                if(incoming && Arrays.asList("buy","entry","swapEnter").contains(type)) cost=d(row.get("price"));
                else {
                    BigDecimal total=BigDecimal.ZERO;
                    for(String serial:serials) total=total.add(serialCosts.getOrDefault(key(goods,serial),purchase));
                    exactValue=total.setScale(4,RoundingMode.HALF_UP);
                    cost=exactValue.divide(quantity,8,RoundingMode.HALF_UP);
                }
            }
            // SRE value is a source-issued cost allocation, not a new purchase or current-price receipt.
            if(incoming && "sre".equals(type))exactValue=d(row.get("bct"));
            BigDecimal value=exactValue==null ? cost.multiply(quantity).setScale(4,RoundingMode.HALF_UP):exactValue;
            cost=value.divide(quantity,4,RoundingMode.HALF_UP);
            if(closed) { cost=d(row.get("uct"));value=d(row.get("bct")); }
            BigDecimal delta=incoming ? quantity:quantity.negate();
            JSONArray quantities=new JSONArray(),values=new JSONArray();
            for(String scope:scopes) {
                Balance balance=balances.computeIfAbsent(scope,k->new Balance());
                balance.quantity=balance.quantity.add(delta); balance.value=balance.value.add(incoming ? value:value.negate());
                if(balance.quantity.signum()==0) balance.value=BigDecimal.ZERO;
                quantities.add(balance.quantity); values.add(balance.value);
            }
            if(!closed) db.update("UPDATE summary SET uct=?,bct=?,exist=?,balance=? WHERE id=?",cost,value,quantities.toString(),values.toString(),identifier);
            if(incoming && !serials.isEmpty()) {
                BigDecimal allocated=BigDecimal.ZERO;
                for(int index=0;index<serials.size();index++) {
                    BigDecimal serialValue=index==serials.size()-1 ? value.subtract(allocated):value.divide(BigDecimal.valueOf(serials.size()),4,RoundingMode.HALF_UP);
                    serialCosts.put(key(goods,serials.get(index)),serialValue);allocated=allocated.add(serialValue);
                }
            }
            if(incoming && "fifo".equals(valuation)) queue.add(new Layer(identifier,quantity,value));
        }
    }
}
