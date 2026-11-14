package com.zeroone.star.storemanagement.controller;

import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.constant.RedisConstant;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.WarehouseReportDocumentService;
import org.springframework.web.bind.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

@RestController
@RequestMapping("/transfer/report-documents")
public class WarehouseReportDocumentController {
    private final WarehouseReportDocumentService service;
    private final UserHolder users;
    private final JdbcTemplate db;
    private final RedisTemplate<String, Object> redis;
    public WarehouseReportDocumentController(WarehouseReportDocumentService service, UserHolder users, JdbcTemplate db, RedisTemplate<String, Object> redis) { this.service = service; this.users = users; this.db = db; this.redis = redis; }
    private UserDTO authorize(String kind, String action) throws Exception {
        UserDTO user = users.getCurrentUser();
        if (user == null || user.getId() == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        // 沿用原系统约定：数据库 user.role=0 表示超级管理员，不是 role 表的外键。
        List<String> roles = db.queryForList("SELECT CASE WHEN u.role='0' THEN 'ROLE_ADMIN' ELSE r.keyword END FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?", String.class, user.getId());
        user.setRoles(roles);
        if (roles.contains("ROLE_ADMIN")) return user;
        String path;
        if ("entry".equals(kind)) path = "/otherin" + ("read".equals(action) ? "" : "save".equals(action) ? "/update" : "/examine");
        else if ("extry".equals(kind)) path = "/otherout/" + ("read".equals(action) ? "list" : "save".equals(action) ? "update" : "examine");
        else if ("swap".equals(kind)) path = "/transfer/" + ("read".equals(action) ? "query-transferList" : "save".equals(action) ? "modify-transfer" : "batch-audit-transfer");
        else throw new ResponseStatusException(HttpStatus.BAD_REQUEST);
        Object allowed = redis.opsForHash().get(RedisConstant.RESOURCE_ROLES_MAP, path);
        if (!(allowed instanceof Collection) || Collections.disjoint(roles, (Collection<?>) allowed)) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "没有对应单据操作权限");
        return user;
    }
    private String frame(UserDTO user) {
        if (user.getRoles().contains("ROLE_ADMIN")) return null;
        if (user.getFrameId() == null || user.getFrameId().isEmpty()) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "缺少组织权限");
        return user.getFrameId();
    }
    private void checkFrame(String kind, String id, UserDTO user) {
        String allowed = frame(user);
        if (allowed != null) {
            Map<?, ?> head = (Map<?, ?>) service.detail(kind, id).get("header");
            if (!allowed.equals(String.valueOf(head.get("frame")))) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "不能操作其他组织的单据");
        }
    }
    @GetMapping("/{kind}")
    public JsonVO<Map<String, Object>> list(@PathVariable String kind, @RequestParam(defaultValue="1") int pageIndex, @RequestParam(defaultValue="20") int pageSize, @RequestParam(defaultValue="") String number) throws Exception {
        UserDTO user = authorize(kind, "read");
        return JsonVO.success(service.list(kind, pageIndex, pageSize, number, frame(user)));
    }
    @GetMapping("/{kind}/{id}")
    public JsonVO<Map<String, Object>> detail(@PathVariable String kind, @PathVariable String id) throws Exception { UserDTO user = authorize(kind, "read"); checkFrame(kind, id, user); return JsonVO.success(service.detail(kind, id)); }
    @PutMapping("/{kind}/{id}")
    public JsonVO<Map<String, Object>> save(@PathVariable String kind, @PathVariable String id, @RequestBody WarehouseReportDocumentService.Edit edit) throws Exception {
        UserDTO user = authorize(kind, "save"); checkFrame(kind, id, user);
        return JsonVO.success(service.save(kind, id, edit, user.getUsername()));
    }
    @PostMapping("/{kind}/{id}/audit")
    public JsonVO<Map<String, Object>> audit(@PathVariable String kind, @PathVariable String id, @RequestBody Map<String, Object> body) throws Exception {
        UserDTO user = authorize(kind, "audit"); checkFrame(kind, id, user);
        return JsonVO.success(service.audit(kind, id, Integer.parseInt(String.valueOf(body.get("target"))), String.valueOf(body.get("version")), user.getUsername()));
    }
}
