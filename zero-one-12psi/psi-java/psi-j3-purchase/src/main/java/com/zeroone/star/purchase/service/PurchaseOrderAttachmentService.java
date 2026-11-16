package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.web.multipart.MultipartFile;
import java.util.*;
import java.io.IOException;
import java.security.MessageDigest;

@Service
public class PurchaseOrderAttachmentService {
    public static final int MAX_BYTES=5*1024*1024;
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseOrderAuditService orders;
    private final PurchaseOrderAttachmentStore store;
    public PurchaseOrderAttachmentService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseOrderAuditService orders,PurchaseOrderAttachmentStore store){this.db=db;this.access=access;this.orders=orders;this.store=store;}
    private static String uid(){return UUID.randomUUID().toString().replace("-","");}
    private static String sha(byte[] bytes){
        try{StringBuilder out=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))out.append(String.format("%02x",b&255));return out.toString();}
        catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException("无法校验附件",e);}
    }
    private void readable(String id){
        UserDTO actor=access.authorize("/purchase-order/detail");List<String> frames=db.queryForList("SELECT frame FROM bor WHERE id=?",String.class,id);
        if(frames.size()!=1)throw new IllegalArgumentException("采购订单不存在");access.requireFrame(actor,frames.get(0));
    }
    private Map<String,Object> result(String order){Map<String,Object> result=new LinkedHashMap<>();result.put("version",orders.attachmentVersion(order));result.put("items",store.items(order));return result;}
    private void history(String order,UserDTO actor,String action){
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bor',?,NOW(),?,?)",uid(),order,actor.getId(),action);
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",uid(),actor.getId(),action+" "+order);
    }
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> upload(String order,String version,MultipartFile file) throws IOException {
        UserDTO actor=orders.guardAttachment(order,version);
        if(file==null || file.isEmpty() || file.getSize()>MAX_BYTES)throw new IllegalArgumentException("请选择非空附件，单个文件不能超过5MiB");
        String name=file.getOriginalFilename()==null?"":file.getOriginalFilename().trim();
        if(name.isEmpty() || name.length()>200 || name.equals(".") || name.equals("..") || name.contains("/") || name.contains("\\") || name.chars().anyMatch(c->Character.isISOControl(c)))throw new IllegalArgumentException("附件文件名无效，请使用不含路径的200字以内名称");
        byte[] bytes=file.getBytes();if(bytes.length==0 || bytes.length>MAX_BYTES)throw new IllegalArgumentException("单个附件必须为1字节至5MiB");
        String hash=sha(bytes);
        List<Map<String,Object>> existing=db.queryForList("SELECT name,sha256 FROM psi_bor_attachment WHERE order_id=? AND removed_at IS NULL FOR UPDATE",order);
        for(Map<String,Object> item:existing)if(name.equalsIgnoreCase(item.get("name").toString())){
            if(hash.equals(item.get("sha256")))return result(order);
            throw new IllegalArgumentException("已有同名附件；请先移除旧文件，再上传新文件");
        }
        if(existing.size()>=10)throw new IllegalArgumentException("每张订单最多保留10个有效附件，请先移除不需要的文件");
        db.update("INSERT INTO psi_bor_attachment(id,order_id,name,file_size,sha256,body,created_at,user_id) VALUES(?,?,?,?,?,?,NOW(),?)",uid(),order,name,bytes.length,hash,bytes,actor.getId());
        history(order,actor,"上传采购订单附件");return result(order);
    }
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> remove(String order,String id,String version){
        UserDTO actor=orders.guardAttachment(order,version);
        if(db.update("UPDATE psi_bor_attachment SET removed_at=NOW(),removed_by=? WHERE id=? AND order_id=? AND removed_at IS NULL",actor.getId(),id,order)!=1)throw new IllegalArgumentException("附件不存在或已移除");
        history(order,actor,"移除采购订单附件");return result(order);
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> download(String order,String id){
        readable(order);List<Map<String,Object>> rows=db.queryForList("SELECT name,file_size,sha256,body FROM psi_bor_attachment WHERE order_id=? AND id=? AND removed_at IS NULL",order,id);
        if(rows.size()!=1)throw new IllegalArgumentException("附件不存在或已移除");Map<String,Object> row=rows.get(0);byte[] bytes=(byte[])row.get("body");
        if(bytes==null || bytes.length>MAX_BYTES || bytes.length!=((Number)row.get("file_size")).intValue() || !sha(bytes).equals(row.get("sha256")))throw new IllegalStateException("附件内容校验失败，请联系管理员核对原文件");
        return row;
    }
}
