#pragma once


#ifndef _INVENTORYBALANCEREPORTQUERY_H  // 头文件保护宏（全大写+下划线）
#define _INVENTORYBALANCEREPORTQUERY_H

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class InventoryBalanceReportQuery : public PageQuery {
    DTO_INIT(InventoryBalanceReportQuery, PageQuery);

    // 字段定义
    DTO_FIELD(String, end_date);       // 终止日期（格式：YYYY-MM-DD，例如："2025-10-28"）
    DTO_FIELD(String, product_name);   // 商品名称（模糊匹配，单选：用 LIKE 匹配）
    DTO_FIELD(Vector<String>, warehouse_names); // 仓库名称列表（精确匹配，多选：用 IN 列表）

    // 字段描述（国际化支持）
    DTO_FIELD_INFO(end_date) {
        info->description = ZH_WORDS_GETTER("inventory_balance_report.field.end_date");
    }
    DTO_FIELD_INFO(product_name) {
        info->description = ZH_WORDS_GETTER("inventory_balance_report.field.product_name");
    }
    DTO_FIELD_INFO(warehouse_names) {
        info->description = ZH_WORDS_GETTER("inventory_balance_report.field.warehouse_names");
    }
};

#include OATPP_CODEGEN_END(DTO)
#endif // _INVENTORYBALANCEREPORTQUERY_H