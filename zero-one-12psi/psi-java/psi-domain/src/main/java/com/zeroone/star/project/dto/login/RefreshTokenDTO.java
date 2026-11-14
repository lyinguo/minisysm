package com.zeroone.star.project.dto.login;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

/**
 * <p>
 * 描述：凭证刷新请求数据对象
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@ApiModel("凭证刷新请求数据对象")
@Data
public class RefreshTokenDTO {
    /**
     * 访问令牌
     */
    @ApiModelProperty(value = "授权令牌", required = true, example = "REDACTED_EXAMPLE_TOKEN")
    private String token;

    /**
     * 刷新令牌
     */
    @ApiModelProperty(value = "刷新令牌", required = true, example = "REDACTED_EXAMPLE_TOKEN")
    private String refreshToken;
}
