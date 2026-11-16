package com.zeroone.star.fund.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.fund.ReceiptAddDTO;
import com.zeroone.star.project.dto.j4.fund.ReceiptSettlementDetailDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import javax.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.*;

/** Saving a receipt is a draft operation; only explicit settlement moves money. */
@Service
public class ReceiptDraftService {
    private final JdbcTemplate db;
    private final ReceiptDocumentAccess access;
    private final com.fasterxml.jackson.databind.ObjectMapper json;
    public ReceiptDraftService(JdbcTemplate db, ReceiptDocumentAccess access,com.fasterxml.jackson.databind.ObjectMapper json) { this.db=db;this.access=access;this.json=json; }
    @PostConstruct public void initialize() { db.execute("CREATE TABLE IF NOT EXISTS psi_document_write_lock(scope VARCHAR(40) NOT NULL PRIMARY KEY)"); }
    private String uid() { return UUID.randomUUID().toString().replace("-", ""); }
    private String trim(String value) { return value==null?"":value.trim(); }
    private void length(String value,int maximum,String field) { if(value!=null && value.length()>maximum)throw new IllegalArgumentException(field+"最多"+maximum+"个字符"); }
    private void reference(String table,String identifier,String frame,boolean optional,String field) {
        if(optional && (identifier==null || identifier.isEmpty() || "0".equals(identifier))) return;
        if(identifier==null || identifier.isEmpty() || db.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE id=? AND frame IN ('0',?)",Integer.class,identifier,frame)!=1)
            throw new IllegalArgumentException(field+"不存在或与收款组织不一致");
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public String createLegacy(ReceiptAddDTO input) {
        UserDTO actor=access.authorize("/fund/receipt/add");
        if(actor.getFrameId()==null || "0".equals(actor.getFrameId()) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,actor.getFrameId())!=1)
            throw new IllegalArgumentException("当前账号缺少有效制单组织");
        BigDecimal total=fields(input,actor.getFrameId(),true);String number=input.getNumber(),more=input.getMore();
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('imy') ON DUPLICATE KEY UPDATE scope='imy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='imy' FOR UPDATE",String.class);
        if(!db.queryForList("SELECT id FROM imy WHERE number=? FOR UPDATE",number).isEmpty())throw new IllegalArgumentException("收款单编号已被使用");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,input.getTime())>0)throw new IllegalArgumentException("收款日期已结账，不能保存草稿");
        String identifier=uid();String people=trim(input.getPeople());if(people.isEmpty() || "0".equals(people))people=null;
        db.update("INSERT INTO imy(id,frame,customer,time,number,total,people,file,data,more,examine,nucleus,`user`) VALUES(?,?,?,?,?,?,?,'[]',?,?,0,0,?)",identifier,actor.getFrameId(),input.getCustomer(),input.getTime(),number,total,people,input.getData(),more,actor.getId());
        for(ReceiptSettlementDetailDTO line:input.getInfo())
            db.update("INSERT INTO imy_info(id,pid,account,money,settle,data) VALUES(?,?,?,?,?,?)",uid(),identifier,line.getAccount(),line.getAmount(),line.getSettle()==null?"":line.getSettle(),line.getData());
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'imy',?,CURRENT_TIMESTAMP,?,?)",uid(),identifier,actor.getId(),"新增收款草稿 "+number);
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,CURRENT_TIMESTAMP,?,?)",uid(),actor.getId(),"新增收款草稿 "+number);
        return identifier;
    }
    public BigDecimal fields(ReceiptAddDTO input,String frame,boolean creating) {
        if(input==null || input.getInfo()==null || input.getInfo().isEmpty() || input.getInfo().size()>200)
            throw new IllegalArgumentException("请填写1到200条收款账户明细");
        String number=trim(input.getNumber());
        if(number.isEmpty() || number.length()>32)throw new IllegalArgumentException("收款单编号必须为1到32个字符");
        if(input.getTime()==null)throw new IllegalArgumentException("请选择有效收款日期");
        if(creating && input.getFile()!=null && !input.getFile().isEmpty())throw new IllegalArgumentException("附件须通过真实文件流程上传，不能在草稿中填写任意文件地址");
        length(input.getData(),256,"单据备注");
        String more=trim(input.getMore());if(more.isEmpty())more="{}";
        length(more,16384,"扩展信息");
        try {if(!json.readTree(more).isObject())throw new IllegalArgumentException();}
        catch(Exception error){throw new IllegalArgumentException("扩展信息须为有效JSON对象");}
        reference("customer",input.getCustomer(),frame,false,"客户");
        reference("people",input.getPeople(),frame,true,"关联人员");
        BigDecimal total=BigDecimal.ZERO;
        for(int index=0;index<input.getInfo().size();index++) {
            ReceiptSettlementDetailDTO line=input.getInfo().get(index);String label="第"+(index+1)+"条收款明细";
            if(line==null)throw new IllegalArgumentException(label+"不能为空");
            reference("account",line.getAccount(),frame,false,label+"账户");
            BigDecimal amount=line.getAmount();
            if(amount==null || amount.signum()<=0 || amount.stripTrailingZeros().scale()>4 || amount.compareTo(new BigDecimal("99999999.9999"))>0)
                throw new IllegalArgumentException(label+"金额须大于0，最多8位整数和4位小数");
            length(line.getSettle(),256,label+"结算号");length(line.getData(),256,label+"备注");
            total=total.add(amount);
        }
        if(total.compareTo(new BigDecimal("999999999999.9999"))>0)throw new IllegalArgumentException("收款合计超过范围");
        input.setNumber(number);input.setTotal(total);input.setMore(more);
        String people=trim(input.getPeople());input.setPeople(people.isEmpty() || "0".equals(people)?null:people);
        return total;
    }
    public void validateRevision(ReceiptAddDTO input,String identifier,String frame) {
        fields(input,frame,false);
        if(!db.queryForList("SELECT id FROM imy WHERE number=? AND id<>? FOR UPDATE",input.getNumber(),identifier).isEmpty())throw new IllegalArgumentException("收款单编号已被使用");
    }

}
