package com.zeroone.star.fund.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.fund.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import java.io.*;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.time.format.*;
import java.util.*;

/** Preview complete receipts by business codes, then atomically save reviewed drafts. */
@Service
public class ReceiptImportService {
    public static class Line {public String number,date,customerNumber,accountNumber,settle,remark,lineRemark;public BigDecimal money;}
    public static class Command {public List<Line> rows;public String version;}
    private static final String[] HEADERS={"收款单编号","收款时间","客户编号","结算账户编号","结算金额","结算号","单据备注","明细备注"};
    private static final DateTimeFormatter TIME=DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss").withResolverStyle(ResolverStyle.STRICT);
    private final JdbcTemplate db;private final ReceiptDocumentAccess access;private final ReceiptDraftService drafts;private final ObjectMapper mapper;
    public ReceiptImportService(JdbcTemplate db,ReceiptDocumentAccess access,ReceiptDraftService drafts,ObjectMapper mapper){this.db=db;this.access=access;this.drafts=drafts;this.mapper=mapper;}
    private String s(String value){return value==null?"":value.trim();}
    private String reference(String table,String code,String frame,String label){
        List<String> ids=db.queryForList("SELECT id FROM "+table+" WHERE number=? AND frame IN ('0',?)",String.class,s(code),frame);
        if(s(code).isEmpty() || ids.size()!=1)throw new IllegalArgumentException(label+"编号不存在、不属于当前组织或不唯一："+s(code));return ids.get(0);
    }
    private UserDTO actor(){
        UserDTO actor=access.authorize("/fund/receipt/import");access.authorize("/fund/receipt/add");
        if(actor.getFrameId()==null || "0".equals(actor.getFrameId()) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,actor.getFrameId())!=1)throw new IllegalArgumentException("请选择有效制单组织");return actor;
    }
    private LocalDateTime date(String value,int index){
        try{return s(value).length()==10?LocalDate.parse(s(value)).atStartOfDay():LocalDateTime.parse(s(value).replace('T',' '),TIME);}
        catch(Exception error){throw new IllegalArgumentException("第"+index+"行收款时间须为YYYY-MM-DD或YYYY-MM-DD HH:mm:ss");}
    }
    private Map<String,Object> prepare(Command command,UserDTO actor){
        if(command==null || command.rows==null || command.rows.isEmpty() || command.rows.size()>1000)throw new IllegalArgumentException("请提交1到1000行收款模板数据");
        LinkedHashMap<String,ReceiptAddDTO> groups=new LinkedHashMap<>();List<Map<String,Object>> references=new ArrayList<>();int index=0;
        for(Line line:command.rows){
            index++;if(line==null)throw new IllegalArgumentException("第"+index+"行不能为空");
            String number=s(line.number),customer=reference("customer",line.customerNumber,actor.getFrameId(),"第"+index+"行客户"),account=reference("account",line.accountNumber,actor.getFrameId(),"第"+index+"行账户");LocalDateTime time=date(line.date,index);
            ReceiptAddDTO draft=groups.get(number);
            if(draft==null){draft=new ReceiptAddDTO();draft.setNumber(number);draft.setTime(time);draft.setCustomer(customer);draft.setData(s(line.remark));draft.setFile(Collections.emptyList());draft.setInfo(new ArrayList<>());groups.put(number,draft);}
            else if(!draft.getCustomer().equals(customer) || !draft.getTime().equals(time) || !draft.getData().equals(s(line.remark)))throw new IllegalArgumentException("同一收款单编号的客户、时间和单据备注必须一致："+number);
            ReceiptSettlementDetailDTO detail=new ReceiptSettlementDetailDTO();detail.setAccount(account);detail.setAmount(line.money);detail.setSettle(s(line.settle));detail.setData(s(line.lineRemark));draft.getInfo().add(detail);
            Map<String,Object> ref=new LinkedHashMap<>();ref.put("number",number);ref.put("customerNumber",s(line.customerNumber));ref.put("customer",db.queryForObject("SELECT name FROM customer WHERE id=?",String.class,customer));ref.put("accountNumber",s(line.accountNumber));ref.put("account",db.queryForObject("SELECT name FROM account WHERE id=?",String.class,account));ref.put("money",line.money);references.add(ref);
        }
        if(groups.size()>100)throw new IllegalArgumentException("一次最多导入100张收款草稿");BigDecimal cash=BigDecimal.ZERO;
        for(ReceiptAddDTO draft:groups.values()){
            drafts.fields(draft,actor.getFrameId(),true);
            if(db.queryForObject("SELECT COUNT(*) FROM imy WHERE number=?",Integer.class,draft.getNumber())>0)throw new IllegalArgumentException("收款单编号已存在："+draft.getNumber());
            if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,draft.getTime())>0)throw new IllegalArgumentException("收款日期已结账："+draft.getNumber());cash=cash.add(draft.getTotal());
        }
        Map<String,Object> result=new LinkedHashMap<>();result.put("documents",new ArrayList<>(groups.values()));result.put("documentCount",groups.size());result.put("lineCount",command.rows.size());result.put("cash",cash);result.put("references",references);
        try{String raw=actor.getId()+":"+actor.getFrameId()+":"+mapper.writeValueAsString(result);StringBuilder hash=new StringBuilder();for(byte value:MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8)))hash.append(String.format("%02x",value&255));result.put("version",hash.toString());}
        catch(Exception error){throw new IllegalStateException("收款导入预览版本生成失败",error);}
        return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> preview(Command command){return prepare(command,actor());}
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    @SuppressWarnings("unchecked")
    public Map<String,Object> save(Command command){
        UserDTO actor=actor();db.update("INSERT INTO psi_document_write_lock(scope) VALUES('imy') ON DUPLICATE KEY UPDATE scope='imy'");db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='imy' FOR UPDATE",String.class);
        Map<String,Object> plan=prepare(command,actor);
        if(command.version==null || !command.version.equals(plan.get("version")))throw new IllegalArgumentException("模板数据或基础资料已变化，请重新预览核对后导入");
        List<String> ids=new ArrayList<>();for(ReceiptAddDTO draft:(List<ReceiptAddDTO>)plan.get("documents"))ids.add(drafts.createLegacy(draft));
        Map<String,Object> result=new LinkedHashMap<>();result.put("ids",ids);result.put("documentCount",ids.size());result.put("lineCount",plan.get("lineCount"));result.put("cash",plan.get("cash"));result.put("summary","收款草稿已保存；尚未入账，请打开单据核对后确认收款");return result;
    }
    private String cell(Cell cell,int index){
        if(cell==null || cell.getCellType()==CellType.BLANK)return "";
        if(cell.getCellType()==CellType.FORMULA || cell.getCellType()==CellType.ERROR || cell.getCellType()==CellType.BOOLEAN)throw new IllegalArgumentException("模板不能包含公式、错误或布尔单元格");
        if(index==1 && cell.getCellType()==CellType.NUMERIC && DateUtil.isCellDateFormatted(cell))return cell.getDateCellValue().toInstant().atZone(ZoneId.systemDefault()).toLocalDateTime().format(TIME);
        return new DataFormatter(Locale.ROOT).formatCellValue(cell).trim();
    }
    public Command read(MultipartFile file){
        actor();
        if(file==null || file.isEmpty() || file.getSize()>5L*1024*1024)throw new IllegalArgumentException("请选择不超过5MiB的收款Excel模板");
        try(Workbook workbook=WorkbookFactory.create(file.getInputStream())){
            if(workbook.getNumberOfSheets()==0)throw new IllegalArgumentException("模板缺少数据工作表");Sheet sheet=workbook.getSheetAt(0);Row head=sheet.getRow(0);
            for(int index=0;index<HEADERS.length;index++)if(head==null || !HEADERS[index].equals(cell(head.getCell(index),index)))throw new IllegalArgumentException("模板表头不匹配，请使用本页下载的收款模板");
            if(sheet.getLastRowNum()>1000)throw new IllegalArgumentException("模板最多1000行数据，请移除多余行后重试");
            Command command=new Command();command.rows=new ArrayList<>();
            for(int index=1;index<=sheet.getLastRowNum();index++){
                Row row=sheet.getRow(index);if(row==null)continue;String[] values=new String[HEADERS.length];boolean empty=true;
                for(int column=0;column<values.length;column++){values[column]=cell(row.getCell(column),column);if(!values[column].isEmpty())empty=false;}
                if(empty)continue;
                for(int column=HEADERS.length;column<row.getLastCellNum();column++)if(!cell(row.getCell(column),column).isEmpty())throw new IllegalArgumentException("第"+(index+1)+"行包含模板之外的数据列");
                Line line=new Line();line.number=values[0];line.date=values[1];line.customerNumber=values[2];line.accountNumber=values[3];
                try{
                    if(values[4].contains(",") && !values[4].matches("[0-9]{1,3}(,[0-9]{3})+(\\.[0-9]+)?"))throw new IllegalArgumentException();
                    line.money=new BigDecimal(values[4].replace(",",""));
                }catch(Exception error){throw new IllegalArgumentException("第"+(index+1)+"行结算金额无效，请使用数字或规范千分位格式");}
                line.settle=values[5];line.remark=values[6];line.lineRemark=values[7];command.rows.add(line);
            }
            if(command.rows.isEmpty())throw new IllegalArgumentException("模板没有收款数据，请保留表头并填写客户编号、账户编号及金额");return command;
        }catch(IllegalArgumentException error){throw error;}catch(Exception error){throw new IllegalArgumentException("无法读取收款模板，请使用本页下载的有效Excel文件");}
    }
    public byte[] template(){
        actor();
        try(Workbook workbook=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            Sheet sheet=workbook.createSheet("收款模板");Row head=sheet.createRow(0);CellStyle text=workbook.createCellStyle();text.setDataFormat(workbook.createDataFormat().getFormat("@"));
            for(int index=0;index<HEADERS.length;index++){head.createCell(index).setCellValue(HEADERS[index]);sheet.setColumnWidth(index,24*256);sheet.setDefaultColumnStyle(index,text);}sheet.createFreezePane(0,1);
            Sheet guide=workbook.createSheet("填写说明");String[] instructions={"先填写收款模板工作表，再上传预览；确认后只保存草稿，不会自动增加账户余额或核销销售。","客户编号来自客户管理；结算账户编号来自账户管理。填写当前组织或共享资料的业务编号，不是内部ID。","每行是一条收款账户明细。同一收款单编号合并为一张单，其客户、时间和单据备注必须一致。","收款单编号必填且不可重复；收款时间为YYYY-MM-DD或YYYY-MM-DD HH:mm:ss，日期不完整或已结账不能导入。","金额必须大于0，最多8位整数和4位小数；每单最多200行，一次最多100张单据或1000行。","结算号、单据备注、明细备注可留空。不要修改表头，不要填写公式或附件地址。","预览显示实际解析的客户、账户及合计。修改数据或基础资料后请重新预览，整批任一行失败均不保存。"};
            for(int index=0;index<instructions.length;index++)guide.createRow(index).createCell(0).setCellValue(instructions[index]);guide.setColumnWidth(0,100*256);
            workbook.write(out);return out.toByteArray();
        }catch(IOException error){throw new IllegalStateException("收款模板生成失败，请重试",error);}
    }
}
