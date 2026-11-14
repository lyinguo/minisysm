#pragma once 

#include"BaseDAO.h"
#include"../../domain/do/sale_detail/Sale_DetailDO.h"
#include"../../domain/dto/sale_detail/Sale_DetailDTO.h"
#include "../../domain/query/sale_detail/Sale_DetailQuery.h"

class Sale_DetailDAO :public BaseDAO
{
private:
	//查询条件构建器，根据Sale_DetailQuery对象动态构建查询条件相关参数
	inline std::string queryConditionBuilder(const Sale_DetailQuery::Wrapper& query, SqlParams& params);
public:
	// 统计数据条数
	uint64_t count(const Sale_DetailQuery::Wrapper& query);
	 //分页查询数据
	std::list<Sale_DetailViewDO> selectWithPage(const Sale_DetailQuery::Wrapper& query);
};
