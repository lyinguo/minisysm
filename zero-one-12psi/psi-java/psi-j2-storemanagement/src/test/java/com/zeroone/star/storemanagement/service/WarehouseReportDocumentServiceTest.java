package com.zeroone.star.storemanagement.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.init.DatabasePopulatorUtils;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.transaction.support.TransactionTemplate;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;

class WarehouseReportDocumentServiceTest {
    JdbcTemplate db;
    TransactionTemplate tx;
    WarehouseReportDocumentService service;

    @BeforeEach void setup() {
        DriverManagerDataSource ds = new DriverManagerDataSource("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=10000", "sa", "");
        DatabasePopulatorUtils.execute(new ResourceDatabasePopulator(new ClassPathResource("warehouse-schema.sql")), ds);
        db = new JdbcTemplate(ds);
        tx = new TransactionTemplate(new DataSourceTransactionManager(ds));
        service = new WarehouseReportDocumentService(db);
        new StockDocumentWriteLock(db).initialize();
        db.update("INSERT INTO warehouse(id,name,number) VALUES('w1','仓库一','W1'),('w2','仓库二','W2')");
        db.update("INSERT INTO goods(id,name,py,number,category,unit,buy,sell,stock,type,more) VALUES('g1','测试商品','cs','G1','0','个',2,3,0,0,'{}')");
        db.update("INSERT INTO room(id,warehouse,goods,attr,nums) VALUES('r1','w1','g1','',10),('r2','w2','g1','',3)");
    }
    void document(String kind, String id, int qty) {
        String extra = "entry".equals(kind) ? ",supplier,type,`check`" : "extry".equals(kind) ? ",customer,type,`check`" : "";
        String values = "swap".equals(kind) ? "" : ",'partner',0,0";
        db.update("INSERT INTO `" + kind + "`(id,frame,time,number,total,cost,examine,cse,`user`" + extra + ") VALUES(?,'0','2026-11-14 10:00:00',?,0,0,0,3,'tester'" + values + ")", id, id);
        String target = "swap".equals(kind) ? ",storehouse" : "";
        String targetValue = "swap".equals(kind) ? ",'w2'" : "";
        db.update("INSERT INTO `" + kind + "_info`(id,pid,goods,attr,unit,warehouse,price,nums,total" + target + ") VALUES(?,?,'g1','','个','w1',2,?,?" + targetValue + ")", id + "-item", id, qty, qty * 2);
    }
    String version(String kind, String id) { return (String) service.detail(kind, id).get("version"); }
    void audit(String kind, String id, int target) {
        String version = version(kind, id);
        tx.execute(status -> service.audit(kind, id, target, version, "tester"));
    }
    void assertStock(String room, int value) {
        assertEquals(0, db.queryForObject("SELECT nums FROM room WHERE id=?", BigDecimal.class, room).compareTo(BigDecimal.valueOf(value)));
    }
    @Test void inboundAuditAndReverseUpdateRealStockAndLedgers() {
        document("entry", "in", 4);
        audit("entry", "in", 1);
        assertStock("r1", 14);
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM room_info", Integer.class));
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM summary", Integer.class));
        audit("entry", "in", 0);
        assertStock("r1", 10);
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM room_info", Integer.class));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM summary", Integer.class));
    }
    @Test void listUsesDocumentIdsAndRespectsOrganizationScope() {
        document("entry", "in", 4);
        db.update("INSERT INTO entry_info(id,pid,goods,unit,warehouse,price,nums,total) VALUES('second','in','g1','个','w1',2,1,2)");
        Map<String, Object> all = service.list("entry", 1, 20, "", null);
        assertEquals(1L, all.get("total"));
        assertEquals(1, ((List<?>) all.get("rows")).size());
        assertEquals(0L, service.list("entry", 1, 20, "", "other-frame").get("total"));
    }
    @Test void outboundAuditAndReverseUpdateRealStock() {
        document("extry", "out", 4);
        audit("extry", "out", 1);
        assertStock("r1", 6);
        audit("extry", "out", 0);
        assertStock("r1", 10);
    }
    @Test void transferMovesBothWarehousesAndCanReverse() {
        document("swap", "move", 4);
        audit("swap", "move", 1);
        assertStock("r1", 6); assertStock("r2", 7);
        audit("swap", "move", 0);
        assertStock("r1", 10); assertStock("r2", 3);
    }
    @Test void insufficientStockRollsBackStatusAndInventory() {
        document("extry", "out", 20);
        assertThrows(IllegalStateException.class, () -> audit("extry", "out", 1));
        assertStock("r1", 10);
        assertEquals(0, db.queryForObject("SELECT examine FROM extry WHERE id='out'", Integer.class));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM room_info", Integer.class));
    }
    @Test void failureOnSecondLineRollsBackFirstLine() {
        document("extry", "out", 4);
        db.update("INSERT INTO extry_info(id,pid,goods,attr,unit,warehouse,price,nums,total) VALUES('zz','out','g1','','个','w2',2,20,40)");
        assertThrows(IllegalStateException.class, () -> audit("extry", "out", 1));
        assertStock("r1", 10); assertStock("r2", 3);
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM summary", Integer.class));
    }
    @Test void repeatedAndConcurrentAuditDoesNotApplyStockTwice() throws Exception {
        document("entry", "in", 4);
        String version = version("entry", "in");
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch start = new CountDownLatch(1);
        try {
            Callable<Object> task = () -> { start.await(); return tx.execute(status -> service.audit("entry", "in", 1, version, "tester")); };
            Future<Object> a = pool.submit(task); Future<Object> b = pool.submit(task); start.countDown();
            a.get(15, TimeUnit.SECONDS); b.get(15, TimeUnit.SECONDS);
            assertStock("r1", 14);
            assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM room_info", Integer.class));
        } finally { pool.shutdownNow(); }
    }
    @Test void reverseFailsIfReceivedStockHasAlreadyBeenConsumed() {
        document("entry", "in", 4); audit("entry", "in", 1);
        db.update("UPDATE room SET nums=1 WHERE id='r1'");
        assertThrows(IllegalStateException.class, () -> audit("entry", "in", 0));
        assertStock("r1", 1);
        assertEquals(1, db.queryForObject("SELECT examine FROM entry WHERE id='in'", Integer.class));
    }
    @SuppressWarnings("unchecked")
    WarehouseReportDocumentService.Edit edit(String kind, String id) {
        Map<String, Object> data = service.detail(kind, id);
        WarehouseReportDocumentService.Edit edit = new WarehouseReportDocumentService.Edit();
        edit.setVersion((String) data.get("version"));
        edit.setHeader((Map<String, Object>) data.get("header"));
        edit.setItems((List<Map<String, Object>>) data.get("items"));
        return edit;
    }
    @Test void savePersistsValuesButDoesNotChangeStockUntilAudit() {
        document("entry", "in", 4);
        WarehouseReportDocumentService.Edit edit = edit("entry", "in");
        edit.getItems().get(0).put("nums", 5);
        tx.execute(status -> service.save("entry", "in", edit, "tester"));
        assertStock("r1", 10);
        assertEquals(0, db.queryForObject("SELECT total FROM entry WHERE id='in'", BigDecimal.class).compareTo(BigDecimal.TEN));
        audit("entry", "in", 1); assertStock("r1", 15);
    }
    @Test void staleSaveAndAuditedSaveAreRejected() {
        document("entry", "in", 4);
        WarehouseReportDocumentService.Edit stale = edit("entry", "in");
        db.update("UPDATE entry SET data='changed' WHERE id='in'");
        assertThrows(IllegalStateException.class, () -> tx.execute(status -> service.save("entry", "in", stale, "tester")));
        audit("entry", "in", 1);
        WarehouseReportDocumentService.Edit audited = edit("entry", "in");
        assertThrows(IllegalStateException.class, () -> tx.execute(status -> service.save("entry", "in", audited, "tester")));
    }
    @Test void batchesMoveWithTheirWarehouseStock() {
        document("swap", "move", 4);
        db.update("UPDATE goods SET batch=1 WHERE id='g1'");
        db.update("UPDATE swap_info SET batch='B1',mfd='2026-11-01' WHERE pid='move'");
        db.update("INSERT INTO batch(id,room,warehouse,goods,number,time,nums) VALUES('b1','r1','w1','g1','B1','2026-11-01',10)");
        audit("swap", "move", 1);
        assertStock("r1", 6); assertStock("r2", 7);
        audit("swap", "move", 0);
        assertStock("r1", 10); assertStock("r2", 3);
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM batch_info", Integer.class));
    }
    @Test void serialTransferAndReverseKeepCurrentLocationConsistent() {
        document("swap", "move", 1);
        db.update("UPDATE goods SET serial=1 WHERE id='g1'");
        db.update("UPDATE swap_info SET serial='[\"SN1\"]' WHERE pid='move'");
        db.update("INSERT INTO serial(id,room,warehouse,goods,number,state) VALUES('s1','r1','w1','g1','SN1',0)");
        audit("swap", "move", 1);
        assertStock("r1", 9); assertStock("r2", 4);
        assertEquals("w2", db.queryForObject("SELECT warehouse FROM serial WHERE id='s1'", String.class));
        audit("swap", "move", 0);
        assertStock("r1", 10); assertStock("r2", 3);
        assertEquals("w1", db.queryForObject("SELECT warehouse FROM serial WHERE id='s1'", String.class));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM serial_info", Integer.class));
    }
    @Test void serialQuantityMismatchRollsBackInventory() {
        document("entry", "in", 4);
        db.update("UPDATE goods SET serial=1 WHERE id='g1'");
        db.update("UPDATE entry_info SET serial='[\"SN1\"]' WHERE pid='in'");
        assertThrows(IllegalArgumentException.class, () -> audit("entry", "in", 1));
        assertStock("r1", 10);
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM serial", Integer.class));
    }
}
