package com.zeroone.star.project.components.user;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Base64;

/** One authority identity for token issuance, resource caches and authorization. */
public final class RoleAuthority {
    private RoleAuthority() { }
    public static String resolve(String id, String keyword) {
        if (keyword != null && !keyword.trim().isEmpty()) return keyword;
        if (id == null || id.trim().isEmpty()) throw new IllegalStateException("Role identity is required for authorization");
        String compact = id.replace("-", "");
        byte[] identity = new byte[16];
        if (compact.matches("[0-9a-fA-F]{32}")) {
            for (int index = 0; index < identity.length; index++)
                identity[index] = (byte) Integer.parseInt(compact.substring(index * 2, index * 2 + 2), 16);
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
