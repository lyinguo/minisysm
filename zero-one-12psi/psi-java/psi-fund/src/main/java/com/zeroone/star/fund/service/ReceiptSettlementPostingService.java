package com.zeroone.star.fund.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import javax.annotation.PostConstruct;
import java.math.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Cash, original invoices and return credits form one reviewed financial transaction. */
@Service
public class ReceiptSettlementPostingService {
    public static class Allocation {public String id,type,version;public BigDecimal money;}
    public static class Command {public String id,version;public Integer status;public List<Allocation> allocations;}
    private final JdbcTemplate db;private final ReceiptDocumentAccess access;private final ReceiptSettlementPreviewService previews;
    public ReceiptSettlementPostingService(JdbcTemplate db,ReceiptDocumentAccess access,ReceiptSettlementPreviewService previews){this.db=db;this.access=access;this.previews=previews;}
    @PostConstruct public void initialize(){db.execute("CREATE TABLE IF NOT EXISTS psi_receipt_posting(receipt_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(64) NOT NULL,ledger_fingerprint VARCHAR(64) NOT NULL,created_at DATETIME NOT NULL)");}
    private String id(){return UUID.randomUUID().toString().replace("-","");}
    private String s(Object v){return Objects.toString(v,"");}
    private BigDecimal d(Object v){return v==null?BigDecimal.ZERO:new BigDecimal(v.toString());}
    private int n(Object v){return v instanceof Boolean?((Boolean)v?1:0):v==null?-1:((Number)v).intValue();}
    private int count(String query,Object... args){return db.queryForObject(query,Integer.class,args);}
    private Map<String,Object> one(List<Map<String,Object>> rows,String message){if(rows.size()!=1)throw new IllegalArgumentException(message);return rows.get(0);}
    private BigDecimal amount(BigDecimal value,boolean signed){if(value==null || (!signed && value.signum()<=0) || value.signum()==0)throw new IllegalArgumentException("结算金额必须是有效非零金额");try{value=value.setScale(4,RoundingMode.UNNECESSARY);}catch(ArithmeticException error){throw new IllegalArgumentException("结算金额最多4位小数");}if(value.precision()>16)throw new IllegalArgumentException("结算金额超出范围");return value;}
    private String hash(List<Map<String,Object>> rows){StringBuilder text=new StringBuilder();for(Map<String,Object> row:rows){text.append('{');for(String key:new TreeSet<>(row.keySet())){String value=Objects.toString(row.get(key),"<null>");text.append(key.length()).append(':').append(key).append(value.length()).append(':').append(value);}text.append('}');}try{StringBuilder out=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(text.toString().getBytes(StandardCharsets.UTF_8)))out.append(String.format("%02x",b&255));return out.toString();}catch(Exception error){throw new IllegalStateException("收款凭据校验失败",error);}}
    private String fingerprint(Map<String,Object> head,List<Map<String,Object>> lines){Map<String,Object> immutable=new LinkedHashMap<>(head);immutable.remove("examine");immutable.remove("nucleus");immutable.keySet().removeIf(key->key.endsWith("_state"));List<Map<String,Object>> rows=new ArrayList<>();rows.add(immutable);rows.addAll(lines);return hash(rows);}
    private String ledger(String payment){List<Map<String,Object>> rows=new ArrayList<>();for(String table:Arrays.asList("account_info","imy_bill","sell_bill","sre_bill")){rows.add(Collections.singletonMap("table",table));String where=table.equals("account_info")?"type='imy' AND `class`=?":table.equals("imy_bill")?"pid=?":"type='imy' AND source=?";rows.addAll(db.queryForList("SELECT * FROM "+table+" WHERE "+where+" ORDER BY id FOR UPDATE",payment));}return hash(rows);}
    private void lock(String scope){db.update("INSERT INTO psi_document_write_lock(scope) VALUES(?) ON DUPLICATE KEY UPDATE scope=VALUES(scope)",scope);db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope=? FOR UPDATE",String.class,scope);}
    private Map<String,Object> head(String payment){return one(db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM imy o WHERE id=? FOR UPDATE",payment),"收款单不存在");}
    private void reference(String table,String identifier,String frame){Map<String,Object> row=one(db.queryForList("SELECT id,frame FROM "+table+" WHERE id=? FOR UPDATE",identifier),"客户或结算账户不存在");if(!"0".equals(s(row.get("frame"))) && !frame.equals(s(row.get("frame"))))throw new IllegalArgumentException("客户或账户所属组织与收款单不一致");}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> document(String payment){UserDTO actor=access.authorize("/fund/receipt/fundReceiptDetail");Map<String,Object> head=one(db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM imy o WHERE id=?",payment),"收款单不存在");access.requireFrame(actor,s(head.get("frame")));head.put("examine",head.remove("approval_state"));head.put("nucleus",head.remove("settlement_state"));Map<String,Object> result=new LinkedHashMap<>();result.put("header",head);result.put("version",previews.receiptVersion(payment));result.put("items",db.queryForList("SELECT * FROM imy_info WHERE pid=? ORDER BY id",payment));result.put("allocations",db.queryForList("SELECT * FROM imy_bill WHERE pid=? ORDER BY id",payment));return result;}
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    @SuppressWarnings("unchecked")
    public int post(Command command){
        UserDTO actor=access.authorize("/fund/receipt/audit");
        if(command==null || command.id==null || command.id.isEmpty() || command.id.length()>32 || command.status==null || (command.status!=0 && command.status!=1) || command.version==null || !command.version.matches("[0-9a-f]{64}"))throw new IllegalArgumentException("请提交收款单及已读版本、明确的审核目标");
        lock("imy");lock("sell");Map<String,Object> head=head(command.id);access.requireFrame(actor,s(head.get("frame")));
        if(!command.version.equals(previews.receiptVersion(command.id)))throw new IllegalArgumentException("收款单已变化，请重新读取并核对，本次未处理");
        List<Map<String,Object>> lines=db.queryForList("SELECT * FROM imy_info WHERE pid=? ORDER BY id FOR UPDATE",command.id);
        List<Map<String,Object>> proof=db.queryForList("SELECT * FROM psi_receipt_posting WHERE receipt_id=? FOR UPDATE",command.id);
        int approved=n(head.get("approval_state"));boolean target=command.status==1;
        if(approved!=0 && approved!=1)throw new IllegalArgumentException("收款单审核状态无效");
        if(approved==1){if(proof.size()!=1 || !fingerprint(head,lines).equals(s(proof.get(0).get("fingerprint"))) || !ledger(command.id).equals(s(proof.get(0).get("ledger_fingerprint"))))throw new IllegalArgumentException("原收款入账凭据缺失或已变化，不能自动反冲或重复入账");}
        else if(!proof.isEmpty())throw new IllegalArgumentException("未审核收款单存在入账凭据");
        if((approved==1)==target)return 0;
        if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)throw new IllegalArgumentException("收款日期已结账，不能审核或反审核");
        BigDecimal total=amount(d(head.get("total")),false),sum=BigDecimal.ZERO;TreeMap<String,BigDecimal> cash=new TreeMap<>();
        if(lines.isEmpty() || lines.size()>200)throw new IllegalArgumentException("收款账户明细缺失或超限");
        for(Map<String,Object> line:lines){BigDecimal value=amount(d(line.get("money")),false);sum=sum.add(value);cash.merge(s(line.get("account")),value,BigDecimal::add);}
        if(sum.compareTo(total)!=0)throw new IllegalArgumentException("收款主从金额不一致");
        reference("customer",s(head.get("customer")),s(head.get("frame")));
        for(String account:cash.keySet())reference("account",account,s(head.get("frame")));
        if(target){
            if(n(head.get("settlement_state"))!=0 || count("SELECT COUNT(*) FROM account_info WHERE type='imy' AND `class`=?",command.id)>0)throw new IllegalArgumentException("收款草稿已有结算或资金流水");
            Map<String,Object> plan=previews.preview(command.id);Map<String,Map<String,Object>> sources=new HashMap<>();
            for(Map<String,Object> row:(List<Map<String,Object>>)plan.get("documents"))sources.put(row.get("type")+":"+row.get("id"),row);
            if(command.allocations==null || command.allocations.isEmpty() || command.allocations.size()>200)throw new IllegalArgumentException("请选择原销售单及退货抵扣，并核对结算方案");
            BigDecimal net=BigDecimal.ZERO,credits=BigDecimal.ZERO;Set<String> seen=new HashSet<>();
            for(Allocation allocation:command.allocations){
                if(allocation==null || !Arrays.asList("sell","sre").contains(allocation.type))throw new IllegalArgumentException("结算来源类型无效");
                String key=allocation.type+":"+allocation.id;Map<String,Object> source=sources.get(key);BigDecimal value=amount(allocation.money,true);
                if(!seen.add(key) || source==null || !Objects.equals(source.get("version"),allocation.version) || value.abs().compareTo(d(source.get("remaining")))>0 || ("sell".equals(allocation.type)?value.signum()<0:value.signum()>0))throw new IllegalArgumentException("来源单据、已读版本或结算金额已变化，请重新核对方案");
                net=net.add(value);if(value.signum()<0)credits=credits.add(value.abs());
            }
            if(net.compareTo(total)!=0)throw new IllegalArgumentException("销售结算减退货抵扣必须等于本次实际收款");
            if(total.compareTo(d(plan.get("receivableNet")))==0 && credits.compareTo(d(plan.get("creditTotal")))!=0)throw new IllegalArgumentException("本次收款将结清净应收，请同时关联全部剩余退货抵扣，可重新核对建议分配方案");
            for(Map.Entry<String,BigDecimal> entry:cash.entrySet())if(db.update("UPDATE account SET balance=COALESCE(balance,0)+? WHERE id=?",entry.getValue(),entry.getKey())!=1)throw new IllegalArgumentException("收款账户不存在，未执行入账");
            if(db.update("UPDATE customer SET balance=COALESCE(balance,0)-? WHERE id=? AND COALESCE(balance,0)>=?",total,head.get("customer"),total)!=1)throw new IllegalArgumentException("客户应收余额不足，请核对已有收款和历史核销");
            for(Map.Entry<String,BigDecimal> entry:cash.entrySet())db.update("INSERT INTO account_info(id,pid,type,`class`,time,direction,money) VALUES(?,?,'imy',?,?,1,?)",id(),entry.getKey(),command.id,head.get("time"),entry.getValue());
            for(Allocation allocation:command.allocations){db.update("INSERT INTO imy_bill(id,pid,type,source,time,money) VALUES(?,?,?,?,?,?)",id(),command.id,allocation.type,allocation.id,head.get("time"),allocation.money);db.update("INSERT INTO "+allocation.type+"_bill(id,pid,type,source,time,money) VALUES(?,?,'imy',?,?,?)",id(),allocation.id,command.id,head.get("time"),allocation.money.abs());settlement(allocation.type,allocation.id);sourceHistory(allocation.type,allocation.id,actor,head,true);}
            db.update("UPDATE imy SET examine=1,nucleus=2 WHERE id=?",command.id);
            db.update("INSERT INTO psi_receipt_posting(receipt_id,fingerprint,ledger_fingerprint,created_at) VALUES(?,?,?,CURRENT_TIMESTAMP)",command.id,fingerprint(head,lines),ledger(command.id));
        }else{
            if(count("SELECT COUNT(*) FROM cost WHERE LOWER(type)='imy' AND `class`=?",command.id)>0 || count("SELECT COUNT(*) FROM imy_bill WHERE source=? AND pid<>?",command.id,command.id)>0)throw new IllegalArgumentException("收款单已关联费用或其他收款核销，请先处理关联单据后再反审核");
            if(n(head.get("settlement_state"))!=2 || count("SELECT COUNT(*) FROM bill_info WHERE source=?",command.id)>0 || count("SELECT COUNT(*) FROM omy_bill WHERE source=?",command.id)>0 || count("SELECT COUNT(*) FROM invoice WHERE LOWER(type)='imy' AND `class`=?",command.id)>0)throw new IllegalArgumentException("收款单存在后续关联或状态变化，请先处理后续单据");
            List<Map<String,Object>> allocations=db.queryForList("SELECT * FROM imy_bill WHERE pid=? ORDER BY type,source FOR UPDATE",command.id);
            if(allocations.isEmpty())throw new IllegalArgumentException("原收款没有核销来源凭据");
            for(Map<String,Object> allocation:allocations){String type=s(allocation.get("type"));if(!Arrays.asList("sell","sre").contains(type))throw new IllegalArgumentException("原核销来源类型无效");Map<String,Object> source=one(db.queryForList("SELECT frame,customer,CAST(examine AS SIGNED) AS approval_state FROM "+type+" WHERE id=? FOR UPDATE",allocation.get("source")),"原核销单据不存在");if(!Objects.equals(source.get("frame"),head.get("frame")) || !Objects.equals(source.get("customer"),head.get("customer")) || n(source.get("approval_state"))!=1)throw new IllegalArgumentException("原核销单据归属或状态已变化");}
            for(Map.Entry<String,BigDecimal> entry:cash.entrySet())if(db.update("UPDATE account SET balance=COALESCE(balance,0)-? WHERE id=? AND COALESCE(balance,0)>=?",entry.getValue(),entry.getKey(),entry.getValue())!=1)throw new IllegalArgumentException("账户余额不足以撤销本次收款，请先处理后续资金使用");
            db.update("UPDATE customer SET balance=COALESCE(balance,0)+? WHERE id=?",total,head.get("customer"));
            for(Map<String,Object> allocation:allocations){String type=s(allocation.get("type"));db.update("DELETE FROM "+type+"_bill WHERE pid=? AND type='imy' AND source=?",allocation.get("source"),command.id);settlement(type,s(allocation.get("source")));sourceHistory(type,s(allocation.get("source")),actor,head,false);}
            db.update("DELETE FROM account_info WHERE type='imy' AND `class`=?",command.id);db.update("DELETE FROM imy_bill WHERE pid=?",command.id);db.update("DELETE FROM psi_receipt_posting WHERE receipt_id=?",command.id);db.update("UPDATE imy SET examine=0,nucleus=0 WHERE id=?",command.id);
        }
        java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());String action=target?"审核收款并核销销售退货":"反审核收款并撤销原单核销";
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'imy',?,?,?,?)",id(),command.id,now,actor.getId(),action);db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",id(),now,actor.getId(),action+"["+command.id+"]");return 1;
    }
    private void sourceHistory(String type,String source,UserDTO actor,Map<String,Object> payment,boolean forward){String action=(forward?"收款核销关联":"撤销收款核销关联")+"["+s(payment.get("number"))+"]";db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,?,?,CURRENT_TIMESTAMP,?,?)",id(),type,source,actor.getId(),action);}
    private void settlement(String type,String source){Map<String,Object> head=one(db.queryForList("SELECT actual FROM "+type+" WHERE id=? FOR UPDATE",source),"原核销单据不存在");BigDecimal paid=db.queryForObject("SELECT COALESCE(SUM(money),0) FROM "+type+"_bill WHERE pid=?",BigDecimal.class,source);if(paid.signum()<0 || paid.compareTo(d(head.get("actual")))>0)throw new IllegalArgumentException("原单核销总额超出实际金额");int state=paid.signum()==0?0:paid.compareTo(d(head.get("actual")))==0?2:1;db.update("UPDATE "+type+" SET nucleus=? WHERE id=?",state,source);}
}
