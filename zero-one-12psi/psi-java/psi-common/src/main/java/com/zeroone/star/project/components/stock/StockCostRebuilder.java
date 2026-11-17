package com.zeroone.star.project.components.stock;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import org.springframework.jdbc.core.JdbcTemplate;
import java.math.*;
import java.util.*;

/** Shared business-time cost replay. Caller holds sorted product locks in its transaction. */
public final class StockCostRebuilder {
    private final JdbcTemplate db;
    public StockCostRebuilder(JdbcTemplate db) { this.db=db; }
    private static String id() { return UUID.randomUUID().toString().replace("-",""); }
    private static String s(Object value) { return value==null ? "":value.toString(); }
    private static BigDecimal d(Object value) { return value==null ? BigDecimal.ZERO:new BigDecimal(value.toString()); }
    private static int n(Object value) { return value instanceof Boolean ? ((Boolean)value ? 1:0):value==null ? 0:((Number)value).intValue(); }
    private static class Balance { BigDecimal quantity=BigDecimal.ZERO,value=BigDecimal.ZERO; }
    private static class Layer {
        String id; BigDecimal available,value;
        final Map<String,BigDecimal> serialValues=new LinkedHashMap<>();
        Layer(String id,BigDecimal available,BigDecimal value) { this.id=id;this.available=available;this.value=value; }
    }
    private static class TransferLeg {
        final Map<String,Object> source;
        final BigDecimal quantity,value;
        final Map<String,BigDecimal> serialValues;
        TransferLeg(Map<String,Object> source,BigDecimal quantity,BigDecimal value,Map<String,BigDecimal> serialValues){this.source=source;this.quantity=quantity;this.value=value;this.serialValues=serialValues;}
        void requireMate(Map<String,Object> incoming,List<String> serials){
            if(quantity.compareTo(d(incoming.get("nums")))!=0 || s(source.get("warehouse")).equals(s(incoming.get("warehouse"))) || !serialValues.keySet().equals(new LinkedHashSet<>(serials)))throw new IllegalStateException("调拨出入库数量、仓库或序列号成本来源不一致");
            for(String field:Arrays.asList("attr","batch","mfd"))if(!s(source.get(field)).equals(s(incoming.get(field))))throw new IllegalStateException("调拨出入库商品属性或批次不一致");
        }
    }
    private void consume(String outgoing,Layer layer,BigDecimal quantity,BigDecimal value){
        layer.available=layer.available.subtract(quantity);layer.value=layer.value.subtract(value);
        db.update("INSERT INTO fifo(id,`out`,`in`,handle) VALUES(?,?,?,?)",id(),outgoing,layer.id,quantity);
        db.update("UPDATE summary SET handle=handle+? WHERE id=?",quantity,layer.id);
    }
    private static String key(Object... values) { return new JSONArray(Arrays.asList(values)).toString(); }
    private List<String> keys(Map<String,Object> row,String rule) {
        String goods=s(row.get("goods")),warehouse=s(row.get("warehouse"));
        String attr=rule.contains("attr") ? s(row.get("attr")):"";
        String batch=rule.contains("batch") ? s(row.get("batch")):"";
        String mfd=rule.contains("batch") ? s(row.get("mfd")):"";
        return Arrays.asList(key(goods),key(goods,warehouse),key(goods,attr,batch,mfd),key(goods,warehouse,attr,batch,mfd));
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
        List<Map<String,Object>> movements=db.queryForList("SELECT s.*,CASE WHEN s.type='buy' THEN (SELECT total FROM buy_info WHERE id=s.info AND pid=s.`class`) END AS purchase_net,CASE WHEN s.type='bre' THEN (SELECT total FROM bre_info WHERE id=s.info AND pid=s.`class`) END AS purchase_return_net,CAST(s.time AS DATE) AS posting_date FROM summary s LEFT JOIN psi_stock_posting_order o ON o.movement_id=s.id WHERE s.goods=? ORDER BY s.time,COALESCE(o.sequence,0),s.id FOR UPDATE",goods);
        clearFifo(goods);
        db.update("UPDATE summary SET handle=0 WHERE goods=?",goods);
        Map<String,Balance> balances=new HashMap<>();
        Map<String,Deque<Layer>> layers=new HashMap<>();
        Map<String,BigDecimal> serialCosts=new HashMap<>();
        Map<String,TransferLeg> transfers=new HashMap<>();
        for(Map<String,Object> row:movements) {
            String type=s(row.get("type")),identifier=s(row.get("id"));
            boolean incoming=n(row.get("direction"))==1;
            boolean closed=!closedDate.isEmpty() && closedDate.compareTo(s(row.get("posting_date")))>=0;
            BigDecimal quantity=d(row.get("nums"));
            if(quantity.signum()<=0) throw new IllegalStateException("历史收发记录数量无效");
            List<String> serials=serials(row.get("serial"));
            if(!serials.isEmpty() && (serials.stream().anyMatch(value->value==null || value.trim().isEmpty()) || new HashSet<>(serials).size()!=serials.size() || quantity.compareTo(BigDecimal.valueOf(serials.size()))!=0))throw new IllegalStateException("历史序列号数量或唯一性与收发记录不一致");
            List<String> scopes=keys(row,rule);
            String selected=scopes.get(branch ? 3:2);
            Balance previous=balances.computeIfAbsent(selected,k->new Balance());
            BigDecimal purchase=prices.getOrDefault(s(row.get("attr")),d(product.get("buy")));
            BigDecimal cost=purchase,exactValue=null;
            boolean fixed=Arrays.asList("buy","bre","entry").contains(type);
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
                    if(!serials.isEmpty()){
                        for(String serial:serials){
                            boolean matched=false;
                            Iterator<Layer> iterator=queue.iterator();
                            while(iterator.hasNext()){
                                Layer layer=iterator.next();BigDecimal original=layer.serialValues.remove(serial);
                                if(original==null)continue;
                                consume(identifier,layer,BigDecimal.ONE,original);total=total.add(original);remaining=remaining.subtract(BigDecimal.ONE);matched=true;
                                if(layer.available.signum()==0)iterator.remove();break;
                            }
                            if(!matched && serialCosts.containsKey(key(goods,serial)))throw new IllegalStateException("序列号缺少当前成本范围的原始成本层，请先核对库存流水");
                        }
                    }else{
                        while(remaining.signum()>0 && !queue.isEmpty()) {
                            Layer layer=queue.peek();
                            if(!layer.serialValues.isEmpty())throw new IllegalStateException("序列号成本层不能由未指定序列号的出库消耗");
                            BigDecimal used=remaining.min(layer.available);
                            BigDecimal usedValue=used.compareTo(layer.available)==0 ? layer.value:layer.value.multiply(used).divide(layer.available,4,RoundingMode.HALF_UP);
                            total=total.add(usedValue);remaining=remaining.subtract(used);consume(identifier,layer,used,usedValue);
                            if(layer.available.signum()==0)queue.remove();
                        }
                    }
                    // Legacy opening balances may precede the available movement history.
                    exactValue=total.add(remaining.multiply(purchase)).setScale(4,RoundingMode.HALF_UP);
                    cost=exactValue.divide(quantity,8,RoundingMode.HALF_UP);
                }
            }
            if(!serials.isEmpty()) {
                if(incoming && Arrays.asList("buy","entry","swapEnter").contains(type)) cost=d(row.get("price"));
                else if(!"fifo".equals(valuation) || incoming) {
                    BigDecimal total=BigDecimal.ZERO;
                    for(String serial:serials) total=total.add(serialCosts.getOrDefault(key(goods,serial),purchase));
                    exactValue=total.setScale(4,RoundingMode.HALF_UP);
                    cost=exactValue.divide(quantity,8,RoundingMode.HALF_UP);
                }
            }
            // SRE value is a source-issued cost allocation, not a new purchase or current-price receipt.
            if(incoming && "sre".equals(type))exactValue=d(row.get("bct"));
            String transferKey=key(row.get("class"),row.get("info"));
            TransferLeg transferred=null;
            if(incoming && "swapEnter".equals(type) && !closed){
                transferred=transfers.remove(transferKey);
                if(transferred==null)throw new IllegalStateException("调拨入库缺少对应的原始调出成本记录");
                transferred.requireMate(row,serials);exactValue=transferred.value;
            }
            BigDecimal value=exactValue==null ? cost.multiply(quantity).setScale(4,RoundingMode.HALF_UP):exactValue;
            cost=value.divide(quantity,4,RoundingMode.HALF_UP);
            if(closed) { cost=d(row.get("uct"));value=d(row.get("bct")); }
            if(!incoming && "swapOut".equals(type) && !closed){
                Map<String,BigDecimal> originalSerialValues=new LinkedHashMap<>();
                for(String serial:serials)originalSerialValues.put(serial,serialCosts.getOrDefault(key(goods,serial),cost));
                if(transfers.put(transferKey,new TransferLeg(row,quantity,value,originalSerialValues))!=null)throw new IllegalStateException("调拨调出成本记录重复");
            }
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
                Map<String,BigDecimal> receiptValues=transferred!=null ? transferred.serialValues:receiptSerialValues(type,serials,value,serialValuesFor(goods,serials,serialCosts));
                for(int index=0;index<serials.size();index++) {
                    serialCosts.put(key(goods,serials.get(index)),receiptValues.get(serials.get(index)));
                }
            }
            if(incoming && "fifo".equals(valuation)){
                Layer layer=new Layer(identifier,quantity,value);
                for(String serial:serials)layer.serialValues.put(serial,serialCosts.get(key(goods,serial)));
                queue.add(layer);
            }
        }
        if(!transfers.isEmpty())throw new IllegalStateException("调拨调出缺少对应的入库成本记录");
    }
    private Map<String,BigDecimal> serialValuesFor(String goods,List<String> numbers,Map<String,BigDecimal> costs){
        Map<String,BigDecimal> result=new LinkedHashMap<>();
        for(String number:numbers)if(costs.containsKey(key(goods,number)))result.put(number,costs.get(key(goods,number)));
        return result;
    }
    /** Transfers and returns carry each original serial value; new receipts allocate their exact net value. */
    public static Map<String,BigDecimal> receiptSerialValues(String type,List<String> numbers,BigDecimal value,Map<String,BigDecimal> previous){
        Map<String,BigDecimal> result=new LinkedHashMap<>();BigDecimal allocated=BigDecimal.ZERO;
        boolean original="swapEnter".equals(type)||"sre".equals(type);
        for(int index=0;index<numbers.size();index++){
            String number=numbers.get(index);BigDecimal part;
            if(original){part=previous.get(number);if(part==null)throw new IllegalStateException("调拨或退货序列号缺少原始成本凭据");}
            else part=index==numbers.size()-1?value.subtract(allocated):value.divide(BigDecimal.valueOf(numbers.size()),4,RoundingMode.HALF_UP);
            result.put(number,part);allocated=allocated.add(part);
        }
        if(original && allocated.compareTo(value)!=0)throw new IllegalStateException("调拨或退货序列号原始成本与入库成本不一致");
        return result;
    }
}
