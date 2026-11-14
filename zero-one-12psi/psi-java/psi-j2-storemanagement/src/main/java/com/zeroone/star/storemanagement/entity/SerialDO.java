package com.zeroone.star.storemanagement.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

/**
 * 序列号
 */
@Data
@TableName("serial")
public class SerialDO {
    @TableId("id")
    private String id;

    @TableField("room")
    private String room;

    @TableField("warehouse")
    private String warehouse;

    @TableField("batch")
    private String batch;

    @TableField("goods")
    private String goods;

    @TableField("number")
    private String number;

    /** 0未销售 1已销售 2已调拨 3已退货 */
    @TableField("state")
    private Integer state;
}
