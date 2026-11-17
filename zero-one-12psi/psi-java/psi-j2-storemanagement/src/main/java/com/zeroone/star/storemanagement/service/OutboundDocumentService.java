package com.zeroone.star.storemanagement.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j2.store.StockDocumentCommand;
import com.zeroone.star.project.dto.j2.store.OtherOutListDTO;
import com.zeroone.star.project.dto.j2.store.OtherOutListInfoDTO;
import com.zeroone.star.project.dto.j2.store.CostDTO;
import com.zeroone.star.project.query.j2.store.OtherOutQuery;
import cn.hutool.json.JSONArray;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.time.*;
import java.sql.Timestamp;
import java.math.*;
import java.util.*;

/** UUID/version commands for the legacy outbound URLs and the actual workbench. */
@Service
public class OutboundDocumentService {
    private final JdbcTemplate db;private final StockDocumentAccess access;
    private final StockDocumentWriteLock writes;private final WarehouseReportDocumentService reports;
    private final WarehousePostingProof proofs;
    public OutboundDocumentService(JdbcTemplate db,StockDocumentAccess access,StockDocumentWriteLock writes,WarehouseReportDocumentService reports){
        this.db=db;this.access=access;this.writes=writes;this.reports=reports;this.proofs=new WarehousePostingProof(db);
    }
    private static String text(Object v){return v==null?"":v.toString();}
    private static int number(Object v){return v==null?0:((Number)v).intValue();}
    private int count(String query,Object... args){return db.queryForObject(query,Integer.class,args);}
    private void scope(UserDTO actor,Map<String,Object> head){
        String allowed=access.frame(actor);
        if(allowed!=null && !allowed.equals(text(head.get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的出库单");
    }
    private Map<String,Object> head(String id,boolean lock){
        List<Map<String,Object>> rows=db.queryForList("SELECT e.*,CAST(e.examine AS SIGNED) AS audit_state,CAST(e.`check` AS SIGNED) AS check_state,CAST(e.cse AS SIGNED) AS fee_state,CAST(e.type AS SIGNED) AS type_state FROM extry e WHERE id=?"+(lock?" FOR UPDATE":""),id);
        if(rows.size()!=1)throw new IllegalArgumentException("出库单不存在，请刷新列表");return rows.get(0);
    }
    private List<String> validate(StockDocumentCommand command,boolean target){
        if(command==null || command.getIds()==null || command.getIds().isEmpty() || command.getIds().size()>200 || new HashSet<>(command.getIds()).size()!=command.getIds().size() || command.getIds().stream().anyMatch(id->id==null || id.trim().isEmpty() || id.length()>32))throw new IllegalArgumentException("请选择1到200张不同的出库单");
        if(target && (command.getTarget()==null || command.getTarget()!=0 && command.getTarget()!=1))throw new IllegalArgumentException("请选择明确的核对或审核目标状态");
        if(command.getVersions()==null || !command.getVersions().keySet().equals(new HashSet<>(command.getIds())) || command.getVersions().values().stream().anyMatch(v->v==null || !v.matches("[0-9a-f]{32}")))throw new IllegalArgumentException("请重新读取并核对每张出库单的版本");
        List<String> ids=new ArrayList<>(command.getIds());Collections.sort(ids);return ids;
    }
    private Map<String,Map<String,Object>> reviewed(StockDocumentCommand command,UserDTO actor,List<String> ids){
        writes.lock("extry");Map<String,Map<String,Object>> result=new LinkedHashMap<>();
        for(String id:ids){
            CountAdjustmentGuard.require(db,"extry",id);Map<String,Object> row=head(id,true);scope(actor,row);
            if(!Arrays.asList(0,1).contains(number(row.get("audit_state"))) || !Arrays.asList(0,1).contains(number(row.get("check_state"))))throw new IllegalStateException("历史单据状态异常，请先核对原始数据");
            if(!reports.lockedVersion("extry",id).equals(command.getVersions().get(id)))throw new IllegalStateException("单据已被其他操作修改，请重新打开详情后重试");
            result.put(id,row);
        }
        return result;
    }
    private void operation(String id,UserDTO actor,String action,String documentNumber){
        Timestamp now=Timestamp.valueOf(LocalDateTime.now());
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'extry',?,?,?,?)",UUID.randomUUID().toString().replace("-",""),id,now,actor.getId(),action);
        db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",UUID.randomUUID().toString().replace("-",""),now,actor.getId(),action+"["+documentNumber+"]["+id+"]");
    }
    @Transactional(rollbackFor=Exception.class)
    public int audit(StockDocumentCommand command){
        UserDTO actor=access.authorize("extry","audit");List<String> ids=validate(command,true);reviewed(command,actor,ids);
        for(String id:ids)reports.audit("extry",id,command.getTarget(),command.getVersions().get(id),actor.getId());
        return ids.size();
    }
    @Transactional(rollbackFor=Exception.class)
    public int check(StockDocumentCommand command){
        UserDTO actor=access.authorize("extry","check");List<String> ids=validate(command,true);Map<String,Map<String,Object>> rows=reviewed(command,actor,ids);
        for(Map<String,Object> row:rows.values())if(number(row.get("check_state"))!=command.getTarget()){
            if(number(row.get("audit_state"))!=0 || proofs.hasMarker("extry",text(row.get("id"))) || proofs.hasMovements(text(row.get("id"))))throw new IllegalStateException("已审核或存在入账流水的出库单不能修改核对状态，请先反审核");
            proofs.requireOpenPeriod(row.get("time"));
        }
        for(Map.Entry<String,Map<String,Object>> row:rows.entrySet())if(number(row.getValue().get("check_state"))!=command.getTarget()){
            db.update("UPDATE extry SET `check`=? WHERE id=?",command.getTarget(),row.getKey());operation(row.getKey(),actor,command.getTarget()==1?"核对出库单":"反核对出库单",text(row.getValue().get("number")));
        }
        return ids.size();
    }
    @Transactional(rollbackFor=Exception.class)
    public int remove(StockDocumentCommand command){
        UserDTO actor=access.authorize("extry","delete");List<String> ids=validate(command,false);Map<String,Map<String,Object>> rows=reviewed(command,actor,ids);
        for(Map.Entry<String,Map<String,Object>> item:rows.entrySet()){
            String id=item.getKey();Map<String,Object> row=item.getValue();
            if(number(row.get("audit_state"))!=0 || number(row.get("check_state"))!=0 || !Arrays.asList(0,3).contains(number(row.get("fee_state"))))throw new IllegalStateException("已核对、审核或费用结算的单据不能删除，请先处理关联状态");
            proofs.requireOpenPeriod(row.get("time"));
            if(proofs.hasMarker("extry",id) || proofs.hasMovements(id) || count("SELECT COUNT(*) FROM invoice WHERE type='extry' AND `class`=?",id)>0 || count("SELECT COUNT(*) FROM bill_info WHERE mold='extry' AND source=?",id)>0 || count("SELECT COUNT(*) FROM cost WHERE type='extry' AND `class`=? AND (COALESCE(settle,0)<>0 OR COALESCE(state,0)<>0)",id)>0 || count("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='extry' AND `class`=?)",id)>0)throw new IllegalStateException("单据存在入账、发票或费用结算引用，不能删除");
        }
        for(Map.Entry<String,Map<String,Object>> item:rows.entrySet()){
            db.update("DELETE FROM extry_info WHERE pid=?",item.getKey());db.update("DELETE FROM cost WHERE type='extry' AND `class`=?",item.getKey());
            if(db.update("DELETE FROM extry WHERE id=?",item.getKey())!=1)throw new IllegalStateException("出库单删除失败");operation(item.getKey(),actor,"删除出库草稿",text(item.getValue().get("number")));
        }
        return ids.size();
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> detail(String id){
        UserDTO actor=access.authorize("extry","detail");Map<String,Object> original=head(id,false);scope(actor,original);
        Map<String,Object> result=reports.detail("extry",id);Map<String,Object> header=(Map<String,Object>)result.get("header");
        for(String[] names:new String[][]{{"examine","audit_state"},{"check","check_state"},{"cse","fee_state"},{"type","type_state"}})header.put(names[0],original.get(names[1]));
        result.put("costs",db.queryForList("SELECT * FROM cost WHERE type='extry' AND `class`=? ORDER BY id",id));
        result.put("goods",db.queryForList("SELECT g.* FROM goods g WHERE g.id IN (SELECT goods FROM extry_info WHERE pid=?)",id));
        result.put("warehouses",db.queryForList("SELECT id,name,number FROM warehouse WHERE id IN (SELECT warehouse FROM extry_info WHERE pid=?)",id));return result;
    }
    private String uid(){return UUID.randomUUID().toString().replace("-","");}
    @Transactional(rollbackFor=Exception.class)
    public String create(OtherOutListDTO dto){
        UserDTO actor=access.authorize("extry","create");writes.lock("extry");prepare(dto,actor,null);
        String id=uid();
        db.update("INSERT INTO extry(id,customer,frame,time,number,type,total,cost,people,logistics,file,data,more,examine,cse,`check`,`user`) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,0,?)",id,dto.getCustomer(),dto.getFrame(),Timestamp.valueOf(dto.getTime()),dto.getNumber(),dto.getType(),dto.getTotal(),dto.getCost(),dto.getPeople(),dto.getLogistics(),dto.getFile(),dto.getData(),dto.getMore(),dto.getCse(),actor.getId());
        persist(id,dto);operation(id,actor,"新增出库单",dto.getNumber());return id;
    }
    @Transactional(rollbackFor=Exception.class)
    public void save(OtherOutListDTO dto){
        UserDTO actor=access.authorize("extry","save");if(dto==null || dto.getId()==null)throw new IllegalArgumentException("请重新打开出库单");
        writes.lock("extry");CountAdjustmentGuard.require(db,"extry",dto.getId());Map<String,Object> original=head(dto.getId(),true);scope(actor,original);
        if(number(original.get("audit_state"))!=0 || number(original.get("check_state"))!=0 || !Arrays.asList(0,3).contains(number(original.get("fee_state"))))throw new IllegalStateException("请先处理审核、核对及费用结算状态，再修改草稿");
        if(proofs.hasMarker("extry",dto.getId()) || proofs.hasMovements(dto.getId()))throw new IllegalStateException("单据存在原始入账凭据，请核对历史记录");
        if(dto.getVersion()==null || !dto.getVersion().equals(reports.lockedVersion("extry",dto.getId())))throw new IllegalStateException("单据已被其他操作修改，请重新打开详情");
        proofs.requireOpenPeriod(original.get("time"));
        if(count("SELECT COUNT(*) FROM invoice WHERE type='extry' AND `class`=?",dto.getId())>0 || count("SELECT COUNT(*) FROM bill_info WHERE mold='extry' AND source=?",dto.getId())>0 || count("SELECT COUNT(*) FROM cost_info WHERE pid IN (SELECT id FROM cost WHERE type='extry' AND `class`=?)",dto.getId())>0)throw new IllegalStateException("单据存在关联记录，不能重写草稿");
        if(count("SELECT COUNT(*) FROM cost WHERE type='extry' AND `class`=? AND (COALESCE(settle,0)<>0 OR COALESCE(state,0)<>0)",dto.getId())>0)throw new IllegalStateException("费用已有结算记录，不能重写草稿");
        if(dto.getFile()==null)dto.setFile((String)original.get("file"));if(dto.getMore()==null)dto.setMore((String)original.get("more"));if(dto.getLogistics()==null)dto.setLogistics((String)original.get("logistics"));
        if(dto.getCustomer()==null)dto.setCustomer((String)original.get("customer"));if(dto.getPeople()==null)dto.setPeople((String)original.get("people"));if(dto.getData()==null)dto.setData((String)original.get("data"));
        dto.setFrame(text(original.get("frame")));prepare(dto,actor,dto.getId());
        db.update("UPDATE extry SET customer=?,time=?,number=?,type=?,total=?,cost=?,people=?,logistics=?,file=?,data=?,more=?,cse=? WHERE id=?",dto.getCustomer(),Timestamp.valueOf(dto.getTime()),dto.getNumber(),dto.getType(),dto.getTotal(),dto.getCost(),dto.getPeople(),dto.getLogistics(),dto.getFile(),dto.getData(),dto.getMore(),dto.getCse(),dto.getId());
        db.update("DELETE FROM extry_info WHERE pid=?",dto.getId());db.update("DELETE FROM cost WHERE type='extry' AND `class`=?",dto.getId());
        persist(dto.getId(),dto);operation(dto.getId(),actor,"修改出库单",dto.getNumber());
    }
    private BigDecimal amount(BigDecimal value,boolean positive){
        if(value==null || (positive?value.signum()<=0:value.signum()<0))throw new IllegalArgumentException("数量必须大于零，预计单价和费用不能为负数");
        try{value=value.setScale(4,RoundingMode.UNNECESSARY);}catch(ArithmeticException e){throw new IllegalArgumentException("数量和金额最多4位小数");}
        if(value.precision()>12)throw new IllegalArgumentException("数量或金额超过允许范围");return value;
    }
    private void reference(String table,String id,String frame){
        if(id!=null && !id.isEmpty() && count("SELECT COUNT(*) FROM `"+table+"` WHERE id=? AND frame IN ('0',?)",id,frame)!=1)throw new IllegalArgumentException("客户或关联人员不存在，或不属于单据组织");
    }
    private void prepare(OtherOutListDTO dto,UserDTO actor,String excluded){
        if(dto==null || dto.getTime()==null || dto.getNumber()==null || dto.getNumber().trim().isEmpty())throw new IllegalArgumentException("请填写出库单号和日期");
        dto.setFrame(access.creationFrame(actor,dto.getFrame()));dto.setNumber(dto.getNumber().trim());
        if(dto.getNumber().codePointCount(0,dto.getNumber().length())>32)throw new IllegalArgumentException("单据编号最多32个字符");
        if(dto.getType()==null || !Arrays.asList(0,1).contains(dto.getType()) || !Integer.valueOf(0).equals(dto.getExamine()) || !Integer.valueOf(0).equals(dto.getCheck()))throw new IllegalArgumentException("请先保存为未核对、未审核的其他出库或盘亏草稿");
        proofs.requireOpenPeriod(Timestamp.valueOf(dto.getTime()));
        if(!db.queryForList("SELECT id FROM extry WHERE number=? AND id<>? FOR UPDATE",dto.getNumber(),excluded==null?"":excluded).isEmpty())throw new IllegalArgumentException("单据编号已存在");
        reference("customer",dto.getCustomer(),dto.getFrame());reference("people",dto.getPeople(),dto.getFrame());
        List<OtherOutListInfoDTO> lines=dto.getOtherOutListInfoDTOList();
        if(lines==null || lines.isEmpty() || lines.size()>200)throw new IllegalArgumentException("请添加1到200行商品明细");
        Set<String> lineIds=new HashSet<>(),serialNumbers=new HashSet<>();BigDecimal total=BigDecimal.ZERO;
        for(OtherOutListInfoDTO line:lines){
            if(line==null || line.getGoods()==null || line.getWarehouse()==null)throw new IllegalArgumentException("请选择商品和出库仓库");
            if(line.getId()!=null && !line.getId().isEmpty()){
                if(excluded==null || !lineIds.add(line.getId()) || count("SELECT COUNT(*) FROM extry_info WHERE id=? AND pid=?",line.getId(),excluded)!=1)throw new IllegalArgumentException("明细重复或不属于当前出库单");
            }else line.setId(uid());
            List<Map<String,Object>> products=db.queryForList("SELECT * FROM goods WHERE id=?",line.getGoods());if(products.size()!=1)throw new IllegalArgumentException("商品已不存在");
            Map<String,Object> product=products.get(0);WarehouseScope.require(db,dto.getFrame(),line.getWarehouse());
            String unit=text(product.get("unit"));if("-1".equals(unit)){JSONArray units=new JSONArray(text(product.get("units")));if(units.isEmpty())throw new IllegalArgumentException("商品缺少基础单位");unit=units.getJSONObject(0).getStr("source");}
            if(!unit.equals(line.getUnit()))throw new IllegalArgumentException("其他出库必须使用商品基本单位，请核对数量");
            line.setAttr(line.getAttr()==null?"":line.getAttr());
            if(!line.getAttr().isEmpty() && count("SELECT COUNT(*) FROM attr WHERE pid=? AND name=?",line.getGoods(),line.getAttr())!=1)throw new IllegalArgumentException("所选辅助属性不属于商品");
            line.setNums(amount(line.getNums(),true));line.setPrice(amount(line.getPrice(),false));line.setTotal(amount(line.getNums().multiply(line.getPrice()).setScale(4,RoundingMode.HALF_UP),false));total=total.add(line.getTotal());
            boolean batch=Boolean.TRUE.equals(product.get("batch")) || "1".equals(text(product.get("batch"))),serial=Boolean.TRUE.equals(product.get("serial")) || "1".equals(text(product.get("serial")));
            if(batch && (line.getBatch()==null || line.getBatch().trim().isEmpty() || line.getMfd()==null))throw new IllegalArgumentException("批次商品必须填写批次号和生产日期");
            if(!batch && (!text(line.getBatch()).isEmpty() || line.getMfd()!=null))throw new IllegalArgumentException("普通商品不能填写批次或生产日期");
            JSONArray numbers;try{numbers=new JSONArray(text(line.getSerial()).isEmpty()?"[]":line.getSerial());}catch(Exception e){throw new IllegalArgumentException("序列号必须为JSON数组");}
            if((serial && line.getNums().compareTo(BigDecimal.valueOf(numbers.size()))!=0) || (!serial && !numbers.isEmpty()))throw new IllegalArgumentException("序列号数量必须与商品数量一致");
            for(Object raw:numbers){if(!(raw instanceof String) || text(raw).trim().isEmpty() || !serialNumbers.add(line.getGoods()+"/"+text(raw)))throw new IllegalArgumentException("序列号为空或重复");}
            line.setSerial(numbers.toString());
        }
        dto.setTotal(amount(total,false));BigDecimal feeTotal=BigDecimal.ZERO;
        if(dto.getCostDTOList()==null)dto.setCostDTOList(Collections.emptyList());
        for(CostDTO fee:dto.getCostDTOList()){
            if(fee==null || fee.getIet()==null || count("SELECT COUNT(*) FROM iet WHERE id=?",fee.getIet())!=1)throw new IllegalArgumentException("请选择有效费用类别");
            fee.setMoney(amount(fee.getMoney(),false));feeTotal=feeTotal.add(fee.getMoney());
        }
        if(amount(dto.getCost(),false).compareTo(amount(feeTotal,false))!=0)throw new IllegalArgumentException("费用合计与明细不一致");
        if(dto.getCse()==null || dto.getCse()!=(feeTotal.signum()==0?3:0))throw new IllegalArgumentException("草稿费用状态与费用金额不一致");
        dto.setUser(actor.getId());
    }
    private void persist(String id,OtherOutListDTO dto){
        for(OtherOutListInfoDTO line:dto.getOtherOutListInfoDTOList())db.update("INSERT INTO extry_info(id,pid,goods,attr,unit,warehouse,batch,mfd,price,nums,serial,total,data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",line.getId(),id,line.getGoods(),line.getAttr(),line.getUnit(),line.getWarehouse(),line.getBatch(),line.getMfd()==null?null:Timestamp.valueOf(line.getMfd()),line.getPrice(),line.getNums(),line.getSerial(),line.getTotal(),line.getData());
        for(CostDTO fee:dto.getCostDTOList())db.update("INSERT INTO cost(id,type,`class`,time,iet,money,data,settle,state) VALUES(?,'extry',?,?,?,?,?,0,0)",uid(),id,Timestamp.valueOf(dto.getTime()),fee.getIet(),fee.getMoney(),fee.getData());
    }
    @Transactional(readOnly=true)
    public Map<String,Object> options(String id){
        UserDTO actor=access.authorize("extry",id==null || id.isEmpty()?"create":"save");String frame=actor.getFrameId();
        if(id!=null && !id.isEmpty()){Map<String,Object> original=head(id,false);scope(actor,original);frame=text(original.get("frame"));}
        Map<String,Object> result=new LinkedHashMap<>();result.put("warehouses",db.queryForList("SELECT id,name,number FROM warehouse WHERE frame IN ('0',?) ORDER BY name,id",frame));
        result.put("customers",db.queryForList("SELECT id,name,number FROM customer WHERE frame IN ('0',?) ORDER BY name,id",frame));return result;
    }
    public String requireImportWorkflow(){
        access.authorize("extry","import");
        throw new IllegalArgumentException("旧导入模板只包含主表，不能生成有效出库单。请先在其他出库工作台选择商品并保存完整草稿；完整预览确认导入流程尚待验收。");
    }
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> list(OtherOutQuery query){
        UserDTO actor=access.authorize("extry","read");String frame=access.frame(actor);
        if(frame==null && query.getFrame()!=null && !query.getFrame().trim().isEmpty())frame=query.getFrame().trim();
        StringBuilder where=new StringBuilder(" WHERE 1=1");List<Object> args=new ArrayList<>();
        if(frame!=null){where.append(" AND e.frame=?");args.add(frame);}
        for(String[] filter:new String[][]{{"e.number",query.getNumber()},{"e.data",query.getData()}})if(filter[1]!=null && !filter[1].trim().isEmpty()){where.append(" AND "+filter[0]+" LIKE ?");args.add("%"+filter[1].trim()+"%");}
        if(query.getCustomer()!=null && !query.getCustomer().isEmpty()){where.append(" AND (e.customer=? OR c.name LIKE ?)");args.add(query.getCustomer());args.add("%"+query.getCustomer()+"%");}
        if(query.getName()!=null && !query.getName().isEmpty()){where.append(" AND EXISTS(SELECT 1 FROM extry_info i JOIN goods g ON g.id=i.goods WHERE i.pid=e.id AND (g.name LIKE ? OR g.number LIKE ?))");args.add("%"+query.getName()+"%");args.add("%"+query.getName()+"%");}
        if(query.getStartTime()!=null && !query.getStartTime().isEmpty()){where.append(" AND e.time>=?");args.add(Timestamp.valueOf(LocalDate.parse(query.getStartTime()).atStartOfDay()));}
        if(query.getEndTime()!=null && !query.getEndTime().isEmpty()){where.append(" AND e.time<?");args.add(Timestamp.valueOf(LocalDate.parse(query.getEndTime()).plusDays(1).atStartOfDay()));}
        String[] keys={"examine","check","cse","type"};Integer[] values={query.getExamine(),query.getCheck(),query.getCse(),query.getType()};
        for(int index=0;index<keys.length;index++)if(values[index]!=null && values[index]!=-1){if(values[index]<0 || values[index]>(index==2?3:1))throw new IllegalArgumentException("查询状态无效");where.append(" AND e.`"+keys[index]+"`=?");args.add(values[index]);}
        String joins=" FROM extry e LEFT JOIN customer c ON c.id=e.customer LEFT JOIN frame f ON f.id=e.frame LEFT JOIN `user` u ON u.id=e.`user`";
        long page=Math.max(1,query.getPageIndex()),size=query.getPageSize()<=0?20:Math.min(200,query.getPageSize());long total=db.queryForObject("SELECT COUNT(*)"+joins+where,Long.class,args.toArray());
        List<Object> paged=new ArrayList<>(args);paged.add(size);paged.add((page-1)*size);
        List<Map<String,Object>> rows=db.queryForList("SELECT e.*,CAST(e.type AS SIGNED) AS type,CAST(e.examine AS SIGNED) AS examine,CAST(e.`check` AS SIGNED) AS `check`,CAST(e.cse AS SIGNED) AS cse,c.name AS customerName,f.name AS frameName,u.name AS userName"+joins+where+" ORDER BY e.time DESC,e.id LIMIT ? OFFSET ?",paged.toArray());
        for(Map<String,Object> row:rows){Map<String,Object> doc=reports.detail("extry",text(row.get("id")));row.put("version",doc.get("version"));Map<String,Object> posted=(Map<String,Object>)doc.get("header");if(posted.containsKey("actualCost"))row.put("actualCost",posted.get("actualCost"));if(posted.containsKey("costStatus"))row.put("costStatus",posted.get("costStatus"));}
        Map<String,Object> result=new LinkedHashMap<>();result.put("rows",rows);result.put("total",total);result.put("pageIndex",page);result.put("pageSize",size);return result;
    }
}
