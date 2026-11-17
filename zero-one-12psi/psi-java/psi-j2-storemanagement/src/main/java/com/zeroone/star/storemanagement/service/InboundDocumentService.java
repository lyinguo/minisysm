package com.zeroone.star.storemanagement.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j2.store.StockDocumentCommand;
import com.zeroone.star.project.query.j2.store.OtherInQuery;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.time.*;
import java.sql.Timestamp;
import java.util.*;

/** One UUID/version-aware inbound command path for old URLs and the entry workbench. */
@Service
public class InboundDocumentService {
    private final JdbcTemplate db;private final StockDocumentAccess access;
    private final StockDocumentWriteLock writes;private final WarehouseReportDocumentService reports;
    private final WarehousePostingProof proofs;
    public InboundDocumentService(JdbcTemplate db,StockDocumentAccess access,StockDocumentWriteLock writes,WarehouseReportDocumentService reports){
        this.db=db;this.access=access;this.writes=writes;this.reports=reports;this.proofs=new WarehousePostingProof(db);
    }
    private static String text(Object v){return v==null?"":v.toString();}
    private static int number(Object v){return v==null?0:((Number)v).intValue();}
    private int count(String sql,Object... args){return db.queryForObject(sql,Integer.class,args);}
    private void scope(UserDTO actor,Map<String,Object> head){
        String allowed=access.frame(actor);
        if(allowed!=null && !allowed.equals(text(head.get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的入库单");
    }
    private Map<String,Object> head(String id,boolean lock){
        List<Map<String,Object>> rows=db.queryForList("SELECT e.*,CAST(e.examine AS SIGNED) AS audit_state,CAST(e.`check` AS SIGNED) AS check_state,CAST(e.cse AS SIGNED) AS fee_state,CAST(e.type AS SIGNED) AS type_state FROM entry e WHERE id=?"+(lock?" FOR UPDATE":""),id);
        if(rows.size()!=1)throw new IllegalArgumentException("入库单不存在，请刷新列表");return rows.get(0);
    }
    private List<String> validate(StockDocumentCommand command,boolean target){
        if(command==null || command.getIds()==null || command.getIds().isEmpty() || command.getIds().size()>200 || new HashSet<>(command.getIds()).size()!=command.getIds().size() || command.getIds().stream().anyMatch(id->id==null || id.trim().isEmpty() || id.length()>32))
            throw new IllegalArgumentException("请选择1到200张不同的入库单");
        if(target && (command.getTarget()==null || command.getTarget()!=0 && command.getTarget()!=1))throw new IllegalArgumentException("请选择明确的核对或审核目标状态");
        if(command.getVersions()==null || !command.getVersions().keySet().equals(new HashSet<>(command.getIds())) || command.getVersions().values().stream().anyMatch(v->v==null || !v.matches("[0-9a-f]{32}")))
            throw new IllegalArgumentException("请重新读取并核对每张入库单的版本");
        List<String> ids=new ArrayList<>(command.getIds());Collections.sort(ids);return ids;
    }
    private Map<String,Map<String,Object>> reviewed(StockDocumentCommand command,UserDTO actor,List<String> ids){
        writes.lock("entry");Map<String,Map<String,Object>> result=new LinkedHashMap<>();
        for(String id:ids){
            CountAdjustmentGuard.require(db,"entry",id);Map<String,Object> row=head(id,true);scope(actor,row);
            if(!Arrays.asList(0,1).contains(number(row.get("audit_state"))) || !Arrays.asList(0,1).contains(number(row.get("check_state"))))throw new IllegalStateException("历史单据状态异常，请先核对原始数据");
            if(!reports.lockedVersion("entry",id).equals(command.getVersions().get(id)))throw new IllegalStateException("单据已被其他操作修改，请重新打开详情后重试");
            result.put(id,row);
        }
        return result;
    }
    private void operation(String id,UserDTO actor,String action,String documentNumber){
        Timestamp now=Timestamp.valueOf(LocalDateTime.now());
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'entry',?,?,?,?)",UUID.randomUUID().toString().replace("-",""),id,now,actor.getId(),action);
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",UUID.randomUUID().toString().replace("-",""),now,actor.getId(),action+"["+documentNumber+"]["+id+"]");
    }
    @Transactional(rollbackFor=Exception.class)
    public int audit(StockDocumentCommand command){
        UserDTO actor=access.authorize("entry","audit");List<String> ids=validate(command,true);reviewed(command,actor,ids);
        for(String id:ids)reports.audit("entry",id,command.getTarget(),command.getVersions().get(id),actor.getId());
        return ids.size();
    }
    @Transactional(rollbackFor=Exception.class)
    public int check(StockDocumentCommand command){
        UserDTO actor=access.authorize("entry","check");List<String> ids=validate(command,true);
        Map<String,Map<String,Object>> rows=reviewed(command,actor,ids);
        for(Map<String,Object> row:rows.values())if(number(row.get("check_state"))!=command.getTarget()){
            if(number(row.get("audit_state"))!=0 || proofs.hasMarker("entry",text(row.get("id"))) || proofs.hasMovements(text(row.get("id"))))throw new IllegalStateException("已审核或存在入账流水的入库单不能修改核对状态，请先反审核");
            proofs.requireOpenPeriod(row.get("time"));
        }
        for(Map.Entry<String,Map<String,Object>> row:rows.entrySet())if(number(row.getValue().get("check_state"))!=command.getTarget()){
            db.update("UPDATE entry SET `check`=? WHERE id=?",command.getTarget(),row.getKey());
            operation(row.getKey(),actor,command.getTarget()==1?"核对入库单":"反核对入库单",text(row.getValue().get("number")));
        }
        return ids.size();
    }
    @Transactional(rollbackFor=Exception.class)
    public int remove(StockDocumentCommand command){
        UserDTO actor=access.authorize("entry","delete");List<String> ids=validate(command,false);
        Map<String,Map<String,Object>> rows=reviewed(command,actor,ids);
        for(Map.Entry<String,Map<String,Object>> item:rows.entrySet()){
            String id=item.getKey();Map<String,Object> row=item.getValue();
            if(number(row.get("audit_state"))!=0 || number(row.get("check_state"))!=0 || !Arrays.asList(0,3).contains(number(row.get("fee_state"))))throw new IllegalStateException("已核对、审核或费用结算的单据不能删除，请先处理关联状态");
            proofs.requireOpenPeriod(row.get("time"));
            if(proofs.hasMarker("entry",id) || proofs.hasMovements(id) || count("SELECT COUNT(*) FROM invoice WHERE type='entry' AND `class`=?",id)>0 || count("SELECT COUNT(*) FROM bill_info WHERE mold='entry' AND source=?",id)>0
                    || count("SELECT COUNT(*) FROM cost WHERE type='entry' AND `class`=? AND (COALESCE(settle,0)<>0 OR COALESCE(state,0)<>0)",id)>0
                    || count("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='entry' AND `class`=?)",id)>0)
                throw new IllegalStateException("单据存在入账、发票或费用结算引用，不能删除");
        }
        for(Map.Entry<String,Map<String,Object>> item:rows.entrySet()){
            db.update("DELETE FROM entry_info WHERE pid=?",item.getKey());db.update("DELETE FROM cost WHERE type='entry' AND `class`=?",item.getKey());
            if(db.update("DELETE FROM entry WHERE id=?",item.getKey())!=1)throw new IllegalStateException("入库单删除失败");
            operation(item.getKey(),actor,"删除入库草稿",text(item.getValue().get("number")));
        }
        return ids.size();
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> detail(String id){
        UserDTO actor=access.authorize("entry","detail");Map<String,Object> head=head(id,false);scope(actor,head);
        Map<String,Object> result=reports.detail("entry",id);result.put("costs",db.queryForList("SELECT * FROM cost WHERE type='entry' AND `class`=? ORDER BY id",id));
        head.put("examine",head.remove("audit_state"));head.put("check",head.remove("check_state"));head.put("cse",head.remove("fee_state"));head.put("type",head.remove("type_state"));result.put("header",head);
        result.put("goods",db.queryForList("SELECT g.* FROM goods g WHERE g.id IN (SELECT goods FROM entry_info WHERE pid=?)",id));
        result.put("warehouses",db.queryForList("SELECT id,name,number FROM warehouse WHERE id IN (SELECT warehouse FROM entry_info WHERE pid=?)",id));
        Map<?,?> header=(Map<?,?>)result.get("header");
        List<String> names=db.queryForList("SELECT name FROM frame WHERE id=?",String.class,header.get("frame"));result.put("frameName",names.isEmpty()?text(header.get("frame")):names.get(0));
        return result;
    }
    @Transactional(readOnly=true)
    public Map<String,Object> options(String id){
        UserDTO actor=access.authorize("entry",id==null || id.isEmpty()?"create":"save");
        String frame=actor.getFrameId();if(id!=null && !id.isEmpty()){Map<String,Object> row=head(id,false);scope(actor,row);frame=text(row.get("frame"));}
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("warehouses",db.queryForList("SELECT w.id,w.name,w.number FROM warehouse w WHERE w.frame IN ('0',?) ORDER BY w.name,w.id",frame));
        return result;
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> list(OtherInQuery query){
        UserDTO actor=access.authorize("entry","read");String frame=access.frame(actor);if(frame==null && query.getFrame()!=null && !query.getFrame().trim().isEmpty())frame=query.getFrame().trim();
        StringBuilder where=new StringBuilder(" WHERE 1=1");List<Object> args=new ArrayList<>();
        if(frame!=null){where.append(" AND e.frame=?");args.add(frame);}
        for(String[] filter:new String[][]{{"e.number",query.getNumber()},{"e.data",query.getData()}})if(filter[1]!=null && !filter[1].trim().isEmpty()){where.append(" AND "+filter[0]+" LIKE ?");args.add("%"+filter[1].trim()+"%");}
        if(query.getName()!=null && !query.getName().trim().isEmpty()){where.append(" AND EXISTS(SELECT 1 FROM entry_info i JOIN goods g ON g.id=i.goods WHERE i.pid=e.id AND (g.name LIKE ? OR g.number LIKE ?))");args.add("%"+query.getName().trim()+"%");args.add("%"+query.getName().trim()+"%");}
        for(String[] filter:new String[][]{{"supplier","s.name",query.getSupplier()},{"people","p.name",query.getPeople()},{"user","u.name",query.getUser()}})if(filter[2]!=null && !filter[2].trim().isEmpty()){
            where.append(" AND (e.`"+filter[0]+"`=? OR "+filter[1]+" LIKE ?)");args.add(filter[2].trim());args.add("%"+filter[2].trim()+"%");
        }
        if(query.getStartTime()!=null && !query.getStartTime().trim().isEmpty()){where.append(" AND e.time>=?");args.add(Timestamp.valueOf(LocalDate.parse(query.getStartTime()).atStartOfDay()));}
        if(query.getEndTime()!=null && !query.getEndTime().trim().isEmpty()){where.append(" AND e.time<?");args.add(Timestamp.valueOf(LocalDate.parse(query.getEndTime()).plusDays(1).atStartOfDay()));}
        String[] keys={"examine","check","cse","type"};Integer[] states={query.getExamine(),query.getCheck(),query.getCse(),query.getType()};
        for(int i=0;i<keys.length;i++)if(states[i]!=null && states[i]!=-1){if(states[i]<0 || states[i]>(i==2?3:1))throw new IllegalArgumentException("查询状态无效");where.append(" AND e.`"+keys[i]+"`=?");args.add(states[i]);}
        String joins=" FROM entry e LEFT JOIN supplier s ON s.id=e.supplier LEFT JOIN people p ON p.id=e.people LEFT JOIN `user` u ON u.id=e.`user` LEFT JOIN frame f ON f.id=e.frame";
        long page=Math.max(1,query.getPageIndex()),size=query.getPageSize()<=0?20:Math.min(200,query.getPageSize());
        long total=db.queryForObject("SELECT COUNT(*)"+joins+where,Long.class,args.toArray());List<Object> pageArgs=new ArrayList<>(args);pageArgs.add(size);pageArgs.add((page-1)*size);
        List<Map<String,Object>> rows=db.queryForList("SELECT e.id,e.frame,e.supplier,e.time,e.number,e.total,e.cost,e.people,e.`user`,e.data,CAST(e.type AS SIGNED) AS type,CAST(e.examine AS SIGNED) AS examine,CAST(e.`check` AS SIGNED) AS `check`,CAST(e.cse AS SIGNED) AS cse,f.name AS frameName,s.name AS supplierName,p.name AS peopleName,u.name AS userName"+joins+where+" ORDER BY e.time DESC,e.id LIMIT ? OFFSET ?",pageArgs.toArray());
        for(Map<String,Object> row:rows)row.put("version",reports.detail("entry",text(row.get("id"))).get("version"));
        Map<String,Object> result=new LinkedHashMap<>();result.put("rows",rows);result.put("total",total);result.put("pageIndex",page);result.put("pageSize",size);return result;
    }
}
