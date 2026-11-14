#pragma once

#ifndef _SUPPLIERSTATEMENTDO_
#define _SUPPLIERSTATEMENTDO_

#include "../DoInclude.h"

class SupplierStatementBalanceDO : public BaseDO
{
	MYSQL_SYNTHESIZE(string, billName, BillName);
	MYSQL_SYNTHESIZE(double, balance, Balance);
public:
	SupplierStatementBalanceDO() : BaseDO("supplierStatementBalance")
	{
		MYSQL_ADD_FIELD("bill_name", "s", billName);
		MYSQL_ADD_FIELD("balance", "d", balance);
	}
};
class SupplierStatementDetailDO : public BaseDO
{
	MYSQL_SYNTHESIZE(string, name, Name);
	MYSQL_SYNTHESIZE(string, attr, Attr);
	MYSQL_SYNTHESIZE(string, unit, Unit);
	MYSQL_SYNTHESIZE(double, price, Price);
	MYSQL_SYNTHESIZE(double, nums, Nums);
	MYSQL_SYNTHESIZE(double, dsc, Dsc);
	MYSQL_SYNTHESIZE(double, total, Total);
	MYSQL_SYNTHESIZE(double, tat, Tat);
	MYSQL_SYNTHESIZE(double, tpt, Tpt);
public:
	SupplierStatementDetailDO(): BaseDO("supplierStatementDetail")
	{
		MYSQL_ADD_FIELD("name", "s", name);
		MYSQL_ADD_FIELD("attr", "s", attr);
		MYSQL_ADD_FIELD("unit", "s", unit);
		MYSQL_ADD_FIELD("price", "d", price);
		MYSQL_ADD_FIELD("nums", "d", nums);
		MYSQL_ADD_FIELD("dsc", "d", dsc);
		MYSQL_ADD_FIELD("total", "d", total);
		MYSQL_ADD_FIELD("tat", "d", tat);
		MYSQL_ADD_FIELD("tpt", "d", tpt);
	}
};

class SupplierStatementItemDO : public BaseDO
{
	MYSQL_SYNTHESIZE(string, id, Id);
	MYSQL_SYNTHESIZE(string, bill, Bill);
	MYSQL_SYNTHESIZE(string, billName, BillName);
	MYSQL_SYNTHESIZE(string, frame, Frame);
	MYSQL_SYNTHESIZE(string, time, Time);
	MYSQL_SYNTHESIZE(string, number, Number);
	MYSQL_SYNTHESIZE(double, total, Total);
	MYSQL_SYNTHESIZE(double, discount, Discount);
	MYSQL_SYNTHESIZE(double, actual, Actual);
	MYSQL_SYNTHESIZE(double, money, Money);
	MYSQL_SYNTHESIZE(string, data, Data);
public:
	SupplierStatementItemDO() : BaseDO("supplierStatementItem")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("bill", "s", bill);
		MYSQL_ADD_FIELD("bill_name", "s", billName);
		MYSQL_ADD_FIELD("frame", "s", frame);
		MYSQL_ADD_FIELD("time", "s", time);
		MYSQL_ADD_FIELD("number", "s", number);
		MYSQL_ADD_FIELD("total", "d", total);
		MYSQL_ADD_FIELD("discount", "d", discount);
		MYSQL_ADD_FIELD("actual", "d", actual);
		MYSQL_ADD_FIELD("money", "d", money);
		MYSQL_ADD_FIELD("data", "s", data);
	}
};

#endif // !_SUPPLIERSTATEMENTDO_
