package com.zeroone.star.storemanagement.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.storemanagement.entity.SerialDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.Map;

@Mapper
public interface SerialMapper extends BaseMapper<SerialDO> {

    Page<Map<String, Object>> selectSerialPage(
            Page<Map<String, Object>> page,
            @Param("serialNumber") String serialNumber,
            @Param("goodsName") String goodsName,
            @Param("goodsNumber") String goodsNumber,
            @Param("warehouseId") String warehouseId,
            @Param("state") Integer state
    );
}
