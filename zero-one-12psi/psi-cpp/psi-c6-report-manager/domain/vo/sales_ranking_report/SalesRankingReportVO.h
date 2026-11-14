#pragma
#ifndef _SALES_RANKING_TABLE_VO_H_
#define _SALES_RANKING_TABLE_VO_H_

#include "../../GlobalInclude.h"
#include "../../dto/sales_ranking_report/SalesRankingReportDTO.h"
#include OATPP_CODEGEN_BEGIN(DTO)

class SalesRankingReportJsonVO :public JsonVO< SalesRankingReportPageDTO::Wrapper> 
{
	DTO_INIT(SalesRankingReportJsonVO, JsonVO< SalesRankingReportPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_SALES_RANKING_TABLE_VO_H_
