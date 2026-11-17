package com.zeroone.star.storemanagement.controller;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.TransferDocumentService;
import com.zeroone.star.storemanagement.service.StockDocumentAccess;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/** Legacy aliases use the same complete, versioned protocol as the workbench. */
@RestController
@RequestMapping("/transfer")
public class TransferController {
 private final TransferDocumentService service;private final StockDocumentAccess access;
 public TransferController(TransferDocumentService service,StockDocumentAccess access){this.service=service;this.access=access;}
 @GetMapping("/query-transferList") public JsonVO<Map<String,Object>> list(@RequestParam(defaultValue="1") int pageIndex,@RequestParam(defaultValue="20") int pageSize,@RequestParam(defaultValue="") String number){return JsonVO.success(service.list(pageIndex,pageSize,number));}
 @GetMapping("/detail-transferInfo") public JsonVO<Map<String,Object>> detail(@RequestParam String id){return JsonVO.success(service.detail(id));}
 @PostMapping("/add-transferList") public JsonVO<String> create(@RequestBody Map<String,Object> body){if(body.containsKey("id"))throw new IllegalArgumentException("新增不能携带已有单据ID");return JsonVO.success(service.save(body));}
 @PutMapping("/modify-transfer") public JsonVO<String> save(@RequestBody Map<String,Object> body){if(body.get("id")==null)throw new IllegalArgumentException("修改必须提供单据ID及版本");return JsonVO.success(service.save(body));}
 @PostMapping("/batch-audit-transfer") public JsonVO<String> audit(@RequestBody Map<String,Object> body){service.command(body,false);return JsonVO.success("调拨状态已更新");}
 @PostMapping("/remove-transfer") public JsonVO<String> remove(@RequestBody Map<String,Object> body){service.command(body,true);return JsonVO.success("草稿已删除");}
 @PostMapping("/import") public JsonVO<String> importFile(){access.authorize("swap","import");throw new IllegalArgumentException("旧调拨导入不支持完整事务和真实商品引用，已停用；请在调拨工作台选商品保存。模板预览确认导入尚待实现。");}
 @GetMapping({"/export","/exportDetail"}) public JsonVO<String> export(){access.authorize("swap","read");throw new IllegalArgumentException("调拨文件导出尚待验收，请先使用调拨单报表查询真实数据。");}
}
