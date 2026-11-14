#ifndef _PROCUREMENT_RANKING_REPORT_VO_
#define _PROCUREMENT_RANKING_REPORT_VO_
#include "../../GlobalInclude.h"
#include"domain/vo/BaseJsonVO.h"
#include OATPP_CODEGEN_BEGIN(DTO)
class ProcurementRankingJsonVO :public JsonVO<ProcurementRankingDTO::Wrapper>
{
	DTO_INIT(ProcurementRankingJsonVO, JsonVO<ProcurementRankingDTO::Wrapper>);
};

class ProcurementRankingPageJsonVO :public JsonVO<ProcurementRankingPageDTO::Wrapper>
{
	DTO_INIT(ProcurementRankingPageJsonVO, JsonVO<ProcurementRankingPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif