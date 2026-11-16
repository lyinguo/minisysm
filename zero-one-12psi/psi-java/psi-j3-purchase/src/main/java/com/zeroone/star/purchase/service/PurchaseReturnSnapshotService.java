package com.zeroone.star.purchase.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.util.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Canonical return-draft snapshot shared by list, detail, edits and deletion. */
@Service
public class PurchaseReturnSnapshotService {
    private final JdbcTemplate db;
    private final PurchaseSnapshotService sources;
    public PurchaseReturnSnapshotService(JdbcTemplate db,PurchaseSnapshotService sources){this.db=db;this.sources=sources;}
    private String digest(List<Map<String,Object>> rows){
        StringBuilder text=new StringBuilder();
        for(Map<String,Object> row:rows){text.append('{');for(String key:new TreeSet<>(row.keySet())){
            Object raw=row.get(key);String value=raw==null?null:raw.toString();
            text.append(key.length()).append(':').append(key).append(value==null?-1:value.length()).append(':');if(value!=null)text.append(value);
        }text.append('}');}
        try{StringBuilder result=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(text.toString().getBytes(StandardCharsets.UTF_8)))result.append(String.format("%02x",b&255));return result.toString();}
        catch(java.security.NoSuchAlgorithmException error){throw new IllegalStateException("无法核对采购退货单版本",error);}
    }
    public String version(String id,boolean locked){
        String suffix=locked?" FOR UPDATE":"";List<Map<String,Object>> rows=new ArrayList<>();
        rows.addAll(db.queryForList("SELECT * FROM bre WHERE id=?"+suffix,id));
        rows.addAll(db.queryForList("SELECT * FROM bre_info WHERE pid=? ORDER BY id"+suffix,id));
        rows.addAll(db.queryForList("SELECT id FROM record WHERE type='bre' AND source=? ORDER BY id"+suffix,id));
        String source=rows.isEmpty() || rows.get(0).get("source")==null?"":rows.get(0).get("source").toString();
        rows.add(Collections.singletonMap("sourceVersion",sources.versions(Collections.singletonList(source)).get(source)));
        return digest(rows);
    }
    /** Three return and three source batch reads inside the caller's repeatable-read list transaction. */
    public Map<String,String> versions(List<String> ids){
        Map<String,String> result=new HashMap<>();if(ids.isEmpty())return result;
        if(ids.size()>200)throw new IllegalArgumentException("每页最多200张采购退货单");
        String placeholders=String.join(",",Collections.nCopies(ids.size(),"?"));Object[] args=ids.toArray();
        Map<String,List<Map<String,Object>>> documents=new HashMap<>();
        for(Map<String,Object> head:db.queryForList("SELECT * FROM bre WHERE id IN ("+placeholders+")",args)){List<Map<String,Object>> rows=new ArrayList<>();rows.add(head);documents.put(head.get("id").toString(),rows);}
        for(Map<String,Object> line:db.queryForList("SELECT * FROM bre_info WHERE pid IN ("+placeholders+") ORDER BY pid,id",args)){List<Map<String,Object>> rows=documents.get(line.get("pid").toString());if(rows!=null)rows.add(line);}
        for(Map<String,Object> history:db.queryForList("SELECT id,source FROM record WHERE type='bre' AND source IN ("+placeholders+") ORDER BY source,id",args)){List<Map<String,Object>> rows=documents.get(history.get("source").toString());if(rows!=null)rows.add(Collections.singletonMap("id",history.get("id")));}
        Set<String> sourceIds=new HashSet<>();for(List<Map<String,Object>> rows:documents.values())sourceIds.add(rows.get(0).get("source")==null?"":rows.get(0).get("source").toString());
        Map<String,String> sourceVersions=sources.versions(new ArrayList<>(sourceIds));
        for(Map.Entry<String,List<Map<String,Object>>> entry:documents.entrySet()){
            Object source=entry.getValue().get(0).get("source");entry.getValue().add(Collections.singletonMap("sourceVersion",sourceVersions.get(source==null?"":source.toString())));
            result.put(entry.getKey(),digest(entry.getValue()));
        }
        return result;
    }
    public Map<String,String> expected(List<String> ids,String single,Map<String,String> batch){
        if(ids==null || ids.isEmpty() || ids.size()>200 || new HashSet<>(ids).size()!=ids.size() || ids.stream().anyMatch(id->id==null || id.trim().isEmpty()))throw new IllegalArgumentException("请选择1到200张不同的采购退货单");
        if(single!=null){if(batch!=null || ids.size()!=1)throw new IllegalArgumentException("详情版本只能对应一张采购退货单，不能混用批量版本");batch=Collections.singletonMap(ids.get(0),single);}
        if(batch==null || !batch.keySet().equals(new HashSet<>(ids)) || batch.values().stream().anyMatch(value->value==null || !value.matches("[0-9a-f]{64}")))throw new IllegalArgumentException("请刷新并核对全部选中采购退货单，提交完整版本后再操作");
        return batch;
    }
    public void require(String id,String expected){
        if(expected==null || !expected.matches("[0-9a-f]{64}"))throw new IllegalArgumentException("请重新打开并核对采购退货草稿版本");
        if(!expected.equals(version(id,true)))throw new IllegalStateException("采购退货单已变化，请关闭详情重新打开，或刷新列表重新核对；本次整批未处理");
    }
}
