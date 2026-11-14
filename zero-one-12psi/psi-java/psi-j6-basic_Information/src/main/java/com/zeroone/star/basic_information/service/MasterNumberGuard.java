package com.zeroone.star.basic_information.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import java.util.*;

/** Call inside the same SERIALIZABLE transaction as the insert/update. */
@Service
public class MasterNumberGuard {
    private final JdbcTemplate db;
    public MasterNumberGuard(JdbcTemplate db) { this.db = db; }
    public void assertAvailable(String table, String number, String id) {
        if (!Arrays.asList("customer","supplier","goods","warehouse","account").contains(table)) throw new IllegalArgumentException("资料类型无效");
        if (!TransactionSynchronizationManager.isActualTransactionActive()) throw new IllegalStateException("编号校验必须与保存处于同一事务");
        if (number == null || number.trim().isEmpty() || number.length()>32) throw new IllegalArgumentException("编号必填，最长 32 字");
        if (id != null) {
            List<String> original = db.queryForList("SELECT number FROM `"+table+"` WHERE id=? FOR UPDATE", String.class, id);
            // Preserve legacy duplicated records when editing unrelated fields.
            if (!original.isEmpty() && number.equals(original.get(0))) return;
        }
        if (!db.queryForList("SELECT id FROM `"+table+"` WHERE number=? FOR UPDATE", number).isEmpty()) throw new IllegalArgumentException("编号已存在，请使用其他编号；不会覆盖原资料");
    }
}
