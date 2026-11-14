#pragma once
#ifndef _SOR_INFO_H_
#define _SOR_INFO_H_

#include "BaseDO.h"
#include <memory>
#include <string>

using namespace std;

class SorInfo : public BaseDO
{
    // 唯一标识
    MYSQL_SYNTHESIZE(string, id, Id);
    // 所属ID
    MYSQL_SYNTHESIZE(string, pid, Pid);
    // 所属商品
    MYSQL_SYNTHESIZE(string, goods, Goods);
    // 辅助属性
    MYSQL_SYNTHESIZE(string, attr, Attr);
    // 单位
    MYSQL_SYNTHESIZE(string, unit, Unit);
    // 仓库
    MYSQL_SYNTHESIZE(string, warehouse, Warehouse);
    // 单价
    MYSQL_SYNTHESIZE(string, price, Price);
    // 数量
    MYSQL_SYNTHESIZE(string, nums, Nums);
    // 折扣率
    MYSQL_SYNTHESIZE(string, discount, Discount);
    // 折扣额
    MYSQL_SYNTHESIZE(string, dsc, Dsc);
    // 金额
    MYSQL_SYNTHESIZE(string, total, Total);
    // 税率
    MYSQL_SYNTHESIZE(string, tax, Tax);
    // 税额
    MYSQL_SYNTHESIZE(string, tat, Tat);
    // 价税合计
    MYSQL_SYNTHESIZE(string, tpt, Tpt);
    // 备注信息
    MYSQL_SYNTHESIZE(string, data, Data);
    // 出库数量
    MYSQL_SYNTHESIZE(string, handle, Handle);

public:
    SorInfo() : BaseDO("sor_info")
    {
        MYSQL_ADD_FIELD_PK("id", "s", id);
        MYSQL_ADD_FIELD("pid", "s", pid);
        MYSQL_ADD_FIELD("goods", "s", goods);
        MYSQL_ADD_FIELD_NULLABLE("attr", "s", attr, false);
        MYSQL_ADD_FIELD("unit", "s", unit);
        MYSQL_ADD_FIELD_NULLABLE("warehouse", "s", warehouse, false);
        MYSQL_ADD_FIELD("price", "s", price);
        MYSQL_ADD_FIELD("nums", "s", nums);
        MYSQL_ADD_FIELD("discount", "s", discount);
        MYSQL_ADD_FIELD("dsc", "s", dsc);
        MYSQL_ADD_FIELD("total", "s", total);
        MYSQL_ADD_FIELD("tax", "s", tax);
        MYSQL_ADD_FIELD("tat", "s", tat);
        MYSQL_ADD_FIELD("tpt", "s", tpt);
        MYSQL_ADD_FIELD_NULLABLE("data", "s", data, false);
        MYSQL_ADD_FIELD_NULLABLE("handle", "s", handle, false);
    }
};

// 定义一个智能指针别名方便使用
typedef std::shared_ptr<SorInfo> PtrSorInfo;

#endif // _SOR_INFO_H_