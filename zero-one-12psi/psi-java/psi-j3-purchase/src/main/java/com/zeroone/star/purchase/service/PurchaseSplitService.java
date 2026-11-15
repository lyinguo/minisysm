package com.zeroone.star.purchase.service;

import com.zeroone.star.project.dto.j3.purchase.*;
import lombok.Data;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDate;
import java.util.*;

/** One entry with multiple suppliers becomes one atomic group of independent drafts. */
@Service
public class PurchaseSplitService {
    @Data public static class Row extends PurchaseOrderInfoDTO { private String supplier; }
    @Data public static class Entry {private String number,time,arrival,people,data;private List<Row> rows;}
    private final PurchaseOrderDraftService drafts;
    private final PurchaseDocumentAccess access;
    public PurchaseSplitService(PurchaseOrderDraftService drafts,PurchaseDocumentAccess access) {this.drafts=drafts;this.access=access;}
    @Transactional(rollbackFor=Exception.class)
    public List<Map<String,Object>> save(Entry entry) {
        access.authorize("/purchase-order/add");
        if(entry==null || entry.rows==null || entry.rows.isEmpty() || entry.rows.size()>200)throw new IllegalArgumentException("请填写1到200条商品明细");
        String number=entry.number==null?"":entry.number.trim();
        if(number.isEmpty() || number.length()>28)throw new IllegalArgumentException("本次采购编号必须为1到28个字符，系统会追加拆单序号");
        LocalDate date,arrival;
        try {date=LocalDate.parse(entry.time);arrival=LocalDate.parse(entry.arrival);}catch(Exception error){throw new IllegalArgumentException("请填写有效单据日期和到货日期");}
        Map<String,List<PurchaseOrderInfoDTO>> groups=new LinkedHashMap<>();
        for(Row row:entry.rows) {
            if(row==null || row.supplier==null || row.supplier.trim().isEmpty())throw new IllegalArgumentException("每行商品都必须选择供应商");
            groups.computeIfAbsent(row.supplier,k->new ArrayList<>()).add(row);
        }
        List<Map<String,Object>> result=new ArrayList<>();int index=0;
        for(Map.Entry<String,List<PurchaseOrderInfoDTO>> group:groups.entrySet()) {
            PurchaseOrderAddDTO request=new PurchaseOrderAddDTO();request.setNumber(number+String.format(java.util.Locale.ROOT,"-%03d",++index));
            request.setTime(date);request.setArrival(arrival);request.setSupplier(group.getKey());request.setPeople(entry.people);request.setData(entry.data);
            request.setPurchaseOrderInfoDTOList(group.getValue());
            String id=drafts.create(request);
            Map<String,Object> item=new LinkedHashMap<>();item.put("id",id);item.put("number",request.getNumber());item.put("supplier",group.getKey());item.put("lineCount",group.getValue().size());result.add(item);
        }
        return result;
    }
}
