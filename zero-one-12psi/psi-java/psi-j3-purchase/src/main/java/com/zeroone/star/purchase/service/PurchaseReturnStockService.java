package com.zeroone.star.purchase.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.math.*;
import java.util.*;

/** Source receipts determine identity and base units; stock changes share the posting transaction. */
@Service
public class PurchaseReturnStockService {
    private final JdbcTemplate db;
    private final PurchaseStockSummaryService summaries;
    public PurchaseReturnStockService(JdbcTemplate db,PurchaseStockSummaryService summaries){this.db=db;this.summaries=summaries;}
    private String id(){return UUID.randomUUID().toString().replace("-","");}
    private String s(Object v){return Objects.toString(v,"");}
    private BigDecimal d(Object v){return v==null?BigDecimal.ZERO:new BigDecimal(v.toString());}
    private Map<String,Object> one(List<Map<String,Object>> rows,String message){if(rows.size()!=1)throw new IllegalStateException(message);return rows.get(0);}
    private BigDecimal quantity(Map<String,Object> original,Map<String,Object> line,Map<String,Object> movement){
        BigDecimal result=d(movement.get("nums")).multiply(d(line.get("nums"))).divide(d(original.get("nums")),4,RoundingMode.UNNECESSARY);
        if(result.signum()<=0)throw new IllegalArgumentException("退货基础数量无效");return result;
    }
    public void forward(Map<String,Object> head,Map<String,Object> line){
        Object source=head.get("source"),sourceLine=line.get("source");
        Map<String,Object> original=one(db.queryForList("SELECT * FROM buy_info WHERE id=? AND pid=? FOR UPDATE",sourceLine,source),"原采购明细不存在");
        List<Map<String,Object>> receipts=db.queryForList("SELECT * FROM room_info WHERE type='buy' AND `class`=? AND info=? AND direction=1 FOR UPDATE",source,sourceLine);
        List<Map<String,Object>> services=db.queryForList("SELECT * FROM serve_info WHERE type='buy' AND `class`=? AND info=? FOR UPDATE",source,sourceLine);
        if(receipts.isEmpty() && services.size()==1){
            Map<String,Object> receipt=services.get(0);BigDecimal qty=quantity(original,line,receipt);
            if(db.update("UPDATE serve SET nums=nums-? WHERE id=? AND nums>=?",qty,receipt.get("pid"),qty)!=1)throw new IllegalStateException("采购服务累计数量不足");
            db.update("INSERT INTO serve_info(id,pid,type,`class`,info,time,price,nums) VALUES(?,?,'bre',?,?,?,?,?)",id(),receipt.get("pid"),head.get("id"),line.get("id"),head.get("time"),receipt.get("price"),qty);return;
        }
        if(!services.isEmpty())throw new IllegalStateException("原采购库存与服务凭据冲突");
        Map<String,Object> receipt=one(receipts,"原采购入库凭据缺失或重复");BigDecimal qty=quantity(original,line,receipt);
        Map<String,Object> room=one(db.queryForList("SELECT * FROM room WHERE id=? FOR UPDATE",receipt.get("pid")),"原入库记录不存在");
        for(String field:Arrays.asList("goods","warehouse","attr"))if(!s(room.get(field)).equals(s(line.get(field))))throw new IllegalStateException("来源库存与退货商品或仓库不一致");
        if(db.queryForObject("SELECT COUNT(*) FROM warehouse WHERE id=? AND frame IN ('0',?)",Integer.class,line.get("warehouse"),head.get("frame"))!=1)throw new IllegalArgumentException("原仓库组织已变化");
        if(db.update("UPDATE room SET nums=nums-? WHERE id=? AND nums>=?",qty,room.get("id"),qty)!=1)throw new IllegalStateException("原仓库库存不足，不能退货出库");
        List<Map<String,Object>> batches=db.queryForList("SELECT * FROM batch_info WHERE type='buy' AND `class`=? AND info=? AND direction=1 FOR UPDATE",source,sourceLine);
        String batch="";
        if(!batches.isEmpty()){
            Map<String,Object> received=one(batches,"原采购批次凭据重复");batch=s(received.get("pid"));
            Map<String,Object> current=one(db.queryForList("SELECT * FROM batch WHERE id=? FOR UPDATE",batch),"原采购批次不存在");
            if(!s(current.get("room")).equals(s(room.get("id"))) || d(received.get("nums")).compareTo(d(receipt.get("nums")))!=0)throw new IllegalStateException("原批次与入库凭据不一致");
            if(db.update("UPDATE batch SET nums=nums-? WHERE id=? AND nums>=?",qty,batch,qty)!=1)throw new IllegalStateException("原批次库存不足");
            db.update("INSERT INTO batch_info(id,pid,type,`class`,info,direction,nums) VALUES(?,?,'bre',?,?,0,?)",id(),batch,head.get("id"),line.get("id"),qty);
        }else if(!s(line.get("batch")).isEmpty())throw new IllegalStateException("原采购批次凭据缺失");
        List<String> selected=new ArrayList<>();
        for(Object value:new cn.hutool.json.JSONArray(s(line.get("serial")).isEmpty()?"[]":s(line.get("serial"))))selected.add(value instanceof cn.hutool.json.JSONObject?((cn.hutool.json.JSONObject)value).getStr("number"):s(value));
        if(!selected.isEmpty()){
            if(qty.compareTo(BigDecimal.valueOf(selected.size()))!=0)throw new IllegalArgumentException("退货序列号数量与基础数量不一致");
            for(String number:selected){
                Map<String,Object> serial=one(db.queryForList("SELECT s.*,CAST(s.state AS SIGNED) AS serial_state FROM serial s JOIN serial_info i ON i.pid=s.id WHERE i.type='buy' AND i.`class`=? AND i.info=? AND s.number=? FOR UPDATE",source,sourceLine,number),"序列号不属于来源采购入库");
                if(((Number)serial.get("serial_state")).intValue()!=0 || !s(serial.get("room")).equals(s(room.get("id"))) || !s(serial.get("batch")).equals(batch))throw new IllegalArgumentException("来源序列号已出库或位置已变化");
                if(db.update("UPDATE serial SET state=1 WHERE id=? AND state=0",serial.get("id"))!=1)throw new IllegalStateException("序列号状态并发变化");
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,'bre',?,?)",id(),serial.get("id"),head.get("id"),line.get("id"));
            }
        }
        String ledger=id();BigDecimal price=d(line.get("total")).divide(qty,4,RoundingMode.HALF_UP);
        db.update("INSERT INTO room_info(id,pid,type,`class`,info,time,direction,price,nums) VALUES(?,?,'bre',?,?,?,0,?,?)",ledger,room.get("id"),head.get("id"),line.get("id"),head.get("time"),price,qty);
        requireChronology(s(room.get("id")));
        summaries.addPurchaseReturn(head,line,ledger,qty,price);
    }
    private void requireChronology(String room){
        BigDecimal balance=db.queryForObject("SELECT nums FROM room WHERE id=?",BigDecimal.class,room);
        List<Map<String,Object>> flows=db.queryForList("SELECT nums,CAST(direction AS SIGNED) AS flow_direction FROM room_info WHERE pid=? ORDER BY time,id",room);
        for(Map<String,Object> flow:flows)balance=balance.subtract(((Number)flow.get("flow_direction")).intValue()==1?d(flow.get("nums")):d(flow.get("nums")).negate());
        if(balance.signum()<0)throw new IllegalStateException("原库存流水与当前数量不一致");
        // Same-time legacy movements have no stable sequence; validate the net for each time.
        for(Map<String,Object> flow:db.queryForList("SELECT SUM(CASE WHEN direction=1 THEN nums ELSE -nums END) AS delta FROM room_info WHERE pid=? GROUP BY time ORDER BY time",room)){
            balance=balance.add(d(flow.get("delta")));if(balance.signum()<0)throw new IllegalStateException("退货日期会造成历史库存不足，请核对实际出库时间");
        }
    }
    public void reverse(String identifier){
        for(Map<String,Object> row:db.queryForList("SELECT * FROM room_info WHERE type='bre' AND `class`=? ORDER BY id FOR UPDATE",identifier))
            if(db.update("UPDATE room SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1)throw new IllegalStateException("退货原库存记录缺失");
        for(Map<String,Object> row:db.queryForList("SELECT * FROM batch_info WHERE type='bre' AND `class`=? ORDER BY id FOR UPDATE",identifier))
            if(db.update("UPDATE batch SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1)throw new IllegalStateException("退货原批次缺失");
        for(Map<String,Object> row:db.queryForList("SELECT i.*,s.room,s.batch FROM serial_info i JOIN serial s ON s.id=i.pid WHERE i.type='bre' AND i.`class`=? ORDER BY i.id FOR UPDATE",identifier)){
            Map<String,Object> room=one(db.queryForList("SELECT pid FROM room_info WHERE type='bre' AND `class`=? AND info=?",identifier,row.get("info")),"退货序列号库存凭据缺失");
            List<String> batches=db.queryForList("SELECT pid FROM batch_info WHERE type='bre' AND `class`=? AND info=?",String.class,identifier,row.get("info"));
            if(!s(room.get("pid")).equals(s(row.get("room"))) || batches.size()>1 || !(batches.isEmpty()?"":batches.get(0)).equals(s(row.get("batch"))))throw new IllegalStateException("退货序列号位置已变化");
            Map<String,Object> origin=one(db.queryForList("SELECT s.number,s.goods,m.id AS movement FROM serial s JOIN summary m ON m.type='bre' AND m.`class`=? AND m.info=? WHERE s.id=?",identifier,row.get("info"),row.get("pid")),"退货序列号成本凭据缺失");
            boolean seen=false;
            for(Map<String,Object> movement:db.queryForList("SELECT m.id,m.serial FROM summary m LEFT JOIN psi_stock_posting_order o ON o.movement_id=m.id WHERE m.goods=? ORDER BY m.time,COALESCE(o.sequence,0),m.id FOR UPDATE",origin.get("goods"))){
                if(s(movement.get("id")).equals(s(origin.get("movement")))){seen=true;continue;}
                if(seen)for(Object value:new cn.hutool.json.JSONArray(s(movement.get("serial")).isEmpty()?"[]":s(movement.get("serial")))){
                    String number=value instanceof cn.hutool.json.JSONObject?((cn.hutool.json.JSONObject)value).getStr("number"):s(value);
                    if(number.equals(s(origin.get("number"))))throw new IllegalStateException("退货序列号存在后续流转，请先处理后续单据");
                }
            }
            if(db.update("UPDATE serial SET state=0 WHERE id=? AND state=1",row.get("pid"))!=1)throw new IllegalStateException("退货序列号已存在后续流转");
        }
        for(Map<String,Object> row:db.queryForList("SELECT * FROM serve_info WHERE type='bre' AND `class`=? FOR UPDATE",identifier))
            if(db.update("UPDATE serve SET nums=nums+? WHERE id=?",row.get("nums"),row.get("pid"))!=1)throw new IllegalStateException("原服务记录缺失");
        summaries.removePurchaseReturn(identifier);
        for(String table:Arrays.asList("room_info","batch_info","serial_info","serve_info"))db.update("DELETE FROM "+table+" WHERE type='bre' AND `class`=?",identifier);
    }
}
