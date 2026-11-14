package com.zeroone.star.storemanagement.service.impl;

import cn.hutool.core.date.DateTime;
import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.ExcelWriter;
import com.alibaba.excel.util.ListUtils;
import com.alibaba.excel.write.metadata.WriteSheet;
import com.alibaba.excel.write.metadata.fill.FillConfig;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j2.store.*;
import com.zeroone.star.project.query.j2.store.InventoryQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.entity.AttrDO;
import com.zeroone.star.storemanagement.entity.GoodsDO;
import com.zeroone.star.storemanagement.mapper.AttrMapper;
import com.zeroone.star.storemanagement.mapper.GoodsMapper;
import com.zeroone.star.storemanagement.mapper.InventoryMapper;
import com.zeroone.star.storemanagement.mapper.InventoryVerifyMapper;
import com.zeroone.star.storemanagement.service.InventoryVerifyService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.awt.*;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@Slf4j
public class InventoryVerifyServiceImpl implements InventoryVerifyService {

    @Autowired
    InventoryVerifyMapper inventoryVerifyMapper;

    @Autowired
    GoodsMapper goodsMapper;

    @Autowired
    AttrMapper attrMapper;

    @Autowired
    EasyExcelComponent easyExcelComponent;

    /**
     * 获取盘盈单数据
     *
     * @param inventoryVerifyListS
     * @return
     */
    @Override
    public PageDTO<OtherInListInfoDTO> getInventoryPlus(List<InventoryVerifyDTO> inventoryVerifyListS) {

        List<OtherInListInfoDTO> list = new ArrayList<>();
        if (inventoryVerifyListS == null || inventoryVerifyListS.isEmpty()) {
            PageDTO<OtherInListInfoDTO> empty = new PageDTO<>();
            empty.setRows(list);
            return empty;
        }
        for (InventoryVerifyDTO inventoryVerifyList : inventoryVerifyListS) {
            if (inventoryVerifyList.getGoodId() == null || inventoryVerifyList.getInventoryDifference() == null) {
                continue;
            }
            GoodsDO good = goodsMapper.selectById(inventoryVerifyList.getGoodId());
            if (good == null) {
                throw new RuntimeException("商品不存在: " + inventoryVerifyList.getGoodId());
            }

            String attrName = null;
            if (inventoryVerifyList.getAttrId() != null && !inventoryVerifyList.getAttrId().isEmpty()) {
                AttrDO attr = attrMapper.selectById(inventoryVerifyList.getAttrId());
                if (attr != null) {
                    attrName = attr.getName();
                }
            }

            OtherInListInfoDTO otherInListInfoDTO = OtherInListInfoDTO.builder()
                    .goods(inventoryVerifyList.getGoodId())
                    .attr(attrName)
                    .unit(good.getUnit())
                    .warehouse(inventoryVerifyList.getWarehouseId())
                    .price(good.getBuy())
                    .nums(inventoryVerifyList.getInventoryDifference())
                    .total(inventoryVerifyList.getInventoryDifference().multiply(good.getBuy()))
                    .build();
            list.add(otherInListInfoDTO);
        }


        PageDTO<OtherInListInfoDTO> page = new PageDTO<>();
        page.setRows(list);

        return page;
    }

    /**
     * 获取盘亏单数据
     *
     * @param inventoryVerifyListS
     * @return
     */
    @Override
    public PageDTO<OtherOutListInfoDTO> getInventoryReduce(List<InventoryVerifyDTO> inventoryVerifyListS) {
        List<OtherOutListInfoDTO> list = new ArrayList<>();
        if (inventoryVerifyListS == null || inventoryVerifyListS.isEmpty()) {
            PageDTO<OtherOutListInfoDTO> empty = new PageDTO<>();
            empty.setRows(list);
            return empty;
        }
        for (InventoryVerifyDTO inventoryVerifyList : inventoryVerifyListS) {
            if (inventoryVerifyList.getGoodId() == null || inventoryVerifyList.getInventoryDifference() == null) {
                continue;
            }
            GoodsDO good = goodsMapper.selectById(inventoryVerifyList.getGoodId());
            if (good == null) {
                throw new RuntimeException("商品不存在: " + inventoryVerifyList.getGoodId());
            }

            String attrName = null;
            if (inventoryVerifyList.getAttrId() != null && !inventoryVerifyList.getAttrId().isEmpty()) {
                AttrDO attr = attrMapper.selectById(inventoryVerifyList.getAttrId());
                if (attr != null) {
                    attrName = attr.getName();
                }
            }
            OtherOutListInfoDTO otherOutListInfoDTO = OtherOutListInfoDTO.builder()
                    .goods(inventoryVerifyList.getGoodId())
                    .attr(attrName)
                    .unit(good.getUnit())
                    .warehouse(inventoryVerifyList.getWarehouseId())
                    .price(good.getBuy())
                    .nums(inventoryVerifyList.getInventoryDifference())
                    .total(inventoryVerifyList.getInventoryDifference().multiply(good.getBuy()))
                    .build();
            list.add(otherOutListInfoDTO);
        }

        PageDTO<OtherOutListInfoDTO> page = new PageDTO<>();
        page.setRows(list);

        return page;

    }
    /**
     * 导出库存盘点单（不需要参数，直接在数据库去查）
     */
    @Override
    public ByteArrayOutputStream exportInventoryVerifyExcel() throws IOException {
        try {
            List<InventoryVerifyListDTO> inventoryVerifyList = inventoryVerifyMapper.selectInventoryVerifyListDTO();
            log.info("库存盘点单导出数据条数：{}", inventoryVerifyList == null ? 0 : inventoryVerifyList.size());

            List<InventoryVerifyListDTO> inventoryVerifyListS = new ArrayList<>();
            if (inventoryVerifyList != null) {
                for (int i = 0; i < inventoryVerifyList.size(); i++) {
                    InventoryVerifyListDTO row = inventoryVerifyList.get(i);
                    if (row.getAttrName() != null && !row.getAttrName().isEmpty()) {
                        if (i != 0 && row.getName() != null && row.getName().equals(inventoryVerifyList.get(i - 1).getName())) {
                            InventoryVerifyListDTO attrOnly = new InventoryVerifyListDTO();
                            attrOnly.setName(row.getAttrName());
                            attrOnly.setTotalStock(row.getTotalStock());
                            inventoryVerifyListS.add(attrOnly);
                        } else {
                            InventoryVerifyListDTO copy = new InventoryVerifyListDTO();
                            copy.setId(row.getId());
                            copy.setName(row.getName());
                            copy.setNumber(row.getNumber());
                            copy.setSpec(row.getSpec());
                            copy.setCategoryName(row.getCategoryName());
                            copy.setBrand(row.getBrand());
                            copy.setUnit(row.getUnit());
                            copy.setCode(row.getCode());
                            copy.setData(row.getData());
                            copy.setTotalStock(row.getTotalStock());
                            inventoryVerifyListS.add(copy);
                            InventoryVerifyListDTO attrOnly = new InventoryVerifyListDTO();
                            attrOnly.setName(row.getAttrName());
                            attrOnly.setTotalStock(row.getTotalStock());
                            inventoryVerifyListS.add(attrOnly);
                        }
                    } else {
                        inventoryVerifyListS.add(row);
                    }
                }
            }

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            // 模板文件可能缺失，直接按注解列导出，保证可用
            EasyExcel.write(baos, InventoryVerifyListDTO.class)
                    .sheet("库存盘点单")
                    .doWrite(inventoryVerifyListS);
            return baos;
        } catch (Exception e) {
            log.error("导出库存盘点单Excel失败", e);
            throw new IOException("导出库存盘点单Excel失败: " + e.getMessage(), e);
        }
    }


}