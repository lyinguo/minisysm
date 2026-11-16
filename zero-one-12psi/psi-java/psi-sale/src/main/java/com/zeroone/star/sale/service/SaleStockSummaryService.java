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
    public void rebuild(String goods) {
        new com.zeroone.star.project.components.stock.StockCostRebuilder(db).rebuild(goods);
    }
}
