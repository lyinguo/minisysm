package com.zeroone.star.project.dto.login;

import com.fasterxml.jackson.annotation.JsonIgnore;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * <p>
 * 描述：Oauth2获取Token返回信息封装
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@ApiModel("授权登录响应数据对象")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Oauth2TokenDTO {
    /**
     * 访问令牌
     */
    @ApiModelProperty(value = "授权令牌", example = "REDACTED_EXAMPLE_TOKEN")
    private String token;

    /**
     * 刷新令牌
     */
    @ApiModelProperty(value = "刷新令牌", required = true, example = "REDACTED_EXAMPLE_TOKEN")
    private String refreshToken;

    /**
     * 访问令牌头前缀
     */
    @ApiModelProperty(value = "访问令牌前缀", example = "Bearer ")
    private String tokenHead;

    /**
     * 有效时间（秒）
     */
    @JsonIgnore
    @ApiModelProperty(value = "有效时间", example = "3599")
    private Integer expiresIn;

    /**
     * 登录客户端ID
     */
    @JsonIgnore
    @ApiModelProperty(value = "登录客户端ID：psi-app或psi-manager", example = "psi-manager", required = true)
    private String clientId;
}

