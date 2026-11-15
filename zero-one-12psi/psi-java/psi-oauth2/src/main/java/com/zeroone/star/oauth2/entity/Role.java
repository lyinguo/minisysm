package com.zeroone.star.oauth2.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;
import com.zeroone.star.project.components.user.RoleAuthority;

/**
 * <p>
 * 角色表
 * </p>
 * @author 阿伟
 */
@Getter
@Setter
public class Role implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 唯一ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private String id;


    private String name;


    private String data;

    private String root;

    private String auth;

    private String keyword;

    /** Stable authority for legacy custom roles that were saved without a keyword. */
    public String getKeyword() {
        return RoleAuthority.resolve(id, keyword);
    }
}
