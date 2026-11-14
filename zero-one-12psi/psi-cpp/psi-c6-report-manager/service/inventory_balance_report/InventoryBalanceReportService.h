#ifndef _INVENTORY_BALANCE_REPORT_SERVICE_H
#define _INVENTORY_BALANCE_REPORT_SERVICE_H

#include "domain/dto/inventory_balance_report/InventoryBalanceReportDTO.h"
#include "domain/query/inventory_balance_report/InventoryBalanceReportQuery.h"

class InventoryBalanceReportService
{
public:
	InventoryBalanceReportPageDTO::Wrapper listAll(const InventoryBalanceReportQuery::Wrapper& query);
};

#endif // !_INVENTORY_BALANCE_REPORT_SERVICE_H

