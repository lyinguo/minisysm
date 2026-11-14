#include "stdafx.h"
#include "Macros.h"
#include "ProcurementDetailReportService.h"


ProcurementDetailReportPageDTO::Wrapper ProcurementDetailReportService::listAll(const ProcurementDetailReportQuery::Wrapper& query)
{
	auto page = ProcurementDetailReportPageDTO::createShared();
	page->pageIndex = query->pageIndex;
	page->pageSize = query->pageSize;

	//Log
	cout << "query->pageIndex:" << query->pageIndex << endl;
	cout << "query->pageSize:" << query->pageSize << endl;
	
	
	ProcurementDetailReportDAO pd;
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

	list<ProcurementDetailReportViewDOPtr> list = pd.selectWithPage(query, page->pageIndex, page->pageSize);
	for (auto one : list)
	{
		auto dto = ProcurementDetailReportDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, one,
			id, Id,
			billType, Source,
			frame, Frame,
			customer, Supplier,
			time, Time,
			number, Number,
			goods, Goods,
			attr, Attr,
			warehouse, Warehouse,
			price, Price,
			unit, Unit,
			nums, Nums,
			dsc, Dsc,
			total, Total,
			tat, Tat,
			tpt, Tpt,
			datas, Data
		);

		page->addData(dto);
	}
	return page;
}

