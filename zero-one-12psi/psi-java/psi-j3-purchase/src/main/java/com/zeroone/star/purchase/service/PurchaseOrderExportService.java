package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.io.*;
import java.math.BigDecimal;
import java.util.*;

/** Authorized consistent exports; empty IDs can never mean all orders. */
@Service
public class PurchaseOrderExportService {
    private final JdbcTemplate db;private final PurchaseDocumentAccess access;
    public PurchaseOrderExportService(JdbcTemplate db,PurchaseDocumentAccess access){this.db=db;this.access=access;}
    private static String text(Object value){return value==null?"":value.toString();}
    private static BigDecimal decimal(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private String state(Object value,boolean approval){
        if(value==null)return "异常(空)";int n=((Number)value).intValue();
        if(approval)return n==0?"未审核":n==1?"已审核":"异常("+n+")";
        return n==0?"未入库":n==1?"部分入库":n==2?"已入库":n==3?"关闭":"异常("+n+")";
    }
    private String name(Object name,Object id){return name!=null?name.toString():text(id).isEmpty()?"":"[缺失资料:"+text(id)+"]";}
    private void row(Sheet sheet,int index,CellStyle numbers,Object...values){
        Row row=sheet.createRow(index);for(int i=0;i<values.length;i++){
            Cell cell=row.createCell(i);Object value=values[i];
            if(value instanceof BigDecimal){cell.setCellValue(((BigDecimal)value).doubleValue());cell.setCellStyle(numbers);}
            else cell.setCellValue(text(value)); // Strings remain literals even when beginning with '='.
        }
    }
    private Sheet sheet(Workbook book,String name,CellStyle numbers,String...headers){Sheet sheet=book.createSheet(name);row(sheet,0,numbers,(Object[])headers);sheet.createFreezePane(0,1);for(int i=0;i<headers.length;i++)sheet.setColumnWidth(i,22*256);return sheet;}
    @Transactional(readOnly=true)
    public byte[] simple(List<String> ids){return file(ids,false);}
    @Transactional(readOnly=true)
    public byte[] detailed(List<String> ids){return file(ids,true);}
    private byte[] file(List<String> ids,boolean detail){
        UserDTO actor=access.authorize(detail?"/purchase-order/export/detail":"/purchase-order/export-bor");
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))throw new IllegalArgumentException("请选择1到200张不同的采购订单");
        List<Map<String,Object>> documents=new ArrayList<>();
        for(String id:ids){
            List<Map<String,Object>> found=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS approval_state,CAST(b.state AS SIGNED) AS execution_state,f.name AS frame_name,s.name AS supplier_name,p.name AS people_name,u.name AS user_name FROM bor b LEFT JOIN frame f ON f.id=b.frame LEFT JOIN supplier s ON s.id=b.supplier LEFT JOIN people p ON p.id=b.people LEFT JOIN user u ON u.id=b.user WHERE b.id=?",id);
            if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在，请刷新后重新选择");Map<String,Object> head=found.get(0);access.requireFrame(actor,text(head.get("frame")));documents.add(head);
        }
        SXSSFWorkbook book=new SXSSFWorkbook(100);
        try(ByteArrayOutputStream out=new ByteArrayOutputStream()){
            CellStyle numbers=book.createCellStyle();numbers.setDataFormat(book.createDataFormat().getFormat("0.0000"));
            Sheet summary=sheet(book,"订单汇总",numbers,"所属组织","供应商","单据时间","单据编号","单据金额","实际金额","到货日期","审核状态","入库状态","关联人员","制单人","备注信息");
            Sheet lines=detail?sheet(book,"商品明细",numbers,"单据编号","供应商","商品编号","商品名称","规格","辅助属性","单位","仓库","单价","数量","已入库数量","折扣率(%)","折扣额","金额","税率(%)","税额","价税合计","商品备注"):null;
            int summaryIndex=1,lineIndex=1;BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;BigDecimal[] sums=new BigDecimal[18];Arrays.fill(sums,BigDecimal.ZERO);
            for(Map<String,Object> head:documents){
                row(summary,summaryIndex++,numbers,name(head.get("frame_name"),head.get("frame")),name(head.get("supplier_name"),head.get("supplier")),head.get("time"),head.get("number"),decimal(head.get("total")),decimal(head.get("actual")),head.get("arrival"),state(head.get("approval_state"),true),state(head.get("execution_state"),false),name(head.get("people_name"),head.get("people")),name(head.get("user_name"),head.get("user")),head.get("data"));
                total=total.add(decimal(head.get("total")));actual=actual.add(decimal(head.get("actual")));
                if(detail)for(Map<String,Object> item:db.queryForList("SELECT i.*,g.number AS goods_number,g.name AS goods_name,g.spec,w.name AS warehouse_name FROM bor_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",head.get("id"))){
                    Object[] values={head.get("number"),name(head.get("supplier_name"),head.get("supplier")),item.get("goods_number"),name(item.get("goods_name"),item.get("goods")),item.get("spec"),item.get("attr"),item.get("unit"),name(item.get("warehouse_name"),item.get("warehouse")),decimal(item.get("price")),decimal(item.get("nums")),decimal(item.get("handle")),PurchaseOrderSources.rate(item,true),decimal(item.get("dsc")),decimal(item.get("total")),PurchaseOrderSources.rate(item,false),decimal(item.get("tat")),decimal(item.get("tpt")),item.get("data")};
                    row(lines,lineIndex++,numbers,values);for(int index:new int[]{9,10,12,13,15,16})sums[index]=sums[index].add((BigDecimal)values[index]);
                }
            }
            row(summary,summaryIndex,numbers,"合计("+documents.size()+"张)","","","",total,actual);
            if(detail){Object[] values=new Object[18];Arrays.fill(values,"");values[0]="合计";for(int index:new int[]{9,10,12,13,15,16})values[index]=sums[index];row(lines,lineIndex,numbers,values);}
            book.write(out);return out.toByteArray();
        }catch(IOException error){throw new IllegalStateException("采购订单Excel生成失败，请重试",error);}
        finally{try{book.close();}catch(IOException ignored){}book.dispose();}
    }
}
