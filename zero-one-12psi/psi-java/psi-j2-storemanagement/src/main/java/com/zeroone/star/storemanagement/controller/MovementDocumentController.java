package com.zeroone.star.storemanagement.controller;

import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.*;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
public class MovementDocumentController {
    private final TransferDocumentService transfers;private final InventoryCountDocumentService counts;
    public MovementDocumentController(TransferDocumentService transfers,InventoryCountDocumentService counts){this.transfers=transfers;this.counts=counts;}
    @GetMapping("/transfer/documents") public JsonVO<Map<String,Object>> transfers(@RequestParam(defaultValue="1") int pageIndex,@RequestParam(defaultValue="20") int pageSize,@RequestParam(defaultValue="") String number){return JsonVO.success(transfers.list(pageIndex,pageSize,number));}
    @GetMapping("/transfer/documents/options") public JsonVO<Map<String,Object>> transferOptions(){return JsonVO.success(transfers.options());}
    @GetMapping("/transfer/documents/{id}") public JsonVO<Map<String,Object>> transfer(@PathVariable String id){return JsonVO.success(transfers.detail(id));}
    @PostMapping("/transfer/documents") public JsonVO<String> saveTransfer(@RequestBody Map<String,Object> body){return JsonVO.success(transfers.save(body));}
    @PostMapping("/transfer/documents/audit") public JsonVO<String> auditTransfer(@RequestBody Map<String,Object> body){transfers.command(body,false);return JsonVO.success("调拨审核状态已更新");}
    @PostMapping("/transfer/documents/delete") public JsonVO<String> deleteTransfer(@RequestBody Map<String,Object> body){transfers.command(body,true);return JsonVO.success("调拨草稿已删除");}
    @GetMapping("/verify/documents") public JsonVO<Map<String,Object>> counts(@RequestParam(defaultValue="1") int pageIndex,@RequestParam(defaultValue="20") int pageSize,@RequestParam(defaultValue="") String number){return JsonVO.success(counts.list(pageIndex,pageSize,number));}
    @GetMapping("/verify/documents/options") public JsonVO<Map<String,Object>> countOptions(){return JsonVO.success(counts.options());}
    @GetMapping("/verify/documents/{id}") public JsonVO<Map<String,Object>> count(@PathVariable String id){return JsonVO.success(counts.detail(id));}
    @PostMapping("/verify/documents") public JsonVO<String> saveCount(@RequestBody Map<String,Object> body){return JsonVO.success(counts.save(body));}
    @PostMapping("/verify/documents/{id}/audit") public JsonVO<String> auditCount(@PathVariable String id,@RequestBody Map<String,Object> body){counts.command(id,body,false);return JsonVO.success("盘点及差异库存已更新");}
    @PostMapping("/verify/documents/{id}/delete") public JsonVO<String> deleteCount(@PathVariable String id,@RequestBody Map<String,Object> body){counts.command(id,body,true);return JsonVO.success("盘点草稿已删除");}
}
