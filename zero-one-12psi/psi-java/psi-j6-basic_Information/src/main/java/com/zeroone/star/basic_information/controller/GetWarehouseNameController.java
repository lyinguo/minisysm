package com.zeroone.star.basic_information.controller;

import com.alibaba.cloud.commons.lang.StringUtils;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.basic_information.entity.Warehouse;
import com.zeroone.star.basic_information.service.IWarehouseService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.basic_information.warehouse_management.WarehouseNameDTO;
import com.zeroone.star.project.j6.basic_information.warehouse_management.GetWarehouseNameApis;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.List;

@RestController
@RequestMapping("/basic_information/warehouse")
public class GetWarehouseNameController implements GetWarehouseNameApis {
    @Resource
    private IWarehouseService warehouseService;

    @Override
    @GetMapping("/getWarehouseNameList")
    public JsonVO<List<WarehouseNameDTO>> getWarehouseNameList() {
        try {
            List<WarehouseNameDTO> warehouseNameList = warehouseService.getWarehouseNameList();
            return JsonVO.success(warehouseNameList);
        } catch (Exception e) {
            return JsonVO.fail(null);
        }
    }

    @GetMapping("/query-list")
    @ApiOperation("分页查询仓库列表")
    public JsonVO<PageDTO<Warehouse>> queryWarehouseList(
            @RequestParam(defaultValue = "1") long pageIndex,
            @RequestParam(defaultValue = "10") long pageSize,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String number,
            @RequestParam(required = false) String contacts,
            @RequestParam(required = false) String tel,
            @RequestParam(required = false) String add,
            @RequestParam(required = false) String data) {
        Page<Warehouse> page = new Page<>(pageIndex, pageSize);
        LambdaQueryWrapper<Warehouse> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(name), Warehouse::getName, name)
                .like(StringUtils.isNotBlank(number), Warehouse::getNumber, number)
                .like(StringUtils.isNotBlank(contacts), Warehouse::getContacts, contacts)
                .like(StringUtils.isNotBlank(tel), Warehouse::getTel, tel)
                .like(StringUtils.isNotBlank(add), Warehouse::getAdd, add)
                .like(StringUtils.isNotBlank(data), Warehouse::getData, data);
        Page<Warehouse> result = warehouseService.page(page, wrapper);
        return JsonVO.success(PageDTO.create(result));
    }

    @GetMapping("/query-one")
    @ApiOperation("查询仓库详情")
    public JsonVO<Warehouse> queryWarehouse(@RequestParam String id) {
        Warehouse warehouse = warehouseService.getById(id);
        if (warehouse == null) {
            return JsonVO.fail(null);
        }
        return JsonVO.success(warehouse);
    }

    @PostMapping("/add")
    @ApiOperation("新增仓库")
    public JsonVO<String> addWarehouse(@RequestBody Warehouse warehouse) {
        if (warehouse == null || StringUtils.isBlank(warehouse.getName()) || StringUtils.isBlank(warehouse.getNumber())) {
            return JsonVO.fail("仓库名称和编号不能为空");
        }
        if (StringUtils.isBlank(warehouse.getFrame())) {
            warehouse.setFrame("0");
        }
        warehouse.setId("wh_" + System.currentTimeMillis() + "_" + (int) (Math.random() * 1000));
        if (warehouseService.save(warehouse)) {
            return JsonVO.success(warehouse.getId());
        }
        return JsonVO.fail("新增仓库失败");
    }

    @PutMapping("/update")
    @ApiOperation("更新仓库")
    public JsonVO<String> updateWarehouse(@RequestBody Warehouse warehouse) {
        if (warehouse == null || StringUtils.isBlank(warehouse.getId())) {
            return JsonVO.fail("仓库ID不能为空");
        }
        if (warehouseService.getById(warehouse.getId()) == null) {
            return JsonVO.fail("仓库不存在");
        }
        if (warehouseService.updateById(warehouse)) {
            return JsonVO.success("更新成功");
        }
        return JsonVO.fail("更新失败");
    }

    @DeleteMapping("/delete")
    @ApiOperation("删除仓库")
    public JsonVO<String> deleteWarehouse(@RequestBody List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return JsonVO.fail("仓库ID不能为空");
        }
        if (warehouseService.removeByIds(ids)) {
            return JsonVO.success("删除成功");
        }
        return JsonVO.fail("删除失败");
    }
}
