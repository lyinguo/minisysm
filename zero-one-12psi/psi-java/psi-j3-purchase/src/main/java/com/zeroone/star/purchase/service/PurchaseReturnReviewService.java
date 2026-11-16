package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseReturnCommand;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.util.*;

/** Atomic review only: no return inventory, refund or payable posting here. */
@Service
public class PurchaseReturnReviewService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseReturnDraftService drafts;
    private final PurchaseReturnSnapshotService versions;
    public PurchaseReturnReviewService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseReturnDraftService drafts,PurchaseReturnSnapshotService versions){this.db=db;this.access=access;this.drafts=drafts;this.versions=versions;}
    private String uid(){return UUID.randomUUID().toString().replace("-","");}
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public int check(PurchaseReturnCommand command){
        UserDTO actor=access.authorize("/purchase-return-form/checkout");
        if(command==null || command.getStatus()==null || (command.getStatus()!=0 && command.getStatus()!=1))throw new IllegalArgumentException("核对目标只能为0或1");
        Map<String,String> expected=versions.expected(command.getIds(),command.getVersion(),command.getVersions());
        drafts.lockWrites();List<String> ids=new ArrayList<>(command.getIds());Collections.sort(ids);int changed=0;
        for(String id:ids){
            Map<String,Object> head=drafts.lockForReview(id);access.requireFrame(actor,Objects.toString(head.get("frame"),""));
            versions.require(id,expected.get(id));drafts.validateForReview(head);
            if(((Number)head.get("check_state")).intValue()==command.getStatus())continue;
            db.update("UPDATE bre SET `check`=? WHERE id=?",command.getStatus(),id);
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());String action=command.getStatus()==1?"核对采购退货单":"反核对采购退货单";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bre',?,?,?,?)",uid(),id,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),action+"["+id+"]");changed++;
        }
        return changed;
    }
}
