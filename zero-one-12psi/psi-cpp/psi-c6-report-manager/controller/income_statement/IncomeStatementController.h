#pragma once
#ifndef _INCOMESTATEMENT_CONTROLLER_
#define _INCOMESTATEMENT_CONTROLLER_
#include"ApiHelper.h"
#include"domain/vo/BaseJsonVO.h"
#include"domain/query/income_statement/IncomeStatementQuery.h"
#include"domain/dto/income_statement/IncomeStatementDTO.h"
#include"domain/vo/income_statement/IncomeStatementVO.h"
#include OATPP_CODEGEN_BEGIN(ApiController)
class IncomeStatementController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(IncomeStatementController);
public:
	ENDPOINT_INFO(queryIncomeStatement)
	{
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("income_statement.tags.t1"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(IncomeStatementPageVO);
		API_DEF_ADD_TAG(ZH_WORDS_GETTER("income_statement.get.summary"));
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "start_date", ZH_WORDS_GETTER("income_statement.field.start_date"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "end_date", ZH_WORDS_GETTER("income_statement.field.end_date"), "", false);
	}
	ENDPOINT(API_M_GET, "/income_statement", queryIncomeStatement, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME)
	{
		API_HANDLER_QUERY_PARAM(sdrQuery, IncomeStatementQuery, queryParams);
		API_HANDLER_RESP_VO(execQuerySDR(sdrQuery));
	}
	API_DEF_ENDPOINT_INFO_QUERY_AUTH(
		ZH_WORDS_GETTER("income_statement.tags.t2"),
		exportIncomeStatementXlsx,
		IncomeStatementQuery,
		Void,
		ZH_WORDS_GETTER("income_statement.get.summary")
	);
	API_HANDLER_ENDPOINT_OPTION_AUTH(
		API_M_GET,
		"/income_statement/export.xlsx",
		exportIncomeStatementXlsx,
		QUERIES(QueryParams, queryParams),
		API_HANDLER_QUERY_PARAM(sdrQuery, IncomeStatementQuery, queryParams);
	return execQuerySDRX(sdrQuery);
		)
private:
	IncomeStatementPageVO::Wrapper execQuerySDR(const IncomeStatementQuery::Wrapper& query);
	std::shared_ptr<OutgoingResponse> execQuerySDRX(const IncomeStatementQuery::Wrapper& query);
};
#include OATPP_CODEGEN_END(ApiController)
#endif