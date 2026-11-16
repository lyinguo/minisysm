package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReturnReviewCommand;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import org.springframework.util.DigestUtils;
import javax.annotation.PostConstruct;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** One reviewed command = return stock, source quantity, refund and customer credit in one transaction. */
@Service
public class SaleReturnPostingService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleDraftService sales;
    private final SaleReturnDraftService drafts;
    private final SaleReturnSnapshotService versions;
    private final SaleReturnStockService stock;
    public SaleReturnPostingService(JdbcTemplate db,SaleDocumentAccess access,SaleDraftService sales,SaleReturnDraftService drafts,SaleReturnSnapshotService versions,SaleReturnStockService stock){this.db=db;this.access=access;this.sales=sales;this.drafts=drafts;this.versions=versions;this.stock=stock;}
    @PostConstruct public void initialize(){
        db.execute("CREATE TABLE IF NOT EXISTS psi_sale_return_posting (return_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(32) NOT NULL,ledger_fingerprint VARCHAR(32) NOT NULL,created_at DATETIME NOT NULL)");
    }
    private String id(){return UUID.randomUUID().toString().replace("-","");}
    private String s(Object value){return value==null?"":value.toString();}
    private BigDecimal d(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private int n(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?-1:((Number)value).intValue();}
    private int count(String statement,Object... args){return db.queryForObject(statement,Integer.class,args);}
    private String digest(List<Map<String,Object>> rows){
        StringBuilder canonical=new StringBuilder();
        for(Map<String,Object> row:rows){canonical.append('{');for(String key:new TreeSet<>(row.keySet())){String value=Objects.toString(row.get(key),"<null>");canonical.append(key.length()).append(':').append(key).append(value.length()).append(':').append(value);}canonical.append('}');}
        return DigestUtils.md5DigestAsHex(canonical.toString().getBytes(StandardCharsets.UTF_8));
    }
    private String fingerprint(Map<String,Object> head,List<Map<String,Object>> lines){
        Map<String,Object> immutable=new LinkedHashMap<>(head);immutable.remove("examine");immutable.remove("nucleus");
        immutable.keySet().removeIf(key->key.endsWith("_state"));List<Map<String,Object>> rows=new ArrayList<>();rows.add(immutable);rows.addAll(lines);return digest(rows);
    }
    private String ledgerFingerprint(String identifier){
        List<Map<String,Object>> rows=new ArrayList<>();
        for(String table:Arrays.asList("room_info","batch_info","serial_info","serve_info","account_info")){
            rows.add(Collections.singletonMap("table",table));rows.addAll(db.queryForList("SELECT * FROM "+table+" WHERE type='sre' AND `class`=? ORDER BY id FOR UPDATE",identifier));
        }
        rows.add(Collections.singletonMap("table","summary"));
        rows.addAll(db.queryForList("SELECT id,pid,type,`class`,info,time,goods,attr,warehouse,batch,mfd,serial,direction,price,nums,bct FROM summary WHERE type='sre' AND `class`=? ORDER BY id FOR UPDATE",identifier));
        rows.add(Collections.singletonMap("table","sre_bill"));rows.addAll(db.queryForList("SELECT * FROM sre_bill WHERE pid=? ORDER BY id FOR UPDATE",identifier));
        return digest(rows);
    }
    @Transactional(rollbackFor=Exception.class,isolation=Isolation.READ_COMMITTED)
    public int post(SaleReturnReviewCommand command){
        UserDTO actor=access.authorize("/sale/return/return/examine");
        if(command==null || command.getStatus()==null || (command.getStatus()!=0 && command.getStatus()!=1))throw new IllegalArgumentException("审核目标只能为0或1");
        Map<String,String> expected=versions.expected(command.getIds(),command.getVersion(),command.getVersions());
        sales.lockWrites();List<String> ids=new ArrayList<>(command.getIds());Collections.sort(ids);int changed=0;
        // Multiple returns can share one source. Validate all displayed versions before this
        // transaction changes that source's returned quantity; do not silently reread versions.
        for(String identifier:ids){Map<String,Object> head=drafts.lockForReview(identifier);access.requireFrame(actor,s(head.get("frame")));versions.require(identifier,expected.get(identifier));}
        for(String identifier:ids){
            Map<String,Object> head=drafts.lockForReview(identifier);access.requireFrame(actor,s(head.get("frame")));
            List<Map<String,Object>> lines=db.queryForList("SELECT * FROM sre_info WHERE pid=? ORDER BY id FOR UPDATE",identifier);
            List<Map<String,Object>> markers=db.queryForList("SELECT * FROM psi_sale_return_posting WHERE return_id=? FOR UPDATE",identifier);
            int approval=n(head.get("approval_state"));boolean target=command.getStatus()==1;
            if(approval!=0 && approval!=1)throw new IllegalStateException("退货审核状态无效");
            if(approval==1){
                if(markers.size()!=1 || !fingerprint(head,lines).equals(s(markers.get(0).get("fingerprint"))) || !ledgerFingerprint(identifier).equals(s(markers.get(0).get("ledger_fingerprint"))))throw new IllegalStateException("退货原入账凭据缺失或已变化，不能重复入账或自动撤销");
            }else if(!markers.isEmpty())throw new IllegalStateException("未审核退货单存在入账凭据，请先核对");
            if((approval==1)==target)continue;
            if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)throw new IllegalArgumentException("退货日期已结账，不能审核或反审核");
            if(lines.isEmpty() || lines.size()>200)throw new IllegalArgumentException("退货明细缺失或超过200条");
            if(count("SELECT COUNT(*) FROM sell WHERE id=? AND examine=1 AND time<=?",head.get("source"),head.get("time"))!=1 || count("SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id=?",head.get("source"))!=1)throw new IllegalArgumentException("原销售单未实际入账或退货日期早于销售日期");
            db.queryForList("SELECT id FROM goods WHERE id IN (SELECT goods FROM sre_info WHERE pid=?) ORDER BY id FOR UPDATE",identifier);
            if(target){
                if(n(head.get("check_state"))!=1)throw new IllegalArgumentException("销售退货单未核对，不能审核");
                drafts.validateForReview(head);
                for(Map<String,Object> line:lines){stock.forward(head,line);sourceQuantity(head,line,true);}
                money(head,true);
                int settlement=d(head.get("money")).compareTo(d(head.get("actual")))==0?2:d(head.get("money")).signum()==0?0:1;
                db.update("UPDATE sre SET examine=1,nucleus=? WHERE id=?",settlement,identifier);
                db.update("INSERT INTO psi_sale_return_posting(return_id,fingerprint,ledger_fingerprint,created_at) VALUES(?,?,?,CURRENT_TIMESTAMP)",identifier,fingerprint(head,lines),ledgerFingerprint(identifier));
            }else{
                downstream(head);
                stock.reverse(identifier);
                for(Map<String,Object> line:lines)sourceQuantity(head,line,false);
                money(head,false);
                db.update("UPDATE sre SET examine=0,nucleus=0 WHERE id=?",identifier);
                db.update("DELETE FROM psi_sale_return_posting WHERE return_id=?",identifier);
            }
            java.sql.Timestamp now=new java.sql.Timestamp(System.currentTimeMillis());String action=target?"审核销售退货单":"反审核销售退货单";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'sre',?,?,?,?)",id(),identifier,now,actor.getId(),action);
            db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",id(),now,actor.getId(),action+"["+identifier+"]");changed++;
        }
        return changed;
    }
    private void sourceQuantity(Map<String,Object> head,Map<String,Object> line,boolean forward){
        BigDecimal quantity=d(line.get("nums"));if(!forward)quantity=quantity.negate();
        if(db.update("UPDATE sell_info SET retreat=COALESCE(retreat,0)+? WHERE id=? AND pid=? AND COALESCE(retreat,0)+? BETWEEN 0 AND nums",quantity,line.get("source"),head.get("source"),quantity)!=1)throw new IllegalStateException("原销售退货数量不足或已被其他单据占用");
    }
    private void downstream(Map<String,Object> head){
        String identifier=s(head.get("id"));
        if(count("SELECT COUNT(*) FROM sre_bill WHERE pid=? AND NOT(type='sre' AND source=?)",identifier,identifier)>0
            || count("SELECT COUNT(*) FROM imy_bill WHERE source=?",identifier)>0 || count("SELECT COUNT(*) FROM omy_bill WHERE source=?",identifier)>0
            || count("SELECT COUNT(*) FROM bill_info WHERE source=?",identifier)>0 || count("SELECT COUNT(*) FROM invoice WHERE LOWER(type)='sre' AND `class`=?",identifier)>0
            || count("SELECT COUNT(*) FROM cost WHERE LOWER(type)='sre' AND `class`=?",identifier)>0
            || (n(head.get("cost_state"))!=0 && n(head.get("cost_state"))!=3) || (n(head.get("invoice_state"))!=0 && n(head.get("invoice_state"))!=3))throw new IllegalArgumentException("退货单已有后续退款核销、发票或费用关联，请先处理后续单据");
        int settlement=d(head.get("money")).compareTo(d(head.get("actual")))==0?2:d(head.get("money")).signum()==0?0:1;
        if(n(head.get("settlement_state"))!=settlement)throw new IllegalStateException("退货核销状态与原入账退款不一致");
    }
    private void money(Map<String,Object> head,boolean forward){
        String identifier=s(head.get("id")),frame=s(head.get("frame"));BigDecimal refund=d(head.get("money")),credit=d(head.get("actual")).subtract(refund);
        List<Map<String,Object>> customers=db.queryForList("SELECT id,frame FROM customer WHERE id=? FOR UPDATE",head.get("customer"));
        if(customers.size()!=1 || (!"0".equals(s(customers.get(0).get("frame"))) && !frame.equals(s(customers.get(0).get("frame")))))throw new IllegalArgumentException("客户不存在或组织已变化");
        if(refund.signum()<0 || credit.signum()<0)throw new IllegalArgumentException("实际退款不得为负数或超过退货价税合计");
        if(refund.signum()>0){
            List<Map<String,Object>> accounts=db.queryForList("SELECT id,frame,balance FROM account WHERE id=? FOR UPDATE",head.get("account"));
            if(accounts.size()!=1 || (!"0".equals(s(accounts.get(0).get("frame"))) && !frame.equals(s(accounts.get(0).get("frame")))))throw new IllegalArgumentException("退款账户不存在或组织已变化");
            if(forward && d(accounts.get(0).get("balance")).compareTo(refund)<0)throw new IllegalStateException("账户余额不足以支付本次实际退款");
            if(!forward && (count("SELECT COUNT(*) FROM account_info WHERE type='sre' AND `class`=? AND pid=? AND direction=0 AND money=?",identifier,head.get("account"),refund)!=1
                || count("SELECT COUNT(*) FROM sre_bill WHERE pid=? AND type='sre' AND source=? AND money=?",identifier,identifier,refund)!=1))throw new IllegalStateException("原退款流水与核销凭据不一致");
            db.update("UPDATE account SET balance=COALESCE(balance,0)+? WHERE id=?",forward?refund.negate():refund,head.get("account"));
            if(forward){
                db.update("INSERT INTO account_info(id,pid,type,`class`,time,direction,money) VALUES(?,?,'sre',?,?,0,?)",id(),head.get("account"),identifier,head.get("time"),refund);
                db.update("INSERT INTO sre_bill(id,pid,type,source,time,money) VALUES(?,?,'sre',?,?,?)",id(),identifier,identifier,head.get("time"),refund);
            }else{
                db.update("DELETE FROM account_info WHERE type='sre' AND `class`=?",identifier);
                db.update("DELETE FROM sre_bill WHERE pid=? AND type='sre' AND source=?",identifier,identifier);
            }
        }
        db.update("UPDATE customer SET balance=COALESCE(balance,0)+? WHERE id=?",forward?credit.negate():credit,head.get("customer"));
    }
}
