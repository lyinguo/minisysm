#ifndef _PROCUREMENT_ORDER_TRACKING_VO_
#define _PROCUREMENT_ORDER_TRACKING_VO_
#include "../../GlobalInclude.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/dto/procurement_order_tracking/ProcurementOrderTrackingDTO.h"
#include OATPP_CODEGEN_BEGIN(DTO)

class ProcurementOrderTrackingJsonVO : public JsonVO<ProcurementOrderTrackingDTO::Wrapper>
{
    DTO_INIT(ProcurementOrderTrackingJsonVO, JsonVO<ProcurementOrderTrackingDTO::Wrapper>);
};

class ProcurementOrderTrackingPageJsonVO : public JsonVO<ProcurementOrderTrackingPageDTO::Wrapper>
{
    DTO_INIT(ProcurementOrderTrackingPageJsonVO, JsonVO<ProcurementOrderTrackingPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif