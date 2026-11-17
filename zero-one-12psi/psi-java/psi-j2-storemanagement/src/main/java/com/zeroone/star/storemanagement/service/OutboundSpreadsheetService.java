package com.zeroone.star.storemanagement.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import java.io.*;
import java.math.BigDecimal;
import java.util.*;

/** Export actual source documents, never a JSON-wrapped ResponseEntity. */
@Service
public class OutboundSpreadsheetService {
    private final JdbcTemplate db;private final StockDocumentAccess access;private final WarehouseReportDocumentService reports;
    public OutboundSpreadsheetService(JdbcTemplate db,StockDocumentAccess access,WarehouseReportDocumentService reports){this.db=db;this.access=access;this.reports=reports;}
    private String text(Object v){return v==null?"":v.toString();}
    private int num(Object v){return v==null?0:v instanceof Boolean?((Boolean)v?1:0):((Number)v).intValue();}
    private String name(String table,Object id){List<String> found=db.queryForList("SELECT name FROM `"+table+"` WHERE id=?",String.class,id);return found.size()==1?found.get(0):text(id);}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public byte[] export(List<String> ids,boolean detail){
        UserDTO actor=access.authorize("extry",detail?"export-detail":"export-simple");String frame=access.frame(actor);
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || !id.matches("[A-Za-z0-9_-]{1,32}")))throw new IllegalArgumentException("请选择1到200张不同的出库单");
        List<String> headers=new ArrayList<>(Arrays.asList("所属组织","单据编号","单据日期","单据类型","关联客户","制单人","成本类型","成本合计","费用合计","审核状态","核对状态","单据备注"));
        if(detail)headers.addAll(Arrays.asList("商品编号","商品名称","辅助属性","基本单位","出库仓库","数量","单位成本","成本金额","批次号","生产日期","序列号JSON","明细备注"));
        List<List<Object>> values=new ArrayList<>();
        for(String id:ids){
            Map<String,Object> doc=reports.detail("extry",id),head=(Map<String,Object>)doc.get("header");List<Map<String,Object>> lines=(List<Map<String,Object>>)doc.get("items");
            if(frame!=null && !frame.equals(text(head.get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能导出其他组织的出库单");
            if(lines.isEmpty())throw new IllegalArgumentException("所选出库单缺少商品明细，请核对历史数据");
            boolean posted=num(head.get("examine"))==1;Object cost=posted?head.getOrDefault("actualCost","待核对"):head.get("total");
            List<Object> base=Arrays.asList(name("frame",head.get("frame")),head.get("number"),text(head.get("time")),num(head.get("type"))==1?"盘亏":"其他出库",name("customer",head.get("customer")),name("user",head.get("user")),posted?"实际成本":"预计成本",cost,head.get("cost"),posted?"已审核":"未审核",num(head.get("check"))==1?"已核对":"未核对",head.get("data"));
            if(!detail){values.add(base);continue;}
            for(Map<String,Object> line:lines){
                List<Object> row=new ArrayList<>(base);List<String> numbers=db.queryForList("SELECT number FROM goods WHERE id=?",String.class,line.get("goods"));
                row.add(numbers.size()==1?numbers.get(0):line.get("goods"));row.add(name("goods",line.get("goods")));row.add(line.get("attr"));row.add(line.get("unit"));row.add(name("warehouse",line.get("warehouse")));row.add(line.get("nums"));row.add(posted?line.getOrDefault("actualPrice","待核对"):line.get("price"));row.add(posted?line.getOrDefault("actualCost","待核对"):line.get("total"));
                for(String key:Arrays.asList("batch","mfd","serial","data"))row.add(line.get(key));values.add(row);if(values.size()>5000)throw new IllegalArgumentException("每次最多导出5000行，请减少选择单据");
            }
        }
        try(Workbook book=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            Sheet sheet=book.createSheet(detail?"出库明细":"出库汇总");Row header=sheet.createRow(0);CellStyle number=book.createCellStyle();number.setDataFormat(book.createDataFormat().getFormat("0.0000"));
            for(int c=0;c<headers.size();c++){header.createCell(c).setCellValue(headers.get(c));sheet.setColumnWidth(c,24*256);}sheet.createFreezePane(0,1);
            for(List<Object> line:values){Row row=sheet.createRow(sheet.getLastRowNum()+1);for(int c=0;c<line.size();c++){Cell cell=row.createCell(c);Object v=line.get(c);if(v instanceof BigDecimal){cell.setCellValue(((BigDecimal)v).doubleValue());cell.setCellStyle(number);}else cell.setCellValue(text(v));}}
            book.write(out);return out.toByteArray();
        }catch(IOException e){throw new IllegalStateException("出库文件生成失败",e);}
    }
}
