#pragma once
#include "BaseDAO.h"
#include "../../domain/query/customer_statement/Cus_StateQuery.h"
#include "../customer_statement/Cus_StateMapper.h"
#include "../../domain/dto/customer_statement/Cus_StateDTO.h"

class Cus_StateDAO :public BaseDAO
{
private:
	//查询条件构建器，根据Sale_DetailQuery对象动态构建查询条件相关参数
	inline std::string queryConditionBuilder(const Cus_StateQuery::Wrapper& query, SqlParams& params);
public:
	// 统计数据条数
	uint64_t count(const Cus_StateQuery::Wrapper& query);
	//分页查询数据
	std::list<Cus_StateOneViewDO> selectOneWithPage(const Cus_StateQuery::Wrapper& query);
	std::list<Cus_StateAllViewDO> selectAllWithPage(const Cus_StateQuery::Wrapper& query);
};