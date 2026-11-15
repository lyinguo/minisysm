package com.zeroone.star.sale.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.components.user.RoleAuthority;
import com.zeroone.star.project.constant.RedisConstant;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

@Service
public class SaleDocumentAccess {
    private final UserHolder users;
    private final JdbcTemplate db;
    private final RedisTemplate<String, Object> redis;
    public SaleDocumentAccess(UserHolder users, JdbcTemplate db, RedisTemplate<String, Object> redis) {
        this.users=users; this.db=db; this.redis=redis;
    }
    public UserDTO authorize(String resource) {
        UserDTO user;
        try { user=users.getCurrentUser(); }
        catch (Exception error) { throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录"); }
        if (user==null || user.getId()==null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");
        List<Map<String,Object>> found=db.queryForList("SELECT u.`user` AS login,u.frame,u.role,r.id AS role_id,r.keyword FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?",user.getId());
        if (found.size()!=1) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"账号已不存在");
        Map<String,Object> current=found.get(0);
        user.setUsername(String.valueOf(current.get("login")));
        user.setFrameId(current.get("frame")==null ? null : current.get("frame").toString());
        if ("0".equals(String.valueOf(current.get("role")))) user.setRoles(Collections.singletonList("ROLE_ADMIN"));
        else {
            if (current.get("role_id")==null) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号角色不存在");
            user.setRoles(Collections.singletonList(RoleAuthority.resolve(current.get("role_id").toString(),(String)current.get("keyword"))));
        }
        if (!user.getRoles().contains("ROLE_ADMIN")) {
            Object allowed=redis.opsForHash().get(RedisConstant.RESOURCE_ROLES_MAP,resource);
            if (!(allowed instanceof Collection) || Collections.disjoint(user.getRoles(),(Collection<?>)allowed))
                throw new ResponseStatusException(HttpStatus.FORBIDDEN,"没有销售单操作权限");
        }
        return user;
    }
    public String frame(UserDTO actor) {
        if (actor.getRoles().contains("ROLE_ADMIN")) return null;
        if (actor.getFrameId()==null || actor.getFrameId().isEmpty() || "0".equals(actor.getFrameId()))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号缺少有效组织");
        return actor.getFrameId();
    }
    public void requireFrame(UserDTO actor, String selected) {
        String allowed=frame(actor);
        if (allowed!=null && !allowed.equals(selected)) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的销售单");
    }
}
