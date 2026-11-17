package com.zeroone.star.storemanagement.service;

import javax.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import java.util.Arrays;

/** Serialize document-number writes in the database; release follows transaction completion. */
@Service
public class StockDocumentWriteLock {
    private final JdbcTemplate db;
    public StockDocumentWriteLock(JdbcTemplate db) { this.db = db; }
    @PostConstruct
    public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_document_write_lock (scope VARCHAR(40) NOT NULL PRIMARY KEY)");
        db.execute("CREATE TABLE IF NOT EXISTS psi_stock_posting_order (sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE)");
    }
    public void lock(String kind) {
        if (!Arrays.asList("entry", "extry", "swap", "inventory-count").contains(kind) || !TransactionSynchronizationManager.isActualTransactionActive())
            throw new IllegalStateException("单据写入必须位于事务中");
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES (?) ON DUPLICATE KEY UPDATE scope=VALUES(scope)", kind);
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope=? FOR UPDATE", String.class, kind);
    }
}
