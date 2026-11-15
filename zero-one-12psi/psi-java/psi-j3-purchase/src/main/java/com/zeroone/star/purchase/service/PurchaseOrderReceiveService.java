package com.zeroone.star.purchase.service;

import com.zeroone.star.project.dto.j3.purchase.*;
import lombok.Data;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.*;
import java.util.*;
import static com.zeroone.star.purchase.service.PurchaseOrderSources.*;

/** Build receiving drafts from authoritative order rows; never trusts client prices or totals. */
@Service
public class PurchaseOrderReceiveService {
    @Data public static class Item{private String id;private BigDecimal nums;}
    @Data public static class Request{private String id,number,time;private List<Item> items;}
    private final PurchaseOrderSources sources;private final PurchaseDocumentAccess access;private final PurchaseNoteService purchases;
    public PurchaseOrderReceiveService(PurchaseOrderSources sources,PurchaseDocumentAccess access,PurchaseNoteService purchases){this.sources=sources;this.access=access;this.purchases=purchases;}
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> create(Request request){
        access.authorize("/purchase-order/generate-purchaseData");access.authorize("/purchase-note/add");
        if(request==null || request.getItems()==null || request.getItems().isEmpty() || request.getItems().size()>200)throw new IllegalArgumentException("请选择1到200条待收货明细");
        sources.lock();Map<String,Object> head=sources.header(request.getId());Map<String,Map<String,Object>> rows=new LinkedHashMap<>();for(Map<String,Object> row:sources.lines(request.getId()))rows.put(text(row.get("id")),row);
        PurchaseNoteAddDTO payload=new PurchaseNoteAddDTO();PurchaseNoteBuyDTO header=new PurchaseNoteBuyDTO();header.setSource(request.getId());header.setNumber(request.getNumber());header.setTime(request.getTime());header.setSupplier(text(head.get("supplier")));header.setPeople(text(head.get("people")));header.setMoney(BigDecimal.ZERO);header.setCost(BigDecimal.ZERO);header.setFile(text(head.get("file")));header.setLogistics(text(head.get("logistics")));header.setData(text(head.get("data")));payload.setPurchaseNoteBuyDTO(header);
        Set<String> selected=new HashSet<>();List<PurchaseNoteInfoDTO> lines=new ArrayList<>();
        for(Item input:request.getItems()){
            if(input==null || !selected.add(input.getId()) || input.getNums()==null || input.getNums().signum()<=0 || input.getNums().stripTrailingZeros().scale()>4)throw new IllegalArgumentException("请选择不同的订单明细，收货数量须大于零且最多四位小数");
            Map<String,Object> row=rows.get(input.getId());if(row==null)throw new IllegalArgumentException("选择的明细不属于来源订单");
            PurchaseNoteInfoDTO item=new PurchaseNoteInfoDTO();item.setSource(input.getId());item.setGoods(text(row.get("goods")));item.setAttr(text(row.get("attr")));item.setUnit(text(row.get("unit")));item.setWarehouse(text(row.get("warehouse")));item.setPrice(decimal(row.get("price")));item.setNums(input.getNums());item.setDiscount(rate(row,true));item.setTax(rate(row,false));item.setSerial("[]");item.setData(text(row.get("data")));lines.add(item);
        }
        payload.setPurchaseNoteInfoDTOS(lines);String id=purchases.addPurchaseNote(payload);Map<String,Object> result=new LinkedHashMap<>();result.put("id",id);result.put("number",header.getNumber());result.put("source",request.getId());result.put("lineCount",lines.size());result.put("total",header.getTotal());result.put("actual",header.getActual());return result;
    }
    public PurchaseNoteGenerateDataDTO legacy(String id){
        Map<String,Object> result=sources.preview(id);List<Map<String,Object>> rows=(List<Map<String,Object>>)result.get("items");
        if(rows.size()!=1)throw new IllegalArgumentException("该订单有多条商品，请使用完整收货预览生成采购草稿");
        Map<String,Object> head=(Map<String,Object>)result.get("header"),row=rows.get(0);PurchaseNoteGenerateDataDTO dto=new PurchaseNoteGenerateDataDTO();dto.setGoods(text(row.get("goods")));dto.setName(text(row.get("name")));dto.setSpec(text(row.get("spec")));dto.setAttr(text(row.get("attr")));dto.setUnit(text(row.get("unit")));dto.setWarehouse(text(row.get("warehouse")));dto.setPrice(text(row.get("price")));dto.setNums(text(row.get("available")));dto.setTax(rate(row,false).toPlainString());
        BigDecimal gross=decimal(row.get("price")).multiply(decimal(row.get("available"))).setScale(4,RoundingMode.HALF_UP),deduction=gross.multiply(rate(row,true)).movePointLeft(2).setScale(4,RoundingMode.HALF_UP),net=gross.subtract(deduction),tax=net.multiply(rate(row,false)).movePointLeft(2).setScale(4,RoundingMode.HALF_UP);
        dto.setTat(tax.toPlainString());dto.setAmount(net.toPlainString());dto.setTpt(net.add(tax).toPlainString());dto.setData(text(row.get("data")));PurchaseNoteOtherGenerateDataDTO other=new PurchaseNoteOtherGenerateDataDTO();other.setSupplier(text(head.get("supplier")));other.setNumber(text(head.get("number")));other.setTime(text(head.get("time")));other.setTotal(net.toPlainString());other.setActual(net.add(tax).toPlainString());other.setMoney("0");other.setCost("0");other.setPeople(text(head.get("people")));other.setLogistics(text(head.get("logistics")));other.setFile(text(head.get("file")));other.setData(text(head.get("data")));dto.setPurchaseNoteOtherGenerateDataDTO(other);return dto;
    }
}
