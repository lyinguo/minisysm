#pragma once
#ifndef SALES_INCOME_STATEMENT_DAO_H
#define SALES_INCOME_STATEMENT_DAO_H

#include "BaseDAO.h"
#include "../../domain/do/sales_income_statement/SalesIncomeStatementDO.h"
#include "../../domain/query/sales_income_statement/SalesIncomeStatementQuery.h"

/**
 * 销售利润表数据库操作实现
 */
class SalesIncomeStatementDAO : public BaseDAO
{
private:
	//************************************
	// Method:      queryConditionBuilder
	// FullName:    SalesIncomeStatementDAO::queryConditionBuilder
	// Access:      private 
	// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
	// Parameter:   const SalesIncomeStatementQuery::Wrapper& query 查询数据对象
	// Parameter:   SqlParams& params 存放查询数据的参数对象
	// Description: 查询条件构建器，根据查询数据对象动态构建查询条件相关参数
	//************************************
	inline std::string queryConditionBuilder(const SalesIncomeStatementQuery::Wrapper& query, SqlParams& params);
public:
	//统计数据条数
	uint64_t count(const SalesIncomeStatementQuery::Wrapper& query);
	// 分页查询数据
	std::list<SalesIncomeStatementViewDOPtr> selectWithPage(const SalesIncomeStatementQuery::Wrapper& query, uint32_t pageIndex, uint32_t pageSize);
};

#endif // !SALES_INCOME_STATEMENT_DAO_H