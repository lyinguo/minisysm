package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j4.sale.SalesReturnOrderDTO;
import com.zeroone.star.project.dto.j4.sale.info.SalesReturnOrderInfo;
import com.zeroone.star.project.dto.j4.sale.SaleReturnGenerateDTO;
import com.zeroone.star.project.query.j4.sale.SaleReturnQuery;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import javax.annotation.PostConstruct;
import java.math.*;
import java.util.*;

/** Source-bound draft CRUD. Saving only reserves quantities; it never posts inventory or refunds. */
@Service
public class SaleReturnDraftService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleDraftService sales;
    private final SaleSnapshotService sourceVersions;
    private final SaleReturnSnapshotService versions;
    private final SaleReturnPreviewService previews;
    public SaleReturnDraftService(JdbcTemplate db,SaleDocumentAccess access,SaleDraftService sales,SaleSnapshotService sourceVersions,SaleReturnSnapshotService versions,SaleReturnPreviewService previews){
        this.db=db;this.access=access;this.sales=sales;this.sourceVersions=sourceVersions;this.versions=versions;this.previews=previews;
    }
    @PostConstruct public void initialize(){
        for(String column:Arrays.asList("discount","tax")){
            Map<String,Object> type=db.queryForMap("SELECT NUMERIC_PRECISION AS p,NUMERIC_SCALE AS s FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sre_info' AND COLUMN_NAME=?",column);
            int p=((Number)type.get("p")).intValue(),scale=((Number)type.get("s")).intValue();
            if(p==5 && scale==2)db.execute("ALTER TABLE sre_info MODIFY COLUMN `"+column+"` DECIMAL(7,4) NOT NULL DEFAULT 0.0000");
            else if(scale<4)throw new IllegalStateException("请先执行销售退货税率精度迁移，不能保存会丢失小数的单据");
        }
    }
    private String uid(){return UUID.randomUUID().toString().replace("-","");}
    private String s(Object value){return value==null?"":value.toString();}
    private BigDecimal d(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private int state(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?-1:((Number)value).intValue();}
    private String text(String value,int max,String label){String result=value==null?"":value;if(result.length()>max || result.indexOf('\0')>=0)throw new IllegalArgumentException(label+"过长或含非法字符");return result;}
    private BigDecimal amount(BigDecimal value,int precision,String label){
        if(value==null || value.signum()<0)throw new IllegalArgumentException(label+"不能为空或负数");
        try{value=value.setScale(4,RoundingMode.UNNECESSARY);}catch(ArithmeticException error){throw new IllegalArgumentException(label+"最多4位小数");}
        if(value.precision()>precision)throw new IllegalArgumentException(label+"超出允许范围");return value;
    }
    private Map<String,Object> head(String id,boolean lock){
        List<Map<String,Object>> rows=db.queryForList("SELECT s.*,CAST(s.examine AS SIGNED) AS approval_state,CAST(s.`check` AS SIGNED) AS check_state,CAST(s.nucleus AS SIGNED) AS settlement_state,CAST(s.cse AS SIGNED) AS cost_state,CAST(s.invoice AS SIGNED) AS invoice_state FROM sre s WHERE s.id=?"+(lock?" FOR UPDATE":""),id);
        if(rows.size()!=1)throw new IllegalArgumentException("销售退货单不存在");return rows.get(0);
    }
    private void free(Map<String,Object> head){
        mutable(head,false);
    }
    private void mutable(Map<String,Object> head,boolean allowChecked){
        String id=s(head.get("id"));
        int checked=state(head.get("check_state"));
        if(state(head.get("approval_state"))!=0 || (checked!=0 && !(allowChecked && checked==1)) || state(head.get("settlement_state"))!=0
                || (state(head.get("cost_state"))!=0 && state(head.get("cost_state"))!=3) || (state(head.get("invoice_state"))!=0 && state(head.get("invoice_state"))!=3))
            throw new IllegalArgumentException("已核对、审核或存在核销、费用、发票状态的退货单不能直接修改或删除");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)
            throw new IllegalArgumentException("退货单日期已结账，不能修改或删除");
        for(String table:Arrays.asList("room_info","serve_info","account_info","summary"))
            if(db.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE LOWER(type)='sre' AND `class`=?",Integer.class,id)>0)throw new IllegalArgumentException("退货单已有库存或资金流水，不能直接修改或删除");
        if(db.queryForObject("SELECT COUNT(*) FROM sre_bill WHERE pid=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM imy_bill WHERE source=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM omy_bill WHERE source=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM bill_info WHERE source=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM invoice WHERE LOWER(type)='sre' AND `class`=?",Integer.class,id)>0
                || db.queryForObject("SELECT COUNT(*) FROM cost WHERE LOWER(type)='sre' AND `class`=?",Integer.class,id)>0)
            throw new IllegalArgumentException("退货单已有核销、发票或费用关联，不能直接修改或删除");
    }
    public Map<String,Object> lockForReview(String id){return head(id,true);}
    public void validateForReview(Map<String,Object> head){
        mutable(head,true);String id=s(head.get("id"));
        SaleReturnGenerateDTO preview=previews.previewForDraft(s(head.get("source")),id);
        if(!preview.getFrame().equals(s(head.get("frame"))) || !preview.getCustomer().equals(s(head.get("customer"))))throw new IllegalArgumentException("退货客户或组织与来源销售单不一致");
        Map<String,Map<String,Object>> available=new HashMap<>();for(Map<String,Object> row:preview.getItems())available.put(s(row.get("source")),row);
        List<Map<String,Object>> lines=db.queryForList("SELECT * FROM sre_info WHERE pid=? ORDER BY id FOR UPDATE",id);
        if(lines.isEmpty() || lines.size()>200)throw new IllegalArgumentException("退货明细缺失或数量异常");
        Set<String> seen=new HashSet<>();BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(Map<String,Object> line:lines){
            String source=s(line.get("source"));Map<String,Object> limit=available.get(source);
            BigDecimal quantity=amount(d(line.get("nums")),12,"退货数量");
            if(!seen.add(source) || limit==null || quantity.signum()<=0 || quantity.compareTo(d(limit.get("available")))>0)throw new IllegalArgumentException("退货来源明细重复、失效或数量超出当前可退范围");
            previews.validateSerials(limit,quantity,s(line.get("serial")));
            Map<String,Object> original=db.queryForMap("SELECT * FROM sell_info WHERE id=? AND pid=?",source,head.get("source"));
            for(String field:Arrays.asList("goods","attr","unit","warehouse","batch","mfd"))if(!s(line.get(field)).equals(s(original.get(field))))throw new IllegalArgumentException("退货商品、仓库、属性、单位或批次与来源不一致");
            for(String field:Arrays.asList("price","discount","tax"))if(d(line.get(field)).compareTo(d(original.get(field)))!=0)throw new IllegalArgumentException("退货单价或费率与来源不一致，请重新核对");
            Map<String,Object> used=db.queryForMap("SELECT COUNT(*) AS n,COALESCE(SUM(total),0) AS total,COALESCE(SUM(tat),0) AS tat,COALESCE(SUM(dsc),0) AS dsc FROM sre_info WHERE source=? AND pid<>?",source,id);
            BigDecimal tolerance=new BigDecimal("0.0001").multiply(new BigDecimal(((Number)used.get("n")).longValue()+1));
            for(String field:Arrays.asList("total","tat","dsc")){
                BigDecimal value=amount(d(line.get(field)),12,"退货金额"),expected=d(original.get(field)).multiply(quantity).divide(d(original.get("nums")),4,RoundingMode.HALF_UP);
                if(value.subtract(expected).abs().compareTo(tolerance)>0 || value.add(d(used.get(field))).compareTo(d(original.get(field)))>0)throw new IllegalArgumentException("退货金额与来源或其他退货占用不一致");
            }
            if(d(line.get("tpt")).compareTo(d(line.get("total")).add(d(line.get("tat"))))!=0)throw new IllegalArgumentException("退货价税合计与明细不一致");
            total=total.add(d(line.get("total")));actual=actual.add(d(line.get("tpt")));
        }
        if(total.compareTo(d(head.get("total")))!=0 || actual.compareTo(d(head.get("actual")))!=0)throw new IllegalArgumentException("退货主从金额不一致");
        BigDecimal money=amount(d(head.get("money")),16,"计划退款");amount(d(head.get("cost")),16,"费用");if(money.compareTo(actual)>0)throw new IllegalArgumentException("计划退款超出实际金额");
        reference("account",s(head.get("account")),preview.getFrame(),"退款账户",money.signum()>0);reference("people",s(head.get("people")),preview.getFrame(),"关联人员",false);
    }
    private void reference(String table,String id,String frame,String label,boolean required){
        if(id==null || id.isEmpty() || "0".equals(id)){if(required)throw new IllegalArgumentException("请选择"+label);return;}
        List<Map<String,Object>> found=db.queryForList("SELECT frame FROM "+table+" WHERE id=?",id);
        if(found.size()!=1 || (!"0".equals(s(found.get(0).get("frame"))) && !frame.equals(s(found.get(0).get("frame")))))
            throw new IllegalArgumentException(label+"不存在或不属于来源组织");
    }
    private void history(String id,UserDTO actor,String action){
        java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'sre',?,?,?,?)",uid(),id,now,actor.getId(),action);
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),action+"["+id+"]");
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public String save(SalesReturnOrderDTO dto,boolean update){
        UserDTO actor=access.authorize(update?"/sale/return/updateSalesReturnOrder":"/sale/return/addSalesReturnOrder");
        if(dto==null)throw new IllegalArgumentException("销售退货草稿不能为空");
        sales.lockWrites();
        Map<String,Object> original=null;String id;
        if(update){
            original=head(dto.getId(),true);access.requireFrame(actor,s(original.get("frame")));free(original);
            versions.require(dto.getId(),dto.getVersion());
            if(!s(original.get("source")).equals(dto.getSource()))throw new IllegalArgumentException("退货来源不能直接更换，请删除自由草稿后重新选来源");
            id=dto.getId();
            if(dto.getMoney()==null)dto.setMoney(d(original.get("money")));if(dto.getCost()==null)dto.setCost(d(original.get("cost")));
            if(dto.getAccount()==null)dto.setAccount(s(original.get("account")));if(dto.getPeople()==null)dto.setPeople(s(original.get("people")));
            if(dto.getLogistics()==null)dto.setLogistics(s(original.get("logistics")));if(dto.getFile()==null)dto.setFile(s(original.get("file")));
            if(dto.getMore()==null)dto.setMore(s(original.get("more")));if(dto.getData()==null)dto.setData(s(original.get("data")));
        }else{if(dto.getId()!=null && !dto.getId().isEmpty())throw new IllegalArgumentException("新增退货草稿不能指定ID");id=uid();}
        if(dto.getSourceVersion()==null || !dto.getSourceVersion().matches("[0-9a-f]{64}"))throw new IllegalArgumentException("请重新读取并核对来源销售单");
        SaleReturnGenerateDTO preview=previews.previewForDraft(dto.getSource(),update?id:null);
        sourceVersions.require(dto.getSource(),dto.getSourceVersion());
        String frame=preview.getFrame(),customer=preview.getCustomer();access.requireFrame(actor,frame);
        if((dto.getFrame()!=null && !dto.getFrame().equals(frame)) || (dto.getCustomer()!=null && !dto.getCustomer().equals(customer)))throw new IllegalArgumentException("客户和组织必须与来源销售单一致");
        if((dto.getExamine()!=null && dto.getExamine()!=0) || (dto.getCheck()!=null && dto.getCheck()!=0) || (dto.getNucleus()!=null && dto.getNucleus()!=0)
                || (dto.getInvoice()!=null && dto.getInvoice()!=0 && dto.getInvoice()!=3) || (dto.getCse()!=null && dto.getCse()!=0 && dto.getCse()!=3))throw new IllegalArgumentException("保存草稿不能设置审核、核对、核销或已结算状态");
        if(dto.getTime()==null)throw new IllegalArgumentException("退货日期不能为空");
        java.sql.Date sourceDate=db.queryForObject("SELECT DATE(time) FROM sell WHERE id=?",java.sql.Date.class,dto.getSource());
        if(dto.getTime().toLocalDate().isBefore(sourceDate.toLocalDate()))throw new IllegalArgumentException("退货日期不能早于来源销售日期");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,java.sql.Timestamp.valueOf(dto.getTime()))>0)throw new IllegalArgumentException("退货单日期已结账");
        String number=text(dto.getNumber(),32,"编号").trim();if(number.isEmpty() || number.matches(".*[\\p{Cntrl}].*"))throw new IllegalArgumentException("请输入有效的1到32位退货编号");
        if(db.queryForObject("SELECT COUNT(*) FROM sre WHERE number=? AND id<>?",Integer.class,number,id)>0)throw new IllegalArgumentException("销售退货编号已存在");
        SalesReturnOrderInfo[] input=dto.getSalesReturnOrderInfos();if(input==null || input.length==0 || input.length>200)throw new IllegalArgumentException("请选择1到200条来源明细");
        Map<String,Map<String,Object>> available=new HashMap<>(),previous=new HashMap<>();
        for(Map<String,Object> row:preview.getItems())available.put(s(row.get("source")),row);
        if(update)for(Map<String,Object> row:db.queryForList("SELECT * FROM sre_info WHERE pid=? FOR UPDATE",id))previous.put(s(row.get("source")),row);
        Set<String> seen=new HashSet<>();List<Map<String,Object>> lines=new ArrayList<>();BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(SalesReturnOrderInfo line:input){
            if(line==null || line.getSource()==null || !seen.add(line.getSource()) || !available.containsKey(line.getSource()))throw new IllegalArgumentException("来源明细缺失、重复或不属于当前可退范围");
            Map<String,Object> source=available.get(line.getSource()),old=previous.get(line.getSource());
            if((line.getPid()!=null && !line.getPid().isEmpty() && !id.equals(line.getPid())) || (line.getId()!=null && !line.getId().isEmpty() && (old==null || !line.getId().equals(s(old.get("id"))))))throw new IllegalArgumentException("退货明细ID不属于当前草稿");
            BigDecimal qty=amount(line.getNums(),12,"退货数量");if(qty.signum()==0 || qty.compareTo(d(source.get("available")))>0)throw new IllegalArgumentException("退货数量须大于零且不能超过当前可退量");
            Map<String,Object> row=new LinkedHashMap<>(source);row.put("id",old==null?uid():old.get("id"));row.put("nums",qty);
            Map<String,Object> raw=db.queryForMap("SELECT * FROM sell_info WHERE id=?",line.getSource());
            Map<String,Object> used=db.queryForMap("SELECT COUNT(*) AS n,COALESCE(SUM(total),0) AS total,COALESCE(SUM(tat),0) AS tat,COALESCE(SUM(dsc),0) AS dsc FROM sre_info WHERE source=? AND pid<>?",line.getSource(),id);
            BigDecimal tolerance=new BigDecimal("0.0001").multiply(new BigDecimal(((Number)used.get("n")).longValue()+1));
            for(String field:Arrays.asList("total","tat","dsc")){
                BigDecimal candidate=d(raw.get(field)).multiply(qty).divide(d(raw.get("nums")),4,RoundingMode.HALF_UP),remaining=d(raw.get(field)).subtract(d(used.get(field)));
                if(remaining.signum()<0 || candidate.subtract(remaining).compareTo(tolerance)>0 || (qty.compareTo(d(source.get("available")))==0 && candidate.subtract(remaining).abs().compareTo(tolerance)>0))throw new IllegalArgumentException("来源金额与已有退货记录不一致，请先核对数据");
                row.put(field,amount(qty.compareTo(d(source.get("available")))==0?remaining:candidate.min(remaining),12,"退货金额"));
            }
            row.put("tpt",amount(d(row.get("total")).add(d(row.get("tat"))),12,"价税合计"));
            String serial=text(line.getSerial(),16000,"序列信息");if(serial.isEmpty())serial="[]";
            try{cn.hutool.json.JSONUtil.parseArray(serial);}catch(Exception error){throw new IllegalArgumentException("序列信息必须为JSON数组");}
            previews.validateSerials(source,qty,serial);
            row.put("serial",serial);row.put("data",text(line.getData(),256,"明细备注"));lines.add(row);total=total.add(d(row.get("total")));actual=actual.add(d(row.get("tpt")));
        }
        total=amount(total,16,"单据金额");actual=amount(actual,16,"实际金额");
        BigDecimal money=amount(dto.getMoney()==null?BigDecimal.ZERO:dto.getMoney(),16,"计划退款"),cost=amount(dto.getCost()==null?BigDecimal.ZERO:dto.getCost(),16,"费用");
        if(money.compareTo(actual)>0)throw new IllegalArgumentException("计划退款不能超过实际金额");
        reference("account",dto.getAccount(),frame,"退款账户",money.signum()>0);reference("people",dto.getPeople(),frame,"关联人员",false);
        String file=text(dto.getFile(),1000,"附件");if(!file.isEmpty() && !"[]".equals(file) && !(update && file.equals(s(original.get("file")))))throw new IllegalArgumentException("退货附件需使用真实上传，不能保存任意文件地址");if(file.isEmpty())file="[]";
        String more=text(dto.getMore(),16000,"扩展信息");if(more.isEmpty())more="{}";
        try{cn.hutool.json.JSONUtil.parseObj(more);}catch(Exception error){throw new IllegalArgumentException("扩展信息必须为JSON对象");}
        Object[] values={dto.getSource(),frame,customer,java.sql.Timestamp.valueOf(dto.getTime()),number,total,actual,money,cost,s(dto.getAccount()),s(dto.getPeople()),text(dto.getLogistics(),1000,"物流信息"),file,text(dto.getData(),256,"备注"),more,0,0,cost.signum()==0?3:0,3,0,update?original.get("user"):actor.getId(),id};
        if(update){db.update("UPDATE sre SET source=?,frame=?,customer=?,time=?,number=?,total=?,actual=?,money=?,cost=?,account=?,people=?,logistics=?,file=?,data=?,more=?,examine=?,nucleus=?,cse=?,invoice=?,`check`=?,`user`=? WHERE id=?",values);db.update("DELETE FROM sre_info WHERE pid=?",id);}
        else db.update("INSERT INTO sre(source,frame,customer,time,number,total,actual,money,cost,account,people,logistics,file,data,more,examine,nucleus,cse,invoice,`check`,`user`,id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",values);
        for(Map<String,Object> row:lines)db.update("INSERT INTO sre_info(id,pid,source,goods,attr,unit,warehouse,batch,mfd,price,nums,serial,discount,dsc,total,tax,tat,tpt,data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",row.get("id"),id,row.get("source"),row.get("goods"),row.get("attr"),row.get("unit"),row.get("warehouse"),row.get("batch"),row.get("mfd"),row.get("price"),row.get("nums"),row.get("serial"),row.get("discount"),row.get("dsc"),row.get("total"),row.get("tax"),row.get("tat"),row.get("tpt"),row.get("data"));
        history(id,actor,update?"修改销售退货草稿":"新增销售退货草稿");dto.setId(id);dto.setVersion(versions.version(id,true));return id;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> detail(String id){
        UserDTO actor=access.authorize("/sale/return/{id}");Map<String,Object> head=head(id,false);access.requireFrame(actor,s(head.get("frame")));
        head.putAll(db.queryForMap("SELECT DATE_FORMAT(s.time,'%Y-%m-%d %H:%i:%s') AS timeText,o.number AS sourceNumber,c.name AS customerName,f.name AS frameName,a.name AS accountName,p.name AS peopleName FROM sre s LEFT JOIN sell o ON o.id=s.source LEFT JOIN customer c ON c.id=s.customer LEFT JOIN frame f ON f.id=s.frame LEFT JOIN account a ON a.id=s.account LEFT JOIN people p ON p.id=s.people WHERE s.id=?",id));
        head.put("examine",head.get("approval_state"));head.put("check",head.get("check_state"));head.put("nucleus",head.get("settlement_state"));head.put("cse",head.get("cost_state"));head.put("invoice",head.get("invoice_state"));
        Map<String,Object> result=new LinkedHashMap<>();result.put("header",head);result.put("version",versions.version(id,false));result.put("sourceVersion",sourceVersions.version(s(head.get("source")),false));
        result.put("items",db.queryForList("SELECT i.*,g.name AS goodsName,g.number AS goodsNumber,w.name AS warehouseName FROM sre_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id));return result;
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public void delete(String id,String version){
        UserDTO actor=access.authorize("/sale/return/deleteSalesReturnOrder");sales.lockWrites();Map<String,Object> head=head(id,true);access.requireFrame(actor,s(head.get("frame")));free(head);versions.require(id,version);
        history(id,actor,"删除销售退货自由草稿");db.update("DELETE FROM sre_info WHERE pid=?",id);db.update("DELETE FROM sre WHERE id=?",id);
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> sourceOptions(String id){
        UserDTO actor=access.authorize("/sale/return/updateSalesReturnOrder");Map<String,Object> head=head(id,false);access.requireFrame(actor,s(head.get("frame")));free(head);
        SaleReturnGenerateDTO preview=previews.previewForDraft(s(head.get("source")),id);
        Map<String,Object> result=new LinkedHashMap<>();result.put("version",versions.version(id,false));result.put("sourceVersion",preview.getSourceVersion());result.put("items",preview.getItems());return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public List<Map<String,Object>> accounts(String source,String keyword,boolean updating){
        UserDTO actor=access.authorize(updating?"/sale/return/updateSalesReturnOrder":"/sale/return/addSalesReturnOrder");
        Map<String,Object> sourceHead=(Map<String,Object>)sales.detail(source).get("header");String frame=s(sourceHead.get("frame"));access.requireFrame(actor,frame);
        String q=text(keyword,100,"账户查询").trim();
        return db.queryForList("SELECT id,name,number,frame FROM account WHERE frame IN ('0',?) AND (name LIKE ? OR number LIKE ?) ORDER BY name,id LIMIT 50",frame,"%"+q+"%","%"+q+"%");
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public PageDTO<Map<String,Object>> list(SaleReturnQuery query){
        UserDTO actor=access.authorize("/sale/return/saleReturnList");String frame=access.frame(actor);
        long page=Math.max(1,query.getPageIndex()),size=Math.min(200,Math.max(1,query.getPageSize()));
        StringBuilder where=new StringBuilder(" WHERE 1=1");List<Object> args=new ArrayList<>();
        if(frame!=null){where.append(" AND s.frame=?");args.add(frame);}
        if(query.getId()!=null && !query.getId().trim().isEmpty()){where.append(" AND (s.id=? OR s.number LIKE ?)");args.add(query.getId().trim());args.add("%"+query.getId().trim()+"%");}
        if(query.getCustomer()!=null && !query.getCustomer().trim().isEmpty()){where.append(" AND (s.customer=? OR c.name LIKE ? OR c.number LIKE ?)");String q=query.getCustomer().trim();Collections.addAll(args,q,"%"+q+"%","%"+q+"%");}
        if(query.getGoods()!=null && !query.getGoods().trim().isEmpty()){where.append(" AND EXISTS(SELECT 1 FROM sre_info i JOIN goods g ON g.id=i.goods WHERE i.pid=s.id AND (g.id=? OR g.name LIKE ? OR g.number LIKE ?))");String q=query.getGoods().trim();Collections.addAll(args,q,"%"+q+"%","%"+q+"%");}
        if(query.getBegin()!=null){where.append(" AND s.time>=?");args.add(java.sql.Date.valueOf(query.getBegin()));}
        if(query.getEnd()!=null){where.append(" AND s.time<?");args.add(java.sql.Date.valueOf(query.getEnd().plusDays(1)));}
        if(query.getPeople()!=null && !query.getPeople().isEmpty()){where.append(" AND s.people=?");args.add(query.getPeople());}
        if(query.getUser()!=null && !query.getUser().isEmpty()){where.append(" AND s.`user`=?");args.add(query.getUser());}
        if(query.getData()!=null && !query.getData().isEmpty()){where.append(" AND s.data LIKE ?");args.add("%"+query.getData()+"%");}
        String[] states={"examine","nucleus","cse","invoice","check"};Integer[] values={query.getExamine(),query.getNucleus(),query.getCse(),query.getInvoice(),query.getCheck()};
        for(int i=0;i<states.length;i++)if(values[i]!=null){where.append(" AND s.`"+states[i]+"`=?");args.add(values[i]);}
        String from=" FROM sre s LEFT JOIN customer c ON c.id=s.customer";
        long total=db.queryForObject("SELECT COUNT(*)"+from+where,Long.class,args.toArray());
        List<Object> paged=new ArrayList<>(args);paged.add(size);paged.add(Math.multiplyExact(page-1,size));
        List<Map<String,Object>> rows=db.queryForList("SELECT s.*,CAST(s.examine AS SIGNED) AS approval_state,CAST(s.`check` AS SIGNED) AS check_state,CAST(s.nucleus AS SIGNED) AS settlement_state,CAST(s.cse AS SIGNED) AS cost_state,CAST(s.invoice AS SIGNED) AS invoice_state,DATE_FORMAT(s.time,'%Y-%m-%d %H:%i:%s') AS timeText,c.name AS customerName,o.number AS sourceNumber"+from+" LEFT JOIN sell o ON o.id=s.source"+where+" ORDER BY s.time DESC,s.id LIMIT ? OFFSET ?",paged.toArray());
        List<String> ids=new ArrayList<>();for(Map<String,Object> row:rows)ids.add(s(row.get("id")));Map<String,String> digest=versions.versions(ids);
        for(Map<String,Object> row:rows){row.put("version",digest.get(s(row.get("id"))));row.put("examine",row.get("approval_state"));row.put("check",row.get("check_state"));row.put("nucleus",row.get("settlement_state"));row.put("cse",row.get("cost_state"));row.put("invoice",row.get("invoice_state"));}
        return new PageDTO<>(page,size,total,(total+size-1)/size,rows);
    }
}
