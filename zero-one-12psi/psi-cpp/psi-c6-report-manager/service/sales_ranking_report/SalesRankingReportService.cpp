#include "stdafx.h"
#include "SalesRankingReportService.h"
#include "../../dao/sales_ranking_report/SalesRankingReportDAO.h"

// 内联函数：将DO对象映射为DTO对象
inline void mapSalesRankingReport(const PtrSalesRankingReportViewDO& source, SalesRankingReportDTO::Wrapper& target) {
	target->name = source->getName();
	target->number = source->getNumber();
	target->spec = source->getSpec();
	target->attr = source->getAttr();
	target->unit = source->getUnit();
	target->nums = source->getNums();
	target->dsc = source->getDsc();
	target->tat = source->getTat();
	target->tpt = source->getTpt();
	target->bct = source->getBct();
	target->uct = source->getUct();
	target->gpt = source->getGpt();
	target->gpr = source->getGpr();
}
SalesRankingReportPageDTO::Wrapper SalesRankingReportService::listAll(const SalesRankingTableQuery::Wrapper& query) {
	auto pages = SalesRankingReportPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	SalesRankingReportDAO dao;
	auto count = dao.getCount(query);
	if (count <= 0) {
		return pages;
	}
	pages->total = count;
	pages->calcPages();

	list<PtrSalesRankingReportViewDO>result = dao.selectWithPage(query);
	for (PtrSalesRankingReportViewDO& sub : result) {
		auto dto = SalesRankingReportDTO::createShared();
		mapSalesRankingReport(sub, dto);
		pages->addData(dto);
	}
	return pages;
}