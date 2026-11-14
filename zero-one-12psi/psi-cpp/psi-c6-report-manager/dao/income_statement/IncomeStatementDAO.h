#pragma once
#ifndef INCOME_STATEMENT_DAO_H
#define INCOME_STATEMENT_DAO_H

#include "BaseDAO.h"
#include "../../domain/do/income_statement/IncomeStatementDO.h"
#include "../../domain/query/income_statement/IncomeStatementQuery.h"

/**
 * 销售利润表数据库操作实现
 */
class IncomeStatementDAO : public BaseDAO
{
private:
	//************************************
	// Method:      queryConditionBuilder
	// FullName:    IncomeStatementDAO::queryConditionBuilder
	// Access:      private 
	// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
	// Parameter:   const IncomeStatementQuery::Wrapper& query 查询数据对象
	// Parameter:   SqlParams& params 存放查询数据的参数对象
	// Description: 查询条件构建器，根据查询数据对象动态构建查询条件相关参数
	//************************************
	inline std::string queryConditionBuilder(const IncomeStatementQuery::Wrapper& query, SqlParams& params);
public:
	//统计数据条数
	uint64_t count(const IncomeStatementQuery::Wrapper& query);
	// 分页查询数据
	std::list<IncomeStatementViewDOPtr> selectWithPage(const IncomeStatementQuery::Wrapper& query, uint32_t pageIndex, uint32_t pageSize);
};

#endif // !INCOME_STATEMENT_DAO_H