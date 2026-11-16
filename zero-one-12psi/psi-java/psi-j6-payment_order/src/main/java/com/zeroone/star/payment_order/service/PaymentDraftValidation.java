package com.zeroone.star.payment_order.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.components.user.RoleAuthority;
import com.zeroone.star.project.constant.RedisConstant;
import com.zeroone.star.project.dto.j6.payment_order.*;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import javax.annotation.PostConstruct;
import java.math.BigDecimal;
import java.util.*;

/** Shared field validation for creation and reviewed draft revision; posting uses a separate transaction. */
@Service
@ComponentScan({"com.zeroone.star.project.components.user","com.zeroone.star.project.components.jwt"})
@Import(com.zeroone.star.project.config.redis.RedisConfig.class)
public class PaymentDraftValidation {
    private final JdbcTemplate db;
    private final UserHolder users;
    private final RedisTemplate<String,Object> redis;
    public PaymentDraftValidation(JdbcTemplate db,UserHolder users,RedisTemplate<String,Object> redis) {this.db=db;this.users=users;this.redis=redis;}
    @PostConstruct public void initialize() {db.execute("CREATE TABLE IF NOT EXISTS psi_document_write_lock (scope VARCHAR(40) NOT NULL PRIMARY KEY)");}
    private String clean(String value) {return value==null?"":value.trim();}
    private void length(String value,int max,String label) {if(value!=null && value.length()>max)throw new IllegalArgumentException(label+"最多"+max+"个字符");}
    private void reference(String table,String id,String frame,String label,boolean optional) {
        if(optional && (id==null || id.isEmpty() || "0".equals(id)))return;
        if(id==null || id.isEmpty() || db.queryForObject("SELECT COUNT(*) FROM `"+table+"` WHERE id=? AND frame IN ('0',?)",Integer.class,id,frame)!=1)
            throw new IllegalArgumentException(label+"不存在或与制单组织不一致");
    }
    public UserDTO validate(OmyWithInfoAddDTO request) {
        if(!TransactionSynchronizationManager.isActualTransactionActive())throw new IllegalStateException("付款草稿必须在事务中保存");
        UserDTO actor;
        try {actor=users.getCurrentUser();}catch(Exception error){throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");}
        if(actor==null || actor.getId()==null)throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");
        List<Map<String,Object>> accounts=db.queryForList("SELECT u.frame,u.role,r.id AS role_id,r.keyword FROM `user` u LEFT JOIN role r ON r.id=u.role WHERE u.id=?",actor.getId());
        if(accounts.size()!=1)throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"账号不存在");
        Map<String,Object> account=accounts.get(0);String frame=account.get("frame")==null?"":account.get("frame").toString();
        if(frame.isEmpty() || "0".equals(frame) || db.queryForObject("SELECT COUNT(*) FROM frame WHERE id=?",Integer.class,frame)!=1)
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号缺少有效制单组织");
        actor.setFrameId(frame);
        if(!"0".equals(String.valueOf(account.get("role")))) {
            if(account.get("role_id")==null)throw new ResponseStatusException(HttpStatus.FORBIDDEN,"账号角色不存在");
            String role=RoleAuthority.resolve(account.get("role_id").toString(),(String)account.get("keyword"));
            Object allowed=redis.opsForHash().get(RedisConstant.RESOURCE_ROLES_MAP,"/payment-order/add");
            if(!(allowed instanceof Collection) || !((Collection<?>)allowed).contains(role))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"没有新增付款单权限");
        }
        fields(request,frame);
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('omy') ON DUPLICATE KEY UPDATE scope='omy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='omy' FOR UPDATE",String.class);
        if(!db.queryForList("SELECT id FROM omy WHERE number=? FOR UPDATE",request.getNumber()).isEmpty())throw new IllegalArgumentException("付款单编号已被使用");
        return actor;
    }
    public void fields(OmyWithInfoAddDTO request,String frame) {
        if(request==null || request.getInfoList()==null || request.getInfoList().isEmpty() || request.getInfoList().size()>200)throw new IllegalArgumentException("请填写1到200条结算账户明细");
        request.setNumber(clean(request.getNumber()));
        if(request.getNumber().isEmpty() || request.getNumber().length()>32)throw new IllegalArgumentException("单据编号必须为1到32个字符");
        if(request.getTime()==null)throw new IllegalArgumentException("请选择有效单据日期");
        reference("supplier",request.getSupplier(),frame,"供应商",false);
        reference("people",request.getPeople(),frame,"关联人员",true);
        if(clean(request.getPeople()).isEmpty() || "0".equals(request.getPeople()))request.setPeople(null);
        length(request.getData(),256,"单据备注");
        BigDecimal total=BigDecimal.ZERO;
        for(int i=0;i<request.getInfoList().size();i++) {
            OmyInfoAddDTO line=request.getInfoList().get(i);String label="第"+(i+1)+"条结算明细";
            if(line==null)throw new IllegalArgumentException(label+"不能为空");
            reference("account",line.getAccount(),frame,label+"账户",false);
            BigDecimal money=line.getMoney();
            if(money==null || money.signum()<=0 || money.stripTrailingZeros().scale()>4 || money.compareTo(new BigDecimal("99999999.9999"))>0)
                throw new IllegalArgumentException(label+"金额必须大于0，最多8位整数和4位小数");
            line.setSettle(line.getSettle()==null?"":line.getSettle());
            length(line.getSettle(),256,label+"结算号");length(line.getData1(),256,label+"备注");
            total=total.add(money);
        }
        if(total.compareTo(new BigDecimal("999999999999.9999"))>0)throw new IllegalArgumentException("付款合计超过允许范围");
        request.setTotal(total);
    }
    public void validateRevision(OmyWithInfoAddDTO request,String id,String frame) {
        if(!TransactionSynchronizationManager.isActualTransactionActive())throw new IllegalStateException("付款修改必须在事务中保存");
        fields(request,frame);
        if(!db.queryForList("SELECT id FROM omy WHERE number=? AND id<>? FOR UPDATE",request.getNumber(),id).isEmpty())throw new IllegalArgumentException("付款单编号已被使用");
    }
    public void record(String id,String actor,String number) {
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'omy',?,NOW(),?,?)",UUID.randomUUID().toString().replace("-",""),id,actor,"新增付款单 "+number);
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",UUID.randomUUID().toString().replace("-",""),actor,"新增付款单，单号："+number);
    }
}
