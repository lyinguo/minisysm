#pragma once

#ifndef _ACCOUNT_PAYABLE_AGING_REPORT_QUERY_
#define _ACCOUNT_PAYABLE_AGING_REPORT_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 应付账款明细表报告查询对象
 */

class AccountPayableAgingReportQuery : public PageQuery {

	DTO_INIT(AccountPayableAgingReportQuery, PageQuery);

	// 供应商 supplier
	API_DTO_FIELD_DEFAULT(String, supplier, ZH_WORDS_GETTER("account_payable_aging_report.field.supplier"));

	// 起始日期 start_date
	API_DTO_FIELD_DEFAULT(String, start_date, ZH_WORDS_GETTER("account_payable_aging_report.field.start_date"));

	// 结束日期 end_date
	API_DTO_FIELD_DEFAULT(String, end_date, ZH_WORDS_GETTER("account_payable_aging_report.field.end_date"));

	// 类型（0=全部供应商 1=仅欠款供应商）	
	API_DTO_FIELD_DEFAULT(UInt32, type, ZH_WORDS_GETTER("account_payable_aging_report.field.type"));
};


#include OATPP_CODEGEN_END(DTO)
#endif // !_ACCOUNT_PAYABLE_AGING_REPORT_QUERY_