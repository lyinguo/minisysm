package com.zeroone.star.basic_information.service;

import com.zeroone.star.basic_information.entity.Warehouse;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class WarehouseImportServiceTest {
    JdbcTemplate db; TransactionTemplate tx; WarehouseImportService service;
    @BeforeEach void setup() {
        DriverManagerDataSource ds = new DriverManagerDataSource("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1", "sa", "");
        db = new JdbcTemplate(ds);
        db.execute("CREATE TABLE warehouse(id VARCHAR(32) PRIMARY KEY,name VARCHAR(32),number VARCHAR(32),frame VARCHAR(32),contacts VARCHAR(32),tel VARCHAR(32),`add` VARCHAR(256),data VARCHAR(256))");
        tx = new TransactionTemplate(new DataSourceTransactionManager(ds)); service = new WarehouseImportService(db);
    }
    Warehouse row(String code) {
        Warehouse row = new Warehouse(); row.setName("测试仓库"); row.setNumber(code); row.setTel("00123"); return row;
    }
    @Test void importsAndPreservesPhoneText() {
        tx.execute(s -> service.importRows(Collections.singletonList(row("W1"))));
        assertEquals("00123", db.queryForObject("SELECT tel FROM warehouse", String.class));
    }
    @Test void rejectsDuplicateAndExistingNumbers() {
        assertThrows(IllegalArgumentException.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("W1"),row("W1")))));
        tx.execute(s -> service.importRows(Collections.singletonList(row("W1"))));
        assertThrows(IllegalArgumentException.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("W2"),row("W1")))));
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM warehouse", Integer.class));
    }
    @Test void rollsBackWhenAStoredRowFails() {
        db.execute("ALTER TABLE warehouse ADD CONSTRAINT test_failure CHECK(number <> 'W2')");
        assertThrows(Exception.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("W1"),row("W2")))));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM warehouse", Integer.class));
    }
}
