#pragma once

#ifndef _SUPPLIERSTATEMENTMAPPER_
#define _SUPPLIERSTATEMENTMAPPER_

#include "Mapper.h"
#include "domain/do/supplier_statement/SupplierStatementDO.h"

class SupplierStatementBalanceMapper : public Mapper<SupplierStatementBalanceDO>
{
public:
	SupplierStatementBalanceDO mapper(ResultSet* resultSet) const override
	{
		SupplierStatementBalanceDO data;
		data.setBillName(resultSet->getString(1));
		data.setBalance(resultSet->getDouble(2));
		return data;
	}
};

class SupplierStatementDetailMapper : public Mapper<SupplierStatementDetailDO>
{
public:
	SupplierStatementDetailDO mapper(ResultSet* resultSet) const override
	{
		SupplierStatementDetailDO data;
		data.setName(resultSet->getString(1));
		data.setAttr(resultSet->getString(2));
		data.setUnit(resultSet->getString(3));
		data.setPrice(resultSet->getDouble(4));
		data.setNums(resultSet->getDouble(5));
		data.setDsc(resultSet->getDouble(6));
		data.setTotal(resultSet->getDouble(7));
		data.setTat(resultSet->getDouble(8));
		data.setTpt(resultSet->getDouble(9));
		return data;
	}
};

class SupplierStatementItemMapper : public Mapper<SupplierStatementItemDO>
{
public:
	SupplierStatementItemDO mapper(ResultSet* resultSet) const override
	{
		SupplierStatementItemDO data;
		data.setId(resultSet->getString(1));
		data.setBill(resultSet->getString(2));
		data.setBillName(resultSet->getString(3));
		data.setFrame(resultSet->getString(4));
		data.setTime(resultSet->getString(5));
		data.setNumber(resultSet->getString(6));
		data.setTotal(resultSet->getDouble(7));
		data.setDiscount(resultSet->getDouble(8));
		data.setActual(resultSet->getDouble(9));
		data.setMoney(resultSet->getDouble(10));
		data.setData(resultSet->getString(11));
		return data;
	}
};

#endif // !_SUPPLIERSTATEMENTMAPPER_
