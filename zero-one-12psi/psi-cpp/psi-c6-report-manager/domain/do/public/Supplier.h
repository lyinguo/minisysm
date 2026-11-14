#pragma once
#ifndef _SUPPLIER_H_
#define _SUPPLIER_H_

#include "BaseDO.h"
#include <memory>
#include <string>

using namespace std;

class Supplier : public BaseDO
{
    // 唯一标识
    MYSQL_SYNTHESIZE(string, id, Id);
    // 供应商名称
    MYSQL_SYNTHESIZE(string, name, Name);
    // 拼音信息
    MYSQL_SYNTHESIZE(string, py, Py);
    // 供应商编号
    MYSQL_SYNTHESIZE(string, number, Number);
    // 所属组织
    MYSQL_SYNTHESIZE(string, frame, Frame);
    // 所属用户
    MYSQL_SYNTHESIZE(string, user, User);
    // 供应商类别
    MYSQL_SYNTHESIZE(string, category, Category);
    // 增值税税率
    MYSQL_SYNTHESIZE(string, rate, Rate);
    // 开户银行
    MYSQL_SYNTHESIZE(string, bank, Bank);
    // 银行账号
    MYSQL_SYNTHESIZE(string, account, Account);
    // 纳税号码
    MYSQL_SYNTHESIZE(string, tax, Tax);
    // 备注信息
    MYSQL_SYNTHESIZE(string, data, Data);
    // 联系资料
    MYSQL_SYNTHESIZE(string, contacts, Contacts);
    // 应付款余额
    MYSQL_SYNTHESIZE(string, balance, Balance);
    // 扩展信息
    MYSQL_SYNTHESIZE(string, more, More);

public:
    Supplier() : BaseDO("supplier")
    {
        MYSQL_ADD_FIELD_PK("id", "s", id);
        MYSQL_ADD_FIELD("name", "s", name);
        MYSQL_ADD_FIELD("py", "s", py);
        MYSQL_ADD_FIELD("number", "s", number);
        MYSQL_ADD_FIELD("frame", "s", frame);
        MYSQL_ADD_FIELD("user", "s", user);
        MYSQL_ADD_FIELD("category", "s", category);
        MYSQL_ADD_FIELD("rate", "s", rate);
        MYSQL_ADD_FIELD_NULLABLE("bank", "s", bank, false);
        MYSQL_ADD_FIELD_NULLABLE("account", "s", account, false);
        MYSQL_ADD_FIELD_NULLABLE("tax", "s", tax, false);
        MYSQL_ADD_FIELD_NULLABLE("data", "s", data, false);
        MYSQL_ADD_FIELD_NULLABLE("contacts", "s", contacts, false);
        MYSQL_ADD_FIELD_NULLABLE("balance", "s", balance, false);
        MYSQL_ADD_FIELD_NULLABLE("more", "s", more, false);
    }
};

// 定义一个智能指针别名方便使用
typedef std::shared_ptr<Supplier> PtrSupplier;

#endif // _SUPPLIER_H_