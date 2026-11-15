package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

/** Physical deletion of free drafts only; action history is retained. */
@Service
public class PurchaseDeleteService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchasePostingService postings;
    public PurchaseDeleteService(JdbcTemplate db,PurchaseDocumentAccess access,PurchasePostingService postings) { this.db=db;this.access=access;this.postings=postings; }
    private static String uid() { return UUID.randomUUID().toString().replace("-",""); }
    @Transactional(rollbackFor=Exception.class)
    public int delete(List<String> ids) {
        UserDTO actor=access.authorize("/purchase-note/delete");
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同的采购单");
        db.update("INSERT IGNORE INTO psi_document_write_lock(scope) VALUES('buy')");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        List<String> ordered=new ArrayList<>(ids);Collections.sort(ordered);
        Map<String,Map<String,Object>> documents=new LinkedHashMap<>();
        for(String id:ordered) {
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM buy WHERE id=? FOR UPDATE",id);
            if(found.size()!=1) throw new IllegalArgumentException("采购单不存在，请刷新列表");
            Map<String,Object> header=found.get(0);
            access.requireFrame(actor,String.valueOf(header.get("frame")));
            postings.requireDeletable(id);
            documents.put(id,header);
        }
        for(Map.Entry<String,Map<String,Object>> document:documents.entrySet()) {
            String id=document.getKey();
            db.update("DELETE FROM buy_info WHERE pid=?",id);
            if(db.update("DELETE FROM buy WHERE id=?",id)!=1) throw new IllegalStateException("采购单删除失败");
            String info="删除采购草稿["+document.getValue().get("number")+"]";
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'buy',?,?,?,?)",uid(),id,now,actor.getId(),info);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),info+"["+id+"]");
        }
        return documents.size();
    }
}
