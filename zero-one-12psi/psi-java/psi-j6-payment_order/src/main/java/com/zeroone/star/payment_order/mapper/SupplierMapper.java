package com.zeroone.star.payment_order.mapper;

import com.zeroone.star.payment_order.entity.Supplier;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.math.BigDecimal;

/**
 * <p>
 * 供应商 Mapper 接口
 * </p>
 *
 * @author 温白开
 * @since 2025-10-28
 */
@Mapper
public interface SupplierMapper extends BaseMapper<Supplier> {
        //减少应付款（兼容 id / 编号 / 名称）
        @Update("UPDATE supplier SET balance = balance - #{money} WHERE id = #{supplier} OR number = #{supplier} OR name = #{supplier}")
        int updatePayable(@Param("supplier") String supplierId, @Param("money") BigDecimal money);

        //恢复应付款（兼容 id / 编号 / 名称）
        @Update("UPDATE supplier SET balance = balance + #{money} WHERE id = #{supplier} OR number = #{supplier} OR name = #{supplier}")
        int updatePayableAdd(@Param("supplier") String supplierId, @Param("money") BigDecimal money);

}