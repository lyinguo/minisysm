package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import javax.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.*;

/** Create validation; import, revision and posting have their own pending acceptance gates. */
@Service
public class PurchaseDraftValidation {
    private final JdbcTemplate db;
    private final UserHolder users;
    private final PurchaseDocumentAccess access;
    public PurchaseDraftValidation(JdbcTemplate db,UserHolder users,PurchaseDocumentAccess access) { this.db=db;this.users=users;this.access=access; }
    @PostConstruct public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_document_write_lock (scope VARCHAR(40) NOT NULL PRIMARY KEY)");
    }
    private boolean absent(String value) { return value==null || value.trim().isEmpty() || "0".equals(value); }
    private void date(String value,String label) {
        if(value==null || value.trim().isEmpty()) throw new IllegalArgumentException(label+"不能为空");
        for(java.time.format.DateTimeFormatter format:Arrays.asList(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME,java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss").withResolverStyle(java.time.format.ResolverStyle.STRICT))) {
            try { java.time.LocalDateTime.parse(value,format); return; } catch(java.time.format.DateTimeParseException ignored) { }
        }
        try { java.time.LocalDate.parse(value,java.time.format.DateTimeFormatter.ISO_LOCAL_DATE); }
        catch(java.time.format.DateTimeParseException error) { throw new IllegalArgumentException(label+"格式无效，请填写真实有效的日期"); }
    }
    private void reference(String table,String id,String label,String frame,boolean optional) {
        if(optional && absent(id)) return;
        if(absent(id) || db.queryForObject("SELECT COUNT(*) FROM `"+table+"` WHERE id=?",Integer.class,id)!=1) throw new IllegalArgumentException(label+"不存在，请重新选择");
        if(frame!=null) {
            String actual=db.queryForObject("SELECT frame FROM `"+table+"` WHERE id=?",String.class,id);
            if(!"0".equals(actual) && !frame.equals(actual)) throw new IllegalArgumentException(label+"与当前组织不一致");
        }
    }
    public void validate(PurchaseNoteAddDTO request) {
        validate(request,"");
    }
    public void validate(PurchaseNoteAddDTO request,String excludeId) {
        validate(request,excludeId,null);
    }
    public void validate(PurchaseNoteAddDTO request,String excludeId,String selectedFrame) {
        if(!TransactionSynchronizationManager.isActualTransactionActive()) throw new IllegalStateException("采购单保存必须位于事务中");
        if(request==null || request.getPurchaseNoteBuyDTO()==null || request.getPurchaseNoteInfoDTOS()==null || request.getPurchaseNoteInfoDTOS().isEmpty()) throw new IllegalArgumentException("采购单及商品明细不能为空");
        UserDTO actor=access.current();
        String frame=selectedFrame==null ? actor.getFrameId():selectedFrame;
        access.requireFrame(actor,frame);
        reference("frame",frame,"所属组织",null,false);
        db.update("INSERT IGNORE INTO psi_document_write_lock(scope) VALUES('buy')");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        PurchaseNoteBuyDTO head=request.getPurchaseNoteBuyDTO();
        date(head.getTime(),"单据日期");
        String number=head.getNumber()==null ? "":head.getNumber().trim();
        if(number.isEmpty() || number.length()>32) throw new IllegalArgumentException("采购编号必须为1到32个字符");
        head.setNumber(number);
        if(!db.queryForList("SELECT id FROM buy WHERE number=? AND id<>? FOR UPDATE",number,excludeId).isEmpty()) throw new IllegalArgumentException("采购单编号已被使用");
        reference("supplier",head.getSupplier(),"供应商",frame,false);
        reference("account",head.getAccount(),"结算账户",frame,true);
        reference("people",head.getPeople(),"关联人员",frame,true);
        if(head.getMoney()!=null && head.getMoney().signum()>0 && absent(head.getAccount())) throw new IllegalArgumentException("填写实付金额时必须选择结算账户");
        if(head.getMoney()!=null && head.getActual()!=null && head.getMoney().compareTo(head.getActual())>0) throw new IllegalArgumentException("实付金额不能超过实际金额");
        for(PurchaseNoteInfoDTO line:request.getPurchaseNoteInfoDTOS()) {
            if(line==null) throw new IllegalArgumentException("采购商品明细不能为空");
            reference("goods",line.getGoods(),"商品",null,false);
            reference("warehouse",line.getWarehouse(),"仓库",frame,false);
            if(line.getNums()==null || line.getNums().compareTo(BigDecimal.ZERO)<=0) throw new IllegalArgumentException("采购数量必须大于零");
            if(line.getMfd()!=null && !line.getMfd().trim().isEmpty()) date(line.getMfd(),"生产日期");
            Integer batch=db.queryForObject("SELECT CAST(batch AS SIGNED) FROM goods WHERE id=?",Integer.class,line.getGoods());
            if(batch!=null && batch==1 && (absent(line.getBatch()) || line.getMfd()==null || line.getMfd().trim().isEmpty())) throw new IllegalArgumentException("批次商品必须填写批次号和生产日期");
        }
    }
}
