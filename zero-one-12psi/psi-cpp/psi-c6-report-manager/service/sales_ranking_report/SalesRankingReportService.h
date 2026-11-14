#pragma
#ifndef _SALES_RANKING_REPORT_SERVICE_H
#define _SALES_RANKING_REPORT_SERVICE_H

#include "domain/dto/sales_ranking_report/SalesRankingReportDTO.h"
#include "domain/query/sales_ranking_report/SalesRankingReportQuery.h"
class SalesRankingReportService
{
public:
	SalesRankingReportPageDTO::Wrapper listAll(const SalesRankingTableQuery::Wrapper& query);

};

#endif // !_SALES_RANKING_REPORT_SERVICE_H
