package com.zeroone.star.project.dto.j6.basic_information.supplier_management;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.math.BigDecimal;

/**
 * <p>
 * 描述：供应商DTO
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@Data
@ApiModel("供应商查询传输对象")
public class querySupplierListDto {
    @ApiModelProperty(value = "供应商ID", example = "1001")
    private String id;
    @ApiModelProperty(value = "供应商名称",example = "供应商名称")
    private String name;
    @ApiModelProperty(value = "供应商编号",example = "CHANGE_ME")
    private String number;
    @ApiModelProperty(value = "供应商类别",example = "常规类别")
    private String category;
    @ApiModelProperty(value = "所属组织",example = "0")
    private String frame;
    @ApiModelProperty(value = "应付金额",example = "0.0")
    private BigDecimal balance;
    @ApiModelProperty(value = "所属用户",example = "admin")
    private String user;
    @ApiModelProperty(value = "备注信息",example = "任意")
    private String data;
    @ApiModelProperty(value = "联系资料", example = "[]")
    private String contacts;
}
