package com.zeroone.star.project.constant;

/**
 * <p>
 * 描述：Redis相关常量
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
public interface RedisConstant {
    /**
     * 角色资源映射Map的key
     */
    String RESOURCE_ROLES_MAP = "AUTH:RESOURCE_ROLES";

    /**
     * 注销凭证的key前缀
     */
    String LOGOUT_TOKEN_PREFIX = "AUTH:LOGOUT_TOKEN";


    /**
     * 凭证白名单状态
     * */
    String TOKEN_STATUS_ACTIVE = "ACTIVE";

    /**
     * 图形验证码答案前缀
     */
    String RUNNING_CAPTCHA = "RUNNING:CAPTCHA";


}
