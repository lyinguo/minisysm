package com.zeroone.star.storemanagement.service;

import cn.hutool.core.util.IdUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import lombok.Data;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.DigestUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.*;

/** 报表按整张单据编辑和审核，不使用明细行 ID 代替单据 ID。 */
@Service
public class WarehouseReportDocumentService {
    private final JdbcTemplate db;
    private final WarehousePostingProof proofs;
    private final StockDocumentWriteLock writes;
    private final com.zeroone.star.project.components.stock.StockCostRebuilder costs;
    public WarehouseReportDocumentService(JdbcTemplate db) {
        this.db = db;this.proofs=new WarehousePostingProof(db);this.writes=new StockDocumentWriteLock(db);
        this.costs=new com.zeroone.star.project.components.stock.StockCostRebuilder(db);
    }
    @javax.annotation.PostConstruct public void initializePostingProofs() { proofs.initialize(); }

    @Data
    public static class Edit {
        private String version;
        private Map<String, Object> header;
        private List<Map<String, Object>> items;
    }

    private String table(String kind) {
        if (!Arrays.asList("entry", "extry", "swap").contains(kind)) throw new IllegalArgumentException("单据类型无效");
        return kind;
    }

    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public Map<String, Object> list(String kind, int page, int size, String number, String frame) {
        String t = table(kind);
        int limit = Math.max(1, Math.min(size, 200));
        long offset = (long) (Math.max(1, page) - 1) * limit;
        String filter = "%" + (number == null ? "" : number.trim()) + "%";
        List<Map<String, Object>> rows = db.queryForList("SELECT d.*, f.name AS frameName FROM `" + t + "` d LEFT JOIN frame f ON f.id=d.frame WHERE d.number LIKE ? AND (? IS NULL OR d.frame=?) ORDER BY d.time DESC,d.id LIMIT ? OFFSET ?", filter, frame, frame, limit, offset);
        for(Map<String,Object> row:rows)if(num(row.get("examine"))==1)attachCosts(t,row,items(t,str(row.get("id"))));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("rows", rows);
        result.put("total", db.queryForObject("SELECT COUNT(*) FROM `" + t + "` WHERE number LIKE ? AND (? IS NULL OR frame=?)", Long.class, filter, frame, frame));
        return result;
    }

    private Map<String, Object> header(String t, String id, boolean lock) {
        List<Map<String, Object>> rows = db.queryForList("SELECT * FROM `" + t + "` WHERE id=?" + (lock ? " FOR UPDATE" : ""), id);
        if (rows.size() != 1) throw new IllegalArgumentException("单据不存在，请刷新列表");
        return rows.get(0);
    }

    private List<Map<String, Object>> items(String t, String id) {
        return db.queryForList("SELECT * FROM `" + t + "_info` WHERE pid=? ORDER BY id", id);
    }

    private String version(Map<String, Object> head, List<Map<String, Object>> rows) {
        return DigestUtils.md5DigestAsHex((head.toString() + rows.toString()).getBytes(StandardCharsets.UTF_8));
    }

    public String lockedVersion(String kind, String id) {
        String t = table(kind);
        return version(header(t, id, true), db.queryForList("SELECT * FROM `" + t + "_info` WHERE pid=? ORDER BY id FOR UPDATE", id));
    }

    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public Map<String, Object> detail(String kind, String id) {
        String t = table(kind);
        Map<String, Object> head = header(t, id, false);
        List<Map<String, Object>> rows = items(t, id);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("version", version(head, rows));
        attachCosts(t,head,rows);
        result.put("header", head);
        result.put("items", rows);
        result.put("goods", db.queryForList("SELECT g.id,g.name,g.number,g.spec,g.serial,g.batch,g.type FROM goods g WHERE g.id IN (SELECT goods FROM `" + t + "_info` WHERE pid=?)", id));
        return result;
    }

    /** Original estimates remain immutable; posted cost is read from replayed journals. */
    private void attachCosts(String kind,Map<String,Object> head,List<Map<String,Object>> rows){
        if(num(head.get("examine"))!=1)return;
        String id=str(head.get("id"));Map<String,Map<String,Object>> costs=new HashMap<>();Set<String> ambiguous=new HashSet<>();
        List<Map<String,Object>> journals=db.queryForList("SELECT info,SUM(bct) AS actual_cost,SUM(nums) AS actual_qty FROM summary WHERE `class`=? AND type=? GROUP BY info",id,"swap".equals(kind)?"swapOut":kind);
        journals.addAll(db.queryForList("SELECT info,SUM(price*nums) AS actual_cost,SUM(nums) AS actual_qty FROM serve_info WHERE `class`=? AND type=? GROUP BY info",id,kind));
        for(Map<String,Object> journal:journals)if(costs.put(str(journal.get("info")),journal)!=null)ambiguous.add(str(journal.get("info")));
        BigDecimal total=BigDecimal.ZERO;boolean complete=!rows.isEmpty();
        for(Map<String,Object> row:rows){
            Map<String,Object> journal=costs.get(str(row.get("id")));
            if(decimal(row.get("nums")).signum()<=0 || journal==null || ambiguous.contains(str(row.get("id"))) || decimal(journal.get("actual_qty")).compareTo(decimal(row.get("nums")))!=0){complete=false;continue;}
            BigDecimal value=decimal(journal.get("actual_cost"));row.put("actualCost",value);row.put("actualPrice",value.divide(decimal(row.get("nums")),4,RoundingMode.HALF_UP));total=total.add(value);
        }
        head.put("costStatus",complete?"posted":"missing");if(complete)head.put("actualCost",total);
    }

    private void assertVersion(String expected, Map<String, Object> head, List<Map<String, Object>> rows) {
        if (expected == null || !expected.equals(version(head, rows))) throw new IllegalStateException("单据已被其他操作修改，请重新打开详情");
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> save(String kind, String id, Edit edit, String actor) {
        String t = table(kind);
        if("extry".equals(t))writes.lock(t);
        Map<String, Object> head = header(t, id, true);
        if("extry".equals(t) && (db.queryForObject("SELECT COUNT(*) FROM extry WHERE id=? AND cse IN (1,2)",Integer.class,id)>0 || proofs.hasMarker(t,id) || proofs.hasMovements(id)
                || db.queryForObject("SELECT COUNT(*) FROM cost WHERE type='extry' AND `class`=? AND (COALESCE(settle,0)<>0 OR COALESCE(state,0)<>0)",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='extry' AND `class`=?)",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM invoice WHERE type='extry' AND `class`=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM bill_info WHERE mold='extry' AND source=?",Integer.class,id)>0))throw new IllegalStateException("单据存在入账或结算关联，不能直接修改草稿");
        if(Arrays.asList("entry","extry").contains(t) && num(head.get("check"))!=0)throw new IllegalStateException("已核对单据不能修改，请先反核对");
        proofs.requireOpenPeriod(head.get("time"));
        if (num(head.get("examine")) != 0) throw new IllegalStateException("已审核单据不能修改，请先反审核");
        List<Map<String, Object>> oldItems = items(t, id);
        assertVersion(edit.getVersion(), head, oldItems);
        if (edit.getHeader() == null || edit.getItems() == null || oldItems.isEmpty() || edit.getItems().size() != oldItems.size()) throw new IllegalArgumentException("单据明细不能为空或缺失");
        Map<String, Map<String, Object>> originals = new HashMap<>();
        oldItems.forEach(row -> originals.put(str(row.get("id")), row));
        BigDecimal total = BigDecimal.ZERO;
        for (Map<String, Object> item : edit.getItems()) {
            String itemId = str(item.get("id"));
            Map<String, Object> original = originals.remove(itemId);
            if (original == null) throw new IllegalArgumentException("单据明细重复或不属于当前单据");
            BigDecimal qty = positive(item.get("nums"));
            BigDecimal price = decimal(item.get("price"));
            if (price.signum() < 0) throw new IllegalArgumentException("成本不能为负数");
            String warehouse = requireWarehouse(item.get("warehouse"),str(head.get("frame")));
            BigDecimal amount = price.multiply(qty).setScale(4, RoundingMode.HALF_UP);
            if ("swap".equals(t)) {
                String target = requireWarehouse(item.get("storehouse"),str(head.get("frame")));
                if (warehouse.equals(target)) throw new IllegalArgumentException("调入和调出仓库不能相同");
                db.update("UPDATE swap_info SET price=?,nums=?,total=?,warehouse=?,storehouse=?,data=?,serial=? WHERE id=? AND pid=?", price, qty, amount, warehouse, target, item.get("data"), item.get("serial"), itemId, id);
            } else {
                db.update("UPDATE `" + t + "_info` SET price=?,nums=?,total=?,warehouse=?,data=?,serial=? WHERE id=? AND pid=?", price, qty, amount, warehouse, item.get("data"), item.get("serial"), itemId, id);
            }
            total = total.add(amount);
        }
        String number = str(edit.getHeader().get("number")).trim();
        if (number.isEmpty()) throw new IllegalArgumentException("单据编号不能为空");
        if (db.queryForObject("SELECT COUNT(*) FROM `" + t + "` WHERE number=? AND id<>?", Integer.class, number, id) > 0) throw new IllegalArgumentException("单据编号已存在");
        Timestamp date = documentTime(edit.getHeader().get("time"));
        db.update("UPDATE `" + t + "` SET number=?,time=?,data=?,total=? WHERE id=?", number, date, edit.getHeader().get("data"), total, id);
        log(t, id, actor, "修改单据");
        return detail(t, id);
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> audit(String kind, String id, int target, String expectedVersion, String actor) {
        String t = table(kind);
        if (target != 0 && target != 1) throw new IllegalArgumentException("审核状态无效");
        Map<String, Object> head = header(t, id, true);
        List<Map<String,Object>> rows=db.queryForList("SELECT * FROM `"+t+"_info` WHERE pid=? ORDER BY id FOR UPDATE",id);
        List<Map<String,Object>> products=db.queryForList("SELECT id,type,batch,serial FROM goods WHERE id IN (SELECT goods FROM `"+t+"_info` WHERE pid=?) ORDER BY id FOR UPDATE",id);
        int state=num(head.get("examine"));
        if(state==1)proofs.require(t,id,head,rows,products);
        else if(state!=0 || proofs.hasMarker(t,id) || proofs.hasMovements(id))
            throw new IllegalStateException("单据状态与原始入账凭据不一致，请先核对库存流水");
        if(state==target)return detail(t,id);
        assertVersion(expectedVersion,head,rows);
        proofs.requireOpenPeriod(head.get("time"));
        if(rows.isEmpty())throw new IllegalArgumentException("单据没有商品明细");
        if(target==0)proofs.requireNoDependents(t,id,head,rows,products);
        Map<String, Map<String, Object>> goods = new HashMap<>();
        products.forEach(g -> goods.put(str(g.get("id")), g));
        for (Map<String, Object> item : rows) {
            Map<String, Object> product = goods.get(str(item.get("goods")));
            if (product == null) throw new IllegalArgumentException("商品不存在");
            positive(item.get("nums"));
            int sign = target == 1 ? 1 : -1;
            if (num(product.get("type")) == 1) {
                if ("swap".equals(t)) throw new IllegalArgumentException("服务商品不能进行仓库调拨");
                serviceStock(t, id, head, item, sign * ("entry".equals(t) ? 1 : -1), target);
            } else if ("swap".equals(t)) {
                if (Objects.equals(item.get("warehouse"), item.get("storehouse"))) throw new IllegalArgumentException("调入和调出仓库不能相同");
                stock(t, id, head, item, item.get("warehouse"), -sign, target, product);
                stock(t, id, head, item, item.get("storehouse"), sign, target, product);
            } else {
                stock(t, id, head, item, item.get("warehouse"), sign * ("entry".equals(t) ? 1 : -1), target, product);
            }
            if (num(product.get("serial")) == 1) serials(t, id, item, target, product);
        }
        if (target == 0) {
            db.update("DELETE FROM fifo WHERE `in` IN (SELECT id FROM summary WHERE `class`=?) OR `out` IN (SELECT id FROM summary WHERE `class`=?)",id,id);
            db.update("DELETE FROM psi_stock_posting_order WHERE movement_id IN (SELECT id FROM summary WHERE `class`=? AND type IN (?,?,?))",id,t,"swapOut","swapEnter");
            for (String ledger : Arrays.asList("summary", "room_info", "batch_info", "serve_info", "serial_info")) {
                db.update("DELETE FROM `" + ledger + "` WHERE `class`=? AND type IN (?,?,?)", id, t, "swapOut", "swapEnter");
            }
        }
        for(Map<String,Object> product:products)if(num(product.get("type"))!=1)costs.rebuild(str(product.get("id")));
        if(target==1)proofs.save(t,id,head,rows,products);else proofs.remove(t,id);
        db.update("UPDATE `" + t + "` SET examine=? WHERE id=?", target, id);
        log(t, id, actor, target == 1 ? "审核单据" : "反审核单据");
        return detail(t, id);
    }

    private void stock(String t, String id, Map<String, Object> head, Map<String, Object> item, Object warehouseValue, int sign, int target, Map<String, Object> product) {
        String warehouse = requireWarehouse(warehouseValue,str(head.get("frame")));
        String goods = str(item.get("goods"));
        String attr = str(item.get("attr"));
        BigDecimal qty = positive(item.get("nums"));
        BigDecimal delta = sign > 0 ? qty : qty.negate();
        List<Map<String, Object>> rooms = db.queryForList("SELECT * FROM room WHERE warehouse=? AND goods=? AND COALESCE(attr,'')=? FOR UPDATE", warehouse, goods, attr);
        if (rooms.size() > 1) throw new IllegalStateException("库存存在重复记录，请先整理库存数据");
        String roomId;
        if (rooms.isEmpty()) {
            if (sign < 0) throw new IllegalStateException("仓库库存不足");
            roomId = uid();
            db.update("INSERT INTO room(id,warehouse,goods,attr,nums) VALUES(?,?,?,?,?)", roomId, warehouse, goods, attr, qty);
        } else {
            roomId = str(rooms.get(0).get("id"));
            if (db.update("UPDATE room SET nums=nums+? WHERE id=? AND nums+?>=0", delta, roomId, delta) != 1) throw new IllegalStateException("仓库库存不足");
        }
        String type = "swap".equals(t) ? (sign > 0 ? "swapEnter" : "swapOut") : t;
        if (num(product.get("batch")) == 1) batch(id, item, roomId, warehouse, delta, target, type, sign);
        if (target == 1) {
            String ledgerId = uid();
            db.update("INSERT INTO room_info(id,pid,type,`class`,info,time,direction,price,nums) VALUES(?,?,?,?,?,?,?,?,?)", ledgerId, roomId, type, id, item.get("id"), head.get("time"), sign > 0 ? 1 : 0, item.get("price"), qty);
            String exists="[0,0,0,0]",balances="[0,0,0,0]";
            String summaryId=uid();
            db.update("INSERT INTO summary(id,pid,type,`class`,info,time,goods,attr,warehouse,batch,mfd,serial,direction,price,nums,uct,bct,exist,balance,handle) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", summaryId, ledgerId, type, id, item.get("id"), head.get("time"), goods, item.get("attr"), warehouse, item.get("batch"), item.get("mfd"), item.get("serial"), sign > 0 ? 1 : 0, item.get("price"), qty, item.get("price"), decimal(item.get("price")).multiply(qty), exists, balances, BigDecimal.ZERO);
            db.update("INSERT INTO psi_stock_posting_order(movement_id) VALUES(?)",summaryId);
        }
    }

    private void batch(String id, Map<String, Object> item, String roomId, String warehouse, BigDecimal delta, int target, String type, int sign) {
        String number = str(item.get("batch"));
        if (number.isEmpty() || item.get("mfd") == null) throw new IllegalArgumentException("批次商品必须有批次号和生产日期");
        List<Map<String, Object>> batches = db.queryForList("SELECT * FROM batch WHERE room=? AND number=? FOR UPDATE", roomId, number);
        if (batches.size() > 1) throw new IllegalStateException("批次库存记录重复");
        String batchId;
        if (batches.isEmpty()) {
            if (delta.signum() < 0) throw new IllegalStateException("批次库存不足");
            batchId = uid();
            db.update("INSERT INTO batch(id,room,warehouse,goods,number,time,nums) VALUES(?,?,?,?,?,?,?)", batchId, roomId, warehouse, item.get("goods"), number, item.get("mfd"), delta);
        } else {
            batchId = str(batches.get(0).get("id"));
            if (!str(batches.get(0).get("time")).equals(str(item.get("mfd")))) throw new IllegalArgumentException("批次生产日期不匹配");
            if (db.update("UPDATE batch SET nums=nums+? WHERE id=? AND nums+?>=0", delta, batchId, delta) != 1) throw new IllegalStateException("批次库存不足");
        }
        if (target == 1) db.update("INSERT INTO batch_info(id,pid,type,`class`,info,direction,nums) VALUES(?,?,?,?,?,?,?)", uid(), batchId, type, id, item.get("id"), sign > 0 ? 1 : 0, delta.abs());
    }

    private void serviceStock(String t, String id, Map<String, Object> head, Map<String, Object> item, int sign, int target) {
        String goods = str(item.get("goods"));
        String attr = str(item.get("attr"));
        BigDecimal qty = positive(item.get("nums"));
        BigDecimal delta = sign > 0 ? qty : qty.negate();
        List<Map<String, Object>> services = db.queryForList("SELECT * FROM serve WHERE goods=? AND COALESCE(attr,'')=? FOR UPDATE", goods, attr);
        if (services.size() > 1) throw new IllegalStateException("服务库存记录重复");
        String serveId;
        if (services.isEmpty()) {
            if (sign < 0) throw new IllegalStateException("服务数量不足");
            serveId = uid();
            db.update("INSERT INTO serve(id,goods,attr,nums) VALUES(?,?,?,?)", serveId, goods, attr, delta);
        } else {
            serveId = str(services.get(0).get("id"));
            if (db.update("UPDATE serve SET nums=nums+? WHERE id=? AND nums+?>=0", delta, serveId, delta) != 1) throw new IllegalStateException("服务数量不足");
        }
        if (target == 1) db.update("INSERT INTO serve_info(id,pid,type,`class`,info,time,price,nums) VALUES(?,?,?,?,?,?,?,?)", uid(), serveId, t, id, item.get("id"), head.get("time"), item.get("price"), qty);
    }

    private void serials(String t, String id, Map<String, Object> item, int target, Map<String, Object> product) {
        if (num(product.get("type")) == 1) throw new IllegalArgumentException("服务商品不能使用库存序列号");
        JSONArray values;
        try { values = new JSONArray(str(item.get("serial"))); }
        catch (Exception error) { throw new IllegalArgumentException("序列号必须是JSON数组，例如[\"SN001\"]"); }
        Set<String> numbers = new LinkedHashSet<>();
        for (Object value : values) {
            String number = value instanceof JSONObject ? ((JSONObject) value).getStr("number") : str(value);
            if (number == null || number.trim().isEmpty() || !numbers.add(number.trim())) throw new IllegalArgumentException("序列号为空或重复");
        }
        if (positive(item.get("nums")).compareTo(BigDecimal.valueOf(numbers.size())) != 0) throw new IllegalArgumentException("序列号数量必须与商品数量一致");
        String goods = str(item.get("goods"));
        String originalWarehouse = str(item.get("warehouse"));
        String destination = "swap".equals(t) ? str(item.get("storehouse")) : originalWarehouse;
        for (String number : numbers) {
            List<Map<String, Object>> found = db.queryForList("SELECT * FROM serial WHERE goods=? AND number=? FOR UPDATE", goods, number);
            if (target == 1 && "entry".equals(t)) {
                if (!found.isEmpty()) throw new IllegalArgumentException("序列号已存在：" + number);
                String room = roomId(goods, originalWarehouse, item.get("attr"));
                String batch = num(product.get("batch")) == 1 ? db.queryForObject("SELECT id FROM batch WHERE room=? AND number=?", String.class, room, item.get("batch")) : null;
                String serialId = uid();
                db.update("INSERT INTO serial(id,room,warehouse,batch,goods,number,state) VALUES(?,?,?,?,?,?,0)", serialId, room, originalWarehouse, batch, goods, number);
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,?,?,?)", uid(), serialId, t, id, item.get("id"));
                continue;
            }
            if (found.size() != 1) throw new IllegalArgumentException("序列号不存在或重复：" + number);
            Map<String, Object> serial = found.get(0);
            String serialId = str(serial.get("id"));
            String expectedWarehouse = target == 0 && "swap".equals(t) ? destination : originalWarehouse;
            int expectedState = target == 0 && "extry".equals(t) ? 1 : 0;
            if (!expectedWarehouse.equals(str(serial.get("warehouse"))) || num(serial.get("state")) != expectedState || !roomId(goods, expectedWarehouse, item.get("attr")).equals(str(serial.get("room")))) throw new IllegalStateException("序列号位置或状态已变化：" + number);
            if (target == 0) {
                if (db.queryForObject("SELECT COUNT(*) FROM serial_info WHERE pid=? AND `class`=?", Integer.class, serialId, id) == 0) throw new IllegalStateException("缺少原单据序列号记录，无法反审核");
                if ("entry".equals(t)) {
                    if (db.queryForObject("SELECT COUNT(*) FROM serial_info WHERE pid=? AND `class`<>?", Integer.class, serialId, id) > 0) throw new IllegalStateException("序列号已被后续单据使用，不能反审核");
                    db.update("DELETE FROM serial WHERE id=?", serialId);
                } else if ("extry".equals(t)) db.update("UPDATE serial SET state=0 WHERE id=?", serialId);
                else moveSerial(serialId, goods, originalWarehouse, item, product);
            } else {
                if ("extry".equals(t)) db.update("UPDATE serial SET state=1 WHERE id=?", serialId);
                else moveSerial(serialId, goods, destination, item, product);
                db.update("INSERT INTO serial_info(id,pid,type,`class`,info) VALUES(?,?,?,?,?)", uid(), serialId, t, id, item.get("id"));
            }
        }
    }
    private String roomId(String goods, String warehouse, Object attr) {
        return db.queryForObject("SELECT id FROM room WHERE goods=? AND warehouse=? AND COALESCE(attr,'')=?", String.class, goods, warehouse, str(attr));
    }
    private void moveSerial(String id, String goods, String warehouse, Map<String, Object> item, Map<String, Object> product) {
        String room = roomId(goods, warehouse, item.get("attr"));
        String batch = num(product.get("batch")) == 1 ? db.queryForObject("SELECT id FROM batch WHERE room=? AND number=?", String.class, room, item.get("batch")) : null;
        db.update("UPDATE serial SET room=?,warehouse=?,batch=?,state=0 WHERE id=?", room, warehouse, batch, id);
    }

    private String requireWarehouse(Object id,String frame) {
        return WarehouseScope.require(db,frame,id);
    }
    private void log(String t, String id, String actor, String action) {
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)", uid(), Timestamp.valueOf(LocalDateTime.now()), actor, action + "[" + id + "]");
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,?,?,?,?,?)", uid(), t, id, Timestamp.valueOf(LocalDateTime.now()), actor, action);
    }
    private static String uid() { return IdUtil.fastSimpleUUID(); }
    private static String str(Object value) { return value == null ? "" : value.toString(); }
    private static Timestamp documentTime(Object value) {
        if (value instanceof Number) return new Timestamp(((Number) value).longValue());
        if (value instanceof Timestamp) return (Timestamp) value;
        String text = str(value).trim().replace('T', ' ');
        try {
            if (text.length() == 10) text += " 00:00:00";
            return Timestamp.valueOf(text);
        } catch (IllegalArgumentException error) { throw new IllegalArgumentException("请选择有效单据日期"); }
    }
    private static int num(Object value) {
        if (value == null) return 0;
        if (value instanceof Boolean) return (Boolean) value ? 1 : 0;
        if (value instanceof Number) return ((Number) value).intValue();
        return Integer.parseInt(value.toString());
    }
    private static BigDecimal decimal(Object value) { return new BigDecimal(str(value)).setScale(4, RoundingMode.HALF_UP); }
    private static BigDecimal positive(Object value) {
        BigDecimal result = decimal(value);
        if (result.signum() <= 0) throw new IllegalArgumentException("商品数量必须大于0");
        return result;
    }
}
