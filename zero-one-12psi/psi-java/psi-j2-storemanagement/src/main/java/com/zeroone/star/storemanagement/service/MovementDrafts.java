package com.zeroone.star.storemanagement.service;

import cn.hutool.json.JSONArray;
import com.zeroone.star.project.components.user.UserDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.math.*;
import java.sql.Timestamp;
import java.time.*;
import java.util.*;

/** Shared validation for physical warehouse drafts, never creates product master data. */
@Service
public class MovementDrafts {
    final JdbcTemplate db;
    public MovementDrafts(JdbcTemplate db){this.db=db;}
    public static String str(Object v){return v==null?"":v.toString();}
    public static String uid(){return UUID.randomUUID().toString().replace("-","");}
    public static int integer(Object v){return Boolean.TRUE.equals(v)?1:Boolean.FALSE.equals(v)?0:Integer.parseInt(str(v));}
    public static BigDecimal decimal(Object v,boolean positive){
        try{BigDecimal n=new BigDecimal(str(v)).setScale(4,RoundingMode.UNNECESSARY);
            if(n.precision()>12 || (positive?n.signum()<=0:n.signum()<0))throw new ArithmeticException();return n;
        }catch(Exception e){throw new IllegalArgumentException(positive?"数量必须大于零，最多4位小数":"数量或成本必须非负，最多4位小数");}
    }
    public static Timestamp time(Object value){
        try{return value instanceof Number?new Timestamp(((Number)value).longValue()):Timestamp.valueOf(LocalDateTime.parse(str(value).replace(' ','T')));}
        catch(Exception e){throw new IllegalArgumentException("请填写有效的单据日期及时间");}
    }
    public static String number(Object value){String n=str(value).trim();if(n.isEmpty() || n.codePointCount(0,n.length())>32)throw new IllegalArgumentException("单号须为1到32个字符");return n;}
    public List<Map<String,Object>> lines(Object raw,String frame,boolean transfer,boolean counted){
        if(!(raw instanceof List) || ((List<?>)raw).isEmpty() || ((List<?>)raw).size()>200)throw new IllegalArgumentException("请添加1到200行商品");
        List<Map<String,Object>> result=new ArrayList<>();Set<String> serials=new HashSet<>(),dimensions=new HashSet<>();
        for(Object value:(List<?>)raw){
            if(!(value instanceof Map))throw new IllegalArgumentException("商品明细无效");Map<String,Object> row=new LinkedHashMap<>((Map<String,Object>)value);
            List<Map<String,Object>> products=db.queryForList("SELECT * FROM goods WHERE id=?",str(row.get("goods")));
            if(products.size()!=1 || integer(products.get(0).get("type"))!=0)throw new IllegalArgumentException("请选择真实库存商品，服务商品不能调拨或盘点");
            Map<String,Object> p=products.get(0);String goods=str(p.get("id")),warehouse=str(row.get("warehouse")),attr=str(row.get("attr"));WarehouseScope.require(db,frame,warehouse);
            if(!attr.isEmpty() && db.queryForObject("SELECT COUNT(*) FROM attr WHERE pid=? AND name=?",Integer.class,goods,attr)!=1)throw new IllegalArgumentException("辅助属性不属于所选商品");
            String unit=str(p.get("unit"));if("-1".equals(unit)){JSONArray u=new JSONArray(str(p.get("units")));if(u.isEmpty())throw new IllegalArgumentException("商品缺少基本单位");unit=u.getJSONObject(0).getStr("source");}
            if(!unit.equals(str(row.get("unit"))))throw new IllegalArgumentException("请使用商品基本单位");
            if(transfer){String target=str(row.get("storehouse"));WarehouseScope.require(db,frame,target);if(target.equals(warehouse))throw new IllegalArgumentException("调出和调入仓库不能相同");}
            String batch=str(row.get("batch"));Object mfd=null;
            if(integer(p.get("batch"))==1){if(batch.trim().isEmpty() || batch.length()>64)throw new IllegalArgumentException("请填写有效批次号");try{mfd=java.sql.Date.valueOf(str(row.get("mfd")).substring(0,10));}catch(Exception e){throw new IllegalArgumentException("请填写生产日期");}}
            else if(!batch.isEmpty() || row.get("mfd")!=null)throw new IllegalArgumentException("普通商品不能填写批次日期");
            JSONArray sn;try{sn=new JSONArray(str(row.get("serial")).isEmpty()?"[]":str(row.get("serial")));}catch(Exception e){throw new IllegalArgumentException("序列号须为JSON数组");}
            BigDecimal qty=decimal(row.get(counted?"counted":"nums"),!counted),price=decimal(row.get("price"),false);
            if(integer(p.get("serial"))==1 && qty.compareTo(BigDecimal.valueOf(sn.size()))!=0 || integer(p.get("serial"))!=1 && !sn.isEmpty())throw new IllegalArgumentException("序列号数量与实物数量不一致");
            for(Object s:sn)if(!(s instanceof String) || str(s).trim().isEmpty() || !serials.add(goods+"/"+s))throw new IllegalArgumentException("序列号不能为空或重复");
            if(counted && !dimensions.add(goods+"/"+warehouse+"/"+attr+"/"+batch))throw new IllegalArgumentException("同一商品、仓库、属性、批次只能盘点一次");
            row.put("goods",goods);row.put("warehouse",warehouse);row.put("attr",attr);row.put("unit",unit);row.put("batch",batch);row.put("mfd",mfd);row.put("serial",sn.toString());row.put("nums",qty);row.put("price",price);row.put("total",decimal(qty.multiply(price).setScale(4,RoundingMode.HALF_UP),false));row.put("serialEnabled",integer(p.get("serial")));row.put("batchEnabled",integer(p.get("batch")));result.add(row);
        }return result;
    }
    public void insert(String kind,String id,Map<String,Object> row){
        String columns="id,pid,goods,attr,unit,warehouse,batch,mfd,price,nums,serial,total,data";List<Object> args=new ArrayList<>(Arrays.asList(row.get("id"),id,row.get("goods"),row.get("attr"),row.get("unit"),row.get("warehouse"),row.get("batch"),row.get("mfd"),row.get("price"),row.get("nums"),row.get("serial"),row.get("total"),row.get("data")));
        if("swap".equals(kind)){columns+=",storehouse";args.add(row.get("storehouse"));}
        db.update("INSERT INTO "+kind+"_info("+columns+") VALUES("+String.join(",",Collections.nCopies(args.size(),"?"))+")",args.toArray());
    }
    public void history(String kind,String id,UserDTO actor,String message){Timestamp now=Timestamp.valueOf(LocalDateTime.now());db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,?,?,?,?,?)",uid(),kind,id,now,actor.getId(),message);db.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)",uid(),now,actor.getId(),message+"["+id+"]");}
}
