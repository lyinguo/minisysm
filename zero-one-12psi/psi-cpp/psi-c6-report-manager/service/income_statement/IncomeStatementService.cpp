//#include "stdafx.h"
//#include "Macros.h"
//#include "IncomeStatementService.h"
//
//
//IncomeStatementPageDTO::Wrapper IncomeStatementService::listAll(const IncomeStatementQuery::Wrapper& query)
//{
//	auto page = IncomeStatementPageDTO::createShared();
//	page->pageIndex = query->pageIndex;
//	page->pageSize = query->pageSize;
//
//	//Log
//	cout << "query->pageIndex:" << query->pageIndex << endl;
//	cout << "query->pageSize:" << query->pageSize << endl;
//
//
//	IncomeStatementDAO pd;
//	auto count = pd.count(query);
//	//Log
//	cout << "count:" << count << endl;
//	cout << "-----------------------------------------------------" << endl;
//	if (count <= 0)
//	{
//		return page;
//	}
//	page->total = count;
//	page->calcPages();
//
//
//	//Log
//	cout << "count:" << count << endl;
//	cout << "-----------------------------------------------------" << endl;
//
//	list<IncomeStatementViewDOPtr> list = pd.selectWithPage(query, page->pageIndex, page->pageSize);
//	for (auto one : list)
//	{
//		auto dto = IncomeStatementDTO::createShared();
//		ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, one,
//			id, Id,
//			serial_number, Serial_number,
//			item, Item,
//			amount, Amount
//		);
//
//		page->addData(dto);
//	}
//	return page;
//}
#include "stdafx.h"
#include "Macros.h"
#include "IncomeStatementService.h"


IncomeStatementPageDTO::Wrapper IncomeStatementService::listAll(const IncomeStatementQuery::Wrapper& query)
{
	auto page = IncomeStatementPageDTO::createShared();
	page->pageIndex = query->pageIndex;
	page->pageSize = query->pageSize;

	//Log
	cout << "query->pageIndex:" << query->pageIndex << endl;
	cout << "query->pageSize:" << query->pageSize << endl;


	IncomeStatementDAO pd;
	auto count = pd.count(query);
	//Log
	cout << "count:" << count << endl;
	cout << "-----------------------------------------------------" << endl;
	if (count <= 0)
	{
		return page;
	}
	page->total = count;
	page->calcPages();


	//Log
	cout << "count:" << count << endl;
	cout << "-----------------------------------------------------" << endl;

	list<IncomeStatementViewDOPtr> list = pd.selectWithPage(query, page->pageIndex, page->pageSize);
	for (auto one : list)
	{
		auto dto = IncomeStatementDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, one,
			id, Id,
			serial_number, Serial_number,
			item, Item,
			amount, Amount
		);

		page->addData(dto);
	}
	return page;
}