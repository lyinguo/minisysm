package com.zeroone.star.storemanagement.controller;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.StockDocumentAccess;
import org.springframework.web.bind.annotation.*;

/** Old calculation-only operations cannot claim to have persisted a count. */
@RestController
@RequestMapping("/verify")
public class InventoryVerifyController {
 private final StockDocumentAccess access;
 public InventoryVerifyController(StockDocumentAccess access){this.access=access;}
 @PostMapping({"/inventoryPlus","/inventoryReduce"}) public JsonVO<String> legacyCalculation(){access.authorize("count","save");throw new IllegalArgumentException("请在库存盘点工作台保存盘点单并审核；旧盘盈盘亏计算不执行真实库存入账。");}
 @GetMapping("/export") public JsonVO<String> export(){access.authorize("count","read");throw new IllegalArgumentException("盘点文件导出尚待验收，请在库存盘点工作台查询已保存的真实盘点和差异单。");}
}
