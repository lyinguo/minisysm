package com.zeroone.star.purchase.service;

import com.zeroone.star.project.dto.j3.purchase.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import javax.validation.Validator;
import java.io.*;
import java.math.BigDecimal;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** Explicit workbook schema; every workbook is a single draft-creation transaction. */
@Service
public class PurchaseImportService {
    private static final String[] HEADERS={"供应商编号","单据日期","单据编号","单据金额(自动计算)","实际金额(自动计算)","实付金额","结算账户编号","关联人员编号","物流信息","单据备注","商品编号","辅助属性","单位","仓库编号","批次号","生产日期","单价","数量","序列号(JSON数组)","折扣率(%)","折扣额(自动计算)","金额(自动计算)","税率(%)","税额(自动计算)","价税合计(自动计算)","商品备注"};
    private final PurchaseDocumentAccess access;
    private final PurchaseNoteService drafts;
    private final JdbcTemplate db;
    private final PurchaseDraftAmounts amounts;
    private final Validator validator;
    public PurchaseImportService(PurchaseDocumentAccess access,PurchaseNoteService drafts,JdbcTemplate db,PurchaseDraftAmounts amounts,Validator validator) {
        this.access=access;this.drafts=drafts;this.db=db;this.amounts=amounts;this.validator=validator;
    }

    public byte[] template() throws IOException {
        access.authorize("/purchase-note/import");
        try(Workbook book=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            Sheet sheet=book.createSheet("采购导入");sheet.createRow(0).createCell(0).setCellValue("采购单导入模板 V1（先阅读填写说明，第3行开始填写）");
            Row header=sheet.createRow(1);
            CellStyle text=book.createCellStyle();text.setDataFormat(book.createDataFormat().getFormat("@"));
            for(int i=0;i<HEADERS.length;i++) { header.createCell(i).setCellValue(HEADERS[i]);sheet.setColumnWidth(i,20*256);sheet.setDefaultColumnStyle(i,text); }
            sheet.createFreezePane(3,2);
            Sheet guide=book.createSheet("填写说明");
            String[] notes={
                "每行是一条商品明细；第1、2行不可修改，第3行开始填写。模板不包含可导入的示例。",
                "先在供应商、商品、仓库管理中建立资料，填写其编号（也支持系统ID），不要填写名称；编号列使用文本格式，保留前导零。",
                "第一条明细必填：供应商编号、单据日期、单据编号、商品编号、单位、仓库编号、单价、数量。",
                "同一单据的后续明细可留空前10列；多个单据请填写不同单据编号及其供应商、日期。相同编号的表头信息必须一致。",
                "日期格式：2026-11-15 或 2026-11-15 13:47:00。实付金额默认0；大于0时必须填写本组织结算账户编号。",
                "折扣率表示减免百分比：0不打折、10表示减免10%；税率13表示13%。最多两位小数；Excel百分比单元格也可使用。",
                "所有标注自动计算的金额列留空，服务端按单价、数量、折扣和税率重算，不采信填入的合计。单价和数量最多四位小数。",
                "普通商品批次、生产日期、序列号可留空；批次商品填写批次及生产日期，序列商品使用JSON数组，例如[\"SN001\",\"SN002\"]。",
                "辅助属性填写该商品实际属性名称。多单位商品须填写其配置的真实单位。组织和制单人由当前登录账号确定。",
                "仅创建草稿，不自动审核、不改变库存和资金。导入后请到采购单报表核对明细，再核对、审核。",
                "单文件最多5MiB、1000条明细、100张单据。任意一行或单据失败则整文件不保存，按错误行号修正后重新上传。",
                "已存在的单据编号会整批拒绝，不覆盖原单据。请使用新编号；空文件、错误表头、公式单元格和损坏文件会被拒绝。"};
            for(int i=0;i<notes.length;i++)guide.createRow(i).createCell(0).setCellValue(notes[i]);
            guide.setColumnWidth(0,120*256);book.write(out);return out.toByteArray();
        }
    }

    private String cell(Row row,int index) {
        Cell value=row==null?null:row.getCell(index);
        if(value==null)return "";
        if(value.getCellType()==CellType.FORMULA || value.getCellType()==CellType.ERROR)throw new IllegalArgumentException("不支持公式或错误单元格，请粘贴为值");
        if(value.getCellType()==CellType.NUMERIC && DateUtil.isCellDateFormatted(value))return value.getLocalDateTimeCellValue().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        return new DataFormatter(Locale.ROOT).formatCellValue(value).trim();
    }
    private BigDecimal decimal(String value,String label,boolean optional) {
        if(value.isEmpty() && optional)return BigDecimal.ZERO;
        try { return new BigDecimal(value); } catch(NumberFormatException error) { throw new IllegalArgumentException(label+"必须填写有效数字"); }
    }
    private BigDecimal rate(String value,String label) {
        return decimal(value.endsWith("%")?value.substring(0,value.length()-1):value,label,true);
    }
    private String reference(String table,String value,String frame,String label,boolean optional) {
        if(value.isEmpty() && optional)return null;
        String query="SELECT id FROM `"+table+"` WHERE (id=? OR number=?)";
        List<String> ids=frame==null?db.queryForList(query,String.class,value,value):db.queryForList(query+" AND frame IN ('0',?)",String.class,value,value,frame);
        if(ids.size()!=1)throw new IllegalArgumentException(label+"编号不存在、不唯一或不属于当前组织");
        return ids.get(0);
    }
    private void serial(String value) {
        try {
            Object parsed=new ObjectMapper().readValue(value,Object.class);
            if(!(parsed instanceof List))throw new IllegalArgumentException();
            Set<String> seen=new HashSet<>();
            for(Object item:(List<?>)parsed)if(!(item instanceof String) || ((String)item).trim().isEmpty() || !seen.add((String)item))throw new IllegalArgumentException();
        } catch(Exception error) { throw new IllegalArgumentException("序列号必须是无重复非空字符串的JSON数组"); }
    }

    @Transactional(rollbackFor=Exception.class)
    public String importFile(MultipartFile file) throws IOException {
        String frame=access.authorize("/purchase-note/import").getFrameId();
        if(file==null || file.isEmpty() || file.getSize()>5*1024*1024)throw new IllegalArgumentException("请选择非空Excel文件，最大5MiB");
        Map<String,PurchaseNoteAddDTO> documents=new LinkedHashMap<>();
        Map<String,String[]> headers=new HashMap<>();
        Map<String,Integer> firstRows=new HashMap<>();
        int lines=0;
        try(InputStream in=file.getInputStream();Workbook book=WorkbookFactory.create(in)) {
            if(book.getNumberOfSheets()==0)throw new IllegalArgumentException("Excel没有数据页");
            Sheet sheet=book.getSheetAt(0);
            for(int i=0;i<HEADERS.length;i++)if(!HEADERS[i].equals(cell(sheet.getRow(1),i)))throw new IllegalArgumentException("第2行表头不匹配，请重新下载采购导入模板");
            if(sheet.getLastRowNum()>1001)throw new IllegalArgumentException("单文件最多1000条明细");
            String current=null;
            for(int index=2;index<=sheet.getLastRowNum();index++) {
                int lineNumber=index+1;
                try {
                    String[] values=new String[26];boolean empty=true;
                    for(int i=0;i<26;i++) {values[i]=cell(sheet.getRow(index),i);if(!values[i].isEmpty())empty=false;}
                    if(empty)continue;
                    if(!values[2].isEmpty())current=values[2];
                    if(current==null)throw new IllegalArgumentException("第一条明细必须填写单据编号");
                    PurchaseNoteAddDTO request=documents.get(current);
                    if(request==null) {
                        if(documents.size()>=100)throw new IllegalArgumentException("单文件最多100张采购单");
                        PurchaseNoteBuyDTO head=new PurchaseNoteBuyDTO();
                        head.setSupplier(reference("supplier",values[0],frame,"供应商",false));head.setTime(values[1]);head.setNumber(current);
                        head.setMoney(decimal(values[5],"实付金额",true));head.setCost(BigDecimal.ZERO);head.setTotal(BigDecimal.ZERO);head.setActual(BigDecimal.ZERO);
                        head.setAccount(reference("account",values[6],frame,"结算账户",true));head.setPeople(reference("people",values[7],frame,"关联人员",true));
                        head.setLogistics(values[8]);head.setData(values[9]);head.setSource("0");head.setFile("");
                        request=new PurchaseNoteAddDTO();request.setPurchaseNoteBuyDTO(head);request.setPurchaseNoteInfoDTOS(new ArrayList<>());
                        documents.put(current,request);headers.put(current,values.clone());firstRows.put(current,lineNumber);
                    } else {
                        for(int i:new int[]{0,1,5,6,7,8,9})if(!values[i].isEmpty() && !values[i].equals(headers.get(current)[i]))throw new IllegalArgumentException("同一单据的表头信息不一致");
                    }
                    PurchaseNoteInfoDTO item=new PurchaseNoteInfoDTO();item.setSource("0");
                    item.setGoods(reference("goods",values[10],null,"商品",false));item.setAttr(values[11]);item.setUnit(values[12]);
                    item.setWarehouse(reference("warehouse",values[13],frame,"仓库",false));item.setBatch(values[14]);item.setMfd(values[15]);
                    item.setPrice(decimal(values[16],"单价",false));item.setNums(decimal(values[17],"数量",false));
                    item.setSerial(values[18].isEmpty()?"[]":values[18]);serial(item.getSerial());
                    item.setDiscount(rate(values[19],"折扣率"));item.setTax(rate(values[22],"税率"));item.setData(values[25]);
                    PurchaseNoteAddDTO single=new PurchaseNoteAddDTO();single.setPurchaseNoteBuyDTO(request.getPurchaseNoteBuyDTO());single.setPurchaseNoteInfoDTOS(Collections.singletonList(item));
                    amounts.calculate(single);
                    java.util.Set<javax.validation.ConstraintViolation<PurchaseNoteInfoDTO>> invalidLine=validator.validate(item);
                    if(!invalidLine.isEmpty())throw new IllegalArgumentException(invalidLine.iterator().next().getMessage());
                    request.getPurchaseNoteInfoDTOS().add(item);lines++;
                } catch(IllegalArgumentException error) { throw new IllegalArgumentException("第"+lineNumber+"行："+error.getMessage()); }
            }
        } catch(IllegalArgumentException error) { throw error; }
        catch(Exception error) { throw new IllegalArgumentException("Excel文件无法读取，请使用下载的模板保存后重试"); }
        if(documents.isEmpty())throw new IllegalArgumentException("Excel没有可导入的明细，请从第3行开始填写");
        for(Map.Entry<String,PurchaseNoteAddDTO> entry:documents.entrySet()) {
            try {
                // Canonical percentage input deliberately ignores legacy amount hints.
                amounts.calculate(entry.getValue());
                java.util.Set<javax.validation.ConstraintViolation<PurchaseNoteAddDTO>> violations=validator.validate(entry.getValue());
                if(!violations.isEmpty())throw new IllegalArgumentException(violations.iterator().next().getMessage());
                drafts.addImportedPurchaseNote(entry.getValue());
            } catch(RuntimeException error) { throw new IllegalArgumentException("第"+firstRows.get(entry.getKey())+"行起的采购单保存失败："+error.getMessage(),error); }
        }
        return "成功导入"+documents.size()+"张采购草稿，共"+lines+"条明细；请核对后审核";
    }
}
