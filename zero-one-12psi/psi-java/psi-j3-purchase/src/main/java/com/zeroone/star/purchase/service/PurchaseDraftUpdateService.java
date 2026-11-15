package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.math.*;
import java.util.*;

/** Legacy revise contract uses percentage points (13 means 13%). No inventory/funds posting here. */
@Service
public class PurchaseDraftUpdateService {
    private final JdbcTemplate db;
    private final UserHolder users;
    private final PurchaseDraftValidation validation;
    private final PurchaseDocumentAccess access;
    public PurchaseDraftUpdateService(JdbcTemplate db,UserHolder users,PurchaseDraftValidation validation,PurchaseDocumentAccess access) { this.db=db;this.users=users;this.validation=validation;this.access=access; }
    private static String s(Object v) { return v==null ? "":v.toString(); }
    private static BigDecimal d(Object v) { return v==null ? BigDecimal.ZERO:new BigDecimal(v.toString()); }
    private static int n(Object v) { return v instanceof Boolean ? ((Boolean)v ? 1:0):v==null ? 0:((Number)v).intValue(); }
    private static String choose(String value,Object original) { return value==null ? s(original):value; }
    private static String optional(String value,Object original) { return value==null ? original==null ? null:original.toString():value; }
    private String version(Map<String,Object> head,List<Map<String,Object>> lines) {
        return org.springframework.util.DigestUtils.md5DigestAsHex((head.toString()+lines.toString()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public Map<String,Object> detail(String id) {
        UserDTO actor=access.current();
        List<Map<String,Object>> found=db.queryForList("SELECT b.*,DATE_FORMAT(b.time,'%Y-%m-%d %H:%i:%s') AS time_text FROM buy b WHERE id=?",id);
        if(found.size()!=1) throw new IllegalArgumentException("采购单不存在");
        Map<String,Object> header=found.get(0);
        access.requireFrame(actor,s(header.get("frame")));
        List<Map<String,Object>> lines=db.queryForList("SELECT * FROM buy_info WHERE pid=? ORDER BY id",id);
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("version",version(header,lines));
        header.putAll(db.queryForMap("SELECT s.name AS supplierName,f.name AS frameName,p.name AS peopleName,a.name AS accountName FROM buy b LEFT JOIN supplier s ON s.id=b.supplier LEFT JOIN frame f ON f.id=b.frame LEFT JOIN people p ON p.id=b.people LEFT JOIN account a ON a.id=b.account WHERE b.id=?",id));
        result.put("header",header);
        result.put("items",db.queryForList("SELECT i.*,g.name AS goodsName,g.number AS goodsNumber,w.name AS warehouseName FROM buy_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id));
        result.put("settlements",db.queryForList("SELECT bb.*,CASE bb.type WHEN 'buy' THEN (SELECT number FROM buy WHERE id=bb.source) WHEN 'omy' THEN (SELECT number FROM omy WHERE id=bb.source) WHEN 'bre' THEN (SELECT number FROM bre WHERE id=bb.source) WHEN 'bill' THEN (SELECT number FROM bill WHERE id=bb.source) ELSE bb.source END AS sourceNumber FROM buy_bill bb WHERE bb.pid=? ORDER BY bb.time,bb.id",id));
        result.put("expenses",db.queryForList("SELECT c.*,i.name AS expenseName FROM cost c LEFT JOIN iet i ON i.id=c.iet WHERE c.type='buy' AND c.`class`=? ORDER BY c.time,c.id",id));
        result.put("invoices",db.queryForList("SELECT * FROM invoice WHERE type='buy' AND `class`=? ORDER BY time,id",id));
        return result;
    }
    private static BigDecimal amount(BigDecimal value,String field) {
        if(value==null || value.signum()<0) throw new IllegalArgumentException(field+"不能为空或负数");
        try { return value.setScale(4,RoundingMode.UNNECESSARY); }
        catch(ArithmeticException error) { throw new IllegalArgumentException(field+"最多四位小数"); }
    }
    private BigDecimal percentage(BigDecimal raw,Map<String,Object> original,boolean discount) {
        String key=discount ? "discount":"tax";
        if(original.isEmpty() || raw.compareTo(d(original.get(key)))!=0) return raw;
        BigDecimal base=discount ? d(original.get("price")).multiply(d(original.get("nums"))).setScale(4,RoundingMode.HALF_UP):d(original.get("total"));
        BigDecimal recorded=d(original.get(discount ? "dsc":"tat"));
        if(base.signum()==0) return raw;
        BigDecimal percentageAmount=base.multiply(raw).movePointLeft(2).setScale(4,RoundingMode.HALF_UP);
        if(percentageAmount.compareTo(recorded)==0) return raw;
        if(raw.compareTo(BigDecimal.ONE)<=0) {
            BigDecimal fraction=discount ? BigDecimal.ONE.subtract(raw):raw;
            if(base.multiply(fraction).setScale(4,RoundingMode.HALF_UP).compareTo(recorded)==0) return fraction.movePointRight(2);
        }
        throw new IllegalArgumentException("历史折扣或税率与金额不一致，请先核对原单据，不能直接重新解释比例");
    }
    @Transactional(rollbackFor=Exception.class)
    public void update(RevisePurchaseDTO request) {
        if(request==null || request.getId()==null || request.getId().trim().isEmpty()) throw new IllegalArgumentException("采购单ID不能为空");
        UserDTO actor=access.current();
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('buy') ON DUPLICATE KEY UPDATE scope='buy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        List<Map<String,Object>> found=db.queryForList("SELECT b.*,DATE_FORMAT(b.time,'%Y-%m-%d %H:%i:%s') AS time_text FROM buy b WHERE id=? FOR UPDATE",request.getId());
        if(found.size()!=1) throw new IllegalArgumentException("采购单不存在");
        Map<String,Object> head=found.get(0);
        access.requireFrame(actor,s(head.get("frame")));
        if(n(head.get("examine"))!=0 || n(head.get("check"))!=0 || n(head.get("nucleus"))!=0) throw new IllegalArgumentException("单据已核对、审核或核销，请先按业务规则处理状态");
        if((request.getExamine()!=null && request.getExamine()!=0) || (request.getCheckStatus()!=null && request.getCheckStatus()!=0)) throw new IllegalArgumentException("草稿修改不能设置审核或核对状态");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0) throw new IllegalArgumentException("已结账期间的采购单不能修改");
        String id=request.getId();
        for(String table:Arrays.asList("room_info","account_info","summary"))
            if(db.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE type='buy' AND `class`=?",Integer.class,id)>0) throw new IllegalArgumentException("存在库存或资金凭据，不能直接修改草稿");
        if(db.queryForObject("SELECT COUNT(*) FROM bre WHERE source=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM bre_info WHERE source IN (SELECT id FROM buy_info WHERE pid=?)",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM buy_bill WHERE pid=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM invoice WHERE type='buy' AND `class`=?",Integer.class,id)>0)
            throw new IllegalArgumentException("存在退货、核销或发票关联，不能直接修改草稿");
        if(request.getDetails()==null || request.getDetails().isEmpty()) throw new IllegalArgumentException("采购单至少保留一条明细");
        Map<String,Map<String,Object>> previous=new HashMap<>();
        List<Map<String,Object>> originalLines=db.queryForList("SELECT * FROM buy_info WHERE pid=? ORDER BY id FOR UPDATE",id);
        if(request.getVersion()==null || request.getVersion().trim().isEmpty()) throw new IllegalArgumentException("请先读取完整采购单，再提交编辑版本");
        if(!request.getVersion().equals(version(head,originalLines))) throw new IllegalStateException("采购单已被其他操作修改，请刷新后重试");
        for(Map<String,Object> row:originalLines) {
            if(d(row.get("retreat")).signum()!=0) throw new IllegalArgumentException("已有退货明细不能修改");
            previous.put(s(row.get("id")),row);
        }
        PurchaseNoteBuyDTO header=new PurchaseNoteBuyDTO();
        header.setSupplier(choose(request.getSupplier(),head.get("supplier")));
        header.setTime(request.getTime()==null ? s(head.get("time_text")):request.getTime().toString());
        header.setNumber(choose(request.getNumber(),head.get("number")));
        header.setAccount(optional(request.getAccount(),head.get("account")));
        header.setPeople(optional(request.getPeople(),head.get("people")));
        header.setMoney(request.getMoney()==null ? d(head.get("money")):amount(request.getMoney(),"实付金额"));
        header.setCost(d(head.get("cost")));
        List<PurchaseNoteInfoDTO> lines=new ArrayList<>();
        Set<String> retained=new HashSet<>();
        BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(PurchaseBuyInfoDTO input:request.getDetails()) {
            if(input==null) throw new IllegalArgumentException("采购明细不能为空");
            if(input.getUnit()==null || input.getUnit().trim().isEmpty()) throw new IllegalArgumentException("商品单位不能为空");
            String lineId=input.getId();
            Map<String,Object> original=Collections.emptyMap();
            if(lineId!=null && !lineId.trim().isEmpty()) {
                original=previous.get(lineId);
                if(original==null) throw new IllegalArgumentException("明细不属于当前采购单");
                if(!s(original.get("goods")).equals(input.getGoods()) && (!s(original.get("attr")).isEmpty() || !s(original.get("batch")).isEmpty()
                        || !s(original.get("serial")).isEmpty() && !"[]".equals(s(original.get("serial")))
                        || !s(original.get("source")).isEmpty() && !"0".equals(s(original.get("source")))))
                    throw new IllegalArgumentException("该明细包含属性、批次、序列号或来源信息，更换商品请新增对应明细并核对资料");
            } else lineId=UUID.randomUUID().toString().replace("-","");
            if(!retained.add(lineId)) throw new IllegalArgumentException("采购明细ID重复");
            if(input.getRetreat()!=null && input.getRetreat().signum()!=0) throw new IllegalArgumentException("草稿修改不能设置退货数量");
            BigDecimal price=amount(input.getPrice(),"单价"),quantity=amount(input.getNums(),"数量");
            if(quantity.signum()==0) throw new IllegalArgumentException("采购数量必须大于零");
            BigDecimal discount=input.getDiscount()==null ? d(original.get("discount")):amount(input.getDiscount(),"折扣百分比");
            BigDecimal tax=input.getTax()==null ? d(original.get("tax")):amount(input.getTax(),"税率百分比");
            if(discount.compareTo(new BigDecimal("100"))>0 || tax.compareTo(new BigDecimal("100"))>0) throw new IllegalArgumentException("折扣和税率百分比应在0到100之间");
            // Existing decimal(5,2) fields must never silently round the rate.
            try { discount=discount.setScale(2,RoundingMode.UNNECESSARY);tax=tax.setScale(2,RoundingMode.UNNECESSARY); }
            catch(ArithmeticException error) { throw new IllegalArgumentException("当前采购百分比最多两位小数"); }
            BigDecimal gross=price.multiply(quantity).setScale(4,RoundingMode.HALF_UP);
            BigDecimal deduction=gross.multiply(percentage(discount,original,true)).movePointLeft(2).setScale(4,RoundingMode.HALF_UP);
            BigDecimal net=gross.subtract(deduction),taxAmount=net.multiply(percentage(tax,original,false)).movePointLeft(2).setScale(4,RoundingMode.HALF_UP),inclusive=net.add(taxAmount);
            PurchaseNoteInfoDTO line=new PurchaseNoteInfoDTO();
            line.setGoods(input.getGoods());line.setWarehouse(input.getWarehouse());line.setUnit(input.getUnit());line.setNums(quantity);
            line.setSource(optional(input.getSource(),original.get("source")));
            line.setAttr(optional(input.getAttr(),original.get("attr")));
            line.setSerial(optional(input.getSerial(),original.get("serial")));
            line.setBatch(optional(input.getBatch(),original.get("batch")));line.setMfd(optional(input.getMfd(),original.get("mfd")));
            line.setPrice(price);line.setDiscount(discount);line.setTax(tax);line.setDsc(deduction);line.setTotal(net);line.setTat(taxAmount);line.setTpt(inclusive);
            lines.add(line);
            input.setId(lineId);
            total=total.add(net);actual=actual.add(inclusive);
        }
        header.setTotal(total);header.setActual(actual);
        PurchaseNoteAddDTO validated=new PurchaseNoteAddDTO();validated.setPurchaseNoteBuyDTO(header);validated.setPurchaseNoteInfoDTOS(lines);
        validation.validate(validated,id,s(head.get("frame")));
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,header.getTime())>0) throw new IllegalArgumentException("不能将单据移入已结账期间");
        db.update("UPDATE buy SET supplier=?,time=?,number=?,total=?,actual=?,money=?,account=?,people=?,logistics=?,file=?,data=? WHERE id=?",header.getSupplier(),header.getTime(),header.getNumber(),total,actual,header.getMoney(),header.getAccount(),header.getPeople(),optional(request.getLogistics(),head.get("logistics")),optional(request.getFile(),head.get("file")),optional(request.getData(),head.get("data")),id);
        for(int index=0;index<request.getDetails().size();index++) {
            PurchaseBuyInfoDTO input=request.getDetails().get(index);PurchaseNoteInfoDTO line=lines.get(index);
            boolean existing=previous.containsKey(input.getId());
            Object[] values={line.getGoods(),line.getUnit(),line.getWarehouse(),line.getPrice(),line.getNums(),line.getDiscount(),line.getDsc(),line.getTotal(),line.getTax(),line.getTat(),line.getTpt(),input.getData()==null ? existing ? previous.get(input.getId()).get("data"):null:input.getData(),line.getSource()==null && !existing ? "0":line.getSource(),line.getAttr()==null && !existing ? "":line.getAttr(),line.getSerial()==null && !existing ? "[]":line.getSerial(),line.getBatch(),line.getMfd()==null || line.getMfd().trim().isEmpty() ? null:line.getMfd(),input.getId(),id};
            if(previous.containsKey(input.getId())) db.update("UPDATE buy_info SET goods=?,unit=?,warehouse=?,price=?,nums=?,discount=?,dsc=?,total=?,tax=?,tat=?,tpt=?,data=?,source=?,attr=?,serial=?,batch=?,mfd=? WHERE id=? AND pid=?",values);
            else db.update("INSERT INTO buy_info(goods,unit,warehouse,price,nums,discount,dsc,total,tax,tat,tpt,data,source,attr,serial,batch,mfd,id,pid,retreat) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",values);
        }
        for(String old:previous.keySet()) if(!retained.contains(old)) db.update("DELETE FROM buy_info WHERE id=? AND pid=?",old,id);
        java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'buy',?,?,?,?)",UUID.randomUUID().toString().replace("-",""),id,now,actor.getId(),"修改采购草稿");
    }
}
