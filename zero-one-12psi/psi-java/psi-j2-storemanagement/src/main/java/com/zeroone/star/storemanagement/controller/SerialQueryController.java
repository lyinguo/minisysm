package com.zeroone.star.storemanagement.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.mapper.SerialMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import lombok.extern.slf4j.Slf4j;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.Map;

/**
 * 序列号查询
 */
@Slf4j
@RestController
@RequestMapping("/serial")
@Api(tags = "序列查询")
public class SerialQueryController {

    private static final Map<Integer, String> STATE_LABEL = new HashMap<>();

    static {
        STATE_LABEL.put(0, "未销售");
        STATE_LABEL.put(1, "已销售");
        STATE_LABEL.put(2, "已调拨");
        STATE_LABEL.put(3, "已退货");
    }

    @Resource
    private SerialMapper serialMapper;

    @GetMapping("/list")
    @ApiOperation("序列号列表（条件+分页）")
    public JsonVO<PageDTO<Map<String, Object>>> list(
            @ApiParam("页码") @RequestParam(defaultValue = "1") long pageIndex,
            @ApiParam("每页条数") @RequestParam(defaultValue = "20") long pageSize,
            @ApiParam("序列号") @RequestParam(required = false) String serialNumber,
            @ApiParam("商品名称") @RequestParam(required = false) String goodsName,
            @ApiParam("商品编号") @RequestParam(required = false) String goodsNumber,
            @ApiParam("仓库ID") @RequestParam(required = false) String warehouseId,
            @ApiParam("状态") @RequestParam(required = false) Integer state
    ) {
        try {
            Page<Map<String, Object>> page = new Page<>(Math.max(pageIndex, 1), Math.max(pageSize, 1));
            Page<Map<String, Object>> result = serialMapper.selectSerialPage(
                    page,
                    StringUtils.hasText(serialNumber) ? serialNumber.trim() : null,
                    StringUtils.hasText(goodsName) ? goodsName.trim() : null,
                    StringUtils.hasText(goodsNumber) ? goodsNumber.trim() : null,
                    StringUtils.hasText(warehouseId) ? warehouseId.trim() : null,
                    state
            );
            if (result.getRecords() != null) {
                for (Map<String, Object> row : result.getRecords()) {
                    Object st = row.get("state");
                    Integer stateVal = null;
                    if (st instanceof Number) {
                        stateVal = ((Number) st).intValue();
                    } else if (st != null && StringUtils.hasText(String.valueOf(st))) {
                        try {
                            stateVal = Integer.parseInt(String.valueOf(st));
                        } catch (NumberFormatException ignored) {
                            // ignore
                        }
                    }
                    row.put("stateLabel", STATE_LABEL.getOrDefault(stateVal, "未知"));
                }
            }
            return JsonVO.success(PageDTO.create(result));
        } catch (Exception e) {
            log.error("序列查询失败", e);
            return JsonVO.fail(null);
        }
    }
}
