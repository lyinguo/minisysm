#pragma once

#ifndef _PROCUREMENT_RANKING_REPORT_MAPPER_H_
#define _PROCUREMENT_RANKING_REPORT_MAPPER_H_

#include "Mapper.h"
#include "../../domain/do/procurement_ranking_report/ProcurementRankingReportDO.h"

class PtrGoodsDataMapper : public Mapper<PtrGoodsDataDO>
{
public:
	PtrGoodsDataDO mapper(ResultSet* resultSet) const override
    {
        auto data = std::make_shared<GoodsDataDO>();
		data->setId(resultSet->getString("id"));
		data->setName(resultSet->getString("name"));
		data->setNumber(resultSet->getString("number"));
		data->setSpec(resultSet->getString("spec"));
		data->setUnit(resultSet->getString("unit"));
        return data;
    }
};

class PtrRankingDataMapper : public Mapper<PtrRankingDataDO>
{
public:
	PtrRankingDataDO mapper(ResultSet* resultSet) const override
    {
        auto data = std::make_shared<RankingDataDO>();
		data->setGoods(resultSet->getString("goods"));
		data->setAttr(resultSet->getString("attr"));
		data->setNums(resultSet->getInt("nums"));
        return data;
    }
};

class PtrDetailDataMapper : public Mapper<PtrDetailDataDO>
{
public:
	PtrDetailDataDO mapper(ResultSet* resultSet) const override
    {
        auto data = std::make_shared<DetailDataDO>();
		data->setType(resultSet->getString("type"));
		data->setGoods(resultSet->getString("goods"));
		data->setAttr(resultSet->getString("attr"));
		data->setId(resultSet->getString("id"));
		data->setDsc(resultSet->getDouble("dsc"));
		data->setTat(resultSet->getDouble("tat"));
		data->setTpt(resultSet->getDouble("tpt"));
        return data;
    }
};

class PtrCostDataMapper : public Mapper<PtrCostDataDO>
{
public:
	PtrCostDataDO mapper(ResultSet* resultSet) const override
    {
        auto data = std::make_shared<CostDataDO>();
		data->setType(resultSet->getString("type"));
		data->setInfo(resultSet->getString("info"));
		data->setGoods(resultSet->getString("goods"));
		data->setNums(resultSet->getInt("nums"));
		data->setBct(resultSet->getDouble("bct"));
		data->setAttr(resultSet->getString("attr"));
        return data;
    }
};

#endif //_PROCUREMENT_RANKING_REPORT_WRAPPER_H_