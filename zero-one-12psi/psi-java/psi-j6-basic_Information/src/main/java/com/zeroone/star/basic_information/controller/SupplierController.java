package com.zeroone.star.basic_information.controller;


import com.zeroone.star.basic_information.entity.Supplier;
import com.zeroone.star.basic_information.service.ISupplierService;
import com.zeroone.star.basic_information.service.impl.MsSupplierMapper;
import com.zeroone.star.basic_information.service.querySupplierListService;
import com.zeroone.star.project.components.fastdfs.FastDfsClientComponent;
import com.zeroone.star.project.components.fastdfs.FastDfsFileInfo;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.basic_information.supplier_management.SupplierAddDTO;
import com.zeroone.star.project.dto.j6.basic_information.supplier_management.SupplierDTO;
import com.zeroone.star.project.dto.j6.basic_information.supplier_management.querySupplierDto;
import com.zeroone.star.project.dto.j6.basic_information.supplier_management.querySupplierListDto;
import com.zeroone.star.project.j6.basic_information.supplier_management.SupplierApis;
import com.zeroone.star.project.query.j6.basic_information.supplier_management.supplierListQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.j6.basic_information.supplier_management.ImportResultVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiImplicitParam;
import io.swagger.annotations.ApiOperation;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.util.List;

/**
 * <p>
 * 供应商 前端控制器
 * </p>
 *
 * @author 趣味生煎
 * @since 2025-10-21
 */
@Slf4j
@RestController
@RequestMapping("/basic_information/supplier")
@Api(tags = "供应商管理")
public class SupplierController implements SupplierApis {
    @Resource
    private com.zeroone.star.basic_information.service.MasterNumberGuard numberGuard;


    @Resource
    ISupplierService supplierService;

    @Resource
    MsSupplierMapper ms;

    @Resource
    FastDfsClientComponent dfs;

    @Value("${fastdfs.nginx-servers}")
    private String fileServerUrl;



    @Resource
    querySupplierListService querySupplierListService;
    @ApiOperation(value = "查询供应商列表")
    @GetMapping("/querySupplierList")
    public JsonVO<PageDTO<querySupplierListDto>> querySupplierList(supplierListQuery query) {
        return JsonVO.success(querySupplierListService.querySupplierList(query));
    }

    @Override
    public JsonVO<PageDTO<querySupplierDto>> querySupplier(supplierListQuery query) {
        return null;
    }

    @GetMapping("/query-one")
    @ApiOperation("查询指定供应商信息")
    @ApiImplicitParam(name = "id", value = "供应商ID", required = true)
    @Override
    public JsonVO<SupplierDTO> querySupplierById(@RequestParam String id) {
        Supplier supplier = supplierService.getById(id);
        if (supplier == null) {
            return JsonVO.fail(null);
        }
        return JsonVO.success(ms.supplierToSupplierDto(supplier));
    }

    @PostMapping("/add")
    @ApiOperation("添加供应商")
    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.SERIALIZABLE)
    public JsonVO<String> addSupplier(@Validated @RequestBody SupplierAddDTO supplierAddDTO) {
        numberGuard.assertAvailable("supplier", supplierAddDTO.getNumber(), null);
        try {
            Supplier supplier = ms.addDtoToSupplier(supplierAddDTO);
            // id 列 varchar(32)，避免超长
            supplier.setId(java.util.UUID.randomUUID().toString().replace("-", ""));
            if (supplier.getPy() == null || supplier.getPy().isEmpty()) {
                supplier.setPy(supplier.getNumber() != null ? supplier.getNumber() : supplier.getName());
            }
            if (supplier.getFrame() == null || supplier.getFrame().isEmpty()) {
                supplier.setFrame("0");
            }
            if (supplier.getUser() == null || supplier.getUser().isEmpty()) {
                supplier.setUser("admin");
            }
            if (supplier.getCategory() == null || supplier.getCategory().isEmpty()) {
                supplier.setCategory("常规类别");
            }
            if (supplier.getMore() == null || supplier.getMore().isEmpty()) {
                supplier.setMore("{}");
            }
            if (supplier.getContacts() == null || supplier.getContacts().isEmpty()) {
                supplier.setContacts("[]");
            }
            if (supplierService.save(supplier)) {
                return JsonVO.success(supplier.getId());
            }
            return JsonVO.fail("保存供应商失败");
        } catch (Exception e) {
            log.error("添加供应商失败", e);
            return JsonVO.fail(e.getMessage() != null ? e.getMessage() : "添加供应商失败");
        }
    }

    @PutMapping("/update")
    @ApiOperation("修改供应商信息")
    @Override
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.SERIALIZABLE)
    public JsonVO<String> updateSupplier(@Validated @RequestBody SupplierDTO supplierDTO) {
        numberGuard.assertAvailable("supplier", supplierDTO.getNumber(), supplierDTO.getId());
        if (supplierService.updateById(ms.supplierDtoToSupplier(supplierDTO))) {
            return JsonVO.success(supplierDTO.getId().toString());
        }
        return JsonVO.fail(null);
    }

    @DeleteMapping("/delete")
    @ApiOperation("删除供应商")
    @Override
    public JsonVO<String> deleteSupplier(@RequestBody List<String> ids) {
        if (supplierService.removeByIds(ids)) {
            return JsonVO.success(ids.toString());
        }
        return JsonVO.fail(null);
    }

    /**
     * 导入供应商数据
     * @param file Excel文件
     * @return 导入结果
     */
    @SneakyThrows
    @PostMapping("/import")
    @ApiOperation(value = "导入供应商数据")
    @ResponseBody
    public JsonVO<ImportResultVO> importSuppliers(MultipartFile file,String url) {
        // 直接调用服务层处理导入
        ImportResultVO importResult = new ImportResultVO();
        try{
            importResult = supplierService.importSuppliers(file,url);
            return JsonVO.success(importResult);
        }catch (Exception e){
            log.error("导入供应商数据失败", e);
            throw new IllegalArgumentException(e instanceof IllegalArgumentException ? e.getMessage() : "供应商导入失败，请检查字段长度和关联资料");
        }

    }


    @Override
    @GetMapping("/export")
    @ApiOperation("导出供应商数据")
    public JsonVO<String> exportSuppliers(supplierListQuery query) {
        try {
            String fileUrl = supplierService.exportSuppliers(query);
            return JsonVO.success(fileUrl);
        } catch (Exception e) {
            log.error("导出供应商数据失败", e);
            return JsonVO.fail("导出失败: " + e.getMessage());
        }
    }

    @Override
    @GetMapping("/template")
    @ApiOperation("下载导入模板")
    public JsonVO<String> downloadTemplate() {
        return JsonVO.success("/api/basic_information/supplier/template-file");
    }

    @GetMapping("/template-file")
    public org.springframework.http.ResponseEntity<byte[]> templateFile() {
        java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
        java.util.List<java.util.List<String>> headers = new java.util.ArrayList<>();
        for (String title : java.util.Arrays.asList("供应商编号","供应商名称","供应商类别","增值税税率","联系人","联系电话","联系地址","开户银行","银行账号","纳税号码","备注")) headers.add(java.util.Collections.singletonList(title));
        com.alibaba.excel.EasyExcel.write(output).head(headers).sheet("供应商").doWrite(java.util.Collections.emptyList());
        return org.springframework.http.ResponseEntity.ok().header("Content-Disposition","attachment; filename=supplier-template.xlsx")
            .contentType(org.springframework.http.MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).body(output.toByteArray());
    }


}


