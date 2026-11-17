package com.zeroone.star.storemanagement.service;

import static com.zeroone.star.storemanagement.service.MovementDrafts.*;
import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.math.BigDecimal;
import java.util.*;

@Service
public class TransferDocumentService {
    private final JdbcTemplate db;private final StockDocumentAccess access;private final MovementDrafts drafts;
    private final StockDocumentWriteLock writes;private final WarehouseReportDocumentService reports;private final WarehousePostingProof proofs;
    public TransferDocumentService(JdbcTemplate db,StockDocumentAccess access,MovementDrafts drafts,StockDocumentWriteLock writes,WarehouseReportDocumentService reports){this.db=db;this.access=access;this.drafts=drafts;this.writes=writes;this.reports=reports;this.proofs=new WarehousePostingProof(db);}
    private Map<String,Object> scoped(String id,UserDTO actor){Map<String,Object> doc=reports.detail("swap",id);String frame=access.frame(actor);if(frame!=null && !frame.equals(str(((Map<?,?>)doc.get("header")).get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的调拨单");return doc;}
    @Transactional(readOnly=true) public Map<String,Object> detail(String id){return scoped(id,access.authorize("swap","detail"));}
    @Transactional(readOnly=true) public Map<String,Object> list(int page,int size,String number){UserDTO actor=access.authorize("swap","read");return reports.list("swap",page,size,number,access.frame(actor));}
    @Transactional(readOnly=true) public Map<String,Object> options(){UserDTO actor=access.authorize("swap","read");Map<String,Object> result=new LinkedHashMap<>();result.put("warehouses",db.queryForList("SELECT id,name,number FROM warehouse WHERE frame IN ('0',?) ORDER BY name,id",actor.getFrameId()));return result;}
    @Transactional(rollbackFor=Exception.class) public String save(Map<String,Object> body){
        String id=str(body.get("id"));boolean create=id.isEmpty();UserDTO actor=access.authorize("swap",create?"create":"save");writes.lock("swap");Map<String,Object> old=null;String frame;
        if(create){frame=access.creationFrame(actor,str(body.get("frame")));id=uid();}
        else{reports.lockedVersion("swap",id);old=(Map<String,Object>)scoped(id,actor).get("header");if(!reports.lockedVersion("swap",id).equals(body.get("version")))throw new IllegalStateException("单据已变化，请重新打开");editable(id,old);frame=str(old.get("frame"));}
        if(body.containsKey("examine") && integer(body.get("examine"))!=0)throw new IllegalArgumentException("请先保存草稿，审核单独执行");
        String number=number(body.get("number"));java.sql.Timestamp time=time(body.get("time"));proofs.requireOpenPeriod(time);
        if(!db.queryForList("SELECT id FROM swap WHERE number=? AND id<>? FOR UPDATE",number,id).isEmpty())throw new IllegalArgumentException("调拨单号已存在");
        List<Map<String,Object>> lines=drafts.lines(body.get("items"),frame,true,false);Set<String> used=new HashSet<>();BigDecimal total=BigDecimal.ZERO;
        for(Map<String,Object> row:lines){String line=str(row.get("id"));if(!line.isEmpty() && (create || !used.add(line) || db.queryForObject("SELECT COUNT(*) FROM swap_info WHERE id=? AND pid=?",Integer.class,line,id)!=1))throw new IllegalArgumentException("明细不属于当前单据或重复");row.put("id",line.isEmpty()?uid():line);total=total.add((BigDecimal)row.get("total"));}
        decimal(total,false);
        if(create)db.update("INSERT INTO swap(id,frame,time,number,total,cost,examine,cse,`user`,data) VALUES(?,?,?,?,?,0,0,3,?,?)",id,frame,time,number,total,actor.getId(),body.get("data"));
        else{db.update("UPDATE swap SET time=?,number=?,total=?,data=? WHERE id=?",time,number,total,body.containsKey("data")?body.get("data"):old.get("data"),id);db.update("DELETE FROM swap_info WHERE pid=?",id);}
        for(Map<String,Object> row:lines)drafts.insert("swap",id,row);drafts.history("swap",id,actor,create?"新增调拨草稿":"修改调拨草稿");return id;
    }
    private void editable(String id,Map<String,Object> head){
        if(integer(head.get("examine"))!=0 || proofs.hasMarker("swap",id) || proofs.hasMovements(id) || db.queryForObject("SELECT COUNT(*) FROM swap WHERE id=? AND (cost<>0 OR cse IN (1,2))",Integer.class,id)>0 || db.queryForObject("SELECT COUNT(*) FROM cost WHERE type='swap' AND `class`=?",Integer.class,id)>0 || db.queryForObject("SELECT COUNT(*) FROM invoice WHERE type='swap' AND `class`=?",Integer.class,id)>0 || db.queryForObject("SELECT COUNT(*) FROM bill_info WHERE mold='swap' AND source=?",Integer.class,id)>0)throw new IllegalStateException("已审核、有流水或费用关联的调拨单不能重写，请先处理关联状态");proofs.requireOpenPeriod(head.get("time"));
    }
    @Transactional(rollbackFor=Exception.class) public void command(Map<String,Object> body,boolean remove){
        UserDTO actor=access.authorize("swap",remove?"delete":"audit");Object raw=body.get("ids"),versions=body.get("versions");
        if(!(raw instanceof List) || ((List<?>)raw).isEmpty() || ((List<?>)raw).size()>200 || !(versions instanceof Map))throw new IllegalArgumentException("请选择单据并重新获取版本");
        List<String> ids=new ArrayList<>();for(Object value:(List<?>)raw){if(!(value instanceof String) || str(value).isEmpty() || str(value).length()>32 || ids.contains(value))throw new IllegalArgumentException("单据ID无效或重复");ids.add((String)value);}Collections.sort(ids);
        if(!((Map<?,?>)versions).keySet().equals(new HashSet<>(ids)))throw new IllegalArgumentException("缺少单据版本");
        int target=-1;if(!remove){if(!(body.get("target") instanceof Integer) || !Arrays.asList(0,1).contains(body.get("target")))throw new IllegalArgumentException("审核须明确指定0或1");target=(Integer)body.get("target");}
        writes.lock("swap");for(String id:ids){String current=reports.lockedVersion("swap",id);Map<String,Object> doc=scoped(id,actor);if(!current.equals(((Map<?,?>)versions).get(id)))throw new IllegalStateException("单据已变化，请重新打开");if(remove)editable(id,(Map<String,Object>)doc.get("header"));}
        for(String id:ids)if(remove){db.update("DELETE FROM swap_info WHERE pid=?",id);db.update("DELETE FROM swap WHERE id=?",id);drafts.history("swap",id,actor,"删除调拨草稿");}else reports.audit("swap",id,target,str(((Map<?,?>)versions).get(id)),actor.getId());
    }
}
