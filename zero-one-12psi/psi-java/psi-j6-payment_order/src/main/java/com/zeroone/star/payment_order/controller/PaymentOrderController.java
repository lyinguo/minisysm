package com.zeroone.star.payment_order.controller;

import com.zeroone.star.payment_order.service.PaymentOrderService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.payment_order.*;
import com.zeroone.star.project.j6.payment_order.PaymentOrderApis;
import com.zeroone.star.project.query.j6.payment_order.OmyQuery;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.Api;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/payment-order")
@Api(tags = "付款单管理")
public class PaymentOrderController implements PaymentOrderApis {

    @Autowired
    private PaymentOrderService paymentOrderService;
    @Autowired
    private com.zeroone.star.payment_order.service.PaymentSettlementPreviewService settlements;
    @Autowired
    private com.zeroone.star.payment_order.service.PaymentSettlementPostingService posting;
    @Autowired
    private com.zeroone.star.payment_order.service.PaymentDocumentAccess access;
    @Autowired
    private com.zeroone.star.payment_order.service.PaymentDraftDocumentService drafts;

    @GetMapping("/options")
    public JsonVO<java.util.Map<String,Object>> options(@RequestParam String kind,@RequestParam(defaultValue="") String keyword,@RequestParam(required=false) String document){return JsonVO.success(drafts.options(kind,keyword,document));}

    @GetMapping("/documents")
    public JsonVO<java.util.Map<String,Object>> documents(@RequestParam java.util.Map<String,String> query) {return JsonVO.success(drafts.list(query));}
    @GetMapping("/document/{id}")
    public JsonVO<java.util.Map<String,Object>> document(@PathVariable String id) {return JsonVO.success(drafts.document(id));}
    @PutMapping("/document/{id}")
    public JsonVO<String> revise(@PathVariable String id,@RequestBody com.zeroone.star.payment_order.service.PaymentDraftDocumentService.Revision command) {return JsonVO.success(drafts.revise(id,command));}
    @DeleteMapping("/document/{id}")
    public JsonVO<String> delete(@PathVariable String id,@RequestBody com.zeroone.star.payment_order.service.PaymentDraftDocumentService.Removal command) {return JsonVO.success(drafts.delete(id,command.version));}

    @PostMapping("/settle")
    public JsonVO<Integer> settle(@RequestBody com.zeroone.star.payment_order.service.PaymentSettlementPostingService.Command command) {
        return JsonVO.success(posting.post(command));
    }

    @GetMapping("/settlement-document/{id}")
    public JsonVO<java.util.Map<String,Object>> settlementDocument(@PathVariable String id) {
        return JsonVO.success(drafts.document(id));
    }

    @GetMapping("/settlement-preview")
    public JsonVO<java.util.Map<String,Object>> settlementPreview(@RequestParam String id) {
        return JsonVO.success(settlements.preview(id));
    }

    /**
     * 新增付款单
     * @param addDto 新增付款单参数
     * @return 新增结果
     */
    @PostMapping("/add")
    @Override
    public JsonVO<String> addOmyWithInfo(@Validated @RequestBody OmyWithInfoAddDTO addDto) {
        String result = paymentOrderService.insertOmyWithInfo(addDto);
        return JsonVO.success(result);
    }


    /**
     * 修改付款单
     * @param dto 修改付款单参数
     * @return 修改结果
     */
    @PutMapping("/modify")
    @Override
    public JsonVO<String> modifyOmyAll(@Validated @RequestBody OmyAllDTO dto,String id) {
        access.authorize("/payment-order/modify");
        throw new IllegalArgumentException("不能在修改时自动反冲并重新付款，请先读取付款单并显式反审核后修改草稿");
    }

    /**
     * 获取付款单列表
     * @param condition 查询条件
     * @return 查询结果
     */
    @GetMapping("query-all")
    @Override
    public JsonVO<PageDTO<OmyWithBillDTO>> queryAllWithBill(@Validated  OmyQuery condition) {
        PageDTO<OmyWithBillDTO> result = paymentOrderService.listOmyWithBill(condition);
        return JsonVO.success(result);
    }

    /**
     * 获取指定付款单详情
     * @param id 付款单id
     * @return 详情
     */
    @GetMapping("/query-by-id/{id}")
    @Override
    public JsonVO<OmyWithInfoDTO> queryByIdWithInfo(@PathVariable String id) {
        drafts.requireScoped(id,"/payment-order/query-by-id");
        OmyWithInfoDTO result = paymentOrderService.getOmyWithInfoById(id);
        return JsonVO.success(result);
    }

    /**
     * 删除付款单
     * @param ids 删除的付款单id
     * @return 删除结果
     */
    @DeleteMapping("/remove")
    @Override
    public JsonVO<String> removeOmy(@RequestBody List<String> ids) {
        access.authorize("/payment-order/remove");
        throw new IllegalArgumentException("删除付款单需要当前已读版本，请先读取草稿，不能使用无版本删除入口");
    }

    /**
     * 修改付款单审核状态(审核/反审核)
     * @param ids 修改的付款单id
     * @return 修改结果
     */
    @PutMapping("/modify-examine-status")
    @Override
    public JsonVO<String> modifyExamineStatus(@RequestBody List<String> ids) {
        access.authorize("/payment-order/modify-examine-status");
        throw new IllegalArgumentException("请先核对原采购及退货结算方案，并提交明确的审核目标和已读版本，不能切换状态代替入账");
    }
}
