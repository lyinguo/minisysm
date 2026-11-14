
#ifndef _INVENTORYBALANCEREPORTCONTROLLER_H
#define _INVENTORYBALANCEREPORTCONTROLLER_H

#include "ApiHelper.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/query/inventory_balance_report/InventoryBalanceReportQuery.h"
#include "domain/dto/inventory_balance_report/InventoryBalanceReportDTO.h"
#include "domain/vo/inventory_balance_report/InventoryBalanceReportVO.h"


#include OATPP_CODEGEN_BEGIN(ApiController)
#define API_TAG ZH_WORDS_GETTER("inventory_balance_report.tags.t1")
#define API_TAG2 ZH_WORDS_GETTER("inventory_balance_report.tags.t1")
//商品库存余额报表
class InventoryBalanceReportController : public oatpp::web::server::api::ApiController
{
    // 定义控制器访问入口
    API_ACCESS_DECLARE(InventoryBalanceReportController);
    // 定义接口
public:
    // 获取报表接口描述
    ENDPOINT_INFO(queryInventoryBalanceReport) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("inventory_balance_report.get.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式
        API_DEF_ADD_RSP_JSON_WRAPPER(InventoryBalanceReportPageVO);
        // 定义标签
        API_DEF_ADD_TAG(ZH_WORDS_GETTER("inventory_balance_report.tags.t1"));
        // 定义分页查询参数描述
        API_DEF_ADD_PAGE_PARAMS();
        // 定义其他查询参数描述
        // 终止日期（必填）
        API_DEF_ADD_QUERY_PARAMS(String, "end_date", ZH_WORDS_GETTER("inventory_balance_report.field.end_date"), "2025-11-13", true);
        // 商品名称（模糊匹配，单选：用 LIKE 匹配）
        API_DEF_ADD_QUERY_PARAMS(String, "product_name", ZH_WORDS_GETTER("inventory_balance_report.field.product_name"), "", false);
        // 仓库名称列表（精确匹配，多选：用 IN 列表）
        API_DEF_ADD_QUERY_PARAMS(Vector<String>, "warehouse_names", ZH_WORDS_GETTER("inventory_balance_report.field.warehouse_names"), , false);
    }
    // 获取报表接口处理
    ENDPOINT(API_M_GET, "/inventory_balance_report", queryInventoryBalanceReport, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
        // 解析查询参数为Query领域模型
        API_HANDLER_QUERY_PARAM(ibrQuery, InventoryBalanceReportQuery, queryParams);
        // 呼叫执行函数响应结果
        API_HANDLER_RESP_VO(execQueryIBR(ibrQuery));
    }
    // 导出接口描述 导出全部不分页
    ENDPOINT_INFO(exportInventoryBalanceReportXlsx) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("inventory_balance_report.export.xlsx.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式（导出Excel文件，返回二进制流）
        // 注意：导出接口返回的是文件流，不是JSON，所以不需要定义响应类型
        // 定义标签
        API_DEF_ADD_TAG(API_TAG2);
        // 定义分页查询参数描述（导出时可选，用于分页导出）
        API_DEF_ADD_PAGE_PARAMS();
        // 定义其他查询参数描述
        // 终止日期（必填）
        API_DEF_ADD_QUERY_PARAMS(String, "end_date", ZH_WORDS_GETTER("inventory_balance_report.field.end_date"), "", false);
        // 商品名称（模糊匹配，单选：用 LIKE 匹配）
        API_DEF_ADD_QUERY_PARAMS(String, "product_name", ZH_WORDS_GETTER("inventory_balance_report.field.product_name"), "", false);
        // 仓库名称列表（精确匹配，多选：用 IN 列表）
        API_DEF_ADD_QUERY_PARAMS(Vector<String>, "warehouse_names", ZH_WORDS_GETTER("inventory_balance_report.field.warehouse_names"), , false);
    }

    // 导出接口处理
    API_HANDLER_ENDPOINT_OPTION_AUTH(
        API_M_GET,
        "/inventory_balance_report/export.xlsx",
        exportInventoryBalanceReportXlsx,
        QUERIES(QueryParams, queryParams),
        API_HANDLER_QUERY_PARAM(ibrQuery, InventoryBalanceReportQuery, queryParams);
        return execQueryIBRX(ibrQuery);
    )

private:
    InventoryBalanceReportPageVO::Wrapper execQueryIBR(const InventoryBalanceReportQuery::Wrapper& query);
    std::shared_ptr<OutgoingResponse> execQueryIBRX(const InventoryBalanceReportQuery::Wrapper& query);

};
#undef API_TAG
#undef API_TAG2
#include OATPP_CODEGEN_END(ApiController)



#endif // !_INVENTORYBALANCEREPORTCONTROLLER_H
