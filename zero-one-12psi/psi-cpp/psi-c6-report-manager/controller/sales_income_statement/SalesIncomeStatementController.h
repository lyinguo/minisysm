#pragma once
#ifndef _SALESINCOMESTATEMENT_CONTROLLER_
#define _SALESINCOMESTATEMENT_CONTROLLER_
#include"ApiHelper.h"
#include"domain/vo/BaseJsonVO.h"
#include"domain/query/sales_income_statement/SalesIncomeStatementQuery.h"
#include"domain/dto/sales_income_statement/SalesIncomeStatementDTO.h"
#include"domain/vo/sales_income_statement/SalesIncomeStatementVO.h"
#include OATPP_CODEGEN_BEGIN(ApiController)
class SalesIncomeStatementController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(SalesIncomeStatementController);
public:
	ENDPOINT_INFO(querySalesIncomeStatement)
	{
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("sales_income_statement.tags.t1"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(SalesIncomeStatementPageVO);
		API_DEF_ADD_TAG(ZH_WORDS_GETTER("sales_income_statement.get.summary"));
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "customer", ZH_WORDS_GETTER("sales_income_statement.field.customer"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "bill_number", ZH_WORDS_GETTER("sales_income_statement.field.bill_number"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "start_date", ZH_WORDS_GETTER("sales_income_statement.field.start_date"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "end_date", ZH_WORDS_GETTER("sales_income_statement.field.end_date"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "bill_preparer", ZH_WORDS_GETTER("sales_income_statement.field.bill_preparer"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "relevant_personnel", ZH_WORDS_GETTER("sales_income_statement.field.relevant_personnel"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "bill_type", ZH_WORDS_GETTER("sales_income_statement.field.bill_type"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "show_or_hide_details", ZH_WORDS_GETTER("sales_income_statement.field.show_or_hide_details"), "", false);
	}
	ENDPOINT(API_M_GET, "/sales_income_statement", querySalesIncomeStatement, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME)
	{
		API_HANDLER_QUERY_PARAM(sdrQuery, SalesIncomeStatementQuery, queryParams);
		API_HANDLER_RESP_VO(execQuerySDR(sdrQuery));
	}
	API_DEF_ENDPOINT_INFO_QUERY_AUTH(
		ZH_WORDS_GETTER("sales_income_statement.tags.t2"),
		exportSalesIncomeStatementXlsx,
		SalesIncomeStatementQuery,
		Void,
		ZH_WORDS_GETTER("sales_income_statement.get.summary")
	);
	API_HANDLER_ENDPOINT_OPTION_AUTH(
		API_M_GET,
		"/sales_income_statement/export.xlsx",
		exportSalesIncomeStatementXlsx,
		QUERIES(QueryParams, queryParams),
		API_HANDLER_QUERY_PARAM(sdrQuery, SalesIncomeStatementQuery, queryParams);
	return execQuerySDRX(sdrQuery);
		)
private:
	SalesIncomeStatementPageVO::Wrapper execQuerySDR(const SalesIncomeStatementQuery::Wrapper& query);
	std::shared_ptr<OutgoingResponse> execQuerySDRX(const SalesIncomeStatementQuery::Wrapper& query);
};
#include OATPP_CODEGEN_END(ApiController)
#endif