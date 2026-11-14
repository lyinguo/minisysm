package com.zeroone.star.basic_information.service;

import org.junit.jupiter.api.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

class MasterNumberGuardTest {
    JdbcTemplate db; TransactionTemplate tx; MasterNumberGuard guard;
    @BeforeEach void setup() {
        DriverManagerDataSource ds=new DriverManagerDataSource("jdbc:h2:mem:"+UUID.randomUUID()+";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1","sa","");
        db=new JdbcTemplate(ds); tx=new TransactionTemplate(new DataSourceTransactionManager(ds)); guard=new MasterNumberGuard(db);
        db.execute("CREATE TABLE customer(id VARCHAR(32) PRIMARY KEY,number VARCHAR(32))");
        db.execute("INSERT INTO customer VALUES('one','C1'),('legacy','C1')");
    }
    @Test void rejectsNewDuplicateButPreservesLegacyEditing() {
        assertThrows(IllegalArgumentException.class,()->tx.execute(s->{guard.assertAvailable("customer","C1",null);return null;}));
        tx.execute(s->{guard.assertAvailable("customer","C1","one");return null;});
        tx.execute(s->{guard.assertAvailable("customer","C2","one");return null;});
    }
    @Test void requiresTransactionAndKnownTable() {
        assertThrows(IllegalStateException.class,()->guard.assertAvailable("customer","C2",null));
        assertThrows(IllegalArgumentException.class,()->tx.execute(s->{guard.assertAvailable("customer;DELETE","C2",null);return null;}));
    }
}
