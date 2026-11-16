package com.zeroone.star.payment_order.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j6.payment_order.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Reviewed complete drafts, never unattached account rows or automatic payments. */
@Service
public class PaymentImportService {
    public static class Row {public String number,date,supplierNumber,accountNumber,settle,remark,lineRemark;public BigDecimal money;}
    public static class Command {public List<Row> rows;public String version;}
    private final JdbcTemplate db;private final PaymentDocumentAccess access;private final PaymentDraftValidation validation;private final PaymentOrderService orders;private final ObjectMapper mapper;
    public PaymentImportService(JdbcTemplate db,PaymentDocumentAccess access,PaymentDraftValidation validation,PaymentOrderService orders,ObjectMapper mapper){this.db=db;this.access=access;this.validation=validation;this.orders=orders;this.mapper=mapper;}
    private String s(String value){return value==null?"":value.trim();}
    private String reference(String table,String number,String frame,String label){List<String> ids=db.queryForList("SELECT id FROM "+table+" WHERE number=? AND frame IN ('0',?)",String.class,s(number),frame);if(s(number).isEmpty() || ids.size()!=1)throw new IllegalArgumentException(label+"编号不存在、不属于当前组织或不唯一："+s(number));return ids.get(0);}
    private UserDTO actor(){UserDTO actor=access.authorize("/payment-order/addmore");access.authorize("/payment-order/add");if(actor.getFrameId()==null || "0".equals(actor.getFrameId()) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,actor.getFrameId())!=1)throw new IllegalArgumentException("请选择有效制单组织");return actor;}
    private Map<String,Object> prepare(Command command,UserDTO actor){
        if(command==null || command.rows==null || command.rows.isEmpty() || command.rows.size()>1000)throw new IllegalArgumentException("请提交1到1000行付款模板数据");
        LinkedHashMap<String,OmyWithInfoAddDTO> groups=new LinkedHashMap<>();int index=0;
        for(Row row:command.rows){index++;if(row==null)throw new IllegalArgumentException("第"+index+"行不能为空");String number=s(row.number),supplier=reference("supplier",row.supplierNumber,actor.getFrameId(),"第"+index+"行供应商"),account=reference("account",row.accountNumber,actor.getFrameId(),"第"+index+"行结算账户");
            LocalDate date;try{date=LocalDate.parse(s(row.date));}catch(Exception error){throw new IllegalArgumentException("第"+index+"行日期须为YYYY-MM-DD");}
            OmyWithInfoAddDTO draft=groups.get(number);
            if(draft==null){draft=new OmyWithInfoAddDTO();draft.setNumber(number);draft.setTime(date);draft.setSupplier(supplier);draft.setData(s(row.remark));draft.setFile("[]");draft.setInfoList(new ArrayList<>());groups.put(number,draft);}
            else if(!draft.getSupplier().equals(supplier) || !draft.getTime().equals(date) || !draft.getData().equals(s(row.remark)))throw new IllegalArgumentException("同一单据编号的供应商、日期和单据备注必须一致："+number);
            OmyInfoAddDTO line=new OmyInfoAddDTO();line.setAccount(account);line.setMoney(row.money);line.setSettle(s(row.settle));line.setData1(s(row.lineRemark));draft.getInfoList().add(line);
        }
        if(groups.size()>100)throw new IllegalArgumentException("一次最多导入100张付款草稿");BigDecimal cash=BigDecimal.ZERO;
        for(OmyWithInfoAddDTO draft:groups.values()){validation.fields(draft,actor.getFrameId());if(db.queryForObject("SELECT COUNT(*) FROM omy WHERE number=?",Integer.class,draft.getNumber())>0)throw new IllegalArgumentException("付款单编号已存在："+draft.getNumber());if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=?",Integer.class,draft.getTime())>0)throw new IllegalArgumentException("付款日期已结账："+draft.getNumber());cash=cash.add(draft.getTotal());}
        Map<String,Object> result=new LinkedHashMap<>();result.put("documents",new ArrayList<>(groups.values()));result.put("documentCount",groups.size());result.put("lineCount",command.rows.size());result.put("cash",cash);
        try{String raw=actor.getId()+":"+actor.getFrameId()+":"+mapper.writeValueAsString(result);StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8)))hash.append(String.format("%02x",b&255));result.put("version",hash.toString());}catch(Exception error){throw new IllegalStateException("导入预览版本生成失败",error);}return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> preview(Command command){return prepare(command,actor());}
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    @SuppressWarnings("unchecked")
    public Map<String,Object> save(Command command){
        UserDTO actor=actor();db.update("INSERT INTO psi_document_write_lock(scope) VALUES('omy') ON DUPLICATE KEY UPDATE scope='omy'");db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='omy' FOR UPDATE",String.class);
        Map<String,Object> plan=prepare(command,actor);if(command.version==null || !command.version.equals(plan.get("version")))throw new IllegalArgumentException("模板数据或基础资料已变化，请重新预览核对后导入");
        List<String> ids=new ArrayList<>();for(OmyWithInfoAddDTO draft:(List<OmyWithInfoAddDTO>)plan.get("documents"))ids.add(orders.insertOmyWithInfo(draft));
        Map<String,Object> result=new LinkedHashMap<>();result.put("ids",ids);result.put("documentCount",ids.size());result.put("lineCount",plan.get("lineCount"));result.put("cash",plan.get("cash"));return result;
    }
}
