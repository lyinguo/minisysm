package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/** Source quantities include actual receipts plus still-pending purchase drafts. */
@Service
public class PurchaseOrderSources {
    private final JdbcTemplate db;private final PurchaseDocumentAccess access;private final PurchaseSupplyService supply;
    public PurchaseOrderSources(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseSupplyService supply){this.db=db;this.access=access;this.supply=supply;}
    public static String text(Object v){return v==null?"":v.toString();}
    public static BigDecimal decimal(Object v){return v==null?BigDecimal.ZERO:new BigDecimal(v.toString());}
    public static BigDecimal rate(Map<String,Object> row,boolean discount){
        BigDecimal raw=decimal(row.get(discount?"discount":"tax")),base=discount?decimal(row.get("price")).multiply(decimal(row.get("nums"))).setScale(4,RoundingMode.HALF_UP):decimal(row.get("total")),hint=decimal(row.get(discount?"dsc":"tat"));
        if(raw.compareTo(BigDecimal.ONE)<=0 && base.multiply(raw).movePointLeft(2).setScale(4,RoundingMode.HALF_UP).compareTo(hint)!=0){BigDecimal fraction=discount?BigDecimal.ONE.subtract(raw):raw;if(base.multiply(fraction).setScale(4,RoundingMode.HALF_UP).compareTo(hint)==0)return fraction.movePointRight(2);}
        return raw;
    }
    private int integer(Object v){return v instanceof Boolean?((Boolean)v?1:0):v==null?0:((Number)v).intValue();}
    public void lock(){for(String scope:Arrays.asList("buy","bor")){db.update("INSERT INTO psi_document_write_lock(scope) VALUES(?) ON DUPLICATE KEY UPDATE scope=VALUES(scope)",scope);db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope=? FOR UPDATE",String.class,scope);}}
    public Map<String,Object> header(String id){
        List<Map<String,Object>> found=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS source_approval,CAST(b.state AS SIGNED) AS source_state FROM bor b WHERE b.id=? FOR UPDATE",id);
        if(found.size()!=1)throw new IllegalArgumentException("来源采购订单不存在");
        Map<String,Object> head=found.get(0);access.requireFrame(access.current(),text(head.get("frame")));
        if(integer(head.get("source_approval"))!=1 || head.get("source_state")==null || integer(head.get("source_state"))<0 || integer(head.get("source_state"))>2)throw new IllegalArgumentException("来源采购订单未审核、已关闭或状态异常");
        head.put("state",integer(head.remove("source_state")));head.put("examine",integer(head.remove("source_approval")));
        List<String> names=db.queryForList("SELECT name FROM supplier WHERE id=?",String.class,head.get("supplier"));head.put("supplierName",names.isEmpty()?"":names.get(0));return head;
    }
    public List<Map<String,Object>> lines(String id){
        List<Map<String,Object>> rows=db.queryForList("SELECT * FROM bor_info WHERE pid=? ORDER BY id FOR UPDATE",id);
        for(Map<String,Object> row:rows){List<Map<String,Object>> goods=db.queryForList("SELECT name,number,spec FROM goods WHERE id=?",row.get("goods"));if(goods.isEmpty())throw new IllegalArgumentException("订单商品不存在");row.putAll(goods.get(0));List<String> warehouses=db.queryForList("SELECT name FROM warehouse WHERE id=?",String.class,row.get("warehouse"));row.put("warehouseName",warehouses.isEmpty()?"":warehouses.get(0));}return rows;
    }
    public BigDecimal reserved(String line,String exclude){
        BigDecimal total=BigDecimal.ZERO;
        for(Map<String,Object> row:db.queryForList("SELECT i.nums FROM buy_info i JOIN buy b ON b.id=i.pid WHERE i.source=? AND b.examine=0 AND b.id<>? FOR UPDATE",line,exclude))total=total.add(decimal(row.get("nums")));
        return total;
    }
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> preview(String id){
        access.authorize("/purchase-order/generate-purchaseData");lock();Map<String,Object> head=header(id);List<Map<String,Object>> lines=lines(id);
        if(lines.isEmpty())throw new IllegalArgumentException("订单没有商品明细");
        for(Map<String,Object> row:lines){
            BigDecimal pending=reserved(text(row.get("id")),""),available=decimal(row.get("nums")).subtract(decimal(row.get("handle"))).subtract(pending);
            row.put("reserved",pending);row.put("available",available.max(BigDecimal.ZERO));row.put("overReserved",available.signum()<0);
            row.put("discountPercent",rate(row,true));row.put("taxPercent",rate(row,false));
        }
        head.put("time",text(head.get("time")));head.put("arrival",text(head.get("arrival")));
        Map<String,Object> result=new LinkedHashMap<>();result.put("header",head);result.put("items",lines);
        Map<String,Map<String,Object>> drafts=new LinkedHashMap<>();
        for(Map<String,Object> draft:db.queryForList("SELECT b.id,b.number FROM buy b JOIN buy_info i ON i.pid=b.id JOIN bor_info o ON o.id=i.source WHERE o.pid=? AND b.examine=0 ORDER BY b.number FOR UPDATE",id))drafts.put(text(draft.get("id")),draft);
        result.put("drafts",new ArrayList<>(drafts.values()));return result;
    }
    public void validate(PurchaseNoteAddDTO request,String exclude,String frame){
        PurchaseNoteBuyDTO head=request.getPurchaseNoteBuyDTO();String source=head.getSource();
        if(source==null || source.isEmpty() || "0".equals(source)){
            if(request.getPurchaseNoteInfoDTOS().stream().anyMatch(line->line.getSource()!=null && !line.getSource().isEmpty() && !"0".equals(line.getSource())))throw new IllegalArgumentException("商品关联了订单明细，但单据来源为空");
            return;
        }
        access.authorize("/purchase-order/generate-purchaseData");lock();Map<String,Object> order=header(source);
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.getTime())>0)throw new IllegalArgumentException("收货日期已结账，不能新增关联采购单");
        String receiptDate=head.getTime().substring(0,10);if(receiptDate.compareTo(text(order.get("time")).substring(0,10))<0)throw new IllegalArgumentException("收货日期不能早于来源采购订单日期");
        if(!frame.equals(text(order.get("frame"))) || !head.getSupplier().equals(text(order.get("supplier"))))throw new IllegalArgumentException("采购单与来源订单的组织或供应商不一致");
        Map<String,Map<String,Object>> originals=new LinkedHashMap<>();for(Map<String,Object> row:lines(source))originals.put(text(row.get("id")),row);
        Map<String,BigDecimal> totals=new LinkedHashMap<>();
        for(PurchaseNoteInfoDTO line:request.getPurchaseNoteInfoDTOS()){
            Map<String,Object> original=originals.get(line.getSource());if(original==null)throw new IllegalArgumentException("来源订单明细不存在或不属于该订单");
            if(!text(line.getGoods()).equals(text(original.get("goods"))) || !text(line.getUnit()).equals(text(original.get("unit"))) || !text(line.getAttr()).equals(text(original.get("attr"))))throw new IllegalArgumentException("商品、属性或单位与来源订单不一致");
            supply.require(frame,line.getGoods(),head.getSupplier());
            totals.merge(line.getSource(),line.getNums(),BigDecimal::add);
        }
        for(Map.Entry<String,BigDecimal> entry:totals.entrySet()){
            Map<String,Object> original=originals.get(entry.getKey());BigDecimal remaining=decimal(original.get("nums")).subtract(decimal(original.get("handle"))).subtract(reserved(entry.getKey(),exclude));
            if(entry.getValue().compareTo(remaining)>0)throw new IllegalArgumentException("生成数量超过订单剩余可生成数量；请刷新预览，或先处理已生成的待入库采购草稿");
        }
    }
}
