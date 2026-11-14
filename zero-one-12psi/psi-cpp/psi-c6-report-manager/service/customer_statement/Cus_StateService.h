#pragma once
#include "../../domain/vo/customer_statement/Cus_StateVO.h"
#include "../../domain/dto/customer_statement/Cus_StateDTO.h"
#include "../../domain/query/customer_statement/Cus_StateQuery.h"

class Cus_StateService
{
public:
	//分页查询所有不明细数据
	Cus_State_OnepageDTO::Wrapper listOne(const Cus_StateQuery::Wrapper& query);
	//分页查询所有明细数据
	Cus_State_AllpageDTO::Wrapper listAll(const Cus_StateQuery::Wrapper& query);
};