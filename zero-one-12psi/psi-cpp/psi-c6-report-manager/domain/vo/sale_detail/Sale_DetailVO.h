#pragma once

#include"../../GlobalInclude.h"
#include"../../dto/sale_detail/Sale_DetailDTO.h"
#include OATPP_CODEGEN_BEGIN(DTO)
class Sale_DetailJsonVO :public JsonVO<Sale_DetailDTO::Wrapper>
{
	DTO_INIT(Sale_DetailJsonVO, JsonVO<Sale_DetailDTO::Wrapper>);
};

class Sale_DetailpageJsonVO :public JsonVO<Sale_DetailPageDTO::Wrapper>
{
	DTO_INIT(Sale_DetailpageJsonVO, JsonVO<Sale_DetailPageDTO::Wrapper>);
};
#include OATPP_CODEGEN_END(DTO)