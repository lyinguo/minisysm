package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

/** Only unused, unaudited orders can be physically deleted; history survives. */
@Service
public class PurchaseOrderDeleteService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseOrderSources sources;
    public PurchaseOrderDeleteService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseOrderSources sources){this.db=db;this.access=access;this.sources=sources;}
    private static String uid(){return UUID.randomUUID().toString().replace("-","");}
    @Transactional(rollbackFor=Exception.class)
    public int delete(List<String> ids){
        UserDTO actor=access.authorize("/purchase-order/delete");
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同的采购订单");
        // Same buy -> bor order as receiving, approval and revision prevents orphan races.
        sources.lock();
        List<String> ordered=new ArrayList<>(ids);Collections.sort(ordered);
        Map<String,Map<String,Object>> documents=new LinkedHashMap<>();
        for(String id:ordered){
            List<Map<String,Object>> found=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS approved,CAST(b.state AS SIGNED) AS execution_state FROM bor b WHERE b.id=? FOR UPDATE",id);
            if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在，请刷新列表");
            Map<String,Object> head=found.get(0);access.requireFrame(actor,String.valueOf(head.get("frame")));
            if(((Number)head.get("approved")).intValue()!=0 || ((Number)head.get("execution_state")).intValue()!=0)
                throw new IllegalArgumentException("已审核、接收或关闭的采购订单不能删除");
            if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)
                throw new IllegalArgumentException("订单日期已结账，不能删除");
            if(!db.queryForList("SELECT id FROM buy WHERE source=? OR source=? FOR UPDATE",id,head.get("number")).isEmpty()
                || !db.queryForList("SELECT i.id FROM buy_info i JOIN bor_info o ON o.id=i.source WHERE o.pid=? FOR UPDATE",id).isEmpty()
                || !db.queryForList("SELECT id FROM bor_info WHERE pid=? AND COALESCE(handle,0)<>0 FOR UPDATE",id).isEmpty()
                || !db.queryForList("SELECT id FROM invoice WHERE type='bor' AND `class`=? FOR UPDATE",id).isEmpty())
                throw new IllegalArgumentException("采购订单存在收货单、接收记录或关联凭据，不能删除");
            documents.put(id,head);
        }
        for(Map.Entry<String,Map<String,Object>> entry:documents.entrySet()){
            String id=entry.getKey(),info="删除采购订单草稿["+entry.getValue().get("number")+"]";
            db.update("DELETE FROM bor_info WHERE pid=?",id);
            if(db.update("DELETE FROM bor WHERE id=?",id)!=1)throw new IllegalStateException("采购订单删除失败");
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bor',?,NOW(),?,?)",uid(),id,actor.getId(),info);
            db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",uid(),actor.getId(),info+"["+id+"]");
        }
        return documents.size();
    }
}
