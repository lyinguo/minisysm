package com.zeroone.star.storemanagement.service;

import org.springframework.jdbc.core.JdbcTemplate;
import java.util.List;
import java.util.Objects;

/** A document may use a shared warehouse or a warehouse owned by its organization. */
public final class WarehouseScope {
    private WarehouseScope() { }
    public static String require(JdbcTemplate db,String documentFrame,Object value) {
        String id=value==null?"":value.toString();
        List<String> frames=db.queryForList("SELECT frame FROM warehouse WHERE id=?",String.class,id);
        if(id.isEmpty() || frames.size()!=1)throw new IllegalArgumentException("请选择有效仓库");
        if(!"0".equals(frames.get(0)) && !Objects.equals(frames.get(0),documentFrame))
            throw new IllegalArgumentException("仓库不属于单据组织，请重新选择仓库");
        return id;
    }
}
