package com.zeroone.star.purchase.controller;
import com.zeroone.star.project.j3.purchase.PurchaseReturnFormApis;
import com.zeroone.star.project.vo.JsonVO;

import com.zeroone.star.project.vo.j3.purchase.PurchaseReturnDetailVO;
import com.zeroone.star.project.vo.j3.purchase.PurchaseReturnListVO;
import com.zeroone.star.purchase.DO.BreDO;
import com.zeroone.star.purchase.service.IBreBillService;
import com.zeroone.star.purchase.service.IBreInfoService;

import com.zeroone.star.purchase.service.IBreService;
import com.zeroone.star.project.components.fastdfs.FastDfsClientComponent;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiImplicitParams;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;

import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import com.zeroone.star.purchase.service.impl.BreInfoServiceImpl;
import com.zeroone.star.purchase.service.impl.BreServiceImpl;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import com.zeroone.star.project.query.j3.purchase.PurchaseReturnQuery;

import io.swagger.annotations.ApiImplicitParam;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;

/**
 * @Author: 小夏
 * @CreateTime: 2025-10-18
 * @Description: 采购退货单接口功能
 * @Version: 1.0
 */
@RestController
@RequestMapping("purchase-return-form")
@Api(tags = "采购管理-采购退货单")
@RequiredArgsConstructor
public class PurchaseReturnFormController implements PurchaseReturnFormApis {


    @Resource
    private IBreService breService;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseReturnDraftService drafts;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseReturnReviewService reviews;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseReturnPostingService postings;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDocumentAccess access;

    /**
     * 注入采购退货单服务：IBreService
     */
    @Resource
    private IBreService iBreService;

    /**
     * 注入采购退货单核销详情服务：IBreBillService
     *
     */
    @Resource
    private IBreBillService iBreBillService;

    /**
     * 注入采购退货单详情服务：IBreInfoService
     *
     */
    @Resource
    private IBreInfoService iBreInfoService;
    private final BreInfoServiceImpl breInfoService;
    /**
     * 删除采购退货单接口
     *
     * @param pid 需要删除的订单 id
     * @return 删除状态 0表示失败 1表示成功
     */
    @DeleteMapping("/delete")
    @ApiOperation(value = "删除采购退货单 (支持批量)")
    public JsonVO<String> deletePurchaseReturnForm(@RequestBody PurchaseReturnCommand command) {
        return JsonVO.success(String.valueOf(drafts.delete(command)));
    }

    /**
     * 更新采购退货单接口
     *
     * @param purchaseUpdateDTO 前端更新之后的 DTO 对象
     * @return 在数据库的更新状态 0表示失败 1表示成功
     *
     */
    @PutMapping("/update")
    @ApiOperation(value = "修改采购退货单")
    public JsonVO<Integer> updatePurchaseReturnForm(@RequestBody PurchaseReturnDraftDTO purchaseUpdateDTO) {
        drafts.save(purchaseUpdateDTO,true); return JsonVO.success(1);
    }

    /**
     * @param checkOutReturnGoodsDTO 需要核对或者反核对的订单
     * @return 核对或反核对之后的状态 0表示失败 1表示成功
     */
    @ApiOperation(value = "核对/反核对 (支持批量)")
    @PostMapping("/checkout")
    public JsonVO<Integer> checkOut(@RequestBody PurchaseReturnCommand command) {
        return JsonVO.success(reviews.check(command));
    }

    /**

     * @author xiaoliu


    public JsonVO<Integer> checkOut(@RequestBody List<String> pid) {
        return null;
    }

    /**
     * @param purchaseReturnQuery
     * @return
     * @Author: xiaoliu
     * @CreateTime: 2025-10-20
     * 获取采购退货单列表（条件+分页）
     */
    @Override
    @GetMapping("/list")

    @ApiOperation(value= "获取采购退货单列表（条件+分页）")
    public JsonVO<PageDTO<Map<String,Object>>> listPurchaseReturns(PurchaseReturnQuery purchaseReturnQuery) {
        return JsonVO.success(drafts.list(purchaseReturnQuery));
    }


    /**
     * @author xiaoliu
     * @CreateTime: 2025-10-20
     * 获取指定采购退货单详情
     * @param id 采购退货单id
     * @return 采购退货单详情
     */
    @Override
    @GetMapping("/detail")
    @ApiOperation(value = "获取指定采购退货单详情")
    @ApiImplicitParam(name= "id",value = "采购退货单id",required = true,example = "b005")
    public JsonVO<Map<String,Object>> getPurchaseReturnDetail(@RequestParam String id) {

        return JsonVO.success(drafts.detail(id));
    }


    /**
     * @param purchaseReturnAddDTO 采购退货单详情
     * @return 采购退货单id
     * @Author:
     * @Author: xiaoliu
     * @CreateTime: 2025-10-20
     * 新增采购退货单
     */
    @Override
    @PostMapping("/add")
    @ApiOperation(value = "新增采购退货单")
    public JsonVO<String> savePurchaseReturn(@RequestBody PurchaseReturnDraftDTO purchaseReturnAddDTO) {
        // TODO 新增采购退货单
        String breId = drafts.save(purchaseReturnAddDTO,false);
        return JsonVO.success(breId);
    }

    /**
     * @param purchaseReturnBreAuditDTO 采购退货单审核DTO
     * @return 审核结果
     * @author 斗气化码
     * 批量审核/反审核
     */
    @PutMapping("/approve")
    @ApiOperation(value = "审核/反审核（支持批量）")
    @Override
    public JsonVO<Integer> approve(@RequestBody PurchaseReturnCommand command) {
        return JsonVO.success(postings.post(command));
    }

    @Autowired
    FastDfsClientComponent dfs;

    /**
     * @param file  导入文件
     * @param file 导入文件
     * @return 导入结果
     * @author 斗气化码
     * 导入数据
     */
    @PostMapping("/import")
    @ApiOperation(value = "导入数据")
    @Override
    public JsonVO<String> importData(@RequestParam("file") MultipartFile file) {
        access.authorize("/purchase-return-form/import");throw new IllegalArgumentException("采购退货导入需真实来源及已读版本，当前入口尚未开放，本次未导入任何记录");
    }

    /**
     * @param ids 导出采购退货单简单报表id
     * @return 带有导出报表信息的响应实体
     * @author 斗气化码
     * 导出简单报表
     */
    @GetMapping(value = "/bre-export", produces = "application/octet-stream")
    @ApiOperation(value = "导出简单报表")
    @Override
    public ResponseEntity<byte[]> exportBre(@RequestParam("ids") List<String> ids) {
        drafts.requireScoped(ids,"/purchase-return-form/bre-export");return breService.exportBre(ids);
    }

    /**

     * 导出详细报表
     * @param ids 导出采购退货单详细报表列表
     * @return 带有导出报表信息的响应实体
     * @author 简单点
     * @since 2025-10-20
     * 导出详细报表
     */
    @GetMapping(value = "/breInfo-export", produces = "application/octet-zip")
    @ApiOperation(value = "导出详细报表")
    @Override
    public ResponseEntity<byte[]> exportBreInfo(@RequestParam("ids") List<String> ids) {
        drafts.requireScoped(ids,"/purchase-return-form/breInfo-export");return breService.exportBreInfo(ids);
    }
    @GetMapping("/document/{id}")
    public JsonVO<Map<String,Object>> document(@PathVariable String id){return JsonVO.success(drafts.detail(id));}
    @PutMapping("/document/{id}")
    public JsonVO<String> revise(@PathVariable String id,@RequestBody PurchaseReturnDraftDTO command){
        if(command.getId()!=null && !id.equals(command.getId()))throw new IllegalArgumentException("请求退货单与路径不一致");command.setId(id);return JsonVO.success(drafts.save(command,true));
    }
    public static class DraftRemoval {public String version;}
    @DeleteMapping("/document/{id}")
    public JsonVO<String> remove(@PathVariable String id,@RequestBody DraftRemoval command){drafts.delete(id,command.version);return JsonVO.success(id);}
    @GetMapping("/document/{id}/source-options")
    public JsonVO<Map<String,Object>> sourceOptions(@PathVariable String id){return JsonVO.success(drafts.sourceOptions(id));}
    @GetMapping("/accounts")
    public JsonVO<List<Map<String,Object>>> accounts(@RequestParam String source,@RequestParam(defaultValue="") String keyword,@RequestParam(defaultValue="false") boolean updating,@RequestParam(defaultValue="") String draft){return JsonVO.success(drafts.accounts(source,keyword,updating,draft));}
}
