#pragma once

#ifndef _SALESRECEIPTSTABLEMAPPER_
#define _SALESRECEIPTSTABLEMAPPER_

#include "Mapper.h"
#include "domain/do/sales_receipts_table/SalesReceiptsTableDO.h"

class SalesReceiptsTableMapper : public Mapper<SalesReceiptsTableDO>
{
public:
	SalesReceiptsTableDO mapper(ResultSet* resultSet) const override
	{
		SalesReceiptsTableDO data;
		data.setType(resultSet->getString(1));
		data.setFrame(resultSet->getString(2));
		data.setCustomer(resultSet->getString(3));
		data.setTime(resultSet->getString(4));
		data.setNumber(resultSet->getString(5));
		data.setTotal(resultSet->getDouble(6));
		data.setActual(resultSet->getDouble(7));
		data.setMoney(resultSet->getDouble(8));
		data.setBalance(resultSet->getDouble(9));
		data.setRate(resultSet->getDouble(10));
		data.setNucleus(resultSet->getString(11));
		data.setData(resultSet->getString(12));
		return data;
	}
};

#endif // !_SALESRECEIPTSTABLEMAPPER_
