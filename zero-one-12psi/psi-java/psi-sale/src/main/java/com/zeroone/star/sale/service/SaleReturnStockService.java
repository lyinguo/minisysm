package com.zeroone.star.sale.service;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import com.zeroone.star.project.components.stock.StockCostRebuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.math.*;
import java.util.*;

/** Return movements use the original issue journals, never current unit settings or sale prices.
 * Caller owns the sales write lock, goods locks and one outer posting transaction.
 */
@Service
public class SaleReturnStockService {
    private final JdbcTemplate db;
    private final SaleStockSummaryService summaries;
    public SaleReturnStockService(JdbcTemplate db, SaleStockSummaryService summaries){this.db=db;this.summaries=summaries;}
    private String id(){return UUID.randomUUID().toString().replace("-","");}
    private String s(Object value){return value==null?"":value.toString();}
    private BigDecimal d(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private int n(Object value){return value instanceof Boolean?((Boolean)value?1:0):((Number)value).intValue();}
    private List<String> serials(Object raw){
        JSONArray values;
        try{values=new JSONArray(s(raw).isEmpty()?"[]":s(raw));}catch(Exception error){throw new IllegalArgumentException("退货序列号必须是JSON数组");}
        Set<String> result=new LinkedHashSet<>();
        for(Object value:values){String number=value instanceof JSONObject?((JSONObject)value).getStr("number"):s(value);
            if(number==null || number.trim().isEmpty() || !result.add(number.trim()))throw new IllegalArgumentException("退货序列号为空或重复");}
        return new ArrayList<>(result);
    }
    private Map<String,Object> one(List<Map<String,Object>> rows,String error){if(rows.size()!=1)throw new IllegalStateException(error);return rows.get(0);}
    private BigDecimal baseQuantity(Map<String,Object> original,Map<String,Object> line,Map<String,Object> issue){
        BigDecimal quantity;
        try{quantity=d(issue.get("nums")).multiply(d(line.get("nums"))).divide(d(original.get("nums")),4,RoundingMode.UNNECESSARY);}
        catch(ArithmeticException error){throw new IllegalArgumentException("原出库换算后的退货基础数量不能精确到4位小数");}
        if(quantity.signum()<=0)throw new IllegalArgumentException("退货基础数量必须大于零");return quantity;
    }
    public void forward(Map<String,Object> head,Map<String,Object> line){
        String source=s(head.get("source")),sourceLine=s(line.get("source"));
        Map<String,Object> original=one(db.queryForList("SELECT * FROM sell_info WHERE id=? AND pid=? FOR UPDATE",sourceLine,source),"原销售明细不存在");
        List<Map<String,Object>> physical=db.queryForList("SELECT * FROM room_info WHERE type='sell' AND `class`=? AND info=? AND direction=0 FOR UPDATE",source,sourceLine);
        List<Map<String,Object>> services=db.queryForList("SELECT * FROM serve_info WHERE type='sell' AND `class`=? AND info=? FOR UPDATE",source,sourceLine);
        if(physical.isEmpty() && services.size()==1){
            if(!serials(line.get("serial")).isEmpty())throw new IllegalArgumentException("服务退货不能选择库存序列号");
            Map<String,Object> issue=services.get(0);BigDecimal quantity=baseQuantity(original,line,issue);
            if(db.update("UPDATE serve SET nums=nums-? WHERE id=? AND nums>=?",quantity,issue.get("pid"),quantity)!=1)throw new IllegalStateException("服务累计数量不足或原累计记录不存在");
            db.update("INSERT INTO serve_info(id,pid,type,`class`,info,time,price,nums) VALUES(?,?,'sre',?,?,?,?,?)",id(),issue.get("pid"),head.get("id"),line.get("id"),head.get("time"),issue.get("price"),quantity);
            return;
        }
        if(physical.size()!=1 || !services.isEmpty())throw new IllegalStateException("原销售库存或服务凭据缺失、重复，不能推测退货数量");
        Map<String,Object> issue=physical.get(0);BigDecimal quantity=baseQuantity(original,line,issue);
        Map<String,Object> room=one(db.queryForList("SELECT * FROM room WHERE id=? FOR UPDATE",issue.get("pid")),"原出库库存记录不存在");
        for(String field:Arrays.asList("goods","warehouse","attr"))if(!s(room.get(field)).equals(s(line.get(field))))throw new IllegalStateException("原库存与退货商品、仓库或属性不一致");
        Map<String,Object> summary=one(db.queryForList("SELECT * FROM summary WHERE type='sell' AND `class`=? AND info=? AND pid=? AND direction=0 FOR UPDATE",source,sourceLine,issue.get("id")),"原销售成本凭据缺失或重复");
        if(d(summary.get("nums")).compareTo(d(issue.get("nums")))!=0 || d(summary.get("bct")).signum()<0)throw new IllegalStateException("原出库成本与数量凭据不一致");
        List<Map<String,Object>> batches=db.queryForList("SELECT * FROM batch_info WHERE type='sell' AND `class`=? AND info=? AND direction=0 FOR UPDATE",source,sourceLine);
        String batch="";
        if(!batches.isEmpty()){
            Map<String,Object> issuedBatch=one(batches,"原批次出库凭据重复");
            if(d(issuedBatch.get("nums")).compareTo(d(issue.get("nums")))!=0)throw new IllegalStateException("原批次数量与库存出库不一致");
            Map<String,Object> found=one(db.queryForList("SELECT * FROM batch WHERE id=? FOR UPDATE",issuedBatch.get("pid")),"原批次记录不存在");
            if(!s(found.get("room")).equals(s(room.get("id"))))throw new IllegalStateException("原批次库存归属不一致");
            batch=s(found.get("id"));db.update("UPDATE batch SET nums=nums+? WHERE id=?",quantity,batch);
            db.update("INSERT INTO batch_info(id,pid,type,`class`,info,direction,nums) VALUES(?,?,'sre',?,?,1,?)",id(),batch,head.get("id"),line.get("id"),quantity);
        }else if(!s(line.get("batch")).isEmpty())throw new IllegalStateException("退货批次缺少原出库凭据");
        List<Map<String,Object>> issuedSerials=db.queryForList("SELECT s.* FROM serial_info i JOIN serial s ON s.id=i.pid WHERE i.type='sell' AND i.`class`=? AND i.info=? ORDER BY s.id FOR UPDATE",source,sourceLine);
        List<String> selected=serials(line.get("serial"));BigDecimal value;
        if(!issuedSerials.isEmpty()){
            if(quantity.compareTo(BigDecimal.valueOf(selected.size()))!=0)throw new IllegalArgumentException("所选原销售序列号数量与退货基础数量不一致");
            Map<String,Map<String,Object>> allowed=new HashMap<>();for(Map<String,Object> row:issuedSerials)allowed.put(s(row.get("number")),row);
            if(allowed.size()!=issuedSerials.size())throw new IllegalStateException("原序列号凭据重复");
            if(!allowed.keySet().equals(new HashSet<>(serials(original.get("serial")))))throw new IllegalStateException("原销售序列号与出库凭据不一致");
            Map<String,BigDecimal> costs=originalSerialCosts(summary);
            value=BigDecimal.ZERO;
            for(String number:selected){
                Map<String,Object> row=allowed.get(number);
                if(row==null || n(row.get("state"))!=1 || !s(room.get("id")).equals(s(row.get("room"))) || !batch.equals(s(row.get("batch"))))throw new IllegalArgumentException("序列号未由来源单销售、已退货或位置已改变");
                if(db.queryForObject("SELECT COUNT(*) FROM serial_info j JOIN sre_info i ON i.id=j.info JOIN sre h ON h.id=i.pid WHERE j.type='sre' AND j.pid=? AND i.source=? AND h.examine=1",Integer.class,row.get("id"),sourceLine)>0)throw new IllegalArgumentException("该来源销售序列号已退货，不能因后续再次销售而重复退回原单");
                if(!costs.containsKey(number))throw new IllegalStateException("原序列号成本凭据缺失，不能用当前进价推测退款入库成本");
                value=value.add(costs.get(number));
                if(db.update("UPDATE serial SET state=0 WHERE id=? AND state=1",row.get("id"))!=1)throw new IllegalStateException("序列号状态并发变化");
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,'sre',?,?)",id(),row.get("id"),head.get("id"),line.get("id"));
            }
        }else{
            if(!serials(original.get("serial")).isEmpty())throw new IllegalStateException("原销售序列号出库凭据缺失");
            if(!selected.isEmpty())throw new IllegalArgumentException("来源出库没有所选序列号");
            Map<String,Object> used=db.queryForMap("SELECT COALESCE(SUM(s.nums),0) AS nums,COALESCE(SUM(s.bct),0) AS value FROM summary s JOIN sre_info i ON i.id=s.info JOIN sre h ON h.id=i.pid WHERE s.type='sre' AND h.examine=1 AND i.source=?",sourceLine);
            BigDecimal remaining=d(issue.get("nums")).subtract(d(used.get("nums"))),remainingValue=d(summary.get("bct")).subtract(d(used.get("value")));
            if(quantity.compareTo(remaining)>0 || remainingValue.signum()<0)throw new IllegalStateException("原销售成本或基础数量已被其他退货占用");
            value=quantity.compareTo(remaining)==0?remainingValue:d(summary.get("bct")).multiply(quantity).divide(d(issue.get("nums")),4,RoundingMode.HALF_UP);
            if(value.compareTo(remainingValue)>0)throw new IllegalStateException("本次退货成本超过来源剩余成本");
        }
        db.update("UPDATE room SET nums=nums+? WHERE id=?",quantity,room.get("id"));
        BigDecimal price=value.divide(quantity,4,RoundingMode.HALF_UP);String ledger=id();
        db.update("INSERT INTO room_info(id,pid,type,`class`,info,time,direction,price,nums) VALUES(?,?,'sre',?,?,?,1,?,?)",ledger,room.get("id"),head.get("id"),line.get("id"),head.get("time"),price,quantity);
        summaries.addReturn(head,line,ledger,quantity,value);
    }
    /** Match the serial allocation used by cost replay, stopping at this exact issue sequence. */
    private Map<String,BigDecimal> originalSerialCosts(Map<String,Object> issue){
        Map<String,BigDecimal> costs=new HashMap<>();
        for(Map<String,Object> row:db.queryForList("SELECT s.* FROM summary s LEFT JOIN psi_stock_posting_order o ON o.movement_id=s.id WHERE s.goods=? ORDER BY s.time,COALESCE(o.sequence,0),s.id FOR UPDATE",issue.get("goods"))){
            if(s(row.get("id")).equals(s(issue.get("id"))))return costs;
            List<String> numbers=serials(row.get("serial"));
            if(n(row.get("direction"))!=1 || numbers.isEmpty())continue;
            costs.putAll(StockCostRebuilder.receiptSerialValues(s(row.get("type")),numbers,d(row.get("bct")),costs));
        }
        throw new IllegalStateException("原序列号销售成本凭据不在库存记录中");
    }
    public void reverse(String identifier){
        List<Map<String,Object>> movements=db.queryForList("SELECT * FROM room_info WHERE type='sre' AND `class`=? ORDER BY id FOR UPDATE",identifier);
        for(Map<String,Object> row:movements){
            if(db.update("UPDATE room SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1)throw new IllegalStateException("退回库存已被使用或原库存记录缺失");
        }
        for(Map<String,Object> row:db.queryForList("SELECT * FROM batch_info WHERE type='sre' AND `class`=? ORDER BY id FOR UPDATE",identifier))
            if(db.update("UPDATE batch SET nums=nums-? WHERE id=? AND nums>=?",row.get("nums"),row.get("pid"),row.get("nums"))!=1)throw new IllegalStateException("退回批次库存不足，不能反审核");
        for(Map<String,Object> row:db.queryForList("SELECT i.*,s.number,s.goods,s.room AS current_room,s.batch AS current_batch FROM serial_info i JOIN serial s ON s.id=i.pid WHERE i.type='sre' AND i.`class`=? ORDER BY i.id FOR UPDATE",identifier)){
            Map<String,Object> returnedRoom=one(db.queryForList("SELECT pid FROM room_info WHERE type='sre' AND `class`=? AND info=?",identifier,row.get("info")),"退货序列号原库存流水缺失");
            List<String> returnedBatches=db.queryForList("SELECT pid FROM batch_info WHERE type='sre' AND `class`=? AND info=?",String.class,identifier,row.get("info"));
            if(!s(returnedRoom.get("pid")).equals(s(row.get("current_room"))) || returnedBatches.size()>1 || !(returnedBatches.isEmpty()?"":returnedBatches.get(0)).equals(s(row.get("current_batch"))))throw new IllegalStateException("退货序列号库存或批次位置已被改变");
            String returned= s(one(db.queryForList("SELECT id FROM summary WHERE type='sre' AND `class`=? AND info=?",identifier,row.get("info")),"退货序列号库存凭据缺失").get("id"));
            boolean seen=false;
            for(Map<String,Object> movement:db.queryForList("SELECT s.* FROM summary s LEFT JOIN psi_stock_posting_order o ON o.movement_id=s.id WHERE s.goods=? ORDER BY s.time,COALESCE(o.sequence,0),s.id FOR UPDATE",row.get("goods"))){
                if(s(movement.get("id")).equals(returned)){seen=true;continue;}
                if(seen && serials(movement.get("serial")).contains(s(row.get("number"))))throw new IllegalStateException("退回序列号存在后续库存流转，请先撤销后续单据");
            }
            if(db.update("UPDATE serial SET state=1 WHERE id=? AND state=0",row.get("pid"))!=1)throw new IllegalStateException("退回序列号已被后续业务使用");
        }
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serve_info WHERE type='sre' AND `class`=? ORDER BY id FOR UPDATE",identifier))
            if(db.update("UPDATE serve SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1)throw new IllegalStateException("原服务累计记录不存在");
        summaries.removeReturn(identifier);
        for(String table:Arrays.asList("room_info","batch_info","serial_info","serve_info"))db.update("DELETE FROM "+table+" WHERE type='sre' AND `class`=?",identifier);
    }
}
