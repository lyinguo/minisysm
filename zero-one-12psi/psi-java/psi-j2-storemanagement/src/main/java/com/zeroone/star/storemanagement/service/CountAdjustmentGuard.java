package com.zeroone.star.storemanagement.service;

import org.springframework.jdbc.core.JdbcTemplate;
import java.util.function.Supplier;
import java.util.*;

/** Adjustment documents can only change with their owning count, in one transaction. */
public final class CountAdjustmentGuard {
    private static final ThreadLocal<String> owner=new ThreadLocal<>();
    private CountAdjustmentGuard(){}
    public static <T> T within(String id,Supplier<T> operation){String previous=owner.get();owner.set(id);try{return operation.get();}finally{if(previous==null)owner.remove();else owner.set(previous);}}
    public static List<String> reversingTogether(JdbcTemplate db,String document){
        if(owner.get()==null)return Collections.singletonList(document);
        List<String> ids=db.queryForList("SELECT document_id FROM psi_inventory_adjustment WHERE count_id=? ORDER BY document_id",String.class,owner.get());
        if(!ids.contains(document))throw new IllegalStateException("差异单不属于当前盘点");return ids;
    }
    public static void require(JdbcTemplate db,String kind,String id){
        if(db.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE LOWER(table_name)='psi_inventory_adjustment' AND LOWER(table_schema)=LOWER(DATABASE())",Integer.class)==0)return;
        for(String count:db.queryForList("SELECT count_id FROM psi_inventory_adjustment WHERE kind=? AND document_id=?",String.class,kind,id))if(!count.equals(owner.get()))throw new IllegalStateException("此单据由盘点生成，请在原盘点单统一审核、反审核或修改");
    }
}
