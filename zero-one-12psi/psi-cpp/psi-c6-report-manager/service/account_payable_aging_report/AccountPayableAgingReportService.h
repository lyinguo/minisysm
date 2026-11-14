#ifndef _ACCOUNT_PAYABLE_AGING_REPORT_SERVICE_H
#define _ACCOUNT_PAYABLE_AGING_REPORT_SERVICE_H

#include "domain/dto/account_payable_aging_report/AccountPayableAgingReportDTO.h"
#include "domain/query/account_payable_aging_report/AccountPayableAgingReportQuery.h"

class AccountPayableAgingReportService
{
public:
	AccountPayableAgingReportPageDTO::Wrapper listAll(const AccountPayableAgingReportQuery::Wrapper& query);
};

#endif // !_ACCOUNT_PAYABLE_AGING_REPORT_SERVICE_H

