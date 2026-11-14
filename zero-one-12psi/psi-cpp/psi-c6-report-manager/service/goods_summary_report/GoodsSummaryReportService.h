#pragma
#ifndef _GOODS_SUMMARY_REPORT_SERVICE_H
#define _GOODS_SUMMARY_REPORT_SERVICE_H

#include "domain/dto/goods_summary_report/GoodsSummaryReportDTO.h"
#include "domain/query/goods_summary_report/GoodsSummaryReportQuery.h"

class GoodsSummaryReportService
{
public:
	GoodsSummaryReportPageDTO::Wrapper listAll(const GoodsSummaryReportQuery::Wrapper& query);

};

#endif // !_GOODS_SUMMARY_REPORT_SERVICE_H