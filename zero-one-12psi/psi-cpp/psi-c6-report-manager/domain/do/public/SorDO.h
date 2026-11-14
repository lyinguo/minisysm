#pragma once
#ifndef _SOR_DO_H_
#define _SOR_DO_H_

#include "BaseDO.h"
#include <memory>
#include <string>

using namespace std;

class SorDO : public BaseDO
{
    // 唯一标识
    MYSQL_SYNTHESIZE(string, id, Id);
    // 所属组织
    MYSQL_SYNTHESIZE(string, frame, Frame);
    // 客户
    MYSQL_SYNTHESIZE(string, customer, Customer);
    // 单据时间
    MYSQL_SYNTHESIZE(string, time, Time);
    // 单据编号
    MYSQL_SYNTHESIZE(string, number, Number);
    // 单据金额
    MYSQL_SYNTHESIZE(string, total, Total);
    // 实际金额
    MYSQL_SYNTHESIZE(string, actual, Actual);
    // 关联人员
    MYSQL_SYNTHESIZE(string, people, People);
    // 到货日期
    MYSQL_SYNTHESIZE(string, arrival, Arrival);
    // 物流信息
    MYSQL_SYNTHESIZE(string, logistics, Logistics);
    // 单据附件
    MYSQL_SYNTHESIZE(string, file, File);
    // 备注信息
    MYSQL_SYNTHESIZE(string, data, Data);
    // 扩展信息
    MYSQL_SYNTHESIZE(string, more, More);
    // 审核状态[0:未审核|1:已审核]
    MYSQL_SYNTHESIZE(int, examine, Examine);
    // 出库状态[0:未出库|1:部分出库|2:已出库|3:关闭]
    MYSQL_SYNTHESIZE(int, state, State);
    // 制单人
    MYSQL_SYNTHESIZE(string, user, User);
  
public:
    SorDO() : BaseDO("sor")
    {
        MYSQL_ADD_FIELD_PK("id", "s", id);
        MYSQL_ADD_FIELD("frame", "s", frame);
        MYSQL_ADD_FIELD("customer", "s", customer);
        MYSQL_ADD_FIELD("time", "s", time);
        MYSQL_ADD_FIELD("number", "s", number);
        MYSQL_ADD_FIELD("total", "s", total);
        MYSQL_ADD_FIELD("actual", "s", actual);
        MYSQL_ADD_FIELD_NULLABLE("people", "s", people, false);
        MYSQL_ADD_FIELD("arrival", "s", arrival);
        MYSQL_ADD_FIELD_NULLABLE("logistics", "s", logistics, false);
        MYSQL_ADD_FIELD_NULLABLE("file", "s", file, false);
        MYSQL_ADD_FIELD_NULLABLE("data", "s", data, false);
        MYSQL_ADD_FIELD_NULLABLE("more", "s", more, false);
        MYSQL_ADD_FIELD("examine", "i", examine);
        MYSQL_ADD_FIELD("state", "i", state);
        MYSQL_ADD_FIELD("user", "s", user);
    }
};

// 定义一个智能指针别名方便使用
typedef std::shared_ptr<SorDO> PtrSorDO;

#endif // _SOR_DO_H_