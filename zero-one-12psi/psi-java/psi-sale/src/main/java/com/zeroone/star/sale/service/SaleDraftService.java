package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.sale.SaleDTO;
import com.zeroone.star.project.dto.j4.sale.SaleInfoDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.annotation.PostConstruct;
import java.math.*;
import java.util.*;

/** Draft persistence only. Saving never posts stock or account/customer balances. */
@Service
public class SaleDraftService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleSnapshotService snapshots;
    public SaleDraftService(JdbcTemplate db,SaleDocumentAccess access,SaleSnapshotService snapshots) { this.db=db;this.access=access;this.snapshots=snapshots; }
    @PostConstruct
    public void initialize() {
        db.execute("CREATE TABLE IF NOT EXISTS psi_document_write_lock (scope VARCHAR(40) NOT NULL PRIMARY KEY)");
        for (String column:Arrays.asList("discount","tax")) {
            Map<String,Object> type=db.queryForMap("SELECT NUMERIC_PRECISION AS p,NUMERIC_SCALE AS s FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sell_info' AND COLUMN_NAME=?",column);
            int precision=((Number)type.get("p")).intValue(),scale=((Number)type.get("s")).intValue();
            if (precision==5 && scale==2) db.execute("ALTER TABLE sell_info MODIFY COLUMN `"+column+"` DECIMAL(7,4) NOT NULL DEFAULT 0.0000");
            else if (scale<4) throw new IllegalStateException("请先完成销售税率精度迁移20261115_sale_rate_precision.sql，不能使用会丢失小数的字段保存单据");
        }
    }
    public void lockWrites() {
        if (!org.springframework.transaction.support.TransactionSynchronizationManager.isActualTransactionActive()) throw new IllegalStateException("销售单写入必须位于事务中");
        db.update("INSERT IGNORE INTO psi_document_write_lock(scope) VALUES('sell')");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='sell' FOR UPDATE",String.class);
    }
    private static String uid() { return UUID.randomUUID().toString().replace("-",""); }
    private static String text(Object value) { return value==null ? "" : value.toString(); }
    private static int status(Object value) { return value instanceof Boolean ? ((Boolean)value ? 1 : 0) : value==null ? 0 : ((Number)value).intValue(); }
    private Map<String,Object> header(String id,boolean lock) {
        List<Map<String,Object>> rows=db.queryForList("SELECT id,source,frame,customer,time,number,total,actual,money,cost,account,people,logistics,file,data,more,`user`,CAST(examine AS SIGNED) AS examine,CAST(`check` AS SIGNED) AS `check`,CAST(nucleus AS SIGNED) AS nucleus,CAST(cse AS SIGNED) AS cse,CAST(invoice AS SIGNED) AS invoice FROM sell WHERE id=?"+(lock ? " FOR UPDATE" : ""),id);
        if (rows.size()!=1) throw new IllegalArgumentException("销售单不存在");
        return rows.get(0);
    }
    private List<Map<String,Object>> rows(String id,boolean lock) {
        return db.queryForList("SELECT * FROM sell_info WHERE pid=? ORDER BY id"+(lock ? " FOR UPDATE" : ""),id);
    }
    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public Map<String,Object> detail(String id) {
        UserDTO actor=access.authorize("/sale/form/getSaleDetail");
        return detailFor(actor,id);
    }
    private Map<String,Object> detailFor(UserDTO actor,String id) {
        Map<String,Object> head=header(id,false);
        access.requireFrame(actor,text(head.get("frame")));
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("version",snapshots.version(id,false));
        if (head.get("time") instanceof java.util.Date) head.put("timeEpoch",((java.util.Date)head.get("time")).getTime());
        else if (head.get("time") instanceof java.time.LocalDateTime)
            head.put("timeEpoch",((java.time.LocalDateTime)head.get("time")).atZone(java.time.ZoneId.of("Asia/Shanghai")).toInstant().toEpochMilli());
        head.putAll(db.queryForMap("SELECT c.name AS customerName,f.name AS frameName,p.name AS peopleName,a.name AS accountName FROM sell s LEFT JOIN customer c ON c.id=s.customer LEFT JOIN frame f ON f.id=s.frame LEFT JOIN people p ON p.id=s.people LEFT JOIN account a ON a.id=s.account WHERE s.id=?",id));
        result.put("header",head);
        result.put("items",db.queryForList("SELECT i.*,g.name AS goodsName,g.number AS goodsNumber,g.spec AS spec,w.name AS warehouseName FROM sell_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id));
        return result;
    }
    private BigDecimal amount(BigDecimal input,String field,int precision) {
        if (input==null || input.signum()<0) throw new IllegalArgumentException(field+"不能为空或负数");
        BigDecimal result;
        try { result=input.setScale(4,RoundingMode.UNNECESSARY); }
        catch(ArithmeticException error) { throw new IllegalArgumentException(field+"最多4位小数"); }
        if (result.precision()>precision) throw new IllegalArgumentException(field+"超出允许范围");
        return result;
    }
    private void reference(String table,String id,String label,boolean optional) {
        if (optional && (id==null || id.isEmpty() || "0".equals(id))) return;
        if (id==null || id.trim().isEmpty() || db.queryForObject("SELECT COUNT(*) FROM `"+table+"` WHERE id=?",Integer.class,id)!=1)
            throw new IllegalArgumentException(label+"不存在，请重新选择");
    }
    private void prepare(SaleDTO dto,UserDTO actor) {
        if (dto==null) throw new IllegalArgumentException("销售单不能为空");
        access.requireFrame(actor,dto.getFrame());
        reference("frame",dto.getFrame(),"组织",false);
        reference("customer",dto.getCustomer(),"客户",false);
        String allowed=access.frame(actor);
        if (allowed!=null) {
            String customerFrame=db.queryForObject("SELECT frame FROM customer WHERE id=?",String.class,dto.getCustomer());
            if (!"0".equals(customerFrame)) access.requireFrame(actor,customerFrame);
        }
        reference("people",dto.getPeople(),"关联人员",true);
        reference("account",dto.getAccount(),"结算账户",true);
        if (dto.getTime()==null) throw new IllegalArgumentException("单据日期不能为空");
        String number=text(dto.getNumber()).trim();
        if (number.isEmpty() || number.length()>32) throw new IllegalArgumentException("单据编号须为1到32个字符");
        dto.setNumber(number);
        if (!db.queryForList("SELECT id FROM sell WHERE number=? AND id<>? FOR UPDATE",number,text(dto.getId())).isEmpty())
            throw new IllegalArgumentException("销售单编号已存在");
        if (Boolean.TRUE.equals(dto.getExamine()) || Boolean.TRUE.equals(dto.getCheck()) || (dto.getNucleus()!=null && dto.getNucleus()!=0)
                || (dto.getInvoice()!=null && dto.getInvoice()!=0 && dto.getInvoice()!=3)) throw new IllegalArgumentException("保存不能设置审核、核对、核销或已开票状态");
        if (dto.getItems()==null || dto.getItems().isEmpty()) throw new IllegalArgumentException("至少添加一条商品明细");
        BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        Set<String> identifiers=new HashSet<>();
        for (SaleInfoDTO line:dto.getItems()) {
            if (line==null) throw new IllegalArgumentException("商品明细不能为空");
            reference("goods",line.getGoods(),"商品",false);
            reference("warehouse",line.getWarehouse(),"仓库",false);
            if (allowed!=null) {
                String warehouseFrame=db.queryForObject("SELECT frame FROM warehouse WHERE id=?",String.class,line.getWarehouse());
                if (!"0".equals(warehouseFrame)) access.requireFrame(actor,warehouseFrame);
            }
            if (text(line.getUnit()).trim().isEmpty()) throw new IllegalArgumentException("商品单位不能为空");
            if (line.getId()!=null && !line.getId().isEmpty() && !identifiers.add(line.getId())) throw new IllegalArgumentException("商品明细ID重复");
            line.setNums(amount(line.getNums(),"数量",12));
            if (line.getNums().signum()==0) throw new IllegalArgumentException("数量必须大于零");
            line.setPrice(amount(line.getPrice(),"单价",12));
            BigDecimal discount=line.getDiscount()==null || line.getDiscount().signum()==0 ? BigDecimal.ONE : line.getDiscount();
            BigDecimal tax=line.getTax()==null ? BigDecimal.ZERO : line.getTax();
            if (discount.signum()<0 || discount.compareTo(BigDecimal.ONE)>0 || tax.signum()<0 || tax.compareTo(BigDecimal.ONE)>0)
                throw new IllegalArgumentException("折扣率和税率须在0到1之间，税率13%应提交0.13");
            discount=amount(discount,"折扣率",7); tax=amount(tax,"税率",7);
            BigDecimal gross=line.getPrice().multiply(line.getNums()).setScale(4,RoundingMode.HALF_UP);
            line.setDiscount(discount);
            line.setTotal(amount(gross.multiply(discount).setScale(4,RoundingMode.HALF_UP),"明细金额",12));
            line.setDsc(gross.subtract(line.getTotal()));
            line.setTax(tax);
            line.setTat(amount(line.getTotal().multiply(tax).setScale(4,RoundingMode.HALF_UP),"税额",12));
            line.setTpt(amount(line.getTotal().add(line.getTat()),"价税合计",12));
            line.setRetreat(BigDecimal.ZERO);
            total=total.add(line.getTotal());actual=actual.add(line.getTpt());
        }
        dto.setTotal(amount(total,"单据金额",16)); dto.setActual(amount(actual,"实际金额",16));
        dto.setCost(amount(dto.getCost()==null ? BigDecimal.ZERO : dto.getCost(),"费用",16));
        dto.setMoney(amount(dto.getMoney()==null ? BigDecimal.ZERO : dto.getMoney(),"实收金额",16));
        if (dto.getMoney().compareTo(actual)>0) throw new IllegalArgumentException("本单实收金额不能超过实际金额");
        if (dto.getMoney().signum()>0) reference("account",dto.getAccount(),"结算账户",false);
        dto.setExamine(false);dto.setCheck(false);dto.setNucleus(0);dto.setCse(dto.getCost().signum()==0 ? 3 : 0);
        if (dto.getInvoice()==null) dto.setInvoice(0);
    }
    @Transactional(rollbackFor=Exception.class)
    public void save(SaleDTO dto,boolean update) {
        UserDTO actor=access.authorize(update ? "/sale/form/updateSale" : "/sale/form/addSale");
        lockWrites();
        Map<String,Object> original=null;
        List<Map<String,Object>> previous=Collections.emptyList();
        if (update) {
            original=header(dto.getId(),true); access.requireFrame(actor,text(original.get("frame")));
            previous=rows(dto.getId(),true);
            if (db.queryForObject("SELECT COUNT(*) FROM sre WHERE source=?",Integer.class,dto.getId())>0
                    || db.queryForObject("SELECT COUNT(*) FROM sre_info WHERE source IN (SELECT id FROM sell_info WHERE pid=?)",Integer.class,dto.getId())>0
                    || previous.stream().anyMatch(line->line.get("retreat")!=null && new BigDecimal(line.get("retreat").toString()).signum()>0))
                throw new IllegalStateException("销售单已有关联退货，不能修改原始明细");
            if (status(original.get("examine"))!=0 || status(original.get("check"))!=0 || status(original.get("nucleus"))!=0
                    || status(original.get("invoice"))==1 || status(original.get("invoice"))==2 || status(original.get("cse"))==1 || status(original.get("cse"))==2)
                throw new IllegalStateException("单据已审核、核对或存在结算记录，不能直接修改");
            if (!snapshots.version(dto.getId(),true).equals(dto.getVersion())) throw new IllegalStateException("单据已被其他操作修改，请重新打开详情");
        } else {
            if (dto.getId()!=null && !dto.getId().isEmpty()) throw new IllegalArgumentException("新增销售单不能指定ID");
        }
        prepare(dto,actor);
        String id=update ? dto.getId() : uid();
        dto.setId(id);dto.setUser(update ? text(original.get("user")) : actor.getId());
        Object[] values={dto.getSource(),dto.getFrame(),dto.getCustomer(),new java.sql.Timestamp(dto.getTime().getTime()),dto.getNumber(),dto.getTotal(),dto.getActual(),dto.getMoney(),dto.getCost(),dto.getAccount(),dto.getPeople(),dto.getLogistics(),dto.getFile(),dto.getData(),dto.getMore(),dto.getExamine(),dto.getNucleus(),dto.getCse(),dto.getInvoice(),dto.getCheck(),dto.getUser(),id};
        if (update) db.update("UPDATE sell SET source=?,frame=?,customer=?,time=?,number=?,total=?,actual=?,money=?,cost=?,account=?,people=?,logistics=?,file=?,data=?,more=?,examine=?,nucleus=?,cse=?,invoice=?,`check`=?,`user`=? WHERE id=?",values);
        else db.update("INSERT INTO sell(source,frame,customer,time,number,total,actual,money,cost,account,people,logistics,file,data,more,examine,nucleus,cse,invoice,`check`,`user`,id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",values);
        Set<String> existing=new HashSet<>(); previous.forEach(row->existing.add(text(row.get("id"))));
        Set<String> kept=new HashSet<>();
        for (SaleInfoDTO line:dto.getItems()) {
            boolean known=line.getId()!=null && !line.getId().isEmpty();
            if (known && !existing.contains(line.getId())) throw new IllegalArgumentException("商品明细不属于当前销售单");
            if (!known) line.setId(uid());
            line.setPid(id); kept.add(line.getId());
            Object[] data={id,line.getSource(),line.getGoods(),line.getUnit(),line.getPrice(),line.getNums(),line.getDiscount(),line.getDsc(),line.getTotal(),line.getTax(),line.getTat(),line.getTpt(),line.getAttr()==null ? "" : line.getAttr(),line.getWarehouse(),line.getBatch(),line.getMfd(),line.getSerial()==null ? "[]" : line.getSerial(),line.getData(),line.getRetreat(),line.getId()};
            if (known) db.update("UPDATE sell_info SET pid=?,source=?,goods=?,unit=?,price=?,nums=?,discount=?,dsc=?,total=?,tax=?,tat=?,tpt=?,attr=?,warehouse=?,batch=?,mfd=?,serial=?,data=?,retreat=? WHERE id=?",data);
            else db.update("INSERT INTO sell_info(pid,source,goods,unit,price,nums,discount,dsc,total,tax,tat,tpt,attr,warehouse,batch,mfd,serial,data,retreat,id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",data);
        }
        for (String old:existing) if (!kept.contains(old)) db.update("DELETE FROM sell_info WHERE id=? AND pid=?",old,id);
        java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),(update ? "修改" : "新增")+"销售单["+id+"]");
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'sell',?,?,?,?)",uid(),id,now,actor.getId(),update ? "修改销售草稿" : "新增销售草稿");
        dto.setVersion(snapshots.version(id,true));
    }
}
