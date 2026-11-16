package com.zeroone.star.payment_order.controller;

import cn.hutool.core.date.DateTime;
import com.zeroone.star.payment_order.service.IOmyService;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.j6.payment_order.OmyImportDTO;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.j6.payment_order.OmyInfoDetailVO;
import com.zeroone.star.project.vo.j6.payment_order.OmySimpleVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.SneakyThrows;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import javax.validation.Valid;
import java.io.ByteArrayOutputStream;
import java.util.List;

/**
 * 付款单控制器（处理导入导出及其他业务接口）
 */
@RestController
@RequestMapping("/payment-order")
@Api(tags = "付款单管理接口")
public class PaymentController {

    @Resource
    private IOmyService omyService;
    @Resource
    private com.zeroone.star.payment_order.service.PaymentImportService imports;
    @Resource
    private com.zeroone.star.payment_order.service.PaymentExportService exports;

    @Resource
    private EasyExcelComponent excelComponent;
    /**
         * 批量导入付款单（json导入）
     **/
@PostMapping("/addmore")
@ApiOperation(value = "批量导入付款单（JSON格式）")
public JsonVO<java.util.Map<String,Object>> batchImportOmyInfo(@RequestBody com.zeroone.star.payment_order.service.PaymentImportService.Command command) {
    return JsonVO.success(imports.save(command));
}

    @PostMapping("/import-preview")
    public JsonVO<java.util.Map<String,Object>> previewImport(@RequestBody com.zeroone.star.payment_order.service.PaymentImportService.Command command){return JsonVO.success(imports.preview(command));}

    /**
     * 导出简单报表（付款单+核销单）
     */
    @SneakyThrows
    @GetMapping(value = "/export/simple", produces = "application/octet-stream")
    @ApiOperation(value = "导出付款单简单报表")
    public ResponseEntity<byte[]> exportSimpleReport(@RequestParam java.util.Map<String,String> query) {
        // 1. 查询数据
        List<OmySimpleVO> dataList = exports.simple(query);

        // 2. 生成Excel
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        com.alibaba.excel.EasyExcel.write(out,OmySimpleVO.class).sheet("付款单简单报表").doWrite(dataList);

        // 3. 响应给前端
        HttpHeaders headers = new HttpHeaders();
        String filename = "payment-simple-" + DateTime.now().toString("yyyyMMddHHmmssS") + ".xlsx";
        headers.setContentDispositionFormData("attachment", filename);
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);

        ResponseEntity<byte[]> response = new ResponseEntity<>(out.toByteArray(), headers, HttpStatus.CREATED);
        out.close();
        return response;
    }

    /**
     * 导出详细报表（付款单详情表）
     */
    @SneakyThrows
    @GetMapping(value = "/export/detail", produces = "application/octet-stream")
    @ApiOperation(value = "导出付款单详细报表")
    public ResponseEntity<byte[]> exportDetailReport(@RequestParam java.util.Map<String,String> query) {
        // 1. 查询数据
        List<com.zeroone.star.payment_order.service.PaymentExportService.DetailLine> dataList = exports.detail(query);

        // 2. 生成Excel
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        com.alibaba.excel.EasyExcel.write(out,com.zeroone.star.payment_order.service.PaymentExportService.DetailLine.class).sheet("付款单详细报表").doWrite(dataList);

        // 3. 响应给前端
        HttpHeaders headers = new HttpHeaders();
        String filename = "payment-detail-" + DateTime.now().toString("yyyyMMddHHmmssS") + ".xlsx";
        headers.setContentDispositionFormData("attachment", filename);
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);

        ResponseEntity<byte[]> response = new ResponseEntity<>(out.toByteArray(), headers, HttpStatus.CREATED);
        out.close();
        return response;
    }
}
