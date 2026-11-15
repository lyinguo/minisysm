package com.zeroone.star.purchase.controller;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.purchase.service.*;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
@RestController
@RequestMapping("/purchase-order")
public class PurchaseReceiveController {
    private final PurchaseOrderSources sources;private final PurchaseOrderReceiveService receive;
    public PurchaseReceiveController(PurchaseOrderSources sources,PurchaseOrderReceiveService receive){this.sources=sources;this.receive=receive;}
    @GetMapping("/receive-preview") public JsonVO<Map<String,Object>> preview(@RequestParam String id){return JsonVO.success(sources.preview(id));}
    @PostMapping("/receive") public JsonVO<Map<String,Object>> create(@RequestBody PurchaseOrderReceiveService.Request request){return JsonVO.success(receive.create(request));}
}
