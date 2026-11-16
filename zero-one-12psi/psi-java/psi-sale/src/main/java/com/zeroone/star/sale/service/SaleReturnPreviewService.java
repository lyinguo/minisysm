package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReturnGenerateDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Isolation;
import java.math.*;
import java.time.LocalDateTime;
import java.util.*;

/** Read-only source selection. Actual return saving/posting must revalidate quantities under its write lock. */
@Service
public class SaleReturnPreviewService {
    private final JdbcTemplate db;
    private final SaleDocumentAccess access;
    private final SaleSnapshotService snapshots;
    public SaleReturnPreviewService(JdbcTemplate db,SaleDocumentAccess access,SaleSnapshotService snapshots){this.db=db;this.access=access;this.snapshots=snapshots;}
    private String s(Object v){return v==null?"":v.toString();}
    private BigDecimal d(Object v){return v==null?BigDecimal.ZERO:new BigDecimal(v.toString());}
    private BigDecimal proportion(Object value,BigDecimal available,BigDecimal quantity){return d(value).multiply(available).divide(quantity,4,RoundingMode.HALF_UP);}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public SaleReturnGenerateDTO preview(String id){
        UserDTO actor=access.authorize("/sale/form/getSaleDetail");
        if(id==null || id.trim().isEmpty() || id.length()>32)throw new IllegalArgumentException("请选择有效的来源销售单");
        List<Map<String,Object>> found=db.queryForList("SELECT * FROM sell WHERE id=?",id);
        if(found.size()!=1)throw new IllegalArgumentException("来源销售单不存在");
        Map<String,Object> head=found.get(0);access.requireFrame(actor,s(head.get("frame")));
        if(db.queryForObject("SELECT CAST(examine AS SIGNED) FROM sell WHERE id=?",Integer.class,id)!=1
                || db.queryForObject("SELECT COUNT(*) FROM psi_sale_posting WHERE sale_id=?",Integer.class,id)!=1)
            throw new IllegalArgumentException("来源销售单未实际审核入账，不能生成退货数据");
        List<Map<String,Object>> lines=db.queryForList("SELECT i.*,g.name AS goodsName,g.number AS goodsNumber,g.spec,w.name AS warehouseName FROM sell_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id);
        if(lines.isEmpty() || lines.size()>500)throw new IllegalArgumentException("来源销售单明细缺失或数量异常，请先核对数据");
        Map<String,Map<String,Object>> byId=new HashMap<>();Map<String,BigDecimal> posted=new HashMap<>(),pending=new HashMap<>();
        for(Map<String,Object> line:lines)byId.put(s(line.get("id")),line);
        for(Map<String,Object> linked:db.queryForList("SELECT i.*,h.id AS return_id,h.source AS return_source,h.frame AS return_frame,h.customer AS return_customer,CAST(h.examine AS SIGNED) AS approval_state FROM sre_info i LEFT JOIN sre h ON h.id=i.pid WHERE i.source IN (SELECT id FROM sell_info WHERE pid=?) ORDER BY i.id",id)){
            String source=s(linked.get("source"));Map<String,Object> original=byId.get(source);Object approval=linked.get("approval_state");
            if(original==null || linked.get("return_id")==null || !id.equals(s(linked.get("return_source")))
                    || !s(head.get("frame")).equals(s(linked.get("return_frame"))) || !s(head.get("customer")).equals(s(linked.get("return_customer")))
                    || !s(original.get("goods")).equals(s(linked.get("goods"))) || !s(original.get("unit")).equals(s(linked.get("unit")))
                    || approval==null || (((Number)approval).intValue()!=0 && ((Number)approval).intValue()!=1) || d(linked.get("nums")).signum()<=0)
                throw new IllegalArgumentException("来源销售单的退货关联数据异常，请先核对，不能继续估算可退数量");
            Map<String,BigDecimal> totals=((Number)approval).intValue()==1?posted:pending;
            totals.put(source,totals.getOrDefault(source,BigDecimal.ZERO).add(d(linked.get("nums"))));
        }
        List<Map<String,Object>> items=new ArrayList<>();BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(Map<String,Object> line:lines){
            String lineId=s(line.get("id"));BigDecimal quantity=d(line.get("nums")),returned=d(line.get("retreat")),reserved=pending.getOrDefault(lineId,BigDecimal.ZERO);
            if(quantity.signum()<=0 || returned.signum()<0 || returned.compareTo(posted.getOrDefault(lineId,BigDecimal.ZERO))!=0)
                throw new IllegalArgumentException("来源数量与已审核退货记录不一致，请先核对数据");
            BigDecimal available=quantity.subtract(returned).subtract(reserved);
            if(available.signum()<0)throw new IllegalArgumentException("来源销售单存在超量退货或草稿占用，请先核对数据");
            if(available.signum()==0)continue;
            Map<String,Object> item=new LinkedHashMap<>(line);item.remove("id");item.remove("pid");item.remove("retreat");
            item.put("source",lineId);item.put("sourceQuantity",quantity);item.put("returned",returned);item.put("reserved",reserved);item.put("available",available);item.put("nums",available);
            item.put("total",proportion(line.get("total"),available,quantity));item.put("tat",proportion(line.get("tat"),available,quantity));item.put("dsc",proportion(line.get("dsc"),available,quantity));
            item.put("tpt",d(item.get("total")).add(d(item.get("tat"))));
            // Serial membership and batch selection belong to the eventual return command, not copied sell-out serial JSON.
            item.put("serial","[]");items.add(item);total=total.add(d(item.get("total")));actual=actual.add(d(item.get("tpt")));
        }
        if(items.isEmpty())throw new IllegalArgumentException("来源销售单已无可退数量");
        SaleReturnGenerateDTO result=new SaleReturnGenerateDTO();
        result.setSource(id);result.setSourceNumber(s(head.get("number")));result.setSourceVersion(snapshots.version(id,false));result.setItems(items);
        result.setFrame(s(head.get("frame")));result.setCustomer(s(head.get("customer")));result.setTime(LocalDateTime.now());result.setNumber("");
        result.setTotal(total);result.setActual(actual);result.setMoney(BigDecimal.ZERO);result.setCost(BigDecimal.ZERO);result.setAccount("");result.setPeople("");
        result.setLogistics("");result.setFile("[]");result.setData("");result.setMore("{}");result.setExamine(0);result.setCheck(0);result.setNucleus(0);result.setCse(3);result.setInvoice(3);result.setUser(actor.getId());
        return result;
    }
}
