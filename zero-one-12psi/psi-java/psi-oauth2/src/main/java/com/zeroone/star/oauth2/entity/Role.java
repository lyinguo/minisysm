package com.zeroone.star.oauth2.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;
import java.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

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
        if (keyword != null && !keyword.trim().isEmpty()) {
            return keyword;
        }
        if (id == null || id.trim().isEmpty()) {
            throw new IllegalStateException("Role identity is required for authorization");
        }
        String compact = id.replace("-", "");
        byte[] identity = new byte[16];
        if (compact.matches("[0-9a-fA-F]{32}")) {
            for (int index = 0; index < identity.length; index++) {
                identity[index] = (byte) Integer.parseInt(compact.substring(index * 2, index * 2 + 2), 16);
            }
        } else {
            try {
                identity = Arrays.copyOf(MessageDigest.getInstance("SHA-256").digest(id.getBytes(StandardCharsets.UTF_8)), 16);
            } catch (NoSuchAlgorithmException error) {
                throw new IllegalStateException("Role identity hashing is unavailable", error);
            }
        }
        return "R_" + Base64.getUrlEncoder().withoutPadding().encodeToString(identity);
    }
}
