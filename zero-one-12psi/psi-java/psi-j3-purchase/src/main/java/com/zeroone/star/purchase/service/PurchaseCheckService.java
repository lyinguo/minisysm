package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

/** Check/uncheck is atomic across the selected documents and never posts inventory or cash. */
@Service
public class PurchaseCheckService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseSnapshotService snapshots;
    public PurchaseCheckService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseSnapshotService snapshots) { this.db=db;this.access=access;this.snapshots=snapshots; }
    private static int number(Object value) { return value instanceof Boolean ? ((Boolean)value ? 1:0):value==null ? 0:((Number)value).intValue(); }
    @Transactional(rollbackFor=Exception.class)
    public int change(List<String> ids,int target,String version,Map<String,String> versions) {
        UserDTO actor=access.authorize("/purchase-note/verification");
        if(target!=0 && target!=1) throw new IllegalArgumentException("核对状态只能为0或1");
        Map<String,String> expected=snapshots.expected(ids,version,versions);
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同的采购单");
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('buy') ON DUPLICATE KEY UPDATE scope='buy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        List<String> ordered=new ArrayList<>(ids);Collections.sort(ordered);
        int changed=0;
        for(String id:ordered) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM buy WHERE id=? FOR UPDATE",id);
            if(found.size()!=1) throw new IllegalArgumentException("采购单不存在");
            Map<String,Object> head=found.get(0);
            access.requireFrame(actor,String.valueOf(head.get("frame")));
            snapshots.require(id,expected.get(id));
            if(number(head.get("examine"))!=0 || number(head.get("nucleus"))!=0)
                throw new IllegalArgumentException("已审核或核销的采购单不能更改核对状态");
            if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)
                throw new IllegalArgumentException("已结账期间不能更改核对状态");
            if(target==1 && db.queryForObject("SELECT COUNT(*) FROM buy_info WHERE pid=?",Integer.class,id)==0)
                throw new IllegalArgumentException("采购单没有商品明细");
            if(number(head.get("check"))==target) continue;
            db.update("UPDATE buy SET `check`=? WHERE id=?",target,id);
            String action=target==1 ? "核对采购单":"反核对采购单";
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'buy',?,?,?,?)",UUID.randomUUID().toString().replace("-",""),id,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",UUID.randomUUID().toString().replace("-",""),now,actor.getId(),action+"["+id+"]");
            changed++;
        }
        return changed;
    }
}
