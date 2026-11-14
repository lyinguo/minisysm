package com.zeroone.star.project.query.j1.sysconfig;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 * 字典名称查询对象
 */
@Data
@ApiModel("字典名称查询对象")
public class DictNameQuery {
    @ApiModelProperty(value = "字典类型编码", example = "save_way")
    private String typeCode;

    @ApiModelProperty(value = "字典类型ID")
    private String typeId;
}
