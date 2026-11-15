package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.PostConstruct;
import java.util.*;

/** Explicit, organization-scoped supplier catalog. Disabling preserves its history. */
@Service
public class PurchaseSupplyService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    public PurchaseSupplyService(JdbcTemplate db,PurchaseDocumentAccess access) {this.db=db;this.access=access;}
    @PostConstruct public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_goods_supplier (frame VARCHAR(32) NOT NULL,goods VARCHAR(32) NOT NULL,supplier VARCHAR(32) NOT NULL,enabled TINYINT NOT NULL DEFAULT 1,`user` VARCHAR(32) NOT NULL,updated DATETIME NOT NULL,PRIMARY KEY(frame,goods,supplier),CONSTRAINT psi_supply_goods FOREIGN KEY(goods) REFERENCES goods(id),CONSTRAINT psi_supply_supplier FOREIGN KEY(supplier) REFERENCES supplier(id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci");
    }
    private void valid(String goods,String supplier,String frame) {
        if(goods==null || db.queryForObject("SELECT COUNT(*) FROM goods WHERE id=?",Integer.class,goods)!=1) throw new IllegalArgumentException("商品不存在，请重新选择");
        if(frame==null || "0".equals(frame) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,frame)!=1) throw new IllegalArgumentException("请先为当前账号设置实际制单组织");
        if(supplier!=null && db.queryForObject("SELECT COUNT(*) FROM supplier WHERE id=? AND (frame=? OR frame='0')",Integer.class,supplier,frame)!=1) throw new IllegalArgumentException("供应商不存在或不属于当前组织");
    }
    public List<Map<String,Object>> list(String goods) {
        UserDTO actor=access.authorize("/purchase-order/add");valid(goods,null,actor.getFrameId());
        return db.queryForList("SELECT s.id,s.name,s.number,c.enabled FROM psi_goods_supplier c JOIN supplier s ON s.id=c.supplier WHERE c.frame=? AND c.goods=? AND (s.frame=? OR s.frame='0') ORDER BY c.enabled DESC,s.number,s.id",actor.getFrameId(),goods,actor.getFrameId());
    }
    private void lock(String frame) {
        String scope="supply:"+frame;
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES(?) ON DUPLICATE KEY UPDATE scope=VALUES(scope)",scope);
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope=? FOR UPDATE",String.class,scope);
    }
    @Transactional(rollbackFor=Exception.class)
    public void set(String goods,String supplier,boolean enabled) {
        UserDTO actor=access.authorize("/purchase-order/supply/manage");
        valid(goods,supplier,actor.getFrameId());if(supplier==null || supplier.trim().isEmpty())throw new IllegalArgumentException("请选择供应商");
        lock(actor.getFrameId());
        if(db.queryForList("SELECT id FROM supplier WHERE id=? AND (frame=? OR frame='0') FOR UPDATE",supplier,actor.getFrameId()).size()!=1) throw new IllegalArgumentException("供应商不存在或不属于当前组织");
        db.update("INSERT INTO psi_goods_supplier(frame,goods,supplier,enabled,`user`,updated) VALUES(?,?,?,?,?,NOW()) ON DUPLICATE KEY UPDATE enabled=VALUES(enabled),`user`=VALUES(`user`),updated=NOW()",actor.getFrameId(),goods,supplier,enabled?1:0,actor.getId());
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",UUID.randomUUID().toString().replace("-",""),actor.getId(),(enabled?"建立":"停用")+"商品供货关系，商品："+goods+"，供应商："+supplier);
    }
    public void require(String frame,String goods,String supplier) {
        lock(frame);
        if(db.queryForList("SELECT c.supplier FROM psi_goods_supplier c JOIN supplier s ON s.id=c.supplier WHERE c.frame=? AND c.goods=? AND c.supplier=? AND c.enabled=1 AND (s.frame=? OR s.frame='0') FOR UPDATE",frame,goods,supplier,frame).size()!=1)
            throw new IllegalArgumentException("商品未建立有效供货关系，请先维护该商品的供货商后重试");
    }
}
