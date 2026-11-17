package com.zeroone.star.storemanagement.controller;

import cn.hutool.core.date.DateTime;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j2.store.OtherOutListDTO;
import com.zeroone.star.project.dto.j2.store.OtherOutListInfoDTO;
import com.zeroone.star.project.j2.store.OtherOutApis;
import com.zeroone.star.project.query.j2.store.OtherOutQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.IOtherOutService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiImplicitParam;
import io.swagger.annotations.ApiOperation;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import javax.annotation.Resource;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import com.zeroone.star.project.dto.j2.store.StockDocumentCommand;
import com.zeroone.star.storemanagement.service.OutboundDocumentService;


/**
 * @BelongsProject: psi-java
 * @BelongsPackage: com.zeroone.star.storemanagement.controller
 * @Author: 高
 * @CreateTime: 2025-10-19 18:50
 * @Description: 其他出库单控制器类
 * @Version: 1.0
 */
@RestController
@RequestMapping("/otherout")
@Api(tags = "其他出库单")
public class OtherOutController implements OtherOutApis {

    @Resource
    private IOtherOutService otherOutListService;
    @Resource private OutboundDocumentService outbound;
    @Resource private com.zeroone.star.storemanagement.service.OutboundSpreadsheetService files;

    @PutMapping("/examine")
    @ApiOperation(value = "审核/反审核出库单")
    @Override
    public JsonVO<Integer> examine(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(outbound.audit(command));
    }
    @PutMapping("/check")
    @ApiOperation(value = "核对/反核对出库单")
    @Override
    public JsonVO<Integer> check(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(outbound.check(command));
    }

    @PutMapping("/update")
    @ApiOperation(value = "修改其他出库单")
    @Override
    public JsonVO<String> updateOtherOutList(@RequestBody OtherOutListDTO otherOutListDTO) {
        outbound.save(otherOutListDTO);

        return JsonVO.success(otherOutListDTO.getId());
    }

    @DeleteMapping("/delete")
    @ApiOperation(value = "删除其他出库单")
    @Override
    public JsonVO<Integer> deleteOtherOutList(@RequestBody StockDocumentCommand command) {
        return JsonVO.success(outbound.remove(command));
    }

    @GetMapping("/list")
    @ApiOperation(value = "获取出库单列表")
    @Override
    public JsonVO<Map<String,Object>> listOtherOut(OtherOutQuery query) {
        return JsonVO.success(outbound.list(query));
    }
    @GetMapping("/options")
    public JsonVO<Map<String,Object>> options(@RequestParam(required=false) String id){return JsonVO.success(outbound.options(id));}

    @GetMapping("/getInfo")
    @ApiOperation(value = "获取出库单详情")
    @ApiImplicitParam(name = "id", value = "其他出库单编号", required = true, example = "1d7b0520e93e72715d5d6af1fb7d9a37")
    @Override
    public JsonVO<Map<String,Object>> getOtherOutListInfo(String id) {
        return JsonVO.success(outbound.detail(id));
    }

    @PostMapping("/add")
    @ApiOperation(value = "添加出库单")
    @Override
    public JsonVO<String> addOtherOutList(@RequestBody OtherOutListDTO otherOutListDTO) {
        return JsonVO.success(outbound.create(otherOutListDTO));
    }


    @GetMapping("/exportEasyExcel")
    @ApiOperation(value = "导出其他出库单数据Excel")
    @Override
    public ResponseEntity<byte[]> exportOrderListExcel(@RequestParam("ids") List<String> ids) {
        return ResponseEntity.ok().header("Content-Disposition","attachment; filename=\"outbound-summary.xlsx\"").header("Cache-Control","no-store").contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).body(files.export(ids,false));
    }


    @GetMapping("/exportDetailExcel")
    @ApiOperation(value = "导出其他出库单详情数据Excel")
    @Override
    public ResponseEntity<byte[]> exportOrderDetailExcel(@RequestParam("ids") List<String> ids) {
        return ResponseEntity.ok().header("Content-Disposition","attachment; filename=\"outbound-detail.xlsx\"").header("Cache-Control","no-store").contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).body(files.export(ids,true));
    }


    @PostMapping("/import")
    @ApiOperation(value = "批量导入其他出库单")
    @Override
    public ResponseEntity<JsonVO<String>> importOrderList(@RequestPart("file") MultipartFile file) {
        return ResponseEntity.ok(JsonVO.success(outbound.requireImportWorkflow()));
    }

}
