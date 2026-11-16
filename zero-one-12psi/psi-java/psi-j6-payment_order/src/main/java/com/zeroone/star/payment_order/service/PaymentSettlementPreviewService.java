package com.zeroone.star.payment_order.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.math.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Read a reviewable original-document allocation; this service never pays or settles anything. */
@Service
public class PaymentSettlementPreviewService {
    private final JdbcTemplate db;private final PaymentDocumentAccess access;
    public PaymentSettlementPreviewService(JdbcTemplate db,PaymentDocumentAccess access){this.db=db;this.access=access;}
    private String s(Object v){return Objects.toString(v,"");}
    private BigDecimal d(Object v){return v==null?BigDecimal.ZERO:new BigDecimal(v.toString());}
    private String digest(List<Map<String,Object>> rows){
        StringBuilder value=new StringBuilder();for(Map<String,Object> row:rows){value.append('{');for(String key:new TreeSet<>(row.keySet())){String raw=Objects.toString(row.get(key),"<null>");value.append(key.length()).append(':').append(key).append(raw.length()).append(':').append(raw);}value.append('}');}
        try{StringBuilder result=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(value.toString().getBytes(StandardCharsets.UTF_8)))result.append(String.format("%02x",b&255));return result.toString();}catch(Exception error){throw new IllegalStateException("付款版本生成失败",error);}
    }
    private Map<String,Object> one(List<Map<String,Object>> rows,String message){if(rows.size()!=1)throw new IllegalArgumentException(message);return rows.get(0);}
    public String paymentVersion(String id){
        List<Map<String,Object>> rows=new ArrayList<>(db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM omy o WHERE id=?",id));
        if(rows.size()!=1)throw new IllegalArgumentException("付款单不存在");
        rows.addAll(db.queryForList("SELECT * FROM omy_info WHERE pid=? ORDER BY id",id));rows.addAll(db.queryForList("SELECT * FROM omy_bill WHERE pid=? ORDER BY id",id));
        rows.addAll(db.queryForList("SELECT * FROM record WHERE type='omy' AND source=? ORDER BY id",id));return digest(rows);
    }
    public Map<String,String> paymentVersions(List<String> ids){
        if(ids.isEmpty())return Collections.emptyMap();if(ids.size()>200)throw new IllegalArgumentException("付款列表版本读取超限");
        String in=String.join(",",Collections.nCopies(ids.size(),"?"));Object[] args=ids.toArray();Map<String,List<Map<String,Object>>> groups=new LinkedHashMap<>();
        for(Map<String,Object> head:db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM omy o WHERE id IN ("+in+")",args))groups.put(s(head.get("id")),new ArrayList<>(Collections.singletonList(head)));
        for(String table:Arrays.asList("omy_info","omy_bill"))for(Map<String,Object> line:db.queryForList("SELECT * FROM "+table+" WHERE pid IN ("+in+") ORDER BY pid,id",args)){List<Map<String,Object>> rows=groups.get(s(line.get("pid")));if(rows!=null)rows.add(line);}
        for(Map<String,Object> line:db.queryForList("SELECT * FROM record WHERE type='omy' AND source IN ("+in+") ORDER BY source,id",args)){List<Map<String,Object>> rows=groups.get(s(line.get("source")));if(rows!=null)rows.add(line);}
        Map<String,String> result=new LinkedHashMap<>();for(Map.Entry<String,List<Map<String,Object>>> entry:groups.entrySet())result.put(entry.getKey(),digest(entry.getValue()));return result;
    }
    private List<Map<String,Object>> documents(String type,Map<String,Object> payment){
        String marker=type.equals("buy")?"psi_purchase_posting":"psi_purchase_return_posting",markerId=type.equals("buy")?"purchase_id":"return_id";
        // Aggregate closed histories in one query; their count must not block new business.
        // Validate every matching head before excluding closed ones, including corrupt history.
        List<Map<String,Object>> rows=db.queryForList("SELECT h.id,h.number,h.time,h.frame,h.supplier,h.actual,h.money,CAST(h.examine AS SIGNED) AS approval_state,CAST(h.nucleus AS SIGNED) AS settlement_state,COALESCE(SUM(b.money),0) AS paid_total,MIN(b.money) AS minimum_payment FROM "+type+" h LEFT JOIN "+type+"_bill b ON b.pid=h.id WHERE h.frame=? AND h.supplier=? AND h.examine=1 AND DATE(h.time)<=DATE(?) GROUP BY h.id ORDER BY h.time,h.id",payment.get("frame"),payment.get("supplier"),payment.get("time"));
        List<Map<String,Object>> result=new ArrayList<>();
        for(Map<String,Object> row:rows){
            BigDecimal paid=d(row.remove("paid_total")),minimum=d(row.remove("minimum_payment"));
            if(minimum.signum()<0)throw new IllegalArgumentException("来源单据核销金额无效，请先核对历史数据");
            BigDecimal actual=d(row.get("actual")),remaining=actual.subtract(paid);
            if(actual.signum()<0 || remaining.signum()<0)throw new IllegalArgumentException("来源单据已核销金额超过实际金额");
            int expected=paid.signum()==0?0:remaining.signum()==0?2:1;
            if(((Number)row.get("settlement_state")).intValue()!=expected)throw new IllegalArgumentException("来源单据核销状态与实际核销明细不一致");
            if(remaining.signum()==0)continue;
            List<Map<String,Object>> bills=db.queryForList("SELECT * FROM "+type+"_bill WHERE pid=? ORDER BY id",row.get("id"));
            if(db.queryForObject("SELECT COUNT(*) FROM "+marker+" WHERE "+markerId+"=?",Integer.class,row.get("id"))!=1)throw new IllegalArgumentException("来源单据只有审核标记，缺少实际入账凭据");
            List<Map<String,Object>> evidence=new ArrayList<>();evidence.add(new LinkedHashMap<>(row));evidence.addAll(bills);evidence.addAll(db.queryForList("SELECT id FROM record WHERE type=? AND source=? ORDER BY id",type,row.get("id")));
            row.put("version",digest(evidence));row.put("type",type);row.put("settled",paid);row.put("remaining",remaining);result.add(row);
        }
        return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> preview(String id){
        UserDTO actor=access.authorize("/payment-order/modify-examine-status");
        Map<String,Object> payment=one(db.queryForList("SELECT o.*,CAST(o.examine AS SIGNED) AS approval_state,CAST(o.nucleus AS SIGNED) AS settlement_state FROM omy o WHERE id=?",id),"付款单不存在");
        access.requireFrame(actor,s(payment.get("frame")));
        if(((Number)payment.get("approval_state")).intValue()!=0 || ((Number)payment.get("settlement_state")).intValue()!=0 || db.queryForObject("SELECT COUNT(*) FROM omy_bill WHERE pid=?",Integer.class,id)>0)throw new IllegalArgumentException("请从未审核、未核销的付款草稿准备结算方案");
        BigDecimal cash=d(payment.get("total"));if(cash.signum()<=0)throw new IllegalArgumentException("付款金额必须大于0");
        List<Map<String,Object>> purchases=documents("buy",payment),credits=documents("bre",payment);
        BigDecimal invoices=BigDecimal.ZERO,returns=BigDecimal.ZERO;
        for(Map<String,Object> row:purchases)invoices=invoices.add(d(row.get("remaining")));
        for(Map<String,Object> row:credits)returns=returns.add(d(row.get("remaining")));
        BigDecimal net=invoices.subtract(returns);
        if(net.compareTo(cash)<0)throw new IllegalArgumentException("付款金额超过当前采购减退货的待结算净额，请核对金额及已审核来源单据");
        BigDecimal credit=returns.min(invoices.subtract(cash)),invoiceTarget=cash.add(credit),creditTarget=credit;
        List<Map<String,Object>> allocations=new ArrayList<>();
        for(List<Map<String,Object>> group:Arrays.asList(purchases,credits))for(Map<String,Object> source:group){
            boolean purchase="buy".equals(source.get("type"));BigDecimal left=purchase?invoiceTarget:creditTarget,amount=d(source.get("remaining")).min(left);
            if(amount.signum()==0)continue;
            Map<String,Object> allocation=new LinkedHashMap<>();for(String key:Arrays.asList("id","type","number","version","remaining"))allocation.put(key,source.get(key));
            allocation.put("money",purchase?amount:amount.negate());allocations.add(allocation);
            if(purchase)invoiceTarget=invoiceTarget.subtract(amount);else creditTarget=creditTarget.subtract(amount);
        }
        if(invoiceTarget.signum()!=0 || creditTarget.signum()!=0)throw new IllegalStateException("来源结算方案不完整");
        List<Map<String,Object>> documents=new ArrayList<>(purchases);documents.addAll(credits);
        Map<String,Object> result=new LinkedHashMap<>();result.put("payment",id);result.put("version",paymentVersion(id));result.put("cash",cash);result.put("invoiceTotal",invoices);result.put("creditTotal",returns);result.put("payableNet",net);result.put("allocations",allocations);result.put("documents",documents);result.put("source","oldest-unsettled-first");return result;
    }
}
