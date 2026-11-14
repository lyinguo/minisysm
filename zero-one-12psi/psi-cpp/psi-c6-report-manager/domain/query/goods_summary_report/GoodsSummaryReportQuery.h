#pragma once
#ifndef _GOODS_RECEIPT_DISPATCH_QUERY_
#define _GOODS_RECEIPT_DISPATCH_QUERY_

#include "domain/query/PageQuery.h"
#include "oatpp/core/Types.hpp"
#include "oatpp/core/macro/codegen.hpp"
#include "../../GlobalInclude.h"
#include OATPP_CODEGEN_BEGIN(DTO)

/**
 *	商品收发汇总DTO
 */
class GoodsSummaryReportQuery : public PageQuery
{

	DTO_INIT(GoodsSummaryReportQuery, PageQuery);

	DTO_FIELD(String, goods);
	DTO_FIELD_INFO(goods) {
		info->description = ZH_WORDS_GETTER("goods_summary_report.field.name");
	}


	DTO_FIELD(String, startTime);
	DTO_FIELD_INFO(startTime) {
		info->description = ZH_WORDS_GETTER("goods_summary_report.field.startTime");
	}

	
	DTO_FIELD(String, endTime);
	DTO_FIELD_INFO(endTime) {
		info->description = ZH_WORDS_GETTER("goods_summary_report.field.endTime");
	}

	
	DTO_FIELD(Vector<String>, warehouse);
	DTO_FIELD_INFO(warehouse) {
		info->description = ZH_WORDS_GETTER("goods_summary_report.field.warehouse");
	}

};

#include OATPP_CODEGEN_END(DTO)

#endif // _GOODS_RECEIPT_DISPATCH_QUERY_