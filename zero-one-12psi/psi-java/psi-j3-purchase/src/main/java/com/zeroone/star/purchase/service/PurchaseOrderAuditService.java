package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.util.*;

/** Approval authorizes an order; receiving goods remains a separate purchase transaction. */
@Service
public class PurchaseOrderAuditService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseSupplyService supply;
    private final PurchaseDraftAmounts amounts;
    public PurchaseOrderAuditService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseSupplyService supply,PurchaseDraftAmounts amounts) {this.db=db;this.access=access;this.supply=supply;this.amounts=amounts;}
    private static String text(Object value){return value==null?"":value.toString();}
    private static int integer(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?0:((Number)value).intValue();}
    private static BigDecimal decimal(Object value){return value==null?BigDecimal.ZERO:new BigDecimal(value.toString());}
    private static String uid(){return UUID.randomUUID().toString().replace("-","");}
    private int count(String sql,Object...args){return db.queryForObject(sql,Integer.class,args);}
    public Map<String,Object> document(String id){
        UserDTO actor=access.authorize("/purchase-order/detail");
        List<Map<String,Object>> found=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS source_approval,CAST(b.state AS SIGNED) AS source_state,s.name AS supplierName FROM bor b LEFT JOIN supplier s ON s.id=b.supplier WHERE b.id=?",id);
        if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在");
        Map<String,Object> head=found.get(0);head.put("state",integer(head.remove("source_state")));access.requireFrame(actor,text(head.get("frame")));
        head.put("time",text(head.get("time")));head.put("arrival",text(head.get("arrival")));head.put("examine",integer(head.remove("source_approval")));
        Map<String,Object> result=new LinkedHashMap<>();result.put("header",head);result.put("items",db.queryForList("SELECT i.*,g.name,g.number,g.spec,w.name AS warehouseName FROM bor_info i LEFT JOIN goods g ON g.id=i.goods LEFT JOIN warehouse w ON w.id=i.warehouse WHERE i.pid=? ORDER BY i.id",id));return result;
    }
    public Map<String,Object> status(String id){
        UserDTO actor=access.authorize("/purchase-order/audit");
        List<Map<String,Object>> found=db.queryForList("SELECT id,frame,CAST(examine AS SIGNED) AS examine,CAST(state AS SIGNED) AS state FROM bor WHERE id=?",id);
        if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在");
        Map<String,Object> head=found.get(0);access.requireFrame(actor,text(head.get("frame")));head.put("examine",integer(head.get("examine")));return head;
    }
    private void validate(Map<String,Object> head,List<Map<String,Object>> lines){
        if(lines.isEmpty())throw new IllegalArgumentException("采购订单没有商品明细");
        String frame=text(head.get("frame")),supplier=text(head.get("supplier"));
        PurchaseNoteBuyDTO header=new PurchaseNoteBuyDTO();header.setMoney(BigDecimal.ZERO);header.setCost(BigDecimal.ZERO);
        PurchaseNoteAddDTO request=new PurchaseNoteAddDTO();request.setPurchaseNoteBuyDTO(header);List<PurchaseNoteInfoDTO> items=new ArrayList<>();
        for(Map<String,Object> row:lines){
            supply.require(frame,text(row.get("goods")),supplier);
            if(db.queryForList("SELECT id FROM warehouse WHERE id=? AND (frame=? OR frame='0') FOR UPDATE",row.get("warehouse"),frame).size()!=1)throw new IllegalArgumentException("订单仓库不存在或与组织不一致");
            if(text(row.get("unit")).isEmpty())throw new IllegalArgumentException("订单商品单位不能为空");
            if(!text(row.get("attr")).isEmpty() && !"0".equals(text(row.get("attr"))) && count("SELECT COUNT(*) FROM attr WHERE pid=? AND name=?",row.get("goods"),row.get("attr"))!=1)throw new IllegalArgumentException("订单商品辅助属性不存在");
            if(decimal(row.get("handle")).signum()!=0)throw new IllegalArgumentException("已有接收数量，不能作为未执行订单审核");
            PurchaseNoteInfoDTO item=new PurchaseNoteInfoDTO();item.setPrice(decimal(row.get("price")));item.setNums(decimal(row.get("nums")));item.setDiscount(decimal(row.get("discount")));item.setDsc(decimal(row.get("dsc")));item.setTax(decimal(row.get("tax")));item.setTat(decimal(row.get("tat")));items.add(item);
        }
        request.setPurchaseNoteInfoDTOS(items);amounts.calculate(request);
        if(decimal(head.get("total")).compareTo(header.getTotal())!=0 || decimal(head.get("actual")).compareTo(header.getActual())!=0)throw new IllegalArgumentException("订单合计与商品计算金额不一致，请先核对草稿");
        for(int i=0;i<items.size();i++){
            PurchaseNoteInfoDTO item=items.get(i);Map<String,Object> original=lines.get(i);
            if(decimal(original.get("total")).compareTo(item.getTotal())!=0 || decimal(original.get("tat")).compareTo(item.getTat())!=0 || decimal(original.get("tpt")).compareTo(item.getTpt())!=0 || decimal(original.get("dsc")).compareTo(item.getDsc())!=0)throw new IllegalArgumentException("订单明细金额不一致，请先核对草稿");
        }
    }
    private void lock(){
        for(String scope:Arrays.asList("buy","bor")) {
            db.update("INSERT INTO psi_document_write_lock(scope) VALUES(?) ON DUPLICATE KEY UPDATE scope=VALUES(scope)",scope);db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope=? FOR UPDATE",String.class,scope);
        }
    }
    public void guardUpdate(PurchaseOrderUpdateDTO request){
        UserDTO actor=access.authorize("/purchase-order/update");lock();
        List<Map<String,Object>> found=db.queryForList("SELECT * FROM bor WHERE id=? FOR UPDATE",request.getId());
        if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在");
        Map<String,Object> head=found.get(0);access.requireFrame(actor,text(head.get("frame")));
        if(integer(head.get("examine"))!=0 || integer(head.get("state"))!=0 || !db.queryForList("SELECT id FROM buy WHERE source=? OR source=? FOR UPDATE",request.getId(),head.get("number")).isEmpty())throw new IllegalArgumentException("已审核、接收、关闭或有关联采购单的订单不能修改");
        if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)throw new IllegalArgumentException("订单日期已结账，不能修改");
        if(request.getTime()==null || request.getArrival()==null || request.getArrival().isBefore(request.getTime()) || count("SELECT COUNT(*) FROM period WHERE date>=?",request.getTime())>0)throw new IllegalArgumentException("单据日期或到货日期无效，或已结账");
        if(request.getNumber()==null || request.getNumber().trim().isEmpty() || request.getNumber().length()>32 || !db.queryForList("SELECT id FROM bor WHERE number=? AND id<>? FOR UPDATE",request.getNumber(),request.getId()).isEmpty())throw new IllegalArgumentException("订单编号无效或已被使用");
        if(request.getSource()!=null && !request.getSource().equals(text(head.get("source"))))throw new IllegalArgumentException("修改不能更换来源订单");
        if(request.getPurchaseOrderInfoDTOList()==null || request.getPurchaseOrderInfoDTOList().isEmpty() || request.getPurchaseOrderInfoDTOList().size()>200)throw new IllegalArgumentException("请填写1到200条商品明细");
        head.put("supplier",request.getSupplier());head.put("total",request.getTotal());head.put("actual",request.getActual());
        if(request.getPeople()!=null && !request.getPeople().isEmpty() && db.queryForList("SELECT id FROM people WHERE id=? AND (frame=? OR frame='0') FOR UPDATE",request.getPeople(),head.get("frame")).size()!=1)throw new IllegalArgumentException("关联人员不存在或与组织不一致");
        List<Map<String,Object>> lines=new ArrayList<>();
        for(PurchaseOrderInfoDTO item:request.getPurchaseOrderInfoDTOList()){
            if(item==null)throw new IllegalArgumentException("商品明细不能为空");
            Map<String,Object> row=new LinkedHashMap<>();row.put("goods",item.getGoods());row.put("warehouse",item.getWarehouse());row.put("unit",item.getUnit());row.put("attr",item.getAttr());row.put("price",item.getPrice());row.put("nums",item.getNums());row.put("discount",item.getDiscount());row.put("dsc",item.getDsc());row.put("total",item.getTotal());row.put("tax",item.getTax());row.put("tat",item.getTat());row.put("tpt",item.getTpt());row.put("handle",0);lines.add(row);
        }
        validate(head,lines);
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bor',?,NOW(),?,?)",uid(),request.getId(),actor.getId(),"修改采购订单 "+request.getNumber());
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",uid(),actor.getId(),"修改采购订单 "+request.getNumber());
    }
    @Transactional(rollbackFor=Exception.class)
    public List<String> audit(AuditRequestDTO request){
        UserDTO actor=access.authorize("/purchase-order/audit");
        if(request==null || request.getType()==null || (request.getType()!=0 && request.getType()!=1))throw new IllegalArgumentException("审核操作必须为1，反审核必须为0");
        List<String> ids=request.getIds();
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))throw new IllegalArgumentException("请选择1到200张不同的采购订单");
        lock();
        List<String> ordered=new ArrayList<>(ids);Collections.sort(ordered);
        for(String id:ordered){
            List<Map<String,Object>> found=db.queryForList("SELECT b.*,CAST(b.examine AS SIGNED) AS approval_state,CAST(b.state AS SIGNED) AS execution_state FROM bor b WHERE b.id=? FOR UPDATE",id);
            if(found.size()!=1)throw new IllegalArgumentException("采购订单不存在");
            Map<String,Object> head=found.get(0);access.requireFrame(actor,text(head.get("frame")));
            if(head.get("approval_state")==null || integer(head.get("approval_state"))<0 || integer(head.get("approval_state"))>1 || head.get("execution_state")==null || integer(head.get("execution_state"))<0 || integer(head.get("execution_state"))>3)throw new IllegalArgumentException("采购订单状态异常，请先核对原始业务记录");
            head.put("examine",integer(head.remove("approval_state")));head.put("state",integer(head.remove("execution_state")));
            if(integer(head.get("examine"))==request.getType())continue;
            if(integer(head.get("state"))!=0)throw new IllegalArgumentException("已接收或关闭的订单不能审核或反审核");
            if(count("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",head.get("time"))>0)throw new IllegalArgumentException("订单日期已结账，不能改变审核状态");
            List<Map<String,Object>> lines=db.queryForList("SELECT * FROM bor_info WHERE pid=? ORDER BY id FOR UPDATE",id);
            if(request.getType()==1)validate(head,lines);
            else {
                if(!db.queryForList("SELECT id FROM buy WHERE source=? OR source=? FOR UPDATE",id,head.get("number")).isEmpty() || !db.queryForList("SELECT i.id FROM buy_info i JOIN bor_info o ON o.id=i.source WHERE o.pid=? FOR UPDATE",id).isEmpty() || lines.stream().anyMatch(row->decimal(row.get("handle")).signum()!=0))throw new IllegalArgumentException("订单已生成采购单或存在接收记录，不能反审核");
            }
            db.update("UPDATE bor SET examine=? WHERE id=?",request.getType(),id);
            String action=request.getType()==1?"审核采购订单 ":"反审核采购订单 ";
            db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bor',?,NOW(),?,?)",uid(),id,actor.getId(),action+text(head.get("number")));
            db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",uid(),actor.getId(),action+text(head.get("number")));
        }
        return ids;
    }
}
