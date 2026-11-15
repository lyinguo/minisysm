package com.zeroone.star.purchase.controller;

import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.purchase.service.PurchaseSupplyService;
import com.zeroone.star.purchase.service.PurchaseSplitService;
import lombok.Data;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/purchase-order")
public class PurchaseEntryController {
    private final PurchaseSupplyService supply;
    private final PurchaseSplitService split;
    private final com.zeroone.star.purchase.service.PurchaseOrderAuditService audit;
    public PurchaseEntryController(PurchaseSupplyService supply,PurchaseSplitService split,com.zeroone.star.purchase.service.PurchaseOrderAuditService audit) {this.supply=supply;this.split=split;this.audit=audit;}
    @GetMapping("/status") public JsonVO<Map<String,Object>> status(@RequestParam String id) {return JsonVO.success(audit.status(id));}
    @GetMapping("/document") public JsonVO<Map<String,Object>> document(@RequestParam String id) {return JsonVO.success(audit.document(id));}
    @GetMapping("/supply") public JsonVO<List<Map<String,Object>>> list(@RequestParam String goods) {return JsonVO.success(supply.list(goods));}
    @Data public static class SupplyRequest {private String goods,supplier;private Boolean enabled;}
    @PostMapping("/supply") public JsonVO<String> set(@RequestBody SupplyRequest request) {
        if(request==null || request.enabled==null)throw new IllegalArgumentException("请选择供货关系状态");
        supply.set(request.goods,request.supplier,request.enabled);return JsonVO.success("已更新供货关系");
    }
    @PostMapping("/split") public JsonVO<List<Map<String,Object>>> save(@RequestBody PurchaseSplitService.Entry entry) {return JsonVO.success(split.save(entry));}
}
