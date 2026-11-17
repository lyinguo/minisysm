package com.zeroone.star.storemanagement.service;

import static com.zeroone.star.storemanagement.service.MovementDrafts.*;
import cn.hutool.json.JSONArray;
import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.util.DigestUtils;
import java.math.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Persisted partial counts. Unlisted dimensions are never reset to zero. */
@Service
public class InventoryCountDocumentService {
    private final JdbcTemplate db;private final StockDocumentAccess access;private final MovementDrafts drafts;private final StockDocumentWriteLock writes;private final WarehouseReportDocumentService reports;private final WarehousePostingProof proofs;
    public InventoryCountDocumentService(JdbcTemplate db,StockDocumentAccess access,MovementDrafts drafts,StockDocumentWriteLock writes,WarehouseReportDocumentService reports){this.db=db;this.access=access;this.drafts=drafts;this.writes=writes;this.reports=reports;this.proofs=new WarehousePostingProof(db);}
    @javax.annotation.PostConstruct public void schema(){
        db.execute("CREATE TABLE IF NOT EXISTS psi_inventory_count(id VARCHAR(32) PRIMARY KEY,frame VARCHAR(32) NOT NULL,number VARCHAR(32) NOT NULL UNIQUE,time DATETIME NOT NULL,data TEXT,creator VARCHAR(32) NOT NULL,state INT NOT NULL DEFAULT 0,revision BIGINT NOT NULL DEFAULT 1) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        db.execute("CREATE TABLE IF NOT EXISTS psi_inventory_count_line(id VARCHAR(32) PRIMARY KEY,pid VARCHAR(32) NOT NULL,goods VARCHAR(32) NOT NULL,warehouse VARCHAR(32) NOT NULL,attr VARCHAR(255),unit VARCHAR(32),batch VARCHAR(64),mfd DATE,price DECIMAL(12,4) NOT NULL,counted DECIMAL(12,4) NOT NULL,book_qty DECIMAL(12,4) NOT NULL,serial TEXT,book_serial TEXT,snapshot CHAR(32) NOT NULL,data TEXT,INDEX(pid)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        db.execute("CREATE TABLE IF NOT EXISTS psi_inventory_adjustment(count_id VARCHAR(32) NOT NULL,kind VARCHAR(8) NOT NULL,document_id VARCHAR(32) NOT NULL UNIQUE,PRIMARY KEY(count_id,kind)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    }
    private Map<String,Object> head(String id,UserDTO actor,boolean lock){List<Map<String,Object>> rows=db.queryForList("SELECT * FROM psi_inventory_count WHERE id=?"+(lock?" FOR UPDATE":""),id);if(rows.size()!=1)throw new IllegalArgumentException("盘点单不存在");Map<String,Object> row=rows.get(0);String frame=access.frame(actor);if(frame!=null && !frame.equals(str(row.get("frame"))))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"不能操作其他组织的盘点单");return row;}
    private List<Map<String,Object>> rows(String id){return db.queryForList("SELECT * FROM psi_inventory_count_line WHERE pid=? ORDER BY id",id);}
    private String version(Map<String,Object> h,List<Map<String,Object>> r){return hash(h.toString()+r.toString());}
    private String hash(String s){return DigestUtils.md5DigestAsHex(s.getBytes(StandardCharsets.UTF_8));}
    private void expect(Map<String,Object> h,List<Map<String,Object>> r,Object v){if(!version(h,r).equals(v))throw new IllegalStateException("盘点单已变化，请重新打开");}
    private Map<String,Object> read(String id,UserDTO actor){Map<String,Object> h=head(id,actor,false);List<Map<String,Object>> r=rows(id);Map<String,Object> d=new LinkedHashMap<>();for(Map<String,Object> row:r)row.put("difference",new BigDecimal(str(row.get("counted"))).subtract(new BigDecimal(str(row.get("book_qty")))));d.put("header",h);d.put("items",r);d.put("version",version(h,rows(id)));d.put("adjustments",db.queryForList("SELECT * FROM psi_inventory_adjustment WHERE count_id=? ORDER BY kind",id));d.put("goods",db.queryForList("SELECT * FROM goods WHERE id IN (SELECT goods FROM psi_inventory_count_line WHERE pid=?)",id));return d;}
    @Transactional(readOnly=true) public Map<String,Object> detail(String id){return read(id,access.authorize("count","read"));}
    @Transactional(readOnly=true) public Map<String,Object> list(int page,int size,String number){UserDTO a=access.authorize("count","read");String frame=access.frame(a);Map<String,Object> d=new LinkedHashMap<>();int limit=Math.max(1,Math.min(200,size));d.put("rows",db.queryForList("SELECT * FROM psi_inventory_count WHERE number LIKE ? AND (? IS NULL OR frame=?) ORDER BY time DESC,id LIMIT ? OFFSET ?","%"+number+"%",frame,frame,limit,(long)(Math.max(1,page)-1)*limit));d.put("total",db.queryForObject("SELECT COUNT(*) FROM psi_inventory_count WHERE number LIKE ? AND (? IS NULL OR frame=?)",Integer.class,"%"+number+"%",frame,frame));return d;}
    @Transactional(readOnly=true) public Map<String,Object> options(){UserDTO a=access.authorize("count","read");Map<String,Object> d=new LinkedHashMap<>();d.put("warehouses",db.queryForList("SELECT id,name,number FROM warehouse WHERE frame IN ('0',?) ORDER BY name,id",a.getFrameId()));return d;}
    private void lockGoods(List<Map<String,Object>> rows){TreeSet<String> ids=new TreeSet<>();for(Map<String,Object> r:rows)ids.add(str(r.get("goods")));for(String id:ids)if(db.queryForList("SELECT id FROM goods WHERE id=? FOR UPDATE",id).size()!=1)throw new IllegalArgumentException("盘点商品不存在");}
    private Map<String,Object> snapshot(Map<String,Object> row){
        String g=str(row.get("goods")),w=str(row.get("warehouse")),a=str(row.get("attr")),b=str(row.get("batch"));
        List<Map<String,Object>> rooms=db.queryForList("SELECT * FROM room WHERE goods=? AND warehouse=? AND COALESCE(attr,'')=? FOR UPDATE",g,w,a);if(rooms.size()>1)throw new IllegalStateException("库存记录重复，请先核对");
        List<Map<String,Object>> batches=b.isEmpty()?Collections.emptyList():db.queryForList("SELECT b.* FROM batch b JOIN room r ON r.id=b.room WHERE r.goods=? AND r.warehouse=? AND COALESCE(r.attr,'')=? AND b.number=? FOR UPDATE",g,w,a,b);if(batches.size()>1)throw new IllegalStateException("批次记录重复");
        if(!batches.isEmpty() && !str(batches.get(0).get("time")).substring(0,10).equals(str(row.get("mfd")).substring(0,10)))throw new IllegalArgumentException("生产日期与库存批次不一致");
        BigDecimal qty=new BigDecimal(str((b.isEmpty()?rooms:batches).isEmpty()?0:(b.isEmpty()?rooms:batches).get(0).get("nums")));
        List<String> serials=db.queryForList("SELECT s.number FROM serial s JOIN room r ON r.id=s.room LEFT JOIN batch b ON b.id=s.batch WHERE s.goods=? AND s.warehouse=? AND COALESCE(r.attr,'')=? AND s.state=0 AND (?='' OR b.number=?) ORDER BY s.number FOR UPDATE",String.class,g,w,a,b,b);
        List<Map<String,Object>> ledger=db.queryForList("SELECT id,direction,nums,bct FROM summary WHERE goods=? AND warehouse=? AND COALESCE(attr,'')=? AND (?='' OR COALESCE(batch,'')=?) ORDER BY id FOR UPDATE",g,w,a,b,b);
        List<Map<String,Object>> product=db.queryForList("SELECT type,batch,serial,unit,units FROM goods WHERE id=? FOR UPDATE",g);
        Map<String,Object> result=new LinkedHashMap<>();result.put("qty",qty);result.put("serial",new JSONArray(serials).toString());result.put("hash",hash(rooms.toString()+batches+serials+ledger+product));return result;
    }
    @Transactional(rollbackFor=Exception.class) public String save(Map<String,Object> body){
        UserDTO actor=access.authorize("count","save");writes.lock("inventory-count");String id=str(body.get("id"));boolean create=id.isEmpty();Map<String,Object> old=null;List<Map<String,Object>> previous=Collections.emptyList();String frame;
        if(create){id=uid();frame=access.creationFrame(actor,str(body.get("frame")));}else{old=head(id,actor,true);previous=rows(id);expect(old,previous,body.get("version"));if(integer(old.get("state"))!=0)throw new IllegalStateException("已审核盘点不能修改");proofs.requireOpenPeriod(old.get("time"));frame=str(old.get("frame"));}
        if(body.containsKey("state") && integer(body.get("state"))!=0)throw new IllegalArgumentException("请先保存盘点草稿");String no=number(body.get("number"));java.sql.Timestamp time=time(body.get("time"));proofs.requireOpenPeriod(time);
        if(db.queryForObject("SELECT COUNT(*) FROM psi_inventory_count WHERE number=? AND id<>?",Integer.class,no,id)>0)throw new IllegalArgumentException("盘点单号已存在");
        List<Map<String,Object>> lines=drafts.lines(body.get("items"),frame,false,true);lockGoods(lines);lines=drafts.lines(body.get("items"),frame,false,true);Map<String,Map<String,Object>> originals=new HashMap<>();for(Map<String,Object> row:previous)originals.put(str(row.get("id")),row);Set<String> used=new HashSet<>();
        for(Map<String,Object> row:lines){String line=str(row.get("id"));Map<String,Object> original=originals.get(line);if(!line.isEmpty() && (original==null || !used.add(line)))throw new IllegalArgumentException("盘点明细重复或不属于本单");Map<String,Object> s=snapshot(row);
            if(original!=null){for(String field:Arrays.asList("goods","warehouse","attr","unit","batch","mfd"))if(!str(original.get(field)).equals(str(row.get(field))))throw new IllegalArgumentException("已保存盘点维度不能改变，请删除该行后重新添加并重新盘点");if(!str(original.get("snapshot")).equals(s.get("hash")))throw new IllegalStateException("盘点后库存已变化，请重新建立盘点快照");}
            row.put("id",line.isEmpty()?uid():line);row.put("book_qty",s.get("qty"));row.put("book_serial",s.get("serial"));row.put("snapshot",s.get("hash"));
            if(integer(row.get("serialEnabled"))==1 && new BigDecimal(str(s.get("qty"))).compareTo(BigDecimal.valueOf(new JSONArray(str(s.get("serial"))).size()))!=0)throw new IllegalStateException("账面数量与在库序列号数量不一致，请先核对历史库存");
        }
        if(create)db.update("INSERT INTO psi_inventory_count(id,frame,number,time,data,creator) VALUES(?,?,?,?,?,?)",id,frame,no,time,body.get("data"),actor.getId());else{db.update("UPDATE psi_inventory_count SET number=?,time=?,data=?,revision=revision+1 WHERE id=?",no,time,body.get("data"),id);db.update("DELETE FROM psi_inventory_count_line WHERE pid=?",id);}
        for(Map<String,Object> r:lines)db.update("INSERT INTO psi_inventory_count_line(id,pid,goods,warehouse,attr,unit,batch,mfd,price,counted,book_qty,serial,book_serial,snapshot,data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",r.get("id"),id,r.get("goods"),r.get("warehouse"),r.get("attr"),r.get("unit"),r.get("batch"),r.get("mfd"),r.get("price"),r.get("nums"),r.get("book_qty"),r.get("serial"),r.get("book_serial"),r.get("snapshot"),r.get("data"));
        drafts.history("inventoryCount",id,actor,create?"新增盘点快照草稿":"修改盘点实盘数量");return id;
    }
    private List<Map<String,Object>> differences(List<Map<String,Object>> rows,boolean plus){List<Map<String,Object>> result=new ArrayList<>();for(Map<String,Object> source:rows){Map<String,Object> r=new LinkedHashMap<>(source);boolean serial=integer(db.queryForObject("SELECT CAST(serial AS SIGNED) FROM goods WHERE id=?",Integer.class,r.get("goods")))==1;BigDecimal delta;
        if(serial){Set<String> book=new TreeSet<>(),actual=new TreeSet<>();for(Object s:new JSONArray(str(r.get("book_serial"))))book.add(str(s));for(Object s:new JSONArray(str(r.get("serial"))))actual.add(str(s));Set<String> changed=new TreeSet<>(plus?actual:book);changed.removeAll(plus?book:actual);delta=BigDecimal.valueOf(changed.size());r.put("serial",new JSONArray(changed).toString());}
        else{delta=new BigDecimal(str(r.get("counted"))).subtract(new BigDecimal(str(r.get("book_qty"))));if(!plus)delta=delta.negate();}
        if(delta.signum()>0){r.put("id",uid());r.put("nums",delta);r.put("total",delta.multiply(new BigDecimal(str(r.get("price")))).setScale(4,RoundingMode.HALF_UP));result.add(r);}}
        return result;}
    private void adjustment(String count,Map<String,Object> h,List<Map<String,Object>> rows,boolean plus,UserDTO actor){
        List<Map<String,Object>> changed=differences(rows,plus);if(changed.isEmpty())return;String kind=plus?"entry":"extry",id=uid();BigDecimal total=BigDecimal.ZERO;for(Map<String,Object> r:changed)total=total.add((BigDecimal)r.get("total"));decimal(total,false);
        if(!db.queryForList("SELECT id FROM "+kind+" WHERE number=? FOR UPDATE",(plus?"PY":"PK")+id.substring(0,30)).isEmpty())throw new IllegalStateException("差异单号冲突，请重试");
        db.update("INSERT INTO "+kind+"(id,"+(plus?"supplier":"customer")+",frame,time,number,type,total,cost,examine,cse,`check`,`user`,data) VALUES(?,'',?,?,?,1,?,0,0,3,0,?,?)",id,h.get("frame"),h.get("time"),(plus?"PY":"PK")+id.substring(0,30),total,actor.getId(),"盘点差异："+h.get("number"));for(Map<String,Object> r:changed)drafts.insert(kind,id,r);
        db.update("INSERT INTO psi_inventory_adjustment(count_id,kind,document_id) VALUES(?,?,?)",count,kind,id);drafts.history(kind,id,actor,"盘点生成差异草稿");reports.audit(kind,id,1,reports.lockedVersion(kind,id),actor.getId());
    }
    @Transactional(rollbackFor=Exception.class) public void command(String id,Map<String,Object> body,boolean remove){
        UserDTO actor=access.authorize("count",remove?"delete":"audit");writes.lock("inventory-count");Map<String,Object> h=head(id,actor,true);List<Map<String,Object>> rows=rows(id);expect(h,rows,body.get("version"));proofs.requireOpenPeriod(h.get("time"));
        if(remove){if(integer(h.get("state"))!=0 || !db.queryForList("SELECT * FROM psi_inventory_adjustment WHERE count_id=?",id).isEmpty())throw new IllegalStateException("请先反审核盘点单");db.update("DELETE FROM psi_inventory_count_line WHERE pid=?",id);db.update("DELETE FROM psi_inventory_count WHERE id=?",id);drafts.history("inventoryCount",id,actor,"删除盘点草稿");return;}
        if(!(body.get("target") instanceof Integer) || !Arrays.asList(0,1).contains(body.get("target")))throw new IllegalArgumentException("审核状态须明确为0或1");int target=(Integer)body.get("target");if(integer(h.get("state"))==target)return;
        writes.lock("entry");writes.lock("extry");lockGoods(rows);CountAdjustmentGuard.within(id,()->{
            if(target==1){for(Map<String,Object> row:rows)if(!str(row.get("snapshot")).equals(snapshot(row).get("hash")))throw new IllegalStateException("盘点后库存已变化，请重新盘点，不能用旧数量覆盖新库存");adjustment(id,h,rows,false,actor);adjustment(id,h,rows,true,actor);}
            else{List<Map<String,Object>> links=db.queryForList("SELECT * FROM psi_inventory_adjustment WHERE count_id=? ORDER BY kind",id);for(Map<String,Object> link:links){String kind=str(link.get("kind")),doc=str(link.get("document_id"));reports.audit(kind,doc,0,reports.lockedVersion(kind,doc),actor.getId());db.update("DELETE FROM "+kind+"_info WHERE pid=?",doc);db.update("DELETE FROM "+kind+" WHERE id=?",doc);drafts.history(kind,doc,actor,"反审核盘点并撤销差异单");}db.update("DELETE FROM psi_inventory_adjustment WHERE count_id=?",id);
                for(Map<String,Object> row:rows){Map<String,Object> s=snapshot(row);if(new BigDecimal(str(s.get("qty"))).compareTo(new BigDecimal(str(row.get("book_qty"))))!=0 || !str(s.get("serial")).equals(str(row.get("book_serial"))))throw new IllegalStateException("撤销后账面与原快照不一致，请先撤销后续库存操作");db.update("UPDATE psi_inventory_count_line SET snapshot=? WHERE id=?",s.get("hash"),row.get("id"));}}
            db.update("UPDATE psi_inventory_count SET state=?,revision=revision+1 WHERE id=?",target,id);drafts.history("inventoryCount",id,actor,target==1?"审核盘点并入账差异":"反审核盘点并回滚差异");return null;});
    }
}
