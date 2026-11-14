#pragma once

#ifndef _SALES_ORDER_TRACKING_REPORT_MAPPER_
#define _SALES_ORDER_TRACKING_REPORT_MAPPER_

#include "Mapper.h"
#include "../../domain/do/sales_order_tracking_report/SalesOrderTrackingReportDO.h"

/**
 * 销售订单跟踪表字段匹配映射（与DO字段顺序、SQL查询字段顺序严格对齐）
 */
class SalesOrderTrackingReportMapper : public Mapper<SalesOrderTrackingReportViewDO>
{
public:
	SalesOrderTrackingReportViewDO mapper(ResultSet* resultSet) const override
	{
		SalesOrderTrackingReportViewDO data;
		data.setId(resultSet->getString(1));
		data.setFrame(resultSet->getString(2));
		data.setCustomer(resultSet->getString(3));
		data.setTime(resultSet->getString(4));
		data.setNumber(resultSet->getString(5));
		data.setGoods(resultSet->getString(6));
		data.setAttr(resultSet->getString(7));
		data.setWarehouse(resultSet->getString(8));
		data.setUnit(resultSet->getString(9));
		data.setPrice(resultSet->getDouble(10));
		data.setNums(resultSet->getDouble(11));
		data.setTotal(resultSet->getDouble(12));
		if (resultSet->getInt(13) == 0) data.setState("Unshipped");//未出库 ZH_WORDS_GETTER("sales_order_tracking_report.sor.state0")
		else if (resultSet->getInt(13) == 1) data.setState("Partially Shipped");//部分出库 ZH_WORDS_GETTER("sales_order_tracking_report.sor.state1")
		else if (resultSet->getInt(13) == 2) data.setState("Shipped");//已出库 ZH_WORDS_GETTER("sales_order_tracking_report.sor.state2")
		else data.setState("Closed");//关闭 ZH_WORDS_GETTER("sales_order_tracking_report.sor.state3")
		data.setUnshippedQuantity(resultSet->getDouble(14));
		data.setUnshippedAmount(resultSet->getDouble(15));
		data.setArrival(resultSet->getString(16));
		data.setData(resultSet->getString(17));
		/*data.setDiscount(resultSet->getDouble(18));
		data.setDsc(resultSet->getDouble(19));
		data.setTax(resultSet->getDouble(20));
		data.setTat(resultSet->getDouble(21));
		data.setTpt(resultSet->getDouble(22));*/
		return data;
	}
};

/**
 * 销售订单跟踪表字段匹配映射-创建智能指针对象
 */
class PtrSalesOrderTrackingReportMapper : public Mapper<PtrSalesOrderTrackingReportViewDO>
{
public:
	PtrSalesOrderTrackingReportViewDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<SalesOrderTrackingReportViewDO>();
		data->setId(resultSet->getString(1));
		data->setFrame(resultSet->getString(2));
		data->setCustomer(resultSet->getString(3));
		data->setTime(resultSet->getString(4));
		data->setNumber(resultSet->getString(5));
		data->setGoods(resultSet->getString(6));
		data->setAttr(resultSet->getString(7));
		data->setWarehouse(resultSet->getString(8));
		data->setUnit(resultSet->getString(9));
		data->setPrice(resultSet->getDouble(10));
		data->setNums(resultSet->getDouble(11));
		data->setTotal(resultSet->getDouble(12));
		if (resultSet->getInt(13) == 0) data->setState("未出库");
		else if (resultSet->getInt(13) == 1) data->setState("部分出库");
		else if (resultSet->getInt(13) == 2) data->setState("已出库");
		else data->setState("关闭");
		data->setUnshippedQuantity(resultSet->getDouble(14));
		data->setUnshippedAmount(resultSet->getDouble(15));
		data->setArrival(resultSet->getString(16));
		data->setData(resultSet->getString(17));
		/*data->setDiscount(resultSet->getDouble(18));
		data->setDsc(resultSet->getDouble(19));
		data->setTax(resultSet->getDouble(20));
		data->setTat(resultSet->getDouble(21));
		data->setTpt(resultSet->getDouble(22));*/
		return data;
	}
};

#endif // _SALES_ORDER_TRACKING_REPORT_MAPPER_