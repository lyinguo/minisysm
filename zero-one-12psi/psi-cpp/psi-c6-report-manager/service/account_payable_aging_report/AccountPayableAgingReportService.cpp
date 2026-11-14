#include "stdafx.h"
#include "AccountPayableAgingReportService.h"
#include "../../dao/account_payable_aging_report/AccountPayableAgingReportDAO.h"

// 内联函数：将DO对象映射为DTO对象
inline void mapAccountPayableAgingReport(const AccountPayableAgingReportViewDOPtr& source, AccountPayableAgingReportDTO::Wrapper& target) {
	// 映射字段：customer_name（供应商）
	auto customerNamePtr = source->getCustomerNamePtr();
	if (customerNamePtr) {
		target->customer_name = oatpp::String(customerNamePtr->c_str());
	}

	// 映射字段：category（单据类型）
	auto categoryPtr = source->getCategoryPtr();
	if (categoryPtr) {
		target->category = oatpp::String(categoryPtr->c_str());
	}

	// 映射字段：frame（所属组织）
	auto framePtr = source->getFramePtr();
	if (framePtr) {
		target->frame = oatpp::String(framePtr->c_str());
	}

	// 映射字段：time（单据日期）
	auto timePtr = source->getTimePtr();
	if (timePtr) {
		target->time = oatpp::String(timePtr->c_str());
	}

	// 映射字段：number（单据编号）
	auto numberPtr = source->getNumberPtr();
	if (numberPtr) {
		target->number = oatpp::String(numberPtr->c_str());
	}

	// 映射字段：cw（增加应付款）
	auto cwPtr = source->getCwPtr();
	target->cw = cwPtr ? *cwPtr : 0.0;

	// 映射字段：pia（增加预付款）
	auto piaPtr = source->getPiaPtr();
	target->pia = piaPtr ? *piaPtr : 0.0;

	// 映射字段：balance（应付款余额）
	auto balancePtr = source->getBalancePtr();
	target->balance = balancePtr ? *balancePtr : 0.0;

	// 映射字段：data（备注）
	auto dataPtr = source->getDataPtr();
	if (dataPtr) {
		target->data = oatpp::String(dataPtr->c_str());
	}
}

/**
 * 分页查询应付款明细报表
 * 说明：
 * - 调用 DAO 层的 selectWithPage 方法获取数据
 * - 将 DO 对象转换为 DTO 对象
 * - 封装为分页 DTO 返回
 */
AccountPayableAgingReportPageDTO::Wrapper AccountPayableAgingReportService::listAll(const AccountPayableAgingReportQuery::Wrapper& query)
{
	auto pages = AccountPayableAgingReportPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// // 参数校验：结束日期、类型为必填项
	// if (!query->end_date || !query->type) {
	// 	pages->total = v_int64(0);
	// 	pages->pages = v_int64(0);
	// 	return pages;
	// }

	AccountPayableAgingReportDAO dao;
	
	// 获取分页数据
	std::list<AccountPayableAgingReportViewDOPtr> result = dao.selectWithPage(query, query->pageIndex.getValue(1), query->pageSize.getValue(10));
	
	// 如果没有数据，直接返回
	if (result.empty()) {
		//cout << "no data";
		pages->total = v_int64(0);
		pages->pages = v_int64(0);
		return pages;
	}

	// 转换 DO 为 DTO 并添加到结果集
	for (AccountPayableAgingReportViewDOPtr& sub : result) {
		auto dto = AccountPayableAgingReportDTO::createShared();
		mapAccountPayableAgingReport(sub, dto);
		pages->addData(dto);
	}

	// 计算总数和总页数
	// 注意：由于当前 SQL 使用 CTE 和窗口函数，统计总数需要单独查询
	// 这里先使用当前页数据量作为总数（实际项目中应实现 getCount 方法）
	pages->total = v_int64(result.size());
	pages->calcPages();

	return pages;
}

