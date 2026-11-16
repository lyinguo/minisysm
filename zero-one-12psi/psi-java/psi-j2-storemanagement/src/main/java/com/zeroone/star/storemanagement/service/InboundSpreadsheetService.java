package com.zeroone.star.storemanagement.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j2.store.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.*;
import org.springframework.web.server.ResponseStatusException;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import cn.hutool.json.JSONArray;
import java.io.*;
import java.math.BigDecimal;
import java.time.*;
import java.time.format.*;
import java.security.MessageDigest;
import java.util.*;

/** Business-code spreadsheets share the same validated drafts and stock lifecycle. */
@Service
public class InboundSpreadsheetService {
    private static final String[] HEADERS={"入库单号","单据日期","单据类型","商品编号","入库仓库编号","基本单位","数量","单位成本","辅助属性","批次号","生产日期","序列号JSON","单据备注","明细备注"};
    private static final DateTimeFormatter TIME=DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss").withResolverStyle(ResolverStyle.STRICT);
    private final JdbcTemplate db;private final StockDocumentAccess access;private final IOtherInService drafts;private final StockDocumentWriteLock writes;private final ObjectMapper mapper;private final WarehousePostingProof proofs;
    public InboundSpreadsheetService(JdbcTemplate db,StockDocumentAccess access,IOtherInService drafts,StockDocumentWriteLock writes,ObjectMapper mapper){this.db=db;this.access=access;this.drafts=drafts;this.writes=writes;this.mapper=mapper;this.proofs=new WarehousePostingProof(db);}
    private String text(Object value){return value==null?"":value.toString();}
    private int integer(Object value){return value==null?0:value instanceof Boolean?((Boolean)value?1:0):((Number)value).intValue();}
    private UserDTO actor(){UserDTO user=access.authorize("entry","create");access.creationFrame(user,user.getFrameId());return user;}
    private String cell(Cell cell,int column){
        if(cell==null || cell.getCellType()==CellType.BLANK)return "";
        if(cell.getCellType()==CellType.FORMULA || cell.getCellType()==CellType.ERROR || cell.getCellType()==CellType.BOOLEAN)throw new IllegalArgumentException("模板不能包含公式、错误或布尔单元格");
        if(cell.getCellType()==CellType.NUMERIC){
            if((column==1 || column==10) && DateUtil.isCellDateFormatted(cell)){LocalDateTime value=cell.getDateCellValue().toInstant().atZone(ZoneId.systemDefault()).toLocalDateTime();return column==10?value.toLocalDate().toString():value.format(TIME);}
            if(column==0 || column==3 || column==4)throw new IllegalArgumentException("单据编号、商品编号和仓库编号必须为文本，避免前导零或长编号丢失");
            return BigDecimal.valueOf(cell.getNumericCellValue()).stripTrailingZeros().toPlainString();
        }
        String value=cell.getStringCellValue().trim();if(value.length()>10000)throw new IllegalArgumentException("单元格内容过长");return value;
    }
    private Map<String,Object> reference(String table,String code,String frame){
        String scope="warehouse".equals(table)?" AND frame IN ('0',?)":"";
        List<Map<String,Object>> matches=scope.isEmpty()?db.queryForList("SELECT id,number,name,unit,units,type,batch,serial FROM goods WHERE number=?",code):db.queryForList("SELECT id,number,name,frame FROM warehouse WHERE number=?"+scope,code,frame);
        if(code.isEmpty() || matches.size()!=1)throw new IllegalArgumentException((scope.isEmpty()?"商品":"仓库")+"编号不存在、不属于当前组织或不唯一："+code);return matches.get(0);
    }
    private LocalDateTime time(String value){return value.length()==10?LocalDate.parse(value).atStartOfDay():LocalDateTime.parse(value.replace('T',' '),TIME);}
    @SuppressWarnings("unchecked")
    private Map<String,Object> prepare(MultipartFile file,UserDTO actor){
        if(file==null || file.isEmpty() || file.getSize()>5L*1024*1024)throw new IllegalArgumentException("请选择不超过5MiB的入库Excel模板");
        LinkedHashMap<String,OtherInListAddDTO> groups=new LinkedHashMap<>();List<Map<String,Object>> references=new ArrayList<>();Set<String> serials=new HashSet<>();
        try(InputStream input=file.getInputStream();Workbook book=WorkbookFactory.create(input)){
            Sheet sheet=book.getSheetAt(0);Row head=sheet.getRow(0);
            for(int c=0;c<HEADERS.length;c++)if(head==null || !HEADERS[c].equals(cell(head.getCell(c),c)))throw new IllegalArgumentException("模板表头不匹配，请下载当前入库模板");
            if(sheet.getLastRowNum()>1000)throw new IllegalArgumentException("每次最多1000行商品明细");
            for(int index=1;index<=sheet.getLastRowNum();index++){
                Row row=sheet.getRow(index);if(row==null)continue;String[] values=new String[HEADERS.length];boolean empty=true;
                for(int c=0;c<values.length;c++){values[c]=cell(row.getCell(c),c);if(!values[c].isEmpty())empty=false;}if(empty)continue;
                for(int c=HEADERS.length;c<row.getLastCellNum();c++)if(!cell(row.getCell(c),c).isEmpty())throw new IllegalArgumentException("请勿在模板之外添加其他数据列");
                try {
                    LocalDateTime date=time(values[1]);int type="其他入库".equals(values[2])||"0".equals(values[2])?0:"盘盈".equals(values[2])||"1".equals(values[2])?1:-1;
                    OtherInListAddDTO draft=groups.get(values[0]);
                    if(draft==null){draft=new OtherInListAddDTO();draft.setNumber(values[0]);draft.setTime(date);draft.setType(type);draft.setData(values[12]);draft.setSupplier("");draft.setPeople("");draft.setFrame(actor.getFrameId());draft.setUser(actor.getId());draft.setExamine(0);draft.setCheck(0);draft.setCse(3);draft.setTotal(BigDecimal.ZERO);draft.setCost(BigDecimal.ZERO);draft.setFile(Collections.emptyList());draft.setMore(Collections.emptyMap());draft.setCostDTOList(Collections.emptyList());draft.setOtherInListDetailInfoDTOList(new ArrayList<>());groups.put(values[0],draft);}
                    else if(!draft.getTime().equals(date) || draft.getType()!=type || !draft.getData().equals(values[12]))throw new IllegalArgumentException("同一单号的日期、类型、单据备注必须一致");
                    if(groups.size()>100 || draft.getOtherInListDetailInfoDTOList().size()>=200)throw new IllegalArgumentException("每批最多100张单据，每张最多200行明细");
                    Map<String,Object> product=reference("goods",values[3],actor.getFrameId()),warehouse=reference("warehouse",values[4],actor.getFrameId());
                    OtherInListDetailInfoDTO detail=new OtherInListDetailInfoDTO();detail.setGoods(text(product.get("id")));detail.setName(text(product.get("name")));detail.setNumber(values[3]);detail.setWarehouse(text(warehouse.get("id")));detail.setUnit(values[5]);detail.setNums(new BigDecimal(values[6]));detail.setPrice(new BigDecimal(values[7]));detail.setAttr(values[8]);detail.setBatch(values[9]);detail.setMfd(values[10].isEmpty()?null:LocalDate.parse(values[10]));detail.setSerial(values[11].isEmpty()?"[]":values[11]);detail.setData(values[13]);
                    if(integer(product.get("batch"))==1 && (detail.getBatch().isEmpty() || detail.getMfd()==null))throw new IllegalArgumentException("批次商品必须填写批次号和生产日期");
                    JSONArray numbers=new JSONArray(detail.getSerial());
                    if(integer(product.get("serial"))==1){
                        if(detail.getNums().compareTo(BigDecimal.valueOf(numbers.size()))!=0)throw new IllegalArgumentException("序列号数量必须与商品数量一致");
                        for(Object number:numbers){if(!(number instanceof String) || text(number).trim().isEmpty() || !serials.add(detail.getGoods()+":"+text(number).trim()) || db.queryForObject("SELECT COUNT(*) FROM serial WHERE goods=? AND number=?",Integer.class,detail.getGoods(),text(number).trim())!=0)throw new IllegalArgumentException("序列号为空、重复或已存在");}
                    }else if(!numbers.isEmpty())throw new IllegalArgumentException("非序列号商品不要填写序列号");
                    draft.getOtherInListDetailInfoDTOList().add(detail);
                    Map<String,Object> ref=new LinkedHashMap<>();ref.put("number",values[0]);ref.put("goods",product);ref.put("warehouse",warehouse);ref.put("quantity",detail.getNums());ref.put("price",detail.getPrice());ref.put("unit",detail.getUnit());references.add(ref);
                }catch(Exception error){throw new IllegalArgumentException("第"+(index+1)+"行："+(error.getMessage()==null?"格式无效":error.getMessage()));}
            }
        }catch(IllegalArgumentException error){throw error;}catch(Exception error){throw new IllegalArgumentException("无法读取入库模板，请使用本页下载的有效Excel文件");}
        if(groups.isEmpty())throw new IllegalArgumentException("模板没有商品明细，请保留表头并填写数据");
        BigDecimal total=BigDecimal.ZERO;
        for(OtherInListAddDTO draft:groups.values()){drafts.previewOtherInList(draft);proofs.requireOpenPeriod(draft.getTime());total=total.add(draft.getTotal());}
        Map<String,Object> result=new LinkedHashMap<>();result.put("documents",new ArrayList<>(groups.values()));result.put("references",references);result.put("documentCount",groups.size());result.put("lineCount",references.size());result.put("total",total);
        try{byte[] hash=MessageDigest.getInstance("SHA-256").digest(mapper.writeValueAsBytes(result));StringBuilder version=new StringBuilder();for(byte b:hash)version.append(String.format("%02x",b&255));result.put("version",version.toString());}catch(Exception error){throw new IllegalStateException("无法生成导入核对版本",error);}
        return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> preview(MultipartFile file){return prepare(file,actor());}
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    @SuppressWarnings("unchecked")
    public Map<String,Object> save(MultipartFile file,String version){
        UserDTO actor=actor();writes.lock("entry");Map<String,Object> plan=prepare(file,actor);
        // Lock the reviewed master rows in a deterministic order, then re-read
        // the plan. A changed business-code mapping cannot slip into the save.
        List<Map<String,Object>> references=(List<Map<String,Object>>)plan.get("references");
        for(String table:Arrays.asList("goods","warehouse")){
            SortedSet<String> ids=new TreeSet<>();for(Map<String,Object> ref:references)ids.add(text(((Map<String,Object>)ref.get(table)).get("id")));
            for(String id:ids)db.queryForList("SELECT id FROM "+table+" WHERE id=? FOR UPDATE",id);
        }
        plan=prepare(file,actor());
        if(version==null || !version.equals(plan.get("version")))throw new IllegalArgumentException("请先预览核对；文件、基础资料或制单组织变化后必须重新预览");
        List<String> ids=new ArrayList<>();for(OtherInListAddDTO draft:(List<OtherInListAddDTO>)plan.get("documents"))ids.add(drafts.saveOtherInList(draft).getData());
        Map<String,Object> result=new LinkedHashMap<>();result.put("ids",ids);result.put("documentCount",ids.size());result.put("lineCount",plan.get("lineCount"));result.put("total",plan.get("total"));result.put("summary","已保存入库草稿，尚未增加库存；请打开单据核对后审核");return result;
    }
    private byte[] workbook(String title,List<String> headers,List<List<Object>> values,List<String> guide){
        try(Workbook book=new XSSFWorkbook();ByteArrayOutputStream out=new ByteArrayOutputStream()){
            Sheet sheet=book.createSheet(title);Row head=sheet.createRow(0);CellStyle header=book.createCellStyle();Font font=book.createFont();font.setBold(true);header.setFont(font);header.setFillForegroundColor(IndexedColors.LIGHT_CORNFLOWER_BLUE.getIndex());header.setFillPattern(FillPatternType.SOLID_FOREGROUND);
            CellStyle text=book.createCellStyle();text.setDataFormat(book.createDataFormat().getFormat("@"));CellStyle number=book.createCellStyle();number.setDataFormat(book.createDataFormat().getFormat("0.0000"));
            for(int c=0;c<headers.size();c++){Cell cell=head.createCell(c);cell.setCellValue(headers.get(c));cell.setCellStyle(header);sheet.setColumnWidth(c,24*256);sheet.setDefaultColumnStyle(c,text);}sheet.createFreezePane(0,1);
            for(List<Object> line:values){Row row=sheet.createRow(sheet.getLastRowNum()+1);for(int c=0;c<line.size();c++){Cell cell=row.createCell(c);Object value=line.get(c);if(value instanceof BigDecimal){cell.setCellValue(((BigDecimal)value).doubleValue());cell.setCellStyle(number);}else cell.setCellValue(text(value));}}
            if(guide!=null){Sheet notes=book.createSheet("填写说明");notes.setColumnWidth(0,110*256);for(String line:guide)notes.createRow(notes.getPhysicalNumberOfRows()).createCell(0).setCellValue(line);}
            book.write(out);return out.toByteArray();
        }catch(IOException error){throw new IllegalStateException("Excel文件生成失败",error);}
    }
    public byte[] template(){actor();return workbook("入库模板",Arrays.asList(HEADERS),Collections.emptyList(),Arrays.asList("先填写入库模板，再上传预览并确认。确认只生成草稿，不会自动增加库存或生成采购应付。","用于盘盈、赠品等非采购入库。采购收货请使用采购入库流程。","商品编号、入库仓库编号来自商品管理和仓库管理的业务编号，必须填文本；不能填名称或内部ID。仓库需属于当前组织或共享。","同一入库单号合并为一张单据，日期、类型和单据备注必须一致。制单人及组织由当前登录账号确定。","单据日期填写YYYY-MM-DD或YYYY-MM-DD HH:mm:ss；单据类型填写其他入库或盘盈。已结账期间不可导入。","基本单位须与商品的基本单位一致；数量大于0，单位成本可为0，两者最多4位小数；成本由系统计算。","批次商品必须填写批次号及YYYY-MM-DD生产日期；序列号商品填写JSON字符串数组，例如[\"SN001\",\"SN002\"]，每件一个且不可重复。","辅助属性、非批次商品的批次/生产日期、非序列商品的序列号、单据备注和明细备注可留空。不要填公式。","每批最多100张单据/1000行，每单最多200行；任意一行失败全部不保存。基础资料变化后请重新预览。"));}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public byte[] export(String selected,boolean detail){
        UserDTO actor=access.authorize("entry",detail?"export-detail":"export-simple");String scope=access.frame(actor);
        List<String> ids=selected==null?Collections.emptyList():Arrays.asList(selected.split("[+,\\s]+",-1));
        if(ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->!id.matches("[A-Za-z0-9_-]{1,32}")))throw new IllegalArgumentException("请选择1到200张不同的入库单");
        List<List<Object>> rows=new ArrayList<>();
        for(String id:ids){
            List<Map<String,Object>> found=db.queryForList("SELECT e.*,CAST(e.type AS SIGNED) AS t,CAST(e.examine AS SIGNED) AS a,CAST(e.`check` AS SIGNED) AS c,CAST(e.cse AS SIGNED) AS f,fr.name AS frameName,s.name AS supplierName,p.name AS peopleName,u.name AS userName FROM entry e LEFT JOIN frame fr ON fr.id=e.frame LEFT JOIN supplier s ON s.id=e.supplier LEFT JOIN people p ON p.id=e.people LEFT JOIN `user` u ON u.id=e.`user` WHERE e.id=?",id);
            if(found.size()!=1)throw new IllegalArgumentException("所选入库单已不存在，请刷新列表");Map<String,Object> h=found.get(0);
            if(scope!=null && !scope.equals(text(h.get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能导出其他组织的入库单");
            List<Object> base=Arrays.asList(h.get("frameName"),h.get("number"),text(h.get("time")),integer(h.get("t"))==1?"盘盈":"其他入库",h.get("supplierName"),h.get("peopleName"),h.get("userName"),h.get("total"),h.get("cost"),integer(h.get("a"))==1?"已审核":"未审核",integer(h.get("c"))==1?"已核对":"未核对",new String[]{"未结算","部分结算","已结算","无需结算"}[integer(h.get("f"))],h.get("data"));
            if(!detail){rows.add(base);continue;}
            List<Map<String,Object>> lines=db.queryForList("SELECT i.*,g.number AS goodsNumber,g.name AS goodsName,w.number AS warehouseNumber,w.name AS warehouseName FROM entry_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id);
            if(lines.isEmpty())throw new IllegalArgumentException("所选入库单缺少明细，请先核对历史数据");
            for(Map<String,Object> line:lines){List<Object> values=new ArrayList<>(base);for(String key:Arrays.asList("goodsNumber","goodsName","attr","unit","warehouseNumber","warehouseName","nums","price","total","batch","mfd","serial","data"))values.add(line.get(key));rows.add(values);if(rows.size()>5000)throw new IllegalArgumentException("每次最多导出5000行明细，请减少选择的单据");}
        }
        List<String> headers=new ArrayList<>(Arrays.asList("所属组织","单据编号","单据日期","单据类型","供应商","关联人员","制单人","成本合计","费用合计","审核状态","核对状态","费用状态","单据备注"));
        if(detail)headers.addAll(Arrays.asList("商品编号","商品名称","辅助属性","基本单位","入库仓库编号","入库仓库","数量","单位成本","成本金额","批次号","生产日期","序列号JSON","明细备注"));
        return workbook(detail?"入库明细":"入库汇总",headers,rows,null);
    }
}
