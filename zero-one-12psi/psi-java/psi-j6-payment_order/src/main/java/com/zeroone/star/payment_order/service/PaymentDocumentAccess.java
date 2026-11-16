package com.zeroone.star.payment_order.service;

import com.zeroone.star.project.components.user.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

/** Refresh account, role and organization from persistent identity for each finance action. */
@Service
public class PaymentDocumentAccess {
    private final JdbcTemplate db;private final UserHolder users;
    public PaymentDocumentAccess(JdbcTemplate db,UserHolder users){this.db=db;this.users=users;}
    public UserDTO authorize(String path){
        UserDTO actor;try{actor=users.getCurrentUser();}catch(Exception error){throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");}
        if(actor==null || actor.getId()==null)throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");
        List<Map<String,Object>> rows=db.queryForList("SELECT u.frame,u.role,r.id AS role_id,r.keyword FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?",actor.getId());
        if(rows.size()!=1)throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"账号不存在");Map<String,Object> row=rows.get(0);
        actor.setFrameId(Objects.toString(row.get("frame"),""));
        if("0".equals(Objects.toString(row.get("role"),"")))actor.setRoles(Collections.singletonList("ROLE_ADMIN"));
        else{
            if(row.get("role_id")==null)throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号角色不存在");
            actor.setRoles(Collections.singletonList(RoleAuthority.resolve(row.get("role_id").toString(),(String)row.get("keyword"))));
            if(actor.getFrameId().isEmpty() || "0".equals(actor.getFrameId()))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号缺少有效组织");
            if(db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,actor.getFrameId())!=1)throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号所属组织已不存在，请联系管理员修正组织后重新操作");
            if(!DatabaseResourcePermission.allowed(db,row.get("role_id").toString(),path))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"没有付款单操作权限");
        }
        return actor;
    }
    public void requireFrame(UserDTO actor,String frame){if(!actor.getRoles().contains("ROLE_ADMIN") && !Objects.equals(actor.getFrameId(),frame))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的付款单");}
}
