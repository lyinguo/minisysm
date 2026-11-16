package com.zeroone.star.purchase.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import java.util.*;

/** Bounded binary documents are stored with the purchase transaction, never at public URLs. */
@Service
public class PurchaseAttachmentStore {
    private final JdbcTemplate db;
    private static final String VERSION_COLUMNS="id,purchase_id,name,file_size,sha256,created_at,user_id,removed_at,removed_by";
    public PurchaseAttachmentStore(JdbcTemplate db){this.db=db;}
    @PostConstruct
    public void initialize(){
        db.execute("CREATE TABLE IF NOT EXISTS psi_buy_attachment (id VARCHAR(32) NOT NULL PRIMARY KEY,purchase_id VARCHAR(32) NOT NULL,name VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,file_size INT NOT NULL,sha256 CHAR(64) NOT NULL,body MEDIUMBLOB NOT NULL,created_at DATETIME NOT NULL,user_id VARCHAR(32) NOT NULL,removed_at DATETIME NULL,removed_by VARCHAR(32) NULL,INDEX(purchase_id),CONSTRAINT fk_buy_attachment_purchase FOREIGN KEY(purchase_id) REFERENCES buy(id) ON DELETE CASCADE,CONSTRAINT fk_buy_attachment_user FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE RESTRICT) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci");
    }
    public List<Map<String,Object>> items(String purchase){
        return db.queryForList("SELECT a.id,a.name,a.file_size AS size,a.sha256,DATE_FORMAT(a.created_at,'%Y-%m-%d %H:%i:%s') AS uploadedAt,UNIX_TIMESTAMP(a.created_at)*1000 AS uploadedAtMillis,u.name AS uploaderName FROM psi_buy_attachment a LEFT JOIN user u ON u.id=a.user_id WHERE a.purchase_id=? AND a.removed_at IS NULL ORDER BY a.created_at,a.id",purchase);
    }
    public List<Map<String,Object>> versionRows(String purchase,boolean locked){
        return db.queryForList("SELECT "+VERSION_COLUMNS+" FROM psi_buy_attachment WHERE purchase_id=? ORDER BY id"+(locked?" FOR UPDATE":""),purchase);
    }
    public List<Map<String,Object>> versionRows(List<String> purchases){
        if(purchases.isEmpty())return Collections.emptyList();
        return db.queryForList("SELECT "+VERSION_COLUMNS+" FROM psi_buy_attachment WHERE purchase_id IN ("+String.join(",",Collections.nCopies(purchases.size(),"?"))+") ORDER BY purchase_id,id",purchases.toArray());
    }
}
