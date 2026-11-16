package com.zeroone.star.storemanagement.controller;

import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListAddDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDetailDTO;
import com.zeroone.star.project.j2.store.OtherInApis;
import com.zeroone.star.project.query.j2.store.OtherInQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.IOtherInService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiImplicitParam;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.models.auth.In;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;
import com.zeroone.star.project.dto.j2.store.StockDocumentCommand;
import com.zeroone.star.storemanagement.service.InboundDocumentService;
import java.util.List;

/**
 * @BelongsProject: psi-java
 * @BelongsPackage: com.zeroone.star.storemanagement.controller
 * @Author: 高
 * @CreateTime: 2025-10-19 18:50
 * @Description: 其他入库单控制器类
 * @Version: 1.0
 */
@RestController
@RequestMapping("/otherin")
@Api(tags = "其他入库单")
public class OtherInController implements OtherInApis {

    @Autowired
    IOtherInService otherInListService;
    @Autowired private InboundDocumentService inbound;


    @PutMapping("/update")
    @ApiOperation(value = "修改其他入库单")
    @Override
    public JsonVO<String> updateOtherInList(@RequestBody OtherInListDetailDTO otherInListDetailDTO) {
        otherInListService.updateOtherInList(otherInListDetailDTO);
        return JsonVO.success(otherInListDetailDTO.getId());
    }

    @PutMapping("/examine")
    @ApiOperation(value = "审核/反审核入库单")
    @Override
    public JsonVO<Integer> examine(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(inbound.audit(command));
    }

    @PutMapping("/check")
    @ApiOperation(value = "核对/反核对入库单")
    @Override
    public JsonVO<Integer> check(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(inbound.check(command));
    }

    @GetMapping("/detail")
    @ApiOperation(value = "获取指定其他入库单详情")
    @ApiImplicitParam(name = "id", value = "其他入库单编号", required = true, example = "1d7b0520e93e72715d5d6af1fb7d9a37")
    @Override
    public JsonVO<Map<String,Object>> queryOtherInListDetail(@RequestParam String id) {
        return JsonVO.success(inbound.detail(id));
    }
    @GetMapping("/options")
    public JsonVO<Map<String,Object>> options(@RequestParam(required=false) String id) {
        return JsonVO.success(inbound.options(id));
    }

    @PostMapping("/add")
    @ApiOperation(value = "新增其他入库单")
    @Override
    public  JsonVO<String> addOtherInList(@RequestBody OtherInListAddDTO dto) {
        return otherInListService.saveOtherInList(dto);
    }

    @DeleteMapping("/delete")
    @ApiOperation("删除其他入库单")
    public JsonVO<Integer> removeOtherInList(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(inbound.remove(command));
    }

    @PostMapping("/import")
    @ApiOperation(value = "导入数据")
    @Override
    public JsonVO<String> importExcel(@RequestBody MultipartFile file) {
        return otherInListService.importExcel(file);
    }

    @GetMapping(value = "/exportEasyExcel")
    @ApiOperation(value = "导出简单报表")
    @Override
    public JsonVO<ResponseEntity<byte[]>> exportEasyExcel(@ApiParam(value = "例：\"1+2+4\"") @RequestParam String ids) {
        return otherInListService.exportEasyExcel(ids);
    }

    @GetMapping(value = "/exportDetailExcel")
    @ApiOperation(value = "导出详细报表")
    @Override
    public JsonVO<ResponseEntity<byte[]>> exportDetailExcel(@ApiParam(value = "例：\"1+2+4\"") @RequestParam String ids) {
        return otherInListService.exportDetailExcel(ids);
    }

    /**
     * 获取其他入库单列表（条件+分页）
     * 若不输入查询条件，则默认查询所有数据
     * @param query 查询参数对象，包含分页信息和各种查询条件
     * @return 返回分页的其他入库单列表
     */
    @GetMapping("")
    @ApiOperation(value = "获取其他入库单列表（条件+分页）")
    @Override
    public JsonVO<Map<String,Object>> listOtherIn(OtherInQuery query) {
        // 调用service查询数据
        return JsonVO.success(inbound.list(query));
    }
}
