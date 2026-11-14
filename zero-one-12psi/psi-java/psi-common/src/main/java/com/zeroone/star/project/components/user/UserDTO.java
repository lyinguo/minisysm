package com.zeroone.star.project.components.user;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * <p>
 * 描述：用户数据
 * FIXME 此类需要根据实际业务需求来添加字段
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@Data
@Builder
public class UserDTO {
    /**
     * 用户编号
     */
    private String id;
    /**
     * 用户名称
     */
    private String username;
    /**
     * 是否启用
     */
    //private Byte isEnabled;
    /**
     * 用户拥有角色列表
     */
    private List<String> roles;
    /**
     * 用户头像
     */
    private String avatar;
    /**
     * 组织id
     */
    private String frameId;
    /**
     * 组织名称
     */
    private String frameName;
}
