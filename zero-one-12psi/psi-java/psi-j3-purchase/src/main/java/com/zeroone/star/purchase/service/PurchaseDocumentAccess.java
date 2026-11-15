package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.components.user.RoleAuthority;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.data.redis.core.RedisTemplate;
import com.zeroone.star.project.constant.RedisConstant;
import java.util.*;

/** Live account/role grants and organization scope; dynamic detail paths use the legacy info resource. */
@Service
@org.springframework.context.annotation.Import(com.zeroone.star.project.config.redis.RedisConfig.class)
public class PurchaseDocumentAccess {
    private final UserHolder users;
    private final JdbcTemplate db;
    private final RedisTemplate<String,Object> redis;
    public PurchaseDocumentAccess(UserHolder users,JdbcTemplate db,RedisTemplate<String,Object> redis) { this.users=users;this.db=db;this.redis=redis; }
    public UserDTO authorize(String resource) {
        UserDTO actor=current();
        if(!actor.getRoles().contains("ROLE_ADMIN")) {
            Object allowed=redis.opsForHash().get(RedisConstant.RESOURCE_ROLES_MAP,resource);
            if(!(allowed instanceof Collection) || Collections.disjoint(actor.getRoles(),(Collection<?>)allowed))
                throw new ResponseStatusException(HttpStatus.FORBIDDEN,"没有采购单操作权限");
        }
        return actor;
    }
    public UserDTO current() {
        UserDTO actor;
        try { actor=users.getCurrentUser(); } catch(Exception error) { throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录"); }
        if(actor==null || actor.getId()==null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");
        List<Map<String,Object>> found=db.queryForList("SELECT u.frame,u.role,r.id AS role_id,r.keyword FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?",actor.getId());
        if(found.size()!=1) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"账号不存在");
        Map<String,Object> row=found.get(0);
        actor.setFrameId(row.get("frame")==null ? null:row.get("frame").toString());
        if("0".equals(String.valueOf(row.get("role")))) actor.setRoles(Collections.singletonList("ROLE_ADMIN"));
        else {
            if(row.get("role_id")==null) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号角色不存在");
            actor.setRoles(Collections.singletonList(RoleAuthority.resolve(row.get("role_id").toString(),(String)row.get("keyword"))));
            frame(actor);
        }
        return actor;
    }
    public String frame(UserDTO actor) {
        if(actor.getRoles().contains("ROLE_ADMIN")) return null;
        String frame=actor.getFrameId();
        if(frame==null || frame.isEmpty() || "0".equals(frame)) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号缺少有效组织");
        return frame;
    }
    public void requireFrame(UserDTO actor,String selected) {
        String allowed=frame(actor);
        if(allowed!=null && !allowed.equals(selected)) throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的采购单");
    }
    public void requireDocuments(List<String> ids,String resource) {
        UserDTO actor=authorize(resource);
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))
            throw new IllegalArgumentException("请选择1到200张不同的采购单");
        for(String id:ids) {
            List<String> frames=db.queryForList("SELECT frame FROM buy WHERE id=?",String.class,id);
            if(frames.size()!=1) throw new IllegalArgumentException("采购单不存在");
            requireFrame(actor,frames.get(0));
        }
    }
    public void requireLine(String id,String resource) {
        UserDTO actor=authorize(resource);
        List<String> frames=db.queryForList("SELECT b.frame FROM buy_info i JOIN buy b ON b.id=i.pid WHERE i.id=?",String.class,id);
        if(frames.size()!=1) throw new IllegalArgumentException("采购明细不存在");
        requireFrame(actor,frames.get(0));
    }
}
