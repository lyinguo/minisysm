package com.zeroone.star.purchase.service;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseOrderListDTO;
import com.zeroone.star.purchase.DO.BorDO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** Add presentation fields without replacing reference IDs or rewriting historical states. */
@Service
public class PurchaseOrderListView {
    private final JdbcTemplate db;
    private final PurchaseOrderAuditService orders;
    public PurchaseOrderListView(JdbcTemplate db,PurchaseOrderAuditService orders){this.db=db;this.orders=orders;}
    public static String label(Object value,boolean approval){
        if(value==null)return "异常(空)";int state=((Number)value).intValue();
        if(approval)return state==0?"未审核":state==1?"已审核":"异常("+state+")";
        return state==0?"未入库":state==1?"部分入库":state==2?"已入库":state==3?"关闭":"异常("+state+")";
    }
    public static int filter(String value,boolean approval){
        List<String> names=approval?Arrays.asList("未审核","已审核"):Arrays.asList("未入库","部分入库","已入库","关闭");
        int index=names.indexOf(value);if(index>=0)return index;
        try{int state=Integer.parseInt(value);if(state>=0 && state<names.size())return state;}catch(NumberFormatException ignored){}
        throw new IllegalArgumentException("审核或入库状态筛选无效");
    }
    private String name(Object value,String id){return value!=null?value.toString():id==null || id.isEmpty() || "0".equals(id)?"":"[缺失资料:"+id+"]";}
    public PageDTO<PurchaseOrderListDTO> enrich(PageDTO<PurchaseOrderListDTO> page,List<BorDO> records){
        if(records.isEmpty()){page.setRows(Collections.emptyList());return page;}
        Object[] ids=records.stream().map(BorDO::getId).toArray();String placeholders=String.join(",",Collections.nCopies(ids.length,"?"));
        Map<String,Map<String,Object>> meta=new HashMap<>();
        for(Map<String,Object> row:db.queryForList("SELECT b.id,CAST(b.examine AS SIGNED) AS approval,CAST(b.state AS SIGNED) AS execution,f.name AS frame_name,s.name AS supplier_name,p.name AS people_name,u.name AS user_name FROM bor b LEFT JOIN frame f ON f.id=b.frame LEFT JOIN supplier s ON s.id=b.supplier LEFT JOIN people p ON p.id=b.people LEFT JOIN `user` u ON u.id=b.`user` WHERE b.id IN ("+placeholders+")",ids))meta.put(row.get("id").toString(),row);
        Map<String,BorDO> sources=new HashMap<>();for(BorDO record:records)sources.put(record.getId(),record);
        Map<String,String> versions=orders.versions(new ArrayList<>(sources.keySet()));
        for(PurchaseOrderListDTO row:page.getRows()){
            Map<String,Object> names=meta.get(row.getId());BorDO original=sources.get(row.getId());
            if(names==null)throw new IllegalStateException("订单列表已变化，请刷新重试");
            if(!versions.containsKey(row.getId()))throw new IllegalStateException("订单列表已变化，请刷新重试");
            row.setVersion(versions.get(row.getId()));
            row.setFrameName("0".equals(row.getFrame())?"公共组织":name(names.get("frame_name"),row.getFrame()));row.setSupplierName(name(names.get("supplier_name"),row.getSupplier()));row.setPeopleName(name(names.get("people_name"),row.getPeople()));row.setUserName(name(names.get("user_name"),row.getUser()));
            row.setDocumentTime(original.getTime()==null?null:original.getTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));row.setArrivalTime(original.getArrival()==null?null:original.getArrival().toLocalDate().toString());
            row.setExamine(names.get("approval")==null?null:names.get("approval").toString());row.setState(names.get("execution")==null?null:names.get("execution").toString());row.setExamineName(label(names.get("approval"),true));row.setStateName(label(names.get("execution"),false));
        }
        return page;
    }
}
