package com.zeroone.star.storemanagement.service;

import cn.hutool.json.JSONObject;
import org.springframework.jdbc.core.JdbcTemplate;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Evidence for new warehouse postings; existing approved flags are never backfilled. */
final class WarehousePostingProof {
    private final JdbcTemplate db;
    WarehousePostingProof(JdbcTemplate db) { this.db=db; }
    void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_warehouse_posting (kind VARCHAR(16) NOT NULL,document_id VARCHAR(32) NOT NULL,fingerprint VARCHAR(64) NOT NULL,ledger_hash VARCHAR(64) NOT NULL,created_at DATETIME NOT NULL,PRIMARY KEY(kind,document_id)) ENGINE=InnoDB");
        db.execute("CREATE TABLE IF NOT EXISTS psi_stock_posting_order (sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE) ENGINE=InnoDB");
    }
    private int count(String sql,Object... values) { return db.queryForObject(sql,Integer.class,values); }
    private static String text(Object value) { return value==null?"":value.toString(); }
    private static String hash(String value) {
        try {
            byte[] bytes=MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result=new StringBuilder();for(byte b:bytes)result.append(String.format("%02x",b&255));return result.toString();
        } catch(java.security.NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
    }
    private String fingerprint(Map<String,Object> head,List<Map<String,Object>> rows,List<Map<String,Object>> products) {
        Map<String,Object> original=new LinkedHashMap<>(head);original.remove("examine");
        return hash(original.toString()+rows.toString()+products.toString());
    }
    private String ledgerHash(String id) {
        StringBuilder value=new StringBuilder();
        for(String table:Arrays.asList("room_info","batch_info","serve_info","serial_info"))
            value.append(table).append(db.queryForList("SELECT * FROM `"+table+"` WHERE `class`=? ORDER BY id",id));
        // Replayed valuation/balances and consumed quantities are derived, not immutable source facts.
        value.append(db.queryForList("SELECT id,pid,type,`class`,info,time,goods,attr,warehouse,batch,mfd,serial,direction,price,nums FROM summary WHERE `class`=? ORDER BY id",id));
        value.append(db.queryForList("SELECT sequence,movement_id FROM psi_stock_posting_order WHERE movement_id IN (SELECT id FROM summary WHERE `class`=?) ORDER BY movement_id",id));
        return hash(value.toString());
    }
    boolean hasMarker(String kind,String id) { return count("SELECT COUNT(*) FROM psi_warehouse_posting WHERE kind=? AND document_id=?",kind,id)>0; }
    boolean hasMovements(String id) {
        for(String table:Arrays.asList("summary","room_info","batch_info","serve_info","serial_info"))
            if(count("SELECT COUNT(*) FROM `"+table+"` WHERE `class`=?",id)>0)return true;
        return false;
    }
    void require(String kind,String id,Map<String,Object> head,List<Map<String,Object>> rows,List<Map<String,Object>> products) {
        List<Map<String,Object>> proofs=db.queryForList("SELECT fingerprint,ledger_hash FROM psi_warehouse_posting WHERE kind=? AND document_id=? FOR UPDATE",kind,id);
        if(proofs.size()!=1)throw new IllegalStateException("历史已审核单据缺少入账凭据，请先核对库存和原始流水，不能自动反冲或重复入账");
        if(!fingerprint(head,rows,products).equals(text(proofs.get(0).get("fingerprint"))))
            throw new IllegalStateException("单据或商品库存属性在入账后发生变化，请先核对原始数据");
        if(!ledgerHash(id).equals(text(proofs.get(0).get("ledger_hash"))))
            throw new IllegalStateException("原始库存流水缺失或发生变化，请先核对原始入账凭据");
    }
    void save(String kind,String id,Map<String,Object> head,List<Map<String,Object>> rows,List<Map<String,Object>> products) {
        db.update("INSERT INTO psi_warehouse_posting(kind,document_id,fingerprint,ledger_hash,created_at) VALUES(?,?,?,?,NOW())",kind,id,fingerprint(head,rows,products),ledgerHash(id));
    }
    void remove(String kind,String id) { db.update("DELETE FROM psi_warehouse_posting WHERE kind=? AND document_id=?",kind,id); }
    void requireOpenPeriod(Object date) {
        if(count("SELECT COUNT(*) FROM period WHERE date>=CAST(? AS DATE)",date)>0)
            throw new IllegalStateException("单据日期已结账，不能审核或反审核");
    }
    void requireNoDependents(String id,Map<String,Object> head,List<Map<String,Object>> rows,List<Map<String,Object>> products) {
        if(count("SELECT COUNT(*) FROM fifo WHERE `in` IN (SELECT id FROM summary WHERE `class`=?) AND `out` NOT IN (SELECT id FROM summary WHERE `class`=?)",id,id)>0)
            throw new IllegalStateException("原入库成本层已被后续出库使用，请先处理后续出库单据");
        List<String> settings=db.queryForList("SELECT info FROM sys WHERE name='fun'",String.class);
        if(settings.size()>1)throw new IllegalStateException("成本配置重复，请先核对系统参数");
        JSONObject config=settings.isEmpty()?new JSONObject():new JSONObject(settings.get(0));
        String rule=config.getStr("rule","def");if("aab".equals(rule))rule="attr_batch";
        Map<String,Object> types=new HashMap<>();for(Map<String,Object> product:products)types.put(text(product.get("id")),product.get("type"));
        for(Map<String,Object> row:rows) {
            Object type=types.get(text(row.get("goods")));boolean service=Boolean.TRUE.equals(type) || type instanceof Number && ((Number)type).intValue()==1;
            // Service quantities are cumulative business volume; a sale is not stock consumption.
            if(service)continue;
            StringBuilder query=new StringBuilder("SELECT COUNT(*) FROM summary WHERE goods=? AND `class`<>? AND direction=0 AND time>=?");
            List<Object> args=new ArrayList<>(Arrays.asList(row.get("goods"),id,head.get("time")));
            if(config.getBool("branch",false)){query.append(" AND warehouse=?");args.add(row.get("warehouse"));}
            if(rule.contains("attr")){query.append(" AND COALESCE(attr,'')=?");args.add(text(row.get("attr")));}
            if(rule.contains("batch")){
                query.append(" AND COALESCE(batch,'')=? AND (mfd=? OR (mfd IS NULL AND ? IS NULL))");
                args.add(text(row.get("batch")));args.add(row.get("mfd"));args.add(row.get("mfd"));
            }
            if(count(query.toString(),args.toArray())>0)
                throw new IllegalStateException("同一成本范围已有后续出库，请先处理后续出库单据，再反审核来源单据");
        }
    }
}
