package com.zeroone.star.storemanagement.service;

import com.zeroone.star.project.components.user.RoleAuthority;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.components.user.DatabaseResourcePermission;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

@Service
public class StockDocumentAccess {
    private final UserHolder users;
    private final JdbcTemplate db;
    public StockDocumentAccess(UserHolder users, JdbcTemplate db) {
        this.users = users; this.db = db;
    }
    public UserDTO authorize(String kind, String action) {
        UserDTO user;
        try { user = users.getCurrentUser(); }
        catch (Exception error) { throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请重新登录"); }
        if (user == null || user.getId() == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        List<Map<String, Object>> found = db.queryForList("SELECT u.`user` AS login,u.frame,u.role,r.id AS role_id FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?", user.getId());
        if (found.size() != 1) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号已不存在");
        Map<String, Object> current = found.get(0);
        user.setUsername(String.valueOf(current.get("login")));
        user.setFrameId(current.get("frame") == null ? null : current.get("frame").toString());
        if ("0".equals(String.valueOf(current.get("role")))) user.setRoles(Collections.singletonList("ROLE_ADMIN"));
        else {
            if (current.get("role_id") == null) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "账号角色不存在");
            user.setRoles(Collections.singletonList(RoleAuthority.resolve(current.get("role_id").toString(), null)));
            frame(user);
        }
        String path = permissionPath(kind, action);
        if (user.getRoles().contains("ROLE_ADMIN")) return user;
        if (!DatabaseResourcePermission.allowed(db,current.get("role_id").toString(),"/j2-store"+path))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "没有对应单据操作权限");
        return user;
    }
    public String frame(UserDTO user) {
        if (user.getRoles().contains("ROLE_ADMIN")) return null;
        if (user.getFrameId() == null || user.getFrameId().isEmpty() || "0".equals(user.getFrameId()))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "缺少组织权限");
        if (db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,user.getFrameId())!=1)
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号所属组织已不存在");
        return user.getFrameId();
    }
    public String creationFrame(UserDTO user, String requested) {
        String selected = requested == null || requested.trim().isEmpty() ? user.getFrameId() : requested.trim();
        String allowed = frame(user);
        if (allowed != null && !allowed.equals(selected)) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "不能操作其他组织的单据");
        if (selected == null || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?", Integer.class, selected) != 1)
            throw new IllegalArgumentException("请选择有效组织");
        return selected;
    }
    private String permissionPath(String kind, String action) {
        if ("entry".equals(kind)) {
            Map<String, String> paths = new HashMap<>();
            paths.put("read", "/otherin"); paths.put("create", "/otherin/add"); paths.put("save", "/otherin/update");
            paths.put("audit", "/otherin/examine"); paths.put("delete", "/otherin/delete"); paths.put("check", "/otherin/check");
            paths.put("detail", "/otherin/detail");
            paths.put("export-simple", "/otherin/exportEasyExcel");paths.put("export-detail", "/otherin/exportDetailExcel");
            if (paths.containsKey(action)) return paths.get(action);
        } else if ("extry".equals(kind)) {
            if ("read".equals(action)) return "/otherout/list";
            if ("detail".equals(action)) return "/otherout/getInfo";
            if ("create".equals(action)) return "/otherout/add";
            if ("save".equals(action)) return "/otherout/update";
            if ("audit".equals(action)) return "/otherout/examine";
        } else if ("swap".equals(kind)) {
            if ("read".equals(action)) return "/transfer/query-transferList";
            if ("detail".equals(action)) return "/transfer/detail-transferInfo";
            if ("create".equals(action)) return "/transfer/add-transferList";
            if ("save".equals(action)) return "/transfer/modify-transfer";
            if ("audit".equals(action)) return "/transfer/batch-audit-transfer";
        }
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "单据类型或操作无效");
    }
}
