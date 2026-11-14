package com.zeroone.star.basic_information.service;

import com.alibaba.excel.EasyExcel;
import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.mock.web.MockMultipartFile;
import java.io.ByteArrayOutputStream;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class SupplierWorkbookServiceTest {
    JdbcTemplate db; TransactionTemplate tx; SupplierWorkbookService service;
    @BeforeEach void setup() {
        DriverManagerDataSource ds=new DriverManagerDataSource("jdbc:h2:mem:"+UUID.randomUUID()+";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1","sa","");
        db=new JdbcTemplate(ds); tx=new TransactionTemplate(new DataSourceTransactionManager(ds)); service=new SupplierWorkbookService(db);
        db.execute("CREATE TABLE supplier(id VARCHAR(32) PRIMARY KEY,name VARCHAR(32),py VARCHAR(32),number VARCHAR(32),frame VARCHAR(32),`user` VARCHAR(32),category VARCHAR(32),rate DECIMAL(8,4),bank VARCHAR(32),account VARCHAR(64),tax VARCHAR(64),data VARCHAR(256),contacts CLOB,balance DECIMAL(16,4),more CLOB)");
    }
    MockMultipartFile file(List<List<Object>> rows) {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        List<List<String>> head=new ArrayList<>();
        for (String name:Arrays.asList("供应商编号","供应商名称","增值税税率","联系人","联系电话")) head.add(Collections.singletonList(name));
        EasyExcel.write(out).head(head).sheet("供应商").doWrite(rows);
        return new MockMultipartFile("file","supplier.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",out.toByteArray());
    }
    List<Object> row(String code) { return Arrays.asList(code,"测试供应商","0.13","联系人","00123"); }
    @Test void actuallyPersistsSupplierAndContacts() {
        int count=tx.execute(s->service.importFile(file(Collections.singletonList(row("001")))).getSuccessCount());
        assertEquals(1,count);
        assertEquals("001",db.queryForObject("SELECT number FROM supplier",String.class));
        assertTrue(db.queryForObject("SELECT contacts FROM supplier",String.class).contains("00123"));
    }
    @Test void rejectsDuplicatedWorkbookAndExistingCode() {
        assertThrows(IllegalArgumentException.class,()->tx.execute(s->service.importFile(file(Arrays.asList(row("001"),row("001"))))));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM supplier",Integer.class));
        tx.execute(s->service.importFile(file(Collections.singletonList(row("001")))));
        assertThrows(IllegalArgumentException.class,()->tx.execute(s->service.importFile(file(Arrays.asList(row("002"),row("001"))))));
        assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM supplier",Integer.class));
    }
    @Test void laterDatabaseFailureRollsBackEarlierSuppliers() {
        db.execute("ALTER TABLE supplier ADD CONSTRAINT test_failure CHECK(number <> '002')");
        assertThrows(Exception.class,()->tx.execute(s->service.importFile(file(Arrays.asList(row("001"),row("002"))))));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM supplier",Integer.class));
    }
}
