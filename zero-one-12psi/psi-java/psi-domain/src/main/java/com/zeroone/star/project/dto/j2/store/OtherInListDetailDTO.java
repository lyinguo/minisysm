package com.zeroone.star.project.dto.j2.store;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@Data
@ApiModel("OtherInListDetailDTO")
public class OtherInListDetailDTO extends OtherInListAddDTO{

    @ApiModelProperty(value = "其他入库单ID", example = "1")
    private String id;

    @ApiModelProperty(value = "读取单据时返回的版本，用于防止覆盖其他人的修改")
    private String version;
}
