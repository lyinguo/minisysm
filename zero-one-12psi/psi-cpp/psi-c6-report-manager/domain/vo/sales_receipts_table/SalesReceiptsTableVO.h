#pragma once

#ifndef _SALESRECEIPTSTABLEVO_
#define _SALESRECEIPTSTABLEVO_

#include "../../GlobalInclude.h"
#include "../../dto/sales_receipts_table/SalesReceiptsTableDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)


class SalesReceiptsTableJsonVO : public JsonVO<SalesReceiptsTableDTO::Wrapper> {
	DTO_INIT(SalesReceiptsTableJsonVO, JsonVO<SalesReceiptsTableDTO::Wrapper>);
};

class SalesReceiptsTablePageJsonVO : public JsonVO<SalesReceiptsTablePageDTO::Wrapper> {
	DTO_INIT(SalesReceiptsTablePageJsonVO, JsonVO<SalesReceiptsTablePageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_SALESRECEIPTSTABLEVO_