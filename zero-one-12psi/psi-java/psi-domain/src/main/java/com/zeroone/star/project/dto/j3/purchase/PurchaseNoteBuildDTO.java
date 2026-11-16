package com.zeroone.star.project.dto.j3.purchase;

import com.baomidou.mybatisplus.annotation.TableName;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * @author TWTW
 * @date 2025/10/20 16:22
 * @description 采购退货单数据传输对象，用于采购单相关的参数传递与响应
 * Version: 1.0
 */
@Data
@ApiModel(description = "采购退货单数据传输对象")

public class PurchaseNoteBuildDTO {
    private String source;
    private String sourceNumber;
    private String sourceVersion;
    private String frame;
    private String supplier;
    private String supplierName;
    private String user;
    private String number;
    private LocalDateTime time;
    private BigDecimal total;
    private BigDecimal actual;
    private BigDecimal money;
    private Integer examine;
    private Integer check;
    private Integer nucleus;
    private List<Map<String,Object>> items;
    // 返回信息包含采购单核心信息、采购单明细列表
    @ApiModelProperty(value = "采购单核心信息")
    private PurchaseNoteBorDTO purchaseNoteBorDTO;
    @ApiModelProperty(value = "采购单明细列表")
    private List<PurchaseNoteBuilInfoDTO> purchaseNoteBuilInfoDTOS;

}
