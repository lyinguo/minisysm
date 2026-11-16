package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReviewCommand;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

/** Review transitions share the draft/posting lock and commit operator history atomically. */
@Service
public class SaleCheckService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleDraftService drafts;
    private final SaleSnapshotService snapshots;
    public SaleCheckService(JdbcTemplate db,SaleDocumentAccess access,SaleDraftService drafts,SaleSnapshotService snapshots){
        this.db=db;this.access=access;this.drafts=drafts;this.snapshots=snapshots;
    }
    private int status(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?-1:((Number)value).intValue();}
    private String uid(){return UUID.randomUUID().toString().replace("-","");}
    @Transactional(rollbackFor=Exception.class)
    public int check(SaleReviewCommand command,boolean target){
        UserDTO actor=access.authorize("/sale/form/check");
        if(command==null)throw new IllegalArgumentException("请重新读取销售单后操作");
        Map<String,String> expected=snapshots.expected(command.getIds(),command.getVersion(),command.getVersions());
        drafts.lockWrites();
        List<String> ids=new ArrayList<>(command.getIds());Collections.sort(ids);int changed=0;
        for(String id:ids){
            List<Map<String,Object>> found=db.queryForList("SELECT * FROM sell WHERE id=? FOR UPDATE",id);
            if(found.size()!=1)throw new IllegalArgumentException("销售单不存在，本次整批未处理");
            Map<String,Object> head=found.get(0);access.requireFrame(actor,Objects.toString(head.get("frame"),""));
            snapshots.require(id,expected.get(id));
            if(status(head.get("examine"))!=0 || status(head.get("nucleus"))!=0)
                throw new IllegalArgumentException("已审核或核销的销售单不能核对或反核对");
            int checked=status(head.get("check"));
            if(checked!=0 && checked!=1)throw new IllegalArgumentException("销售单核对状态异常，请先核对数据");
            if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)
                throw new IllegalArgumentException("单据日期已结账，不能核对或反核对");
            if(db.queryForObject("SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id=?",Integer.class,id)>0)
                throw new IllegalArgumentException("销售单已有入账凭据，请先核对库存和资金");
            if(checked==(target?1:0))continue;
            db.update("UPDATE sell SET `check`=? WHERE id=?",target?1:0,id);
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
            String action=target?"核对销售单":"反核对销售单";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'sell',?,?,?,?)",uid(),id,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),action+"["+id+"]");
            changed++;
        }
        return changed;
    }
}
