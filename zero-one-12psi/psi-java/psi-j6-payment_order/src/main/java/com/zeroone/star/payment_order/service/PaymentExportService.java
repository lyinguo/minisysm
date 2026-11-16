package com.zeroone.star.payment_order.service;

import com.alibaba.excel.annotation.ExcelProperty;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.vo.j6.payment_order.OmySimpleVO;
import lombok.Data;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.sql.Timestamp;
import java.util.*;

/** Export the same organization's real documents with usable business names and parent numbers. */
@Service
public class PaymentExportService {
    @Data public static class DetailLine {
        @ExcelProperty("付款单编号") private String number;
        @ExcelProperty("付款日期") private String date;
        @ExcelProperty("供应商") private String supplier;
        @ExcelProperty("结算账户") private String account;
        @ExcelProperty("结算金额") private BigDecimal money;
        @ExcelProperty("结算号") private String settle;
        @ExcelProperty("明细备注") private String data;
    }
    private final JdbcTemplate db;private final PaymentDocumentAccess access;
    public PaymentExportService(JdbcTemplate db,PaymentDocumentAccess access){this.db=db;this.access=access;}
    private String s(Object value){return Objects.toString(value,"");}
    private String filter(UserDTO actor,Map<String,String> query,List<Object> args){
        StringBuilder where=new StringBuilder(" WHERE 1=1");if(!actor.getRoles().contains("ROLE_ADMIN")){where.append(" AND o.frame=?");args.add(actor.getFrameId());}
        for(String key:Arrays.asList("number","supplier"))if(query.get(key)!=null && !query.get(key).trim().isEmpty()){where.append(key.equals("number")?" AND o.number LIKE ?":" AND (o.supplier=? OR c.name LIKE ? OR c.number LIKE ?)");String value=query.get(key).trim();if(key.equals("number"))args.add("%"+value+"%");else Collections.addAll(args,value,"%"+value+"%","%"+value+"%");}
        for(String key:Arrays.asList("startTime","endTime"))if(query.get(key)!=null && !query.get(key).isEmpty()){LocalDate date;try{date=LocalDate.parse(query.get(key));}catch(Exception error){throw new IllegalArgumentException("导出日期无效");}where.append(" AND DATE(o.time)").append(key.equals("startTime")?">=?":"<=?");args.add(date);}
        for(String state:Arrays.asList("examine","nucleus"))if(query.get(state)!=null && !query.get(state).isEmpty()){String value=query.get(state);if(!(state.equals("examine")?Arrays.asList("0","1"):Arrays.asList("0","1","2")).contains(value))throw new IllegalArgumentException("导出状态筛选无效");where.append(" AND o.").append(state).append("=?");args.add(Integer.parseInt(value));}
        if(query.get("ids")!=null){String[] ids=query.get("ids").split(",",-1);if(ids.length<1 || ids.length>200)throw new IllegalArgumentException("一次最多导出200张选中单据");for(String id:ids)if(!id.matches("[A-Za-z0-9_-]{1,32}"))throw new IllegalArgumentException("导出单据ID无效");where.append(" AND o.id IN (").append(String.join(",",Collections.nCopies(ids.length,"?"))).append(")");Collections.addAll(args,(Object[])ids);}
        return where.toString();
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public List<OmySimpleVO> simple(Map<String,String> query){
        UserDTO actor=access.authorize("/payment-order/export/simple");List<Object> args=new ArrayList<>();String where=filter(actor,query,args);
        List<Map<String,Object>> rows=db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state,f.name AS frame_name,c.name AS supplier_name,p.name AS people_name,u.name AS user_name,COALESCE((SELECT SUM(b.money) FROM omy_bill b WHERE b.pid=o.id),0) AS allocated FROM omy o LEFT JOIN supplier c ON c.id=o.supplier LEFT JOIN frame f ON f.id=o.frame LEFT JOIN people p ON p.id=o.people LEFT JOIN `user` u ON u.id=o.user"+where+" ORDER BY o.time,o.id LIMIT 10001",args.toArray());
        if(rows.size()>10000)throw new IllegalArgumentException("导出超过10000张，请按日期或编号缩小范围");List<OmySimpleVO> result=new ArrayList<>();
        for(Map<String,Object> row:rows){OmySimpleVO value=new OmySimpleVO();value.setFrame(s(row.get("frame_name")));value.setSupplier(s(row.get("supplier_name")));value.setTime(row.get("time") instanceof java.time.LocalDateTime?(java.time.LocalDateTime)row.get("time"):((Timestamp)row.get("time")).toLocalDateTime());value.setNumber(s(row.get("number")));value.setTotal((BigDecimal)row.get("total"));value.setWriteOffAmount((BigDecimal)row.get("allocated"));value.setPeople(s(row.get("people_name")));value.setUser(s(row.get("user_name")));value.setData(s(row.get("data")));value.setExamineDesc(((Number)row.get("approval_state")).intValue()==1?"已审核":"未审核");int state=((Number)row.get("settlement_state")).intValue();value.setNucleusDesc(state==0?"未核销":state==1?"部分核销":state==2?"已核销":"状态异常");result.add(value);}return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public List<DetailLine> detail(Map<String,String> query){
        UserDTO actor=access.authorize("/payment-order/export/detail");List<Object> args=new ArrayList<>();String where=filter(actor,query,args);
        List<Map<String,Object>> rows=db.queryForList("SELECT o.number,DATE_FORMAT(o.time,'%Y-%m-%d') AS date,c.name AS supplier,a.name AS account,i.money,i.settle,i.data FROM omy o JOIN omy_info i ON i.pid=o.id LEFT JOIN supplier c ON c.id=o.supplier LEFT JOIN account a ON a.id=i.account"+where+" ORDER BY o.time,o.id,i.id LIMIT 10001",args.toArray());
        if(rows.size()>10000)throw new IllegalArgumentException("导出超过10000条明细，请缩小范围");List<DetailLine> result=new ArrayList<>();for(Map<String,Object> row:rows){DetailLine value=new DetailLine();value.setNumber(s(row.get("number")));value.setDate(s(row.get("date")));value.setSupplier(s(row.get("supplier")));value.setAccount(s(row.get("account")));value.setMoney((BigDecimal)row.get("money"));value.setSettle(s(row.get("settle")));value.setData(s(row.get("data")));result.add(value);}return result;
    }
}
