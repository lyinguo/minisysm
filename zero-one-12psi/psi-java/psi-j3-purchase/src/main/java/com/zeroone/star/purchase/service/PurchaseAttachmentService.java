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
public class PurchaseAttachmentService {
    public static final int MAX_BYTES=5*1024*1024;
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseSnapshotService snapshots;
    private final PurchaseAttachmentStore store;
    public PurchaseAttachmentService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseSnapshotService snapshots,PurchaseAttachmentStore store){this.db=db;this.access=access;this.snapshots=snapshots;this.store=store;}
    private static String uid(){return UUID.randomUUID().toString().replace("-","");}
    private static int state(Object value){return value instanceof Boolean?((Boolean)value?1:0):value==null?-1:((Number)value).intValue();}
    private UserDTO guard(String purchase,String expected){
        UserDTO actor=access.authorize("/purchase-note/revise");access.authorize("/purchase-note/info");
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('buy') ON DUPLICATE KEY UPDATE scope='buy'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='buy' FOR UPDATE",String.class);
        List<Map<String,Object>> found=db.queryForList("SELECT * FROM buy WHERE id=? FOR UPDATE",purchase);
        if(found.size()!=1)throw new IllegalArgumentException("采购单不存在");Map<String,Object> head=found.get(0);access.requireFrame(actor,String.valueOf(head.get("frame")));
        if(expected==null || !expected.matches("[0-9a-f]{64}"))throw new IllegalArgumentException("请重新打开采购单，核对当前版本后再操作附件");
        snapshots.require(purchase,expected);
        if(state(head.get("check"))!=0 || state(head.get("examine"))!=0 || state(head.get("nucleus"))!=0)throw new IllegalArgumentException("已核对、审核或核销的采购单不能修改附件");
        if(db.queryForObject("SELECT COUNT(*) FROM period WHERE date>=DATE(?)",Integer.class,head.get("time"))>0)throw new IllegalArgumentException("已结账期间不能修改采购单附件");
        for(String table:Arrays.asList("room_info","serve_info","account_info","summary"))
            if(!db.queryForList("SELECT id FROM "+table+" WHERE type='buy' AND `class`=? FOR UPDATE",purchase).isEmpty())throw new IllegalArgumentException("已有库存或资金凭据的采购单不能修改附件");
        if(!db.queryForList("SELECT purchase_id FROM psi_purchase_posting WHERE purchase_id=? FOR UPDATE",purchase).isEmpty()
            || !db.queryForList("SELECT id FROM buy_bill WHERE pid=? FOR UPDATE",purchase).isEmpty()
            || !db.queryForList("SELECT id FROM bre WHERE source=? FOR UPDATE",purchase).isEmpty()
            || !db.queryForList("SELECT id FROM bre_info WHERE source IN (SELECT id FROM buy_info WHERE pid=?) FOR UPDATE",purchase).isEmpty()
            || !db.queryForList("SELECT id FROM invoice WHERE type='buy' AND `class`=? FOR UPDATE",purchase).isEmpty())throw new IllegalArgumentException("存在入账、退货、核销或发票关联，不能修改采购单附件");
        return actor;
    }
    private static String sha(byte[] bytes){
        try{StringBuilder out=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))out.append(String.format("%02x",b&255));return out.toString();}
        catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException("无法校验附件",e);}
    }
    private void readable(String id){
        UserDTO actor=access.authorize("/purchase-note/info");List<String> frames=db.queryForList("SELECT frame FROM buy WHERE id=?",String.class,id);
        if(frames.size()!=1)throw new IllegalArgumentException("采购单不存在");access.requireFrame(actor,frames.get(0));
    }
    private Map<String,Object> result(String purchase){Map<String,Object> result=new LinkedHashMap<>();result.put("version",snapshots.version(purchase,true));result.put("items",store.items(purchase));return result;}
    private void history(String purchase,UserDTO actor,String action){
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'buy',?,NOW(),?,?)",uid(),purchase,actor.getId(),action);
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",uid(),actor.getId(),action+" "+purchase);
    }
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> upload(String purchase,String version,MultipartFile file) throws IOException {
        UserDTO actor=guard(purchase,version);
        if(file==null || file.isEmpty() || file.getSize()>MAX_BYTES)throw new IllegalArgumentException("请选择非空附件，单个文件不能超过5MiB");
        String name=file.getOriginalFilename()==null?"":file.getOriginalFilename().trim();
        if(name.isEmpty() || name.length()>200 || name.equals(".") || name.equals("..") || name.contains("/") || name.contains("\\") || name.chars().anyMatch(c->Character.isISOControl(c)))throw new IllegalArgumentException("附件文件名无效，请使用不含路径的200字以内名称");
        byte[] bytes=file.getBytes();if(bytes.length==0 || bytes.length>MAX_BYTES)throw new IllegalArgumentException("单个附件必须为1字节至5MiB");
        String hash=sha(bytes);
        List<Map<String,Object>> existing=db.queryForList("SELECT name,sha256 FROM psi_buy_attachment WHERE purchase_id=? AND removed_at IS NULL FOR UPDATE",purchase);
        for(Map<String,Object> item:existing)if(name.equalsIgnoreCase(item.get("name").toString())){
            if(hash.equals(item.get("sha256")))return result(purchase);
            throw new IllegalArgumentException("已有同名附件；请先移除旧文件，再上传新文件");
        }
        if(existing.size()>=10)throw new IllegalArgumentException("每张采购单最多保留10个有效附件，请先移除不需要的文件");
        db.update("INSERT INTO psi_buy_attachment(id,purchase_id,name,file_size,sha256,body,created_at,user_id) VALUES(?,?,?,?,?,?,NOW(),?)",uid(),purchase,name,bytes.length,hash,bytes,actor.getId());
        history(purchase,actor,"上传采购单附件");return result(purchase);
    }
    @Transactional(rollbackFor=Exception.class)
    public Map<String,Object> remove(String purchase,String id,String version){
        UserDTO actor=guard(purchase,version);
        if(db.update("UPDATE psi_buy_attachment SET removed_at=NOW(),removed_by=? WHERE id=? AND purchase_id=? AND removed_at IS NULL",actor.getId(),id,purchase)!=1)throw new IllegalArgumentException("附件不存在或已移除");
        history(purchase,actor,"移除采购单附件");return result(purchase);
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> download(String purchase,String id){
        readable(purchase);List<Map<String,Object>> rows=db.queryForList("SELECT name,file_size,sha256,body FROM psi_buy_attachment WHERE purchase_id=? AND id=? AND removed_at IS NULL",purchase,id);
        if(rows.size()!=1)throw new IllegalArgumentException("附件不存在或已移除");Map<String,Object> row=rows.get(0);byte[] bytes=(byte[])row.get("body");
        if(bytes==null || bytes.length>MAX_BYTES || bytes.length!=((Number)row.get("file_size")).intValue() || !sha(bytes).equals(row.get("sha256")))throw new IllegalStateException("附件内容校验失败，请联系管理员核对原文件");
        return row;
    }
}
