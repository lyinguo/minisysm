package com.zeroone.star.fund.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import java.io.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

/** Real scoped workbooks; no internal-ID report and no implicit unrestricted export. */
@Service
public class ReceiptExportService {
    private final JdbcTemplate db;private final ReceiptDocumentAccess access;
    public ReceiptExportService(JdbcTemplate db,ReceiptDocumentAccess access){this.db=db;this.access=access;}
    private String text(Object value){return Objects.toString(value,"");}
    private String filter(UserDTO actor,Map<String,String> query,List<Object> args){
        StringBuilder where=new StringBuilder(" WHERE 1=1");
        if(!actor.getRoles().contains("ROLE_ADMIN")){where.append(" AND o.frame=?");args.add(actor.getFrameId());}
        for(String key:Arrays.asList("number","customer"))if(query.get(key)!=null && !query.get(key).trim().isEmpty()){
            String value=query.get(key).trim();
            if(key.equals("number")){where.append(" AND o.number LIKE ?");args.add("%"+value+"%");}
            else{where.append(" AND (o.customer=? OR c.name LIKE ? OR c.number LIKE ?)");Collections.addAll(args,value,"%"+value+"%","%"+value+"%");}
        }
        LocalDate start=null,end=null;
        for(String key:Arrays.asList("startTime","endTime"))if(query.get(key)!=null && !query.get(key).isEmpty()){
            LocalDate date;try{date=LocalDate.parse(query.get(key));}catch(Exception error){throw new IllegalArgumentException("导出日期须为YYYY-MM-DD");}
            if(key.equals("startTime"))start=date;else end=date;
            where.append(" AND DATE(o.time)").append(key.equals("startTime")?">=?":"<=?");args.add(date);
        }
        if(start!=null && end!=null && start.isAfter(end))throw new IllegalArgumentException("导出开始日期不能晚于结束日期");
        for(String key:Arrays.asList("examine","nucleus"))if(query.get(key)!=null && !query.get(key).isEmpty()){
            String value=query.get(key);if(!(key.equals("examine")?Arrays.asList("0","1"):Arrays.asList("0","1","2")).contains(value))throw new IllegalArgumentException("导出状态筛选无效");
            where.append(" AND o.").append(key).append("=?");args.add(Integer.parseInt(value));
        }
        if(query.get("ids")!=null){
            String[] ids=query.get("ids").split(",",-1);if(ids.length<1 || ids.length>200)throw new IllegalArgumentException("一次最多导出200张选中单据");
            for(String id:ids)if(!id.matches("[A-Za-z0-9_-]{1,32}"))throw new IllegalArgumentException("导出单据ID无效");
            where.append(" AND o.id IN (").append(String.join(",",Collections.nCopies(ids.length,"?"))).append(")");Collections.addAll(args,(Object[])ids);
        }
        return where.toString();
    }
    private String state(Object value,boolean approval){int number=((Number)value).intValue();return approval?(number==0?"未审核":number==1?"已审核":"状态异常"):(number==0?"未核销":number==1?"部分核销":number==2?"已核销":"状态异常");}
    private void cell(Row row,int index,Object value){
        Cell cell=row.createCell(index);
        if(value instanceof BigDecimal && ((BigDecimal)value).precision()<=15)cell.setCellValue(((BigDecimal)value).doubleValue());
        else cell.setCellValue(value instanceof BigDecimal?((BigDecimal)value).toPlainString():text(value));
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public byte[] file(String kind,Map<String,String> query){
        if(!Arrays.asList("simple","detail").contains(kind))throw new IllegalArgumentException("导出类型无效");
        UserDTO actor=access.authorize("/fund/receipt/export/"+kind);List<Object> args=new ArrayList<>();String where=filter(actor,query,args);
        boolean simple=kind.equals("simple");
        String select=simple?"SELECT o.number,DATE_FORMAT(o.time,'%Y-%m-%d %H:%i:%s') AS business_time,o.total,o.data,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state,f.name AS frame_name,c.name AS customer_name,p.name AS people_name,u.name AS user_name,COALESCE((SELECT SUM(b.money) FROM imy_bill b WHERE b.pid=o.id),0) AS allocated FROM imy o LEFT JOIN customer c ON c.id=o.customer LEFT JOIN frame f ON f.id=o.frame LEFT JOIN people p ON p.id=o.people LEFT JOIN `user` u ON u.id=o.user":
            "SELECT o.number,DATE_FORMAT(o.time,'%Y-%m-%d %H:%i:%s') AS business_time,c.name AS customer_name,a.name AS account_name,i.money,i.settle,i.data FROM imy o JOIN imy_info i ON i.pid=o.id LEFT JOIN customer c ON c.id=o.customer LEFT JOIN account a ON a.id=i.account";
        List<Map<String,Object>> values=db.queryForList(select+where+" ORDER BY o.time,o.id"+(simple?"":",i.id")+" LIMIT 10001",args.toArray());
        if(values.size()>10000)throw new IllegalArgumentException("导出超过10000"+(simple?"张单据":"条明细")+"，请按日期或编号缩小范围");
        String[] headers=simple?new String[]{"所属组织","客户","单据时间","单据编号","单据金额","核销金额","关联人员","制单人","备注信息","审核状态","核销状态"}:new String[]{"收款单编号","收款日期","客户","结算账户","结算金额","结算号","明细备注"};
        try(Workbook workbook=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            Sheet sheet=workbook.createSheet(simple?"收款单简单报表":"收款单详细报表");Row head=sheet.createRow(0);for(int index=0;index<headers.length;index++)cell(head,index,headers[index]);sheet.createFreezePane(0,1);
            int index=1;for(Map<String,Object> value:values){Object[] cells=simple?new Object[]{value.get("frame_name"),value.get("customer_name"),value.get("business_time"),value.get("number"),value.get("total"),value.get("allocated"),value.get("people_name"),value.get("user_name"),value.get("data"),state(value.get("approval_state"),true),state(value.get("settlement_state"),false)}:new Object[]{value.get("number"),value.get("business_time"),value.get("customer_name"),value.get("account_name"),value.get("money"),value.get("settle"),value.get("data")};
                Row row=sheet.createRow(index++);for(int column=0;column<cells.length;column++)cell(row,column,cells[column]);}
            workbook.write(out);return out.toByteArray();
        }catch(IOException error){throw new IllegalStateException("收款报表生成失败，请重试",error);}
    }
}
