#pragma once

#ifndef _GOODS_RECEIPT_DISPATCH_JSON_VO_
#define _GOODS_RECEIPT_DISPATCH_JSON_VO_

#include "../../GlobalInclude.h"
#include "../../dto/goods_summary_report/GoodsSummaryReportDTO.h"
#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 商品收发汇总表分页响应VO
 */
class GoodsSummaryReportJsonVO : public JsonVO<GoodsSummaryReportPageDTO::Wrapper>
{
	// 初始化
	DTO_INIT(GoodsSummaryReportJsonVO, JsonVO<GoodsSummaryReportPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_GOODS_RECEIPT_DISPATCH_JSON_VO_