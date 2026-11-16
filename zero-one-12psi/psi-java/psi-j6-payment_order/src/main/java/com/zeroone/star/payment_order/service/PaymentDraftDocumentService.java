package com.zeroone.star.payment_order.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j6.payment_order.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

/** Free drafts can be corrected without paying; approval and reversal are explicit separate actions. */
@Service
public class PaymentDraftDocumentService {
    public static class Line extends OmyInfoAddDTO {public String id;}
    public static class Revision extends OmyWithInfoAddDTO {public String version;public List<Line> details;}
    public static class Removal {public String version;}
    private final JdbcTemplate db;private final PaymentDocumentAccess access;private final PaymentDraftValidation validation;private final PaymentSettlementPreviewService versions;
    public PaymentDraftDocumentService(JdbcTemplate db,PaymentDocumentAccess access,PaymentDraftValidation validation,PaymentSettlementPreviewService versions){this.db=db;this.access=access;this.validation=validation;this.versions=versions;}
    private String s(Object value){return Objects.toString(value,"");}
    private String uid(){return UUID.randomUUID().toString().replace("-","");}
    private int n(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?-1:((Number)value).intValue();}
    private Map<String,Object> head(String id,boolean locked){List<Map<String,Object>> rows=db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM omy o WHERE id=?"+(locked?" FOR UPDATE":""),id);if(rows.size()!=1)throw new IllegalArgumentException("付款单不存在");return rows.get(0);}
    private void lock(){db.update("INSERT INTO psi_document_write_lock(scope) VALUES('omy') ON DUPLICATE KEY UPDATE scope='omy'");db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='omy' FOR UPDATE",String.class);}
    private void reviewed(String id,String expected){if(expected==null || !expected.matches("[0-9a-f]{64}") || !expected.equals(versions.paymentVersion(id)))throw new IllegalArgumentException("付款草稿已变化，请重新读取核对后操作，本次未处理");}
    private void free(Map<String,Object> head){
        Object id=head.get("id");
        if(n(head.get("approval_state"))!=0 || n(head.get("settlement_state"))!=0)throw new IllegalArgumentException("已审核或已核销付款单不能直接修改删除，请先显式反审核");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)throw new IllegalArgumentException("付款日期已结账，不能修改或删除");
        if(db.queryForObject("SELECT COUNT(*) FROM psi_payment_posting WHERE payment_id=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM account_info WHERE LOWER(type)='omy' AND `class`=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM omy_bill WHERE pid=? OR source=?",Integer.class,id,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM buy_bill WHERE type='omy' AND source=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM bre_bill WHERE type='omy' AND source=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM imy_bill WHERE source=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM bill_info WHERE source=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM invoice WHERE LOWER(type)='omy' AND `class`=?",Integer.class,id)>0
            || db.queryForObject("SELECT COUNT(*) FROM cost WHERE LOWER(type)='omy' AND `class`=?",Integer.class,id)>0)throw new IllegalArgumentException("付款单已有资金、核销、发票或费用关联，请先处理关联单据");
    }
    private void history(String id,UserDTO actor,String action){db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'omy',?,CURRENT_TIMESTAMP,?,?)",uid(),id,actor.getId(),action);db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,CURRENT_TIMESTAMP,?,?)",uid(),actor.getId(),action+"["+id+"]");}
    public void requireScoped(String id,String resource){UserDTO actor=access.authorize(resource);access.requireFrame(actor,s(head(id,false).get("frame")));}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> options(String kind,String keyword,String document){
        if(!Arrays.asList("supplier","account").contains(kind))throw new IllegalArgumentException("选项类型无效");
        boolean editing=document!=null && !document.isEmpty();UserDTO actor=access.authorize(editing?"/payment-order/modify":"/payment-order/add");String frame=actor.getFrameId();
        if(editing){Map<String,Object> head=head(document,false);access.requireFrame(actor,s(head.get("frame")));frame=s(head.get("frame"));}
        if(frame==null || "0".equals(frame) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,frame)!=1)throw new IllegalArgumentException("制单组织不存在");
        String term=keyword==null?"":keyword.trim();if(term.length()>100)throw new IllegalArgumentException("查询关键词过长");
        List<Map<String,Object>> rows=db.queryForList("SELECT id,name,number FROM "+kind+" WHERE frame IN ('0',?) AND (name LIKE ? OR number LIKE ?) ORDER BY number,id LIMIT 51",frame,"%"+term+"%","%"+term+"%");
        boolean more=rows.size()>50;Map<String,Object> result=new LinkedHashMap<>();result.put("rows",more?rows.subList(0,50):rows);result.put("hasMore",more);return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> document(String id){
        UserDTO actor=access.authorize("/payment-order/query-by-id");Map<String,Object> head=head(id,false);access.requireFrame(actor,s(head.get("frame")));
        head.put("examine",head.remove("approval_state"));head.put("nucleus",head.remove("settlement_state"));
        head.putAll(db.queryForMap("SELECT DATE_FORMAT(o.time,'%Y-%m-%d') AS timeText,c.name AS supplierName,f.name AS frameName,p.name AS peopleName FROM omy o LEFT JOIN supplier c ON c.id=o.supplier LEFT JOIN frame f ON f.id=o.frame LEFT JOIN people p ON p.id=o.people WHERE o.id=?",id));
        Map<String,Object> result=new LinkedHashMap<>();result.put("header",head);result.put("version",versions.paymentVersion(id));
        result.put("items",db.queryForList("SELECT i.*,a.name AS accountName,a.number AS accountNumber FROM omy_info i LEFT JOIN account a ON a.id=i.account WHERE i.pid=? ORDER BY i.id",id));
        result.put("allocations",db.queryForList("SELECT b.*,CASE WHEN b.type='buy' THEN (SELECT number FROM buy WHERE id=b.source) WHEN b.type='bre' THEN (SELECT number FROM bre WHERE id=b.source) END AS sourceNumber FROM omy_bill b WHERE b.pid=? ORDER BY b.type,b.source",id));
        result.put("expenses",db.queryForList("SELECT c.id,c.money,c.settle,CAST(c.state AS SIGNED) AS state,c.data,t.name AS expenseName FROM cost c LEFT JOIN iet t ON t.id=c.iet WHERE LOWER(c.type)='omy' AND c.`class`=? ORDER BY c.id",id));
        result.put("invoices",db.queryForList("SELECT id,number,title,time,money FROM invoice WHERE LOWER(type)='omy' AND `class`=? ORDER BY time,id",id));return result;
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public String revise(String id,Revision request){
        UserDTO actor=access.authorize("/payment-order/modify");lock();Map<String,Object> original=head(id,true);access.requireFrame(actor,s(original.get("frame")));free(original);
        if(request==null)throw new IllegalArgumentException("请提交草稿修改内容");reviewed(id,request.version);
        if(request.getNumber()==null)request.setNumber(s(original.get("number")));
        if(request.getSupplier()==null)request.setSupplier(s(original.get("supplier")));
        if(request.getTime()==null)request.setTime(LocalDate.parse(s(original.get("time")).substring(0,10)));
        if(request.getPeople()==null)request.setPeople(s(original.get("people")));
        if(request.getData()==null)request.setData(s(original.get("data")));
        if(request.getFile()!=null && !request.getFile().equals(s(original.get("file"))))throw new IllegalArgumentException("附件请通过真实文件流程处理，不能直接改写文件地址");
        List<Map<String,Object>> old=db.queryForList("SELECT * FROM omy_info WHERE pid=? ORDER BY id FOR UPDATE",id);Set<String> oldIds=new HashSet<>();for(Map<String,Object> row:old)oldIds.add(s(row.get("id")));
        if(request.details==null){
            if(request.getInfoList()!=null)throw new IllegalArgumentException("请通过带明细ID的details提交修改，避免覆盖错误的账户明细");
            request.details=new ArrayList<>();for(Map<String,Object> row:old){Line line=new Line();line.id=s(row.get("id"));line.setAccount(s(row.get("account")));line.setMoney((BigDecimal)row.get("money"));line.setSettle(s(row.get("settle")));line.setData1(s(row.get("data")));request.details.add(line);}
        }
        Set<String> used=new HashSet<>();
        for(Line line:request.details){if(line==null)throw new IllegalArgumentException("账户明细不能为空");if(line.getPid()!=null && !id.equals(line.getPid()))throw new IllegalArgumentException("账户明细不属于本付款单");if(line.id!=null && !line.id.isEmpty()){if(!oldIds.contains(line.id) || !used.add(line.id))throw new IllegalArgumentException("账户明细ID不存在、不属于本单或重复");}else line.id=uid();}
        request.setInfoList(new ArrayList<OmyInfoAddDTO>(request.details));validation.validateRevision(request,id,s(original.get("frame")));
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=?",Integer.class,request.getTime())>0)throw new IllegalArgumentException("新的付款日期已结账");
        db.update("UPDATE omy SET supplier=?,time=?,number=?,total=?,people=?,data=? WHERE id=?",request.getSupplier(),request.getTime(),request.getNumber(),request.getTotal(),request.getPeople(),request.getData(),id);
        db.update("DELETE FROM omy_info WHERE pid=?",id);
        for(Line line:request.details)db.update("INSERT INTO omy_info(id,pid,account,money,settle,data) VALUES(?,?,?,?,?,?)",line.id,id,line.getAccount(),line.getMoney(),line.getSettle(),line.getData1());
        history(id,actor,"修改付款草稿 "+request.getNumber());return id;
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public String delete(String id,String version){UserDTO actor=access.authorize("/payment-order/remove");lock();Map<String,Object> head=head(id,true);access.requireFrame(actor,s(head.get("frame")));free(head);reviewed(id,version);db.update("DELETE FROM omy_info WHERE pid=?",id);db.update("DELETE FROM omy WHERE id=?",id);history(id,actor,"删除付款草稿 "+s(head.get("number")));return id;}
    private int integer(Map<String,String> query,String key,int fallback,int max){String raw=query.get(key);if(raw==null || raw.isEmpty())return fallback;try{int value=Integer.parseInt(raw);if(value<1 || value>max)throw new IllegalArgumentException();return value;}catch(Exception error){throw new IllegalArgumentException("分页参数无效");}}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> list(Map<String,String> query){
        UserDTO actor=access.authorize("/payment-order/query-all");int page=integer(query,"pageIndex",1,1000000),size=integer(query,"pageSize",10,100);
        StringBuilder where=new StringBuilder(" WHERE 1=1");List<Object> args=new ArrayList<>();
        if(!actor.getRoles().contains("ROLE_ADMIN")){where.append(" AND o.frame=?");args.add(actor.getFrameId());}
        if(query.get("number")!=null && !query.get("number").trim().isEmpty()){where.append(" AND o.number LIKE ?");args.add("%"+query.get("number").trim()+"%");}
        if(query.get("supplier")!=null && !query.get("supplier").trim().isEmpty()){where.append(" AND (o.supplier=? OR c.name LIKE ? OR c.number LIKE ?)");String q=query.get("supplier").trim();Collections.addAll(args,q,"%"+q+"%","%"+q+"%");}
        for(String state:Arrays.asList("examine","nucleus"))if(query.get(state)!=null && !query.get(state).isEmpty()){String value=query.get(state);if(!(state.equals("examine")?Arrays.asList("0","1"):Arrays.asList("0","1","2")).contains(value))throw new IllegalArgumentException("单据状态筛选无效");where.append(" AND o.").append(state).append("=?");args.add(Integer.parseInt(value));}
        for(String key:Arrays.asList("startTime","endTime"))if(query.get(key)!=null && !query.get(key).isEmpty()){LocalDate date;try{date=LocalDate.parse(query.get(key));}catch(Exception error){throw new IllegalArgumentException("查询日期无效");}where.append(" AND DATE(o.time)").append(key.equals("startTime")?">=?":"<=?");args.add(date);}
        String from=" FROM omy o LEFT JOIN supplier c ON c.id=o.supplier";
        Long total=db.queryForObject("SELECT COUNT(*)"+from+where,Long.class,args.toArray());List<Object> paged=new ArrayList<>(args);paged.add(size);paged.add((page-1)*size);
        List<Map<String,Object>> rows=db.queryForList("SELECT o.*,c.name AS supplierName,DATE_FORMAT(o.time,'%Y-%m-%d') AS timeText,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state"+from+where+" ORDER BY o.time DESC,o.id DESC LIMIT ? OFFSET ?",paged.toArray());
        List<String> ids=new ArrayList<>();for(Map<String,Object> row:rows)ids.add(s(row.get("id")));Map<String,String> hashes=versions.paymentVersions(ids);
        for(Map<String,Object> row:rows){row.put("examine",row.remove("approval_state"));row.put("nucleus",row.remove("settlement_state"));row.put("version",hashes.get(s(row.get("id"))));}
        Map<String,Object> result=new LinkedHashMap<>();result.put("rows",rows);result.put("total",total);result.put("pageIndex",page);result.put("pageSize",size);return result;
    }
}
