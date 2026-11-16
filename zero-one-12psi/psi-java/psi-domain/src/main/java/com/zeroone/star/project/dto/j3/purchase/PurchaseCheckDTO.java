package com.zeroone.star.project.dto.j3.purchase;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.util.List;

@Data
@ApiModel("核对/反核对(支持批量)")
public class PurchaseCheckDTO {
    private String version;
    private java.util.Map<String,String> versions;
    @ApiModelProperty(value = "采购单ID", required = true)
    private List<String> ids;

    @ApiModelProperty(value = "核对状态：1=核对 / 0=反核对", required = true, example = "1")
    private Integer type;
}
