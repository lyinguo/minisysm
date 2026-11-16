package com.zeroone.star.purchase.service;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.math.*;
import java.time.LocalDateTime;
import java.util.*;

/** Read-only return-source preparation. Source allowance and current stock are distinct facts.
 * Actual return saving/audit must revalidate both under the shared purchase/goods locks.
 */
@Service
public class PurchaseReturnPreviewService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseSnapshotService snapshots;
    public PurchaseReturnPreviewService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseSnapshotService snapshots){this.db=db;this.access=access;this.snapshots=snapshots;}
    private String s(Object value){return value==null?"":value.toString();}
    private BigDecimal d(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private BigDecimal part(Object value,BigDecimal quantity,BigDecimal original){return d(value).multiply(quantity).divide(original,4,RoundingMode.HALF_UP);}
    private List<String> serials(Object value){
        JSONArray array;try{array=new JSONArray(s(value).isEmpty()?"[]":s(value));}catch(Exception error){throw new IllegalArgumentException("来源或退货序列号记录异常");}
        Set<String> result=new LinkedHashSet<>();for(Object raw:array){String number=raw instanceof JSONObject?((JSONObject)raw).getStr("number"):s(raw);if(number==null || number.trim().isEmpty() || !result.add(number.trim()))throw new IllegalArgumentException("来源或退货序列号为空或重复");}return new ArrayList<>(result);
    }
    private Map<String,List<Map<String,Object>>> group(List<Map<String,Object>> rows,String field){Map<String,List<Map<String,Object>>> result=new HashMap<>();for(Map<String,Object> row:rows)result.computeIfAbsent(s(row.get(field)),key->new ArrayList<>()).add(row);return result;}
    public void validateSerials(Map<String,Object> source,BigDecimal quantity,String raw){
        List<String> selected=serials(raw);
        if(!Boolean.TRUE.equals(source.get("serialRequired"))){if(!selected.isEmpty())throw new IllegalArgumentException("来源采购没有所选序列号");return;}
        if(d(source.get("sourceQuantity")).multiply(BigDecimal.valueOf(selected.size())).compareTo(quantity.multiply(d(source.get("sourceBaseQuantity"))))!=0)throw new IllegalArgumentException("请按退货基础数量选择原采购序列号");
        if(!((List<?>)source.get("availableSerials")).containsAll(selected))throw new IllegalArgumentException("所选序列号已售出、已退货、被其他草稿占用或不属于原采购");
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public PurchaseNoteBuildDTO preview(String identifier){return calculate(identifier,null);}
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public PurchaseNoteBuildDTO previewForDraft(String identifier,String excluded){return calculate(identifier,excluded);}
    private PurchaseNoteBuildDTO calculate(String identifier,String excluded){
        UserDTO actor=access.authorize("/purchase-note/getBuildBre");
        if(identifier==null || identifier.trim().isEmpty() || identifier.length()>32)throw new IllegalArgumentException("请选择有效的来源采购单");
        List<Map<String,Object>> heads=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS approval_state,s.id AS supplier_id,s.name AS supplier_name,s.frame AS supplier_frame FROM buy b LEFT JOIN supplier s ON s.id=b.supplier WHERE b.id=?",identifier);
        if(heads.size()!=1)throw new IllegalArgumentException("来源采购单不存在");Map<String,Object> head=heads.get(0);access.requireFrame(actor,s(head.get("frame")));
        if(((Number)head.get("approval_state")).intValue()!=1 || db.queryForObject("SELECT COUNT(*) FROM psi_purchase_posting WHERE purchase_id=?",Integer.class,identifier)!=1)throw new IllegalArgumentException("来源采购单未实际审核入账，不能生成退货信息");
        if(head.get("supplier_id")==null || (!"0".equals(s(head.get("supplier_frame"))) && !s(head.get("frame")).equals(s(head.get("supplier_frame")))))throw new IllegalArgumentException("原供应商不存在或组织已变化");
        List<Map<String,Object>> lines=db.queryForList("SELECT i.*,g.id AS existing_goods,g.name AS goodsName,g.number AS goodsNumber,g.spec,w.name AS warehouseName,w.number AS warehouseNumber,w.frame AS warehouseFrame FROM buy_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",identifier);
        if(lines.isEmpty() || lines.size()>500)throw new IllegalArgumentException("来源采购明细缺失或超过500条");
        Map<String,Map<String,Object>> originals=new HashMap<>();for(Map<String,Object> line:lines)originals.put(s(line.get("id")),line);
        Map<String,BigDecimal> posted=new HashMap<>(),pending=new HashMap<>();Map<String,Set<String>> reservedSerials=new HashMap<>();
        for(Map<String,Object> linked:db.queryForList("SELECT i.*,h.id AS return_id,h.source AS return_source,h.frame AS return_frame,h.supplier AS return_supplier,CAST(h.examine AS SIGNED) AS approval_state FROM bre_info i LEFT JOIN bre h ON h.id=i.pid WHERE i.source IN (SELECT id FROM buy_info WHERE pid=?) ORDER BY i.id",identifier)){
            String source=s(linked.get("source"));Map<String,Object> original=originals.get(source);Object approval=linked.get("approval_state");
            if(original==null || linked.get("return_id")==null || !identifier.equals(s(linked.get("return_source"))) || !s(head.get("frame")).equals(s(linked.get("return_frame"))) || !s(head.get("supplier")).equals(s(linked.get("return_supplier"))) || approval==null || (((Number)approval).intValue()!=0 && ((Number)approval).intValue()!=1) || d(linked.get("nums")).signum()<=0)throw new IllegalArgumentException("来源采购单的退货关联记录异常，请先核对数据");
            for(String field:Arrays.asList("goods","attr","unit","warehouse","batch","mfd"))if(!s(original.get(field)).equals(s(linked.get(field))))throw new IllegalArgumentException("关联退货商品、单位、仓库或批次与原采购不一致");
            if(excluded!=null && excluded.equals(s(linked.get("return_id")))){if(((Number)approval).intValue()!=0)throw new IllegalArgumentException("已审核退货不能从来源数量中排除");continue;}
            Map<String,BigDecimal> destination=((Number)approval).intValue()==1?posted:pending;destination.put(source,destination.getOrDefault(source,BigDecimal.ZERO).add(d(linked.get("nums"))));reservedSerials.computeIfAbsent(source,key->new HashSet<>()).addAll(serials(linked.get("serial")));
        }
        Map<String,List<Map<String,Object>>> receipts=group(db.queryForList("SELECT i.*,r.id AS current_room,r.nums AS stock_base,r.goods AS room_goods,r.attr AS room_attr,r.warehouse AS room_warehouse FROM room_info i LEFT JOIN room r ON r.id=i.pid WHERE i.type='buy' AND i.`class`=? AND i.direction=1 ORDER BY i.info,i.id",identifier),"info");
        Map<String,List<Map<String,Object>>> services=group(db.queryForList("SELECT * FROM serve_info WHERE type='buy' AND `class`=? ORDER BY info,id",identifier),"info");
        Map<String,List<Map<String,Object>>> summaries=group(db.queryForList("SELECT * FROM summary WHERE type='buy' AND `class`=? AND direction=1 ORDER BY info,id",identifier),"info");
        Map<String,List<Map<String,Object>>> serialRows=group(db.queryForList("SELECT i.info,s.number,s.room,s.batch,CAST(s.state AS SIGNED) AS serial_state,b.pid AS original_batch FROM serial_info i JOIN serial s ON s.id=i.pid LEFT JOIN batch_info b ON b.type='buy' AND b.`class`=i.`class` AND b.info=i.info AND b.direction=1 WHERE i.type='buy' AND i.`class`=? ORDER BY i.info,s.number",identifier),"info");
        List<Map<String,Object>> items=new ArrayList<>();List<PurchaseNoteBuilInfoDTO> legacy=new ArrayList<>();BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(Map<String,Object> line:lines){
            String source=s(line.get("id"));BigDecimal original=d(line.get("nums")),returned=d(line.get("retreat")),reserved=pending.getOrDefault(source,BigDecimal.ZERO);
            if(original.signum()<=0 || returned.signum()<0 || returned.compareTo(posted.getOrDefault(source,BigDecimal.ZERO))!=0)throw new IllegalArgumentException("原采购数量与已审核退货记录不一致");
            BigDecimal available=original.subtract(returned).subtract(reserved);if(available.signum()<0)throw new IllegalArgumentException("来源采购存在超量退货或草稿占用");if(available.signum()==0)continue;
            if(line.get("existing_goods")==null)throw new IllegalArgumentException("原采购商品不存在");
            List<Map<String,Object>> physical=receipts.getOrDefault(source,Collections.emptyList()),service=services.getOrDefault(source,Collections.emptyList());
            if(physical.size()+service.size()!=1)throw new IllegalArgumentException("原采购入库或服务凭据缺失、重复，不能推测退货数量");
            Map<String,Object> receipt=physical.isEmpty()?service.get(0):physical.get(0);BigDecimal base=d(receipt.get("nums"));if(base.signum()<=0)throw new IllegalArgumentException("原采购入账基础数量异常");
            if(!physical.isEmpty()){
                List<Map<String,Object>> costs=summaries.getOrDefault(source,Collections.emptyList());
                if(receipt.get("current_room")==null || costs.size()!=1 || !s(costs.get(0).get("pid")).equals(s(receipt.get("id"))) || d(costs.get(0).get("nums")).compareTo(base)!=0 || !s(line.get("goods")).equals(s(receipt.get("room_goods"))) || !s(line.get("attr")).equals(s(receipt.get("room_attr"))) || !s(line.get("warehouse")).equals(s(receipt.get("room_warehouse"))) || (!"0".equals(s(line.get("warehouseFrame"))) && !s(head.get("frame")).equals(s(line.get("warehouseFrame")))))throw new IllegalArgumentException("原采购库存、报表凭据或仓库组织不一致");
            }
            Map<String,Object> item=new LinkedHashMap<>(line);for(String field:Arrays.asList("id","pid","retreat","existing_goods"))item.remove(field);
            item.put("source",source);item.put("sourceQuantity",original);item.put("returned",returned);item.put("reserved",reserved);item.put("available",available);item.put("nums",available);item.put("sourceBaseQuantity",base);item.put("service",physical.isEmpty());item.put("stockBase",physical.isEmpty()?null:receipt.get("stock_base"));item.put("stockQuantity",physical.isEmpty()?null:d(receipt.get("stock_base")).multiply(original).divide(base,4,RoundingMode.DOWN));
            item.put("total",part(line.get("total"),available,original));item.put("tat",part(line.get("tat"),available,original));item.put("dsc",part(line.get("dsc"),available,original));item.put("tpt",d(item.get("total")).add(d(item.get("tat"))));
            List<Map<String,Object>> serialRecords=serialRows.getOrDefault(source,Collections.emptyList());Set<String> originalNumbers=new HashSet<>();List<String> choices=new ArrayList<>();
            for(Map<String,Object> row:serialRecords){String number=s(row.get("number"));if(!originalNumbers.add(number))throw new IllegalArgumentException("原采购序列号凭据重复");if(!physical.isEmpty() && ((Number)row.get("serial_state")).intValue()==0 && s(row.get("room")).equals(s(receipt.get("pid"))) && s(row.get("batch")).equals(s(row.get("original_batch"))) && !reservedSerials.getOrDefault(source,Collections.emptySet()).contains(number))choices.add(number);}
            if(!originalNumbers.equals(new HashSet<>(serials(line.get("serial")))))throw new IllegalArgumentException("原采购序列号与实际入库凭据不一致");
            item.put("serialRequired",!serialRecords.isEmpty());item.put("availableSerials",choices);item.put("serial","[]");items.add(item);total=total.add(d(item.get("total")));actual=actual.add(d(item.get("tpt")));
            PurchaseNoteBuilInfoDTO previous=BeanUtil.toBean(item,PurchaseNoteBuilInfoDTO.class);previous.setRetreat(returned);GoodsDataDTO goods=new GoodsDataDTO();goods.setId(s(line.get("goods")));goods.setName(s(line.get("goodsName")));goods.setNumber(s(line.get("goodsNumber")));goods.setSpec(s(line.get("spec")));previous.setGoodsData(goods);WarehouseDataDTO warehouse=new WarehouseDataDTO();warehouse.setId(s(line.get("warehouse")));warehouse.setName(s(line.get("warehouseName")));warehouse.setNumber(s(line.get("warehouseNumber")));warehouse.setFrame(s(line.get("warehouseFrame")));previous.setWarehouseData(warehouse);legacy.add(previous);
        }
        if(items.isEmpty())throw new IllegalArgumentException("来源采购单已无可退数量");
        PurchaseNoteBuildDTO result=new PurchaseNoteBuildDTO();result.setSource(identifier);result.setSourceNumber(s(head.get("number")));result.setSourceVersion(snapshots.version(identifier,false));result.setFrame(s(head.get("frame")));result.setSupplier(s(head.get("supplier")));result.setSupplierName(s(head.get("supplier_name")));result.setUser(actor.getId());result.setNumber("");result.setTime(LocalDateTime.now());result.setMoney(BigDecimal.ZERO);result.setTotal(total);result.setActual(actual);result.setExamine(0);result.setCheck(0);result.setNucleus(0);result.setItems(items);
        PurchaseNoteBorDTO previous=new PurchaseNoteBorDTO();previous.setSource(identifier);previous.setSupplier(result.getSupplier());previous.setTotal(total);result.setPurchaseNoteBorDTO(previous);result.setPurchaseNoteBuilInfoDTOS(legacy);return result;
    }
}
