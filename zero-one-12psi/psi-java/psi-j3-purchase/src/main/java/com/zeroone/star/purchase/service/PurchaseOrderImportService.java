package com.zeroone.star.purchase.service;

import com.zeroone.star.project.dto.j3.purchase.*;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import java.io.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

/** Explicit template -> existing draft validation; a workbook never updates existing orders. */
@Service
public class PurchaseOrderImportService {
    private static final String RESOURCE="/purchase-order/import-bor";
    private static final String[] HEADERS={"供应商编号","单据日期","单据编号","单据金额(自动计算)","实际金额(自动计算)","关联人员编号","到货日期","物流信息","单据备注","商品编号","辅助属性","单位","仓库编号","单价","数量","折扣率(%)","折扣额(自动计算)","金额(自动计算)","税率(%)","税额(自动计算)","价税合计(自动计算)","商品备注"};
    private final PurchaseDocumentAccess access;
    private final PurchaseOrderDraftService drafts;
    private final JdbcTemplate db;
    public PurchaseOrderImportService(PurchaseDocumentAccess access,PurchaseOrderDraftService drafts,JdbcTemplate db){this.access=access;this.drafts=drafts;this.db=db;}
    public byte[] template() throws IOException {
        access.authorize(RESOURCE);
        try(Workbook book=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            Sheet sheet=book.createSheet("采购订单导入");sheet.createRow(0).createCell(0).setCellValue("采购订单导入模板 V1（先阅读填写说明，从第3行填写）");Row headers=sheet.createRow(1);
            CellStyle text=book.createCellStyle();text.setDataFormat(book.createDataFormat().getFormat("@"));
            for(int i=0;i<HEADERS.length;i++){headers.createCell(i).setCellValue(HEADERS[i]);sheet.setDefaultColumnStyle(i,text);sheet.setColumnWidth(i,22*256);}sheet.createFreezePane(3,2);
            String[] notes={"第1、2行不要修改，第3行开始每行填写一条商品。此模板没有可导入的演示记录。",
                "先在基础资料创建供应商、商品、仓库、关联人员；填写资料编号（也支持系统ID），不要填写名称。编号使用文本格式保留前导零。",
                "第一行必填：供应商编号、单据日期、单据编号、到货日期、商品编号、单位、仓库编号、单价、数量。",
                "同一订单后续商品可留空前9列；按单据编号分组，每张订单向一家供应商采购，不同供应商使用不同订单编号。同编号非空表头必须一致。",
                "供应商必须存在且与商品建立已启用的供货关系，请先在采购订单开单页维护供货关系。不会自动创建商品或供货关系。",
                "单据和到货日期格式为yyyy-MM-dd，例如2026-11-15；可使用Excel日期单元格。到货日期不能早于单据日期，已结账期间不能导入。",
                "折扣率为减免百分比：0不减免、10减免10%；税率13为13%。可留空为0，支持Excel百分比单元格。最多两位小数。",
                "自动计算的金额列留空，服务端按单价/数量/折扣/税率重算，单价和数量最多四位小数；不采信填入的合计。",
                "商品辅助属性和单位必须是商品实际配置；仓库、人员、供应商必须属于当前组织或公共资料。组织与制单人来自当前账号。",
                "仅新建未审核订单草稿，不改变库存或资金。导入后在采购订单报表核对审核，再生成收货采购单并核对审核入库。",
                "单文件最大5MiB、1000条明细、100张订单，每张订单最多200条商品。公式和错误单元格不支持，请粘贴为值。",
                "已存在单据编号整文件拒绝，不覆盖任何原单；任意一行或一张订单失败均整文件回滚，按错误行号修正后重新上传。"};
            Sheet guide=book.createSheet("填写说明");guide.setColumnWidth(0,120*256);for(int i=0;i<notes.length;i++)guide.createRow(i).createCell(0).setCellValue(notes[i]);book.write(out);return out.toByteArray();
        }
    }
    private String cell(Row row,int index){
        Cell value=row==null?null:row.getCell(index);if(value==null)return "";
        if(value.getCellType()==CellType.FORMULA || value.getCellType()==CellType.ERROR)throw new IllegalArgumentException("不支持公式或错误单元格，请粘贴为值");
        if(value.getCellType()==CellType.NUMERIC && DateUtil.isCellDateFormatted(value))return value.getLocalDateTimeCellValue().toLocalDate().toString();
        return new DataFormatter(Locale.ROOT).formatCellValue(value).trim();
    }
    private BigDecimal number(String value,String label,boolean optional){
        if(optional && value.isEmpty())return BigDecimal.ZERO;
        try{return new BigDecimal(value);}catch(Exception error){throw new IllegalArgumentException(label+"必须填写有效数字");}
    }
    private BigDecimal rate(String value,String label){return number(value.endsWith("%")?value.substring(0,value.length()-1):value,label,true);}
    private LocalDate date(String value,String label){try{return LocalDate.parse(value);}catch(Exception error){throw new IllegalArgumentException(label+"必须为有效的yyyy-MM-dd日期");}}
    private String reference(String table,String value,String frame,String label,boolean optional){
        if(optional && value.isEmpty())return null;
        String query="SELECT id FROM `"+table+"` WHERE (id=? OR number=?)";
        List<String> ids=frame==null?db.queryForList(query,String.class,value,value):db.queryForList(query+" AND frame IN ('0',?)",String.class,value,value,frame);
        if(value.isEmpty() || ids.size()!=1)throw new IllegalArgumentException(label+"编号不存在、不唯一或不属于当前组织");return ids.get(0);
    }
    @Transactional(rollbackFor=Exception.class)
    public String importFile(MultipartFile file) throws IOException {
        String frame=access.authorize(RESOURCE).getFrameId();
        if(file==null || file.isEmpty() || file.getSize()>5*1024*1024)throw new IllegalArgumentException("请选择非空Excel文件，最大5MiB");
        Map<String,PurchaseOrderAddDTO> documents=new LinkedHashMap<>();Map<String,String[]> headers=new HashMap<>();Map<String,Integer> firstRows=new HashMap<>();int lines=0;
        try(InputStream in=file.getInputStream();Workbook book=WorkbookFactory.create(in)){
            if(book.getNumberOfSheets()==0)throw new IllegalArgumentException("Excel没有数据页");Sheet sheet=book.getSheetAt(0);
            for(int i=0;i<HEADERS.length;i++)if(!HEADERS[i].equals(cell(sheet.getRow(1),i)))throw new IllegalArgumentException("第2行表头不匹配，请重新下载采购订单导入模板");
            if(sheet.getLastRowNum()>1001)throw new IllegalArgumentException("单文件最多1000条明细");String current=null;
            for(int rowIndex=2;rowIndex<=sheet.getLastRowNum();rowIndex++){
                int line=rowIndex+1;
                try{
                    String[] values=new String[HEADERS.length];boolean empty=true;for(int i=0;i<values.length;i++){values[i]=cell(sheet.getRow(rowIndex),i);empty&=values[i].isEmpty();}if(empty)continue;
                    if(!values[2].isEmpty())current=values[2];if(current==null)throw new IllegalArgumentException("第一条明细必须填写单据编号");
                    PurchaseOrderAddDTO request=documents.get(current);
                    if(request==null){
                        if(documents.size()>=100)throw new IllegalArgumentException("单文件最多100张订单");
                        request=new PurchaseOrderAddDTO();request.setNumber(current);request.setSupplier(reference("supplier",values[0],frame,"供应商",false));request.setTime(date(values[1],"单据日期"));request.setArrival(date(values[6],"到货日期"));
                        request.setPeople(reference("people",values[5],frame,"关联人员",true));request.setLogistics(values[7]);request.setData(values[8]);request.setSource("0");request.setFile("[]");request.setPurchaseOrderInfoDTOList(new ArrayList<>());
                        documents.put(current,request);headers.put(current,values.clone());firstRows.put(current,line);
                    }else for(int i:new int[]{0,1,5,6,7,8})if(!values[i].isEmpty() && !values[i].equals(headers.get(current)[i]))throw new IllegalArgumentException("同一单据的表头信息不一致");
                    if(request.getPurchaseOrderInfoDTOList().size()>=200)throw new IllegalArgumentException("每张订单最多200条商品");
                    PurchaseOrderInfoDTO item=new PurchaseOrderInfoDTO();item.setGoods(reference("goods",values[9],null,"商品",false));item.setAttr(values[10]);item.setUnit(values[11]);item.setWarehouse(reference("warehouse",values[12],frame,"仓库",false));item.setPrice(number(values[13],"单价",false));item.setNums(number(values[14],"数量",false));item.setDiscount(rate(values[15],"折扣率"));item.setTax(rate(values[18],"税率"));item.setData(values[21]);
                    // Validate each line before grouping so validation errors retain its Excel row.
                    if(item.getPrice().signum()<0 || item.getNums().signum()<=0 || item.getPrice().stripTrailingZeros().scale()>4 || item.getNums().stripTrailingZeros().scale()>4)throw new IllegalArgumentException("单价不得为负、数量必须大于0，最多四位小数");
                    for(BigDecimal value:Arrays.asList(item.getDiscount(),item.getTax()))if(value.signum()<0 || value.compareTo(new BigDecimal("100"))>0 || value.stripTrailingZeros().scale()>2)throw new IllegalArgumentException("折扣率和税率必须在0到100之间且最多两位小数");
                    request.getPurchaseOrderInfoDTOList().add(item);lines++;
                }catch(IllegalArgumentException error){throw new IllegalArgumentException("第"+line+"行："+error.getMessage(),error);}
            }
        }catch(IllegalArgumentException error){throw error;}catch(Exception error){throw new IllegalArgumentException("Excel文件无法读取，请使用下载的模板保存后重试");}
        if(documents.isEmpty())throw new IllegalArgumentException("Excel没有可导入明细，请从第3行开始填写");
        for(Map.Entry<String,PurchaseOrderAddDTO> entry:documents.entrySet())try{
            if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=?",Integer.class,entry.getValue().getTime())>0)throw new IllegalArgumentException("订单日期已结账，不能导入");
            drafts.createImported(entry.getValue());
        }catch(RuntimeException error){throw new IllegalArgumentException("第"+firstRows.get(entry.getKey())+"行起的订单保存失败："+error.getMessage(),error);}
        return "已导入"+documents.size()+"张采购订单、"+lines+"条明细（未审核草稿）";
    }
}
