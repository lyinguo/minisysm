#pragma once
#include "../../domain/vo/sale_detail/Sale_DetailVO.h"
#include "../../domain/dto/sale_detail/Sale_DetailDTO.h"
#include "../../domain/query/sale_detail/Sale_DetailQuery.h"

class Sale_DetailService
{
public:
	//分页查询所有数据
	Sale_DetailPageDTO::Wrapper listAll(const Sale_DetailQuery::Wrapper& query);
};