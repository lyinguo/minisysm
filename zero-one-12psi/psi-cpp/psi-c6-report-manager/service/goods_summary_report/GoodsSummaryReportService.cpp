#include "stdafx.h"
#include "GoodsSummaryReportService.h"
#include "../../dao/goods_summary_report/GoodsSummaryReportDAO.h"

// 内联函数：创建Balance对象
inline Balance::Wrapper createBalance(double uct, int64_t uns, double bct) {
	auto balance = Balance::createShared();
	balance->uct = uct;
	balance->uns = uns;
	balance->bct = bct;
	return balance;
}

// 内联函数：将DO对象映射为DTO对象
inline void mapGoodsSummaryReport(const PtrGoodSummaryReportViewDO& source, GoodsSummaryReportDTO::Wrapper& target) {
	// 基本商品信息
	target->name = source->getName();
	target->warehouse = source->getWarehouse();
	target->number = source->getNumber();
	target->spec = source->getSpec();
	target->unit = source->getUnit();

	// 汇总数据
	target->sum = createBalance(source->getSumUct(), source->getSumUns(), source->getSumBct());

	// 期初数据
	target->state = createBalance(source->getStateUct(), source->getStateUns(), source->getStateBct());

	// 采购数据
	target->buy = createBalance(source->getBuyUct(), source->getBuyUns(), source->getBuyBct());

	// 采购退货数据
	target->bre = createBalance(source->getBreUct(), source->getBreUns(), source->getBreBct());

	// 销售数据
	target->sell = createBalance(source->getSellUct(), source->getSellUns(), source->getSellBct());

	// 销售退货数据
	target->sre = createBalance(source->getSreUct(), source->getSreUns(), source->getSreBct());

	// 调拨-出数据
	target->swapOut = createBalance(source->getSwapOutUct(), source->getSwapOutUns(), source->getSwapOutBct());

	// 调拨-入数据
	target->swapEnter = createBalance(source->getSwapEnterUct(), source->getSwapEnterUns(), source->getSwapEnterBct());

	// 其它入库数据
	target->entry = createBalance(source->getEntryUct(), source->getEntryUns(), source->getEntryBct());

	// 其它出库数据
	target->extry = createBalance(source->getExtryUct(), source->getExtryUns(), source->getExtryBct());
}

GoodsSummaryReportPageDTO::Wrapper GoodsSummaryReportService::listAll(const GoodsSummaryReportQuery::Wrapper& query) {
	auto pages = GoodsSummaryReportPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	GoodsSummaryReportDAO dao;
	auto count = dao.getCount(query);
	if (count <= 0) {
		return pages;
	}
	pages->total = count;
	pages->calcPages();

	std::list<PtrGoodSummaryReportViewDO> result = dao.selectWithPage(query);

	for (PtrGoodSummaryReportViewDO& sub : result) {
		auto dto = GoodsSummaryReportDTO::createShared();
		mapGoodsSummaryReport(sub, dto);
		pages->addData(dto);
	}
	return pages;
}