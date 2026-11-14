
#pragma once
#ifndef _ACCOUNTPAYABLEAGINGREPORTCONTROLLER_H
#define _ACCOUNTPAYABLEAGINGREPORTCONTROLLER_H

#include "ApiHelper.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/query/account_payable_aging_report/AccountPayableAgingReportQuery.h"
#include "domain/dto/account_payable_aging_report/AccountPayableAgingReportDTO.h"
#include "domain/vo/account_payable_aging_report/AccountPayableAgingReportVO.h"

#include OATPP_CODEGEN_BEGIN(ApiController)

// 定义控制器 应收账款明细报表
class AccountPayableAgingReportController : public oatpp::web::server::api::ApiController
{
    // 定义控制器访问入口
    API_ACCESS_DECLARE(AccountPayableAgingReportController);
    // 定义接口
public:

    // 获取报表接口描述
    ENDPOINT_INFO(queryAccountPayableAgingReport) {
        // 定义接口标题
        API_DEF_ADD_TITLE(ZH_WORDS_GETTER("account_payable_aging_report.get.summary"));
        // 定义默认授权参数
        API_DEF_ADD_AUTH();
        // 定义响应参数格式
        API_DEF_ADD_RSP_JSON_WRAPPER(AccountPayableAgingReportPageVO);
        // 定义标签
        API_DEF_ADD_TAG(ZH_WORDS_GETTER("account_payable_aging_report.tags.t1"));
        // 定义分页查询参数描述
        API_DEF_ADD_PAGE_PARAMS();
        // 定义其他查询参数描述
        // 供应商（可选）
        API_DEF_ADD_QUERY_PARAMS(String, "supplier", ZH_WORDS_GETTER("account_payable_aging_report.field.supplier"), "", false);
        // 起始日期（可选）
        API_DEF_ADD_QUERY_PARAMS(String, "start_date", ZH_WORDS_GETTER("account_payable_aging_report.field.start_date"), "", false);
        // 结束日期（可选）
        API_DEF_ADD_QUERY_PARAMS(String, "end_date", ZH_WORDS_GETTER("account_payable_aging_report.field.end_date"), "", false);
        // 类型：0=全部供应商，1=仅欠款供应商（必填）
        // 注意：直接传入 0，让 UInt32 构造函数处理；不能传入 oatpp::UInt32(0) 因为宏会再次包装
        API_DEF_ADD_QUERY_PARAMS(String, "type", ZH_WORDS_GETTER("account_payable_aging_report.field.type"), "0", false);
        /*info->queryParams.add<UInt32>("type").description = ZH_WORDS_GETTER("account_payable_aging_report.field.type");
        info->queryParams["type"].addExample("default", 0);
        info->queryParams["type"].required = true;*/
        // 缺省值

        
    }
  
    
    // 获取报表接口处理
    ENDPOINT(API_M_GET, "/account_payable_aging_report", queryAccountPayableAgingReport, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
        // 解析查询参数为Query领域模型
        API_HANDLER_QUERY_PARAM(aparQuery, AccountPayableAgingReportQuery, queryParams);
        // 呼叫执行函数响应结果
        API_HANDLER_RESP_VO(execQueryAPAR(aparQuery));
    }

    // 导出接口描述 导出全部不分页
    API_DEF_ENDPOINT_INFO_QUERY_AUTH(
        ZH_WORDS_GETTER("account_payable_aging_report.export.xlsx.summary"),
        exportAccountPayableAgingReportXlsx,
        AccountPayableAgingReportQuery,
        Void,
        ZH_WORDS_GETTER("account_payable_aging_report.tags.t1")
    );

    // 导出接口处理
    API_HANDLER_ENDPOINT_OPTION_AUTH(
        API_M_GET,
        "/account_payable_aging_report/export.xlsx",
        exportAccountPayableAgingReportXlsx,
        QUERIES(QueryParams, queryParams),
        API_HANDLER_QUERY_PARAM(aparQuery, AccountPayableAgingReportQuery, queryParams);
        return execQueryAPARX(aparQuery);
    )

private:
    AccountPayableAgingReportPageVO::Wrapper execQueryAPAR(const AccountPayableAgingReportQuery::Wrapper& query);
    std::shared_ptr<OutgoingResponse> execQueryAPARX(const AccountPayableAgingReportQuery::Wrapper& query);

};
#undef API_TAG
#undef API_TAG2

#include OATPP_CODEGEN_END(ApiController)

#endif // !_ACCOUNTPAYABLEAGINGREPORTCONTROLLER_H