#pragma once
#ifndef _GOODS_RECEIPT_DISPATCH_CONTROLLER_H_
#define _GOODS_RECEIPT_DISPATCH_CONTROLLER_H_

#include "ApiHelper.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/query/goods_summary_report/GoodsSummaryReportQuery.h"
#include "domain/dto/goods_summary_report/GoodsSummaryReportDTO.h"
#include "domain/vo/goods_summary_report/GoodsSummaryReportJsonVO.h"



#include OATPP_CODEGEN_BEGIN(ApiController)

class GoodsSummaryReport : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(GoodsSummaryReport);

public:
	// 查询商品收发汇总表接口
	API_DEF_ENDPOINT_INFO_QUERY_AUTH(ZH_WORDS_GETTER("goods_summary_report.summary"), getGoodsSummaryReport, GoodsSummaryReportQuery, GoodsSummaryReportJsonVO::Wrapper, ZH_WORDS_GETTER("goods_summary_report.tag.t1"));
	ENDPOINT(API_M_GET, "report/goods-summary", getGoodsSummaryReport, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, GoodsSummaryReportQuery, queryParams);
		API_HANDLER_RESP_VO(execGoodsSummaryReportQuery(query));
	};

	// 导出商品收发汇总表接口
	API_DEF_ENDPOINT_INFO_QUERY_AUTH(ZH_WORDS_GETTER("goods_summary_report.export.summary"), exportGoodsSummaryReport, GoodsSummaryReportQuery, Void, ZH_WORDS_GETTER("goods_summary_report.tag.t1"));
	ENDPOINT(API_M_GET, "report/goods-summary/export", exportGoodsSummaryReport, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, GoodsSummaryReportQuery, queryParams);
		return execExportGoodsSummaryReportQuery(query);
	};

private:
	// 执行商品收发汇总表查询
	GoodsSummaryReportJsonVO::Wrapper execGoodsSummaryReportQuery(const GoodsSummaryReportQuery::Wrapper& query);
	std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> execExportGoodsSummaryReportQuery(const GoodsSummaryReportQuery::Wrapper& query);
};

#include OATPP_CODEGEN_END(ApiController)

#endif // !_GOODS_RECEIPT_DISPATCH_CONTROLLER_H_