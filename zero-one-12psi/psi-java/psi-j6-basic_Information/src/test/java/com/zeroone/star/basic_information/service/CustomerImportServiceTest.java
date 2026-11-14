package com.zeroone.star.basic_information.service;

import com.zeroone.star.project.dto.j6.basic_information.customer_management.CustomerAddDTO;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import javax.validation.Validation;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class CustomerImportServiceTest {
    JdbcTemplate db;
    TransactionTemplate tx;
    CustomerImportService service;
    @BeforeEach void setup() {
        DriverManagerDataSource ds = new DriverManagerDataSource("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE", "sa", "");
        ds.setUrl(ds.getUrl() + ";DB_CLOSE_DELAY=-1");
        db = new JdbcTemplate(ds);
        db.execute("CREATE TABLE customer(id VARCHAR(32) PRIMARY KEY,name VARCHAR(32),py VARCHAR(32),number VARCHAR(32),frame VARCHAR(32),`user` VARCHAR(32),category VARCHAR(32),grade VARCHAR(32),bank VARCHAR(32),account VARCHAR(64),tax VARCHAR(64),data VARCHAR(256),contacts CLOB,balance DECIMAL(16,4),more CLOB)");
        tx = new TransactionTemplate(new DataSourceTransactionManager(ds));
        service = new CustomerImportService(db, Validation.buildDefaultValidatorFactory().getValidator());
    }
    CustomerAddDTO row(String code) {
        CustomerAddDTO row = new CustomerAddDTO();
        row.setNumber(code); row.setName("测试客户"); row.setPy(code); row.setFrame("0");
        row.setUser("admin"); row.setCategory("常规类别"); row.setGrade("常规等级");
        row.setContacts("[{\"name\":\"联系人\"}]"); row.setBank("测试银行"); row.setData("备注");
        return row;
    }
    @Test void importsCompleteRowsWithoutCreatingOpeningReceivables() {
        int count = tx.execute(s -> service.importRows(Arrays.asList(row("C1"), row("C2"))));
        assertEquals(2, count);
        Map<String,Object> actual = db.queryForMap("SELECT * FROM customer WHERE number='C1'");
        assertEquals("测试银行", actual.get("bank"));
        assertEquals("备注", actual.get("data"));
        assertEquals(0, ((java.math.BigDecimal) actual.get("balance")).signum());
    }
    @Test void rejectsDuplicateCodesInWorkbookWithoutWritingAnything() {
        assertThrows(IllegalArgumentException.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("C1"), row("C1")))));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM customer", Integer.class));
    }
    @Test void rejectsExistingCodeAndPreservesOriginalCustomer() {
        tx.execute(s -> service.importRows(Collections.singletonList(row("C1"))));
        assertThrows(IllegalArgumentException.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("C2"), row("C1")))));
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM customer", Integer.class));
    }
    @Test void databaseFailureInLaterRowRollsBackEarlierInserts() {
        db.execute("ALTER TABLE customer ADD CONSTRAINT test_failure CHECK(number <> 'C2')");
        CustomerAddDTO bad = row("C2");
        assertThrows(Exception.class, () -> tx.execute(s -> service.importRows(Arrays.asList(row("C1"), bad))));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM customer", Integer.class));
    }
    @Test void rejectsEmptyOrInvalidRows() {
        assertThrows(IllegalArgumentException.class, () -> service.importRows(Collections.emptyList()));
        CustomerAddDTO bad = row("C1"); bad.setName("");
        assertThrows(IllegalArgumentException.class, () -> service.importRows(Collections.singletonList(bad)));
    }
}
