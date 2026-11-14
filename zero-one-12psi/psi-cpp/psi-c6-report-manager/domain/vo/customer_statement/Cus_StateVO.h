#ifndef _CUS_STATEVO_H_
#define _CUS_STATEVO_H_

#include"../../GlobalInclude.h"
#include"../../dto/customer_statement/Cus_StateDTO.h"
#include OATPP_CODEGEN_BEGIN(DTO)


class Cus_State_OneJsonVO :public JsonVO<Cus_State_OneDTO::Wrapper>
{
	DTO_INIT(Cus_State_OneJsonVO, JsonVO<Cus_State_OneDTO::Wrapper>);
};

class Cus_State_OnepageJsonVO :public JsonVO<Cus_State_OnepageDTO::Wrapper>
{
	DTO_INIT(Cus_State_OnepageJsonVO, JsonVO<Cus_State_OnepageDTO::Wrapper>);
};

class Cus_State_AllJsonVO :public JsonVO<Cus_State_AllDTO::Wrapper>
{
	DTO_INIT(Cus_State_AllJsonVO, JsonVO<Cus_State_AllDTO::Wrapper>);
};

class Cus_State_AllpageJsonVO :public JsonVO<Cus_State_AllpageDTO::Wrapper>
{
	DTO_INIT(Cus_State_AllpageJsonVO, JsonVO<Cus_State_AllpageDTO::Wrapper>);
};
#include OATPP_CODEGEN_END(DTO)
#endif