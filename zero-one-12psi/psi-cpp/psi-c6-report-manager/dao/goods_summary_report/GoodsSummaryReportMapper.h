#pragma once

/*
@author: WEI伦
@date: 2025/10/26
*/
#ifndef _GOODS_SUMMARY_REPORT_MAPPER_H_
#define _GOODS_SUMMARY_REPORT_MAPPER_H_

#include "Mapper.h"
#include "../../domain/do/goods_summary_report/GoodSummaryReportViewDO.h"

class GoodsSummaryReportMapper : public Mapper<PtrGoodSummaryReportViewDO>
{
public:
    PtrGoodSummaryReportViewDO mapper(ResultSet* resultSet) const override {
        PtrGoodSummaryReportViewDO res = std::make_shared<GoodsSummaryReportViewDO>();

        // 基本商品信息字段
        res->setName(resultSet->getString("name"));
        res->setWarehouse(resultSet->getString("warehouse"));
        res->setNumber(resultSet->getString("number"));
        res->setSpec(resultSet->getString("spec"));
        res->setUnit(resultSet->getString("unit"));



        // 期初数据字段
        res->setStateUct(resultSet->getDouble("state_uct"));
        res->setStateUns(resultSet->getInt64("state_uns"));
        res->setStateBct(resultSet->getDouble("state_bct"));

        // 采购单数据字段
        res->setBuyUct(resultSet->getDouble("buy_uct"));
        res->setBuyUns(resultSet->getInt64("buy_uns"));
        res->setBuyBct(resultSet->getDouble("buy_bct"));

        // 采购退货单据字段
        res->setBreUct(resultSet->getDouble("bre_uct"));
        res->setBreUns(resultSet->getInt64("bre_uns"));
        res->setBreBct(resultSet->getDouble("bre_bct"));

        // 销售单据字段
        res->setSellUct(resultSet->getDouble("sell_uct"));
        res->setSellUns(resultSet->getInt64("sell_uns"));
        res->setSellBct(resultSet->getDouble("sell_bct"));

        // 销售退货单据字段
        res->setSreUct(resultSet->getDouble("sre_uct"));
        res->setSreUns(resultSet->getInt64("sre_uns"));
        res->setSreBct(resultSet->getDouble("sre_bct"));

        // 调拨-出数据字段
        res->setSwapOutUct(resultSet->getDouble("swap_out_uct"));
        res->setSwapOutUns(resultSet->getInt64("swap_out_uns"));
        res->setSwapOutBct(resultSet->getDouble("swap_out_bct"));

        // 调拨-入数据字段
        res->setSwapEnterUct(resultSet->getDouble("swap_enter_uct"));
        res->setSwapEnterUns(resultSet->getInt64("swap_enter_uns"));
        res->setSwapEnterBct(resultSet->getDouble("swap_enter_bct"));

        // 其它入库数据字段
        res->setEntryUct(resultSet->getDouble("entry_uct"));
        res->setEntryUns(resultSet->getInt64("entry_uns"));
        res->setEntryBct(resultSet->getDouble("entry_bct"));

        // 其它出库数据字段
        res->setExtryUct(resultSet->getDouble("extry_uct"));
        res->setExtryUns(resultSet->getInt64("extry_uns"));
        res->setExtryBct(resultSet->getDouble("extry_bct"));


        // 汇总数据字段（需要字段计算）
        res->setSumUct(resultSet->getDouble("sum_uct"));
        res->setSumUns(resultSet->getInt64("sum_uns"));
        res->setSumBct(resultSet->getDouble("sum_bct"));


        return res;
    }
};

#endif // !_GOODS_SUMMARY_REPORT_MAPPER_H_
