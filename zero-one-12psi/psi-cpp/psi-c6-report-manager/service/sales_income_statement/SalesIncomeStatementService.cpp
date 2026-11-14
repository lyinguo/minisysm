#include "stdafx.h"
#include "Macros.h"
#include "SalesIncomeStatementService.h"


SalesIncomeStatementPageDTO::Wrapper SalesIncomeStatementService::listAll(const SalesIncomeStatementQuery::Wrapper& query)
{
	auto page = SalesIncomeStatementPageDTO::createShared();
	page->pageIndex = query->pageIndex;
	page->pageSize = query->pageSize;

	//Log
	cout << "query->pageIndex:" << query->pageIndex << endl;
	cout << "query->pageSize:" << query->pageSize << endl;


	SalesIncomeStatementDAO pd;
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

	list<SalesIncomeStatementViewDOPtr> list = pd.selectWithPage(query, page->pageIndex, page->pageSize);
	for (auto one : list)
	{
		auto dto = SalesIncomeStatementDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, one,
			id, Id,
			bill_type, Bill_type,
			belonging_organization, Belonging_organization,
			customer, Customer,
			bill_time, Bill_time,
			bill_number, Bill_number,
			bill_amount, Bill_amount,
			discount_amount, Discount_amount,
			actual_amount, Actual_amount,
			cost, Cost,
			gross_profit, Gross_profit,
			gross_profit_margin, Gross_profit_margin,
			bill_fee, Bill_fee,
			net_profit, Net_profit,
			net_profit_margin, Net_profit_margin,
			write_off_amount, Write_off_amount,
			write_off_status, Write_off_status,
			bill_preparer, Bill_preparer,
			relevant_personnel, Relevant_personnel,
			remark_information, Remark_information
		);

		page->addData(dto);
	}
	return page;
}

